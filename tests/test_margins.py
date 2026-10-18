"""Tests for the exploratory continuous safety-margin analysis (margins.py).

All tests use synthetic ledgers and synthetic raw episode records in temporary
directories: zero real HighwayEnv episodes are launched.
"""
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from safefliplab.margins import (EXPLORATORY_MARGIN_NOTE, load_margin_data,
                                 margin_quartet_rows, margin_summary)

LEDGER_COLUMNS = [
    "row_type", "episode_key", "run_id", "phase", "method", "master_seed",
    "anchor_id", "anchor_index", "repetition", "condition", "stream", "sim_seed",
    "exit_status", "ego_collision", "termination", "error_type",
    "started_utc", "ended_utc", "wall_time_s", "raw_path",
]


def _write_ledger(root: Path, rows: list[dict]) -> Path:
    runs = root / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    path = runs / "episode_ledger.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=LEDGER_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in LEDGER_COLUMNS})
    return path


def _write_raw(root: Path, rel_path: str, ttc: float, reward: float) -> str:
    p = root / "runs" / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "result": {
            "ego_collision": False,
            "goal_reached": True,
            "min_forward_ttc_sampled_s": ttc,
            "reward_sum": reward,
            "policy_steps": 75,
            "sim_time_s": 15.0,
            "trace_sha256_rounded_9dp": "x" * 64,
        }
    }), encoding="utf-8")
    return str(p)


def _outcome(root: Path, *, run_id: str, method: str, anchor_id: str,
             repetition: int, stream: str, condition: str, ttc: float,
             reward: float, raw_rel: str | None = None,
             master_seed: int = 20261011, phase: str = "pilot") -> dict:
    if raw_rel is None:
        raw_rel = f"{run_id}/anchor-{anchor_id.split('-')[-1]}_rep{repetition}_{condition}.json"
    raw_path = _write_raw(root, raw_rel, ttc, reward)
    return {
        "row_type": "outcome",
        "episode_key": f"{run_id}|{method}|{anchor_id}|{repetition}|{stream}|{condition}",
        "run_id": run_id, "phase": phase, "method": method,
        "master_seed": str(master_seed), "anchor_id": anchor_id,
        "anchor_index": "0", "repetition": str(repetition), "condition": condition,
        "stream": stream, "sim_seed": "123", "exit_status": "completed",
        "ego_collision": "0", "termination": "goal", "error_type": "",
        "started_utc": "", "ended_utc": "2026-10-12T00:00:01+00:00",
        "wall_time_s": "1.0", "raw_path": raw_path,
    }


def _quartet(root: Path, *, run_id: str, method: str, anchor_id: str,
             ttc: dict[str, float], repetition: int = 0, stream: str = "discovery",
             rewards: dict[str, float] | None = None,
             phase: str = "pilot") -> list[dict]:
    rewards = rewards or {c: 60.0 for c in ttc}
    rows = []
    for cond, t in ttc.items():
        rows.append(_outcome(root, run_id=run_id, method=method,
                             anchor_id=anchor_id, repetition=repetition,
                             stream=stream, condition=cond, ttc=t,
                             reward=rewards[cond], phase=phase))
    return rows


class TestMarginLoading(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_complete_quartet_yields_paired_deltas(self) -> None:
        rows = _quartet(self.root, run_id="r1", method="WideExplore",
                        anchor_id="anchor-0000",
                        ttc={"00": 1.4, "10": 0.9, "01": 1.0, "11": 0.95})
        _write_ledger(self.root, rows)
        data = load_margin_data(self.root, "pilot")
        self.assertTrue(data.has_data)
        self.assertEqual(len(data.quartets), 1)
        q = data.quartets[0]
        self.assertAlmostEqual(q.delta("min_forward_ttc_sampled_s", "11", "00"), -0.45)
        self.assertAlmostEqual(q.delta("min_forward_ttc_sampled_s", "10", "00"), -0.5)
        self.assertAlmostEqual(q.delta("min_forward_ttc_sampled_s", "01", "00"), -0.4)

    def test_incomplete_quartet_excluded_not_imputed(self) -> None:
        rows = _quartet(self.root, run_id="r1", method="WideExplore",
                        anchor_id="anchor-0000",
                        ttc={"00": 1.4, "10": 0.9, "01": 1.0})  # missing 11
        _write_ledger(self.root, rows)
        data = load_margin_data(self.root, "pilot")
        self.assertFalse(data.has_data)
        self.assertEqual(len(data.incomplete), 1)

    def test_missing_raw_file_counted_not_imputed(self) -> None:
        rows = _quartet(self.root, run_id="r1", method="WideExplore",
                        anchor_id="anchor-0000",
                        ttc={"00": 1.4, "10": 0.9, "01": 1.0, "11": 0.95})
        # Point one condition at a non-existent raw file
        for r in rows:
            if r["condition"] == "10":
                r["raw_path"] = str(self.root / "runs" / "does_not_exist.json")
        _write_ledger(self.root, rows)
        data = load_margin_data(self.root, "pilot")
        self.assertFalse(data.has_data)
        self.assertEqual(data.missing_raw, 1)

    def test_two_distinct_keys_are_two_quartets(self) -> None:
        # Two different isolation keys (different anchor) in two runs: 2 primary
        # quartets, no replays.
        rows = _quartet(self.root, run_id="r1", method="WideExplore",
                        anchor_id="anchor-0000",
                        ttc={"00": 1.4, "10": 0.9, "01": 1.0, "11": 0.95})
        rows += _quartet(self.root, run_id="r2", method="WideExplore",
                         anchor_id="anchor-0001",
                         ttc={"00": 1.4, "10": 0.9, "01": 1.0, "11": 0.95})
        _write_ledger(self.root, rows)
        data = load_margin_data(self.root, "pilot")
        self.assertEqual(len(data.quartets), 2)
        self.assertEqual(len(data.replays), 0)

    def test_same_key_second_run_is_replay_not_independent_evidence(self) -> None:
        # Same isolation key (seed, method, anchor, rep, stream) in two runs:
        # the earliest run is primary, the later one is a replay (excluded),
        # matching the primary-statistics rule in report.load_phase_data.
        rows = _quartet(self.root, run_id="r1", method="WideExplore",
                        anchor_id="anchor-0000",
                        ttc={"00": 1.4, "10": 0.9, "01": 1.0, "11": 0.95})
        rows += _quartet(self.root, run_id="r2", method="WideExplore",
                         anchor_id="anchor-0000",
                         ttc={"00": 1.4, "10": 0.9, "01": 1.0, "11": 0.95})
        _write_ledger(self.root, rows)
        data = load_margin_data(self.root, "pilot")
        self.assertEqual(len(data.quartets), 1)
        self.assertEqual(len(data.replays), 1)
        self.assertEqual(data.quartets[0].run_id, "r1")
        self.assertEqual(data.replays[0].run_id, "r2")
        s = margin_summary(data)
        self.assertEqual(s["WideExplore/discovery"]["n_quartets"], 1)

    def test_conditions_from_different_runs_never_mixed(self) -> None:
        # 00/10 in run r1, 01/11 in run r2: no complete quartet in any run
        rows = _quartet(self.root, run_id="r1", method="WideExplore",
                        anchor_id="anchor-0000",
                        ttc={"00": 1.4, "10": 0.9})
        rows += _quartet(self.root, run_id="r2", method="WideExplore",
                         anchor_id="anchor-0000",
                         ttc={"01": 1.0, "11": 0.95})
        _write_ledger(self.root, rows)
        data = load_margin_data(self.root, "pilot")
        self.assertFalse(data.has_data)
        self.assertEqual(len(data.incomplete), 2)

    def test_other_phase_rows_ignored(self) -> None:
        rows = _quartet(self.root, run_id="r1", method="WideExplore",
                        anchor_id="anchor-0000",
                        ttc={"00": 1.4, "10": 0.9, "01": 1.0, "11": 0.95},
                        phase="smoke")
        _write_ledger(self.root, rows)
        self.assertFalse(load_margin_data(self.root, "pilot").has_data)
        self.assertTrue(load_margin_data(self.root, "smoke").has_data)

    def test_no_ledger_returns_empty(self) -> None:
        data = load_margin_data(self.root, "pilot")
        self.assertFalse(data.has_data)
        self.assertEqual(data.quartets, [])
        self.assertEqual(data.missing_raw, 0)

    def test_unknown_phase_rejected(self) -> None:
        with self.assertRaises(ValueError):
            load_margin_data(self.root, "nope")


class TestMarginSummary(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_summary_groups_by_method_and_stream(self) -> None:
        rows = _quartet(self.root, run_id="r1", method="WideExplore",
                        anchor_id="anchor-0000",
                        ttc={"00": 1.4, "10": 0.9, "01": 1.0, "11": 0.95})
        rows += _quartet(self.root, run_id="r2", method="WideExplore",
                         anchor_id="anchor-0001",
                         ttc={"00": 2.0, "10": 1.5, "01": 1.8, "11": 1.6},
                         stream="audit")
        rows += _quartet(self.root, run_id="r3", method="VerifyFirst",
                         anchor_id="anchor-0000",
                         ttc={"00": 1.4, "10": 0.9, "01": 1.0, "11": 0.95})
        _write_ledger(self.root, rows)
        data = load_margin_data(self.root, "pilot")
        s = margin_summary(data)
        self.assertEqual(set(s), {"WideExplore/discovery", "WideExplore/audit",
                                  "VerifyFirst/discovery"})
        self.assertEqual(s["WideExplore/discovery"]["n_quartets"], 1)
        # WideExplore discovery has exactly one quartet (r1): -0.45
        self.assertAlmostEqual(
            s["WideExplore/discovery"]["d_min_forward_ttc_sampled_s_both"], -0.45)
        # WideExplore audit (r2): TTC(11)-TTC(00) = 1.6 - 2.0 = -0.4
        self.assertAlmostEqual(
            s["WideExplore/audit"]["d_min_forward_ttc_sampled_s_both"], -0.4)

    def test_quartet_rows_csv_shape(self) -> None:
        rows = _quartet(self.root, run_id="r1", method="WideExplore",
                        anchor_id="anchor-0000",
                        ttc={"00": 1.4, "10": 0.9, "01": 1.0, "11": 0.95})
        _write_ledger(self.root, rows)
        data = load_margin_data(self.root, "pilot")
        out = margin_quartet_rows(data)
        self.assertEqual(len(out), 1)
        self.assertIn("d_min_forward_ttc_sampled_s_both", out[0])
        self.assertIn("d_reward_sum_both", out[0])

    def test_note_marks_non_protocol(self) -> None:
        self.assertIn("不是冻结协议的指标", EXPLORATORY_MARGIN_NOTE)


class TestMarginReportIntegration(unittest.TestCase):
    """The report writer must include the exploratory section only with data."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_report_without_data_says_no_margin_numbers(self) -> None:
        from safefliplab.report import write_report

        _write_ledger(self.root, [])
        summary = write_report(self.root, "pilot")
        self.assertEqual(summary["status"], "NO DATA")
        text = (self.root / "reports" / "pilot_report.md").read_text(encoding="utf-8")
        self.assertIn("无真实数据", text)
        self.assertNotIn("探索性连续安全裕度分析（非协议指标）", text)

    def test_report_with_data_includes_margin_section(self) -> None:
        from safefliplab.report import write_report

        rows: list[dict] = []
        for i in range(3):
            rows += _quartet(self.root, run_id=f"r{i}", method="WideExplore",
                             anchor_id=f"anchor-{i:04d}",
                             ttc={"00": 1.4 + 0.1 * i, "10": 0.9, "01": 1.0,
                                  "11": 0.95})
        # audit stream for the same method so both blocks appear
        rows += _quartet(self.root, run_id="ra", method="WideExplore",
                         anchor_id="anchor-0000",
                         ttc={"00": 1.4, "10": 0.9, "01": 1.0, "11": 0.95},
                         stream="audit")
        _write_ledger(self.root, rows)
        summary = write_report(self.root, "pilot")
        self.assertEqual(summary["status"], "OK")
        text = (self.root / "reports" / "pilot_report.md").read_text(encoding="utf-8")
        self.assertIn("探索性连续安全裕度分析（非协议指标）", text)
        self.assertIn("ΔTTC(both) = TTC(11) − TTC(00)", text)
        self.assertIn("exploratory_margins", summary)
        self.assertTrue((self.root / "reports" / "pilot_margins.csv").is_file())


if __name__ == "__main__":
    unittest.main()

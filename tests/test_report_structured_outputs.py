"""§6 structured outputs: episodes / anchors / budget_summary / comparisons.

These tests run entirely on the FakeAdapter (no real simulation budget) and
pin the properties the protocol needs: a stable header, one row per billed
episode, launch-without-outcome reported as ``unknown`` (never as a safe 0),
counts that reconcile with the denominators, and empty templates (never
invented numbers) for a phase with no data.
"""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from safefliplab.experiments import run_smoke_phase
from safefliplab.ledger import EpisodeKey, EpisodeLedger
from safefliplab.methods import METHOD_VERIFY, METHOD_WIDE
from safefliplab.report import (ANCHOR_COLUMNS, BUDGET_COLUMNS,
                                COMPARISON_COLUMNS, EPISODE_COLUMNS,
                                load_phase_data, write_report,
                                write_structured_outputs)
from safefliplab.seeds import CONDITIONS, DEV_SEED
from tests.fakes import FakeAdapter


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


class TestStructuredOutputsWithRealLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        config_path = self.root / "dev.json"
        config_path.write_text(json.dumps({
            "dev_seed": DEV_SEED,
            "smoke": {"max_episodes": 24, "wide_discovery_anchors": 3,
                      "verify_stage1_anchors": 2, "determinism_replay": True},
        }), encoding="utf-8")
        run_smoke_phase(self.root, config_path, adapter=FakeAdapter())
        self.summary = write_report(self.root, "smoke")
        self.reports = self.root / "reports"

    def tearDown(self):
        self.tmp.cleanup()

    # -- episodes ---------------------------------------------------------
    def test_episodes_csv_header_and_row_count(self):
        header, rows = _read_csv(self.reports / "smoke_episodes.csv")
        self.assertEqual(header, EPISODE_COLUMNS)
        self.assertEqual(len(rows), 24)  # one row per billed episode

    def test_every_episode_is_billed_and_resolved(self):
        _, rows = _read_csv(self.reports / "smoke_episodes.csv")
        for row in rows:
            self.assertEqual(row["billed"], "1")
            self.assertEqual(row["result_recorded"], "1")
            self.assertEqual(row["exit_status"], "completed")
            self.assertIn(row["method"], (METHOD_WIDE, METHOD_VERIFY))
            self.assertIn(row["condition"], CONDITIONS)

    def test_episodes_jsonl_matches_csv(self):
        _, rows = _read_csv(self.reports / "smoke_episodes.csv")
        lines = [json.loads(line) for line in
                 (self.reports / "smoke_episodes.jsonl").read_text(
                     encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(lines), len(rows))
        self.assertEqual({r["episode_key"] for r in lines},
                         {r["episode_key"] for r in rows})

    # -- anchors ----------------------------------------------------------
    def test_anchor_denominator_and_rates_reconcile(self):
        header, rows = _read_csv(self.reports / "smoke_anchors.csv")
        self.assertEqual(header, ANCHOR_COLUMNS)
        self.assertTrue(rows)
        for row in rows:
            n = int(row["denominator"])
            self.assertEqual(n, int(row["n_complete_quartets"]))
            for cond in CONDITIONS:
                count = int(row[f"Y{cond}_count"])
                self.assertLessEqual(count, n)
                if n:
                    self.assertAlmostEqual(float(row[f"rate_{cond}"]),
                                           count / n, places=9)
                else:
                    self.assertEqual(row[f"rate_{cond}"], "")

    def test_anchors_cover_both_methods(self):
        _, rows = _read_csv(self.reports / "smoke_anchors.csv")
        self.assertEqual({r["method"] for r in rows}, {METHOD_WIDE, METHOD_VERIFY})

    # -- budget -----------------------------------------------------------
    def test_budget_summary_reports_the_phase_cap_and_unused_slots(self):
        header, rows = _read_csv(self.reports / "smoke_budget_summary.csv")
        self.assertEqual(header, BUDGET_COLUMNS)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["phase"], "smoke")
        self.assertEqual(int(row["cap"]), 24)
        self.assertEqual(int(row["launched"]), 24)
        self.assertEqual(int(row["completed"]), 24)
        self.assertEqual(int(row["unused_slots"]), 0)
        self.assertEqual(int(row["pending_or_unknown"]), 0)

    # -- comparisons ------------------------------------------------------
    def test_comparisons_marks_smoke_audit_as_not_computable(self):
        header, rows = _read_csv(self.reports / "smoke_comparisons.csv")
        self.assertEqual(header, COMPARISON_COLUMNS)
        audit = [r for r in rows if r["stream"] == "audit"]
        self.assertTrue(audit)
        for row in audit:
            self.assertEqual(row["metric_role"], "PROTOCOL_AUDIT")
            self.assertEqual(row["computable"], "0")
            self.assertEqual(row["contrast_verify_minus_wide"], "")
            self.assertEqual(row["meets_formal_anchor_requirement"], "0")

    def test_comparisons_discovery_row_is_labelled_exploratory(self):
        _, rows = _read_csv(self.reports / "smoke_comparisons.csv")
        disc = [r for r in rows if r["stream"] == "discovery"]
        self.assertTrue(disc)
        for row in disc:
            self.assertEqual(row["metric_role"], "EXPLORATORY_DISCOVERY")
            self.assertIn("NOT the protocol", row["note"])

    # -- summary wiring ---------------------------------------------------
    def test_summary_lists_every_structured_output(self):
        for key in ("episodes_csv", "episodes_jsonl", "anchors_csv",
                    "budget_summary_csv", "comparisons_csv"):
            self.assertIn(key, self.summary)
            self.assertTrue(Path(self.summary[key]).exists(), key)


class TestStructuredOutputsHandleDegenerateLedgers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_phase_without_data_yields_header_only_templates(self):
        data = load_phase_data(self.root, "formal")
        paths = write_structured_outputs(self.root, "formal", data)
        for key, columns in (("episodes_csv", EPISODE_COLUMNS),
                             ("anchors_csv", ANCHOR_COLUMNS),
                             ("budget_summary_csv", BUDGET_COLUMNS),
                             ("comparisons_csv", COMPARISON_COLUMNS)):
            header, rows = _read_csv(Path(paths[key]))
            self.assertEqual(header, columns, key)
            self.assertEqual(rows, [], key)
        self.assertEqual(
            (Path(paths["episodes_jsonl"]).read_text(encoding="utf-8")), "")

    def test_launch_without_outcome_is_unknown_and_still_billed(self):
        """A launch row with no outcome must surface as ``unknown`` (never 0)."""
        runs = self.root / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        ledger = EpisodeLedger(runs / "episode_ledger.csv")
        run_id = "pilot_WideExplore_20261011_20261012T000000000+0000_deadbeef"
        ledger.record_launch(
            EpisodeKey(run_id=run_id, anchor_id="anchor-0000", repetition=0,
                       condition="00"),
            run_id=run_id, phase="pilot", method=METHOD_WIDE, master_seed=DEV_SEED,
            anchor_id="anchor-0000", anchor_index=0, repetition=0, condition="00",
            sim_seed=12345, stream="discovery", budget_scope="pilot",
        )

        data = load_phase_data(self.root, "pilot")
        self.assertEqual(data.quartets, [])
        self.assertEqual(len(data.incomplete), 1)
        paths = write_structured_outputs(self.root, "pilot", data)

        _, rows = _read_csv(Path(paths["episodes_csv"]))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["exit_status"], "unknown")
        self.assertEqual(rows[0]["result_recorded"], "0")
        self.assertEqual(rows[0]["billed"], "1")
        self.assertEqual(rows[0]["ego_collision"], "")

        _, budget = _read_csv(Path(paths["budget_summary_csv"]))
        self.assertEqual(int(budget[0]["launched"]), 1)
        self.assertEqual(int(budget[0]["completed"]), 0)
        self.assertEqual(int(budget[0]["pending_or_unknown"]), 1)
        self.assertEqual(int(budget[0]["unused_slots"]), 239)

    def test_unknown_episode_never_becomes_a_safe_observation(self):
        """The incomplete anchor must not appear as a scored candidate."""
        runs = self.root / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        ledger = EpisodeLedger(runs / "episode_ledger.csv")
        run_id = "pilot_VerifyFirst_20261011_20261012T000000000+0000_feedface"
        ledger.record_launch(
            EpisodeKey(run_id=run_id, anchor_id="anchor-0003", repetition=0,
                       condition="11"),
            run_id=run_id, phase="pilot", method=METHOD_VERIFY,
            master_seed=DEV_SEED, anchor_id="anchor-0003", anchor_index=3,
            repetition=0, condition="11", sim_seed=999, stream="audit",
            budget_scope="pilot",
        )
        data = load_phase_data(self.root, "pilot")
        paths = write_structured_outputs(self.root, "pilot", data)
        _, anchors = _read_csv(Path(paths["anchors_csv"]))
        self.assertEqual(len(anchors), 1)
        row = anchors[0]
        self.assertEqual(row["n_complete_quartets"], "0")
        self.assertEqual(row["denominator"], "0")
        for cond in CONDITIONS:
            self.assertEqual(row[f"rate_{cond}"], "")
            self.assertEqual(row[f"Y{cond}_count"], "0")
        self.assertEqual(row["n_incomplete_quartets"], "1")


if __name__ == "__main__":
    unittest.main()

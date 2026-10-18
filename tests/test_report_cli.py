"""Report and CLI guard tests (no real episodes, no fabricated numbers)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from safefliplab.cli import main
from safefliplab.report import load_phase_data, write_report


class TestReportNoData(unittest.TestCase):
    def test_empty_phase_report_has_no_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = write_report(tmp, "pilot")
            self.assertEqual(summary["status"], "NO DATA")
            self.assertEqual(summary["complete_quartets"], 0)
            self.assertEqual(summary["figures"], {})
            text = (Path(tmp) / "reports" / "pilot_report.md").read_text(encoding="utf-8")
            self.assertIn("无真实数据", text)
            # no figure files produced
            figs = list((Path(tmp) / "reports" / "pilot").glob("*.png"))
            self.assertEqual(figs, [])


class TestReportWithData(unittest.TestCase):
    def test_report_from_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runs").mkdir(parents=True)
            ledger_path = root / "runs" / "episode_ledger.csv"
            from safefliplab.ledger import COLUMNS, EpisodeKey, EpisodeLedger

            ledger = EpisodeLedger(ledger_path)
            # one complete reverse quartet for WideExplore discovery
            ys = {"00": 0, "10": 0, "01": 0, "11": 1}
            for cond, y in ys.items():
                key = EpisodeKey(run_id="r1", anchor_id="anchor-0000", repetition=0, condition=cond)
                launch_row = ledger.record_launch(
                    key, run_id="r1", phase="pilot", method="WideExplore",
                    master_seed=20261011, anchor_id="anchor-0000", anchor_index=0,
                    repetition=0, condition=cond, sim_seed=42, stream="discovery")
                ledger.record_outcome(key, launch_row=launch_row, exit_status="completed",
                                      ego_collision=y,
                                      termination="collision" if y else "goal")
            # plus one independent audit quartet on the same anchor
            for cond, y in {"00": 1, "10": 0, "01": 0, "11": 0}.items():
                key = EpisodeKey(run_id="r2", anchor_id="anchor-0000", repetition=0, condition=cond)
                launch_row = ledger.record_launch(
                    key, run_id="r2", phase="pilot", method="WideExplore",
                    master_seed=20261011, anchor_id="anchor-0000", anchor_index=0,
                    repetition=0, condition=cond, sim_seed=99, stream="audit")
                ledger.record_outcome(key, launch_row=launch_row, exit_status="completed",
                                      ego_collision=y,
                                      termination="collision" if y else "goal")
            summary = write_report(root, "pilot")
            self.assertEqual(summary["status"], "OK")
            self.assertEqual(summary["complete_quartets"], 2)
            by = summary["by_method_stream"]["WideExplore/discovery"]
            self.assertEqual(by["mean_delta_both"], 1.0)
            self.assertEqual(by["reverse_pairs"], 1)
            by_audit = summary["by_method_stream"]["WideExplore/audit"]
            self.assertEqual(by_audit["mean_delta_both"], -1.0)
            self.assertEqual(by_audit["rescue_pairs"], 1)
            self.assertEqual(len(summary["figures"]), 3)
            data = load_phase_data(root, "pilot")
            self.assertTrue(data.has_data)
            self.assertEqual(data.launched, 8)
            self.assertEqual(data.completed, 8)


class TestCliGuards(unittest.TestCase):
    def test_formal_refused_without_confirm(self):
        code = main(["formal", "--max-episodes", "12800"])
        self.assertEqual(code, 2)

    def test_formal_refused_with_wrong_budget(self):
        code = main(["formal", "--confirm", "--max-episodes", "100"])
        self.assertEqual(code, 2)

    def test_formal_refused_with_both_flags_but_not_executed(self):
        # Even with the correct flags the formal driver must not run.
        # GH-2 (P1-01): the real experiments.run_formal_phase is mocked so this
        # unit test cannot leave a runs/ directory behind; the refusal is
        # simulated with the same exception type the real function raises.
        # The real zero-side-effect behaviour is covered by
        # tests/test_formal_no_side_effects.py.
        with mock.patch("safefliplab.experiments.run_formal_phase",
                        side_effect=RuntimeError("refused (mocked)")) as fake:
            code = main(["formal", "--confirm", "--max-episodes", "12800"])
        self.assertEqual(code, 2)
        fake.assert_called_once()

    def test_smoke_over_cap_refused(self):
        code = main(["smoke", "--max-episodes", "25"])
        self.assertEqual(code, 2)

    def test_pilot_over_cap_refused(self):
        code = main(["pilot", "--max-episodes", "241"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()

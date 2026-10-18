"""EpisodeLedger accounting tests (budget, failure billing, durability)."""
import tempfile
import unittest
from pathlib import Path

from safefliplab.ledger import (
    BudgetExhausted,
    EpisodeKey,
    EpisodeLedger,
    LEDGER_FILENAME,
    utc_now_iso,
)


class TestLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger_path = Path(self.tmp.name) / LEDGER_FILENAME
        self.ledger = EpisodeLedger(self.ledger_path)

    def tearDown(self):
        self.tmp.cleanup()

    def _key(self, run="r1", anchor="anchor-0000", rep=0, cond="00"):
        return EpisodeKey(run_id=run, anchor_id=anchor, repetition=rep, condition=cond)

    def _launch(self, cond="00", phase="smoke", method="WideExplore", run="r1"):
        key = self._key(run=run, cond=cond)
        row = self.ledger.record_launch(
            key, run_id=run, phase=phase, method=method, master_seed=20261011,
            anchor_id="anchor-0000", anchor_index=0, repetition=0, condition=cond,
            sim_seed=12345, stream="discovery")
        return key, row

    def test_launch_consumes_budget_even_without_outcome(self):
        self.assertEqual(self.ledger.launched_count("smoke"), 0)
        self._launch("00")
        self.assertEqual(self.ledger.launched_count("smoke"), 1)
        # no outcome row yet: still billed
        self.assertEqual(self.ledger.outcome_count("smoke", "completed"), 0)
        self.assertEqual(self.ledger.launched_count("smoke"), 1)

    def test_outcome_completed(self):
        key, row = self._launch("00")
        self.ledger.record_outcome(key, launch_row=row, exit_status="completed", ego_collision=1,
                                   termination="collision", wall_time_s=0.5)
        self.assertEqual(self.ledger.outcome_count("smoke", "completed"), 1)
        self.assertEqual(self.ledger.outcome_count("smoke", "error"), 0)

    def test_error_billed(self):
        key, row = self._launch("10")
        self.ledger.record_outcome(key, launch_row=row, exit_status="error", ego_collision=None,
                                   error_type="RuntimeError")
        self.assertEqual(self.ledger.launched_count("smoke"), 1)
        self.assertEqual(self.ledger.outcome_count("smoke", "error"), 1)
        self.assertEqual(self.ledger.outcome_count("smoke", "completed"), 0)

    def test_interrupted_billed(self):
        key, row = self._launch("01")
        self.ledger.record_outcome(key, launch_row=row, exit_status="interrupted", ego_collision=None,
                                   error_type="KeyboardInterrupt")
        self.assertEqual(self.ledger.launched_count("smoke"), 1)
        self.assertEqual(self.ledger.outcome_count("smoke", "interrupted"), 1)

    def test_budget_exhaustion(self):
        for i in range(3):
            key = self._key(run="r1", cond=f"0{i}")
            self.ledger.record_launch(
                key, run_id="r1", phase="pilot", method="WideExplore",
                master_seed=1, anchor_id="anchor-0000", anchor_index=0,
                repetition=0, condition=f"0{i}", sim_seed=1, stream="discovery")
        self.ledger.check_budget("pilot", 4)  # 3 used, 4 allowed
        with self.assertRaises(BudgetExhausted):
            self.ledger.check_budget("pilot", 3)  # 3 used, 3 allowed: no room
        with self.assertRaises(BudgetExhausted):
            self.ledger.check_budget("pilot", 2)

    def test_phases_are_independent(self):
        self._launch("00", phase="smoke")
        self._launch("00", phase="pilot")
        self._launch("00", phase="formal")
        self.assertEqual(self.ledger.launched_count("smoke"), 1)
        self.assertEqual(self.ledger.launched_count("pilot"), 1)
        self.assertEqual(self.ledger.launched_count("formal"), 1)

    def test_stream_recorded(self):
        self._launch("00")
        import csv

        with open(self.ledger_path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(rows[-1]["stream"], "discovery")
        self.assertEqual(rows[-1]["exit_status"], "pending")

    def test_duplicate_episode_keys_counted_once(self):
        """Re-launching the same episode_key must not double-count budget."""
        for _ in range(2):
            self._launch("00", run="r1")
        self.assertEqual(self.ledger.launched_count("smoke"), 1)

    def test_same_key_different_runs_counted_twice(self):
        self._launch("00", run="r1")
        self._launch("00", run="r2")
        self.assertEqual(self.ledger.launched_count("smoke"), 2)

    def test_persistence_across_instances(self):
        self._launch("00")
        reopened = EpisodeLedger(self.ledger_path)
        self.assertEqual(reopened.launched_count("smoke"), 1)

    def test_invalid_values_rejected(self):
        key, row = self._launch("00")
        with self.assertRaises(ValueError):
            self.ledger.record_outcome(key, launch_row=row, exit_status="weird", ego_collision=None)
        with self.assertRaises(ValueError):
            self.ledger.record_outcome(key, launch_row=row, exit_status="completed", ego_collision=2)
        with self.assertRaises(ValueError):
            self.ledger.record_outcome(key, launch_row=row, exit_status="completed", ego_collision=None)
        with self.assertRaises(ValueError):
            self.ledger.record_launch(
                key, run_id="r", phase="bogus", method="m", master_seed=1,
                anchor_id="a", anchor_index=0, repetition=0, condition="00",
                sim_seed=1, stream="discovery")
        with self.assertRaises(ValueError):
            self.ledger.record_launch(
                key, run_id="r", phase="smoke", method="m", master_seed=1,
                anchor_id="a", anchor_index=0, repetition=0, condition="00",
                sim_seed=1, stream="bogus")

    def test_utc_now_iso_format(self):
        value = utc_now_iso()
        self.assertRegex(value, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00$")


if __name__ == "__main__":
    unittest.main()

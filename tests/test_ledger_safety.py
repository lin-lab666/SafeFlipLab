"""Ledger safety & billing tests (no real episodes; FakeAdapter not even used).

Covers:
* fresh-ledger init writes a header only (no phantom empty data row);
* legacy activity ledger (with the pre-fix empty row) is read compatibly;
* the atomic reserve refuses duplicates before any simulator work;
* the budget cap is enforced per scope, so formal's 8 seeds stay independent;
* smoke/pilot resume re-opens the durable ledger to verify billing (no stale view).
"""
import json
import tempfile
import unittest
from pathlib import Path

from safefliplab.experiments import run_pilot_phase, run_smoke_phase
from safefliplab.ledger import (
    BudgetExhausted,
    DuplicateLaunch,
    EpisodeKey,
    EpisodeLedger,
    LedgerLockTimeout,
    _exclusive_file_lock,
)
from tests.fakes import FakeAdapter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEGACY_LEDGER = PROJECT_ROOT / "runs" / "episode_ledger.csv"


class TestFreshLedgerInit(unittest.TestCase):
    def test_fresh_ledger_has_header_only_no_empty_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs" / "episode_ledger.csv"
            ledger = EpisodeLedger(path)
            diag = ledger.diagnose()
            # Header-only: zero data rows (no phantom all-empty row).
            self.assertEqual(diag["total_rows"], 0)
            self.assertEqual(ledger.empty_data_rows(), 0)
            self.assertEqual(ledger.launched_count("formal"), 0)
            # The file exists and contains exactly one line (the header).
            self.assertTrue(path.exists())
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertIn("episode_key", lines[0])

    def test_legacy_activity_ledger_reads_compat(self):
        """The real project ledger must be read correctly and must NOT be modified
        by simply opening it. (This particular file happens to have 0 empty rows;
        the synthetic pre-fix test below covers the one-empty-row case.)"""
        if not LEGACY_LEDGER.exists():
            self.skipTest("legacy ledger not present in this checkout")
        size_before = LEGACY_LEDGER.stat().st_size
        ledger = EpisodeLedger(LEGACY_LEDGER)  # read-only use
        # Real counts are preserved.
        self.assertEqual(ledger.launched_count("smoke"), 24)
        self.assertEqual(ledger.launched_count("pilot"), 240)
        diag = ledger.diagnose()
        self.assertGreaterEqual(diag["launch_rows"], 24 + 240)
        # Opening must not rewrite the file.
        self.assertEqual(LEGACY_LEDGER.stat().st_size, size_before)

    def test_pre_fix_empty_row_ledger_reads_compat(self):
        """A ledger written by the pre-fix init (header + one all-empty data row)
        must be read compatibly: the empty row is ignored by all counters."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "episode_ledger.csv"
            # Simulate the pre-fix init: header + one phantom empty data row.
            with open(path, "w", newline="", encoding="utf-8") as fh:
                import csv as _csv
                w = _csv.DictWriter(fh, fieldnames=[
                    "row_type", "episode_key", "run_id", "phase", "method",
                    "master_seed", "anchor_id", "anchor_index", "repetition",
                    "condition", "stream", "sim_seed", "exit_status",
                    "ego_collision", "termination", "error_type", "started_utc",
                    "ended_utc", "wall_time_s", "raw_path", "budget_scope"])
                w.writeheader()
                w.writerow({c: "" for c in w.fieldnames})
            ledger = EpisodeLedger(path)
            self.assertEqual(ledger.empty_data_rows(), 1)
            self.assertEqual(ledger.diagnose()["total_rows"], 1)  # the empty row
            self.assertEqual(ledger.launched_count("smoke"), 0)
            # A real launch appended after the empty row is still counted.
            key = EpisodeKey(run_id="r1", anchor_id="anchor-0000", repetition=0, condition="00")
            ledger.record_launch(key, run_id="r1", phase="smoke", method="WideExplore",
                                master_seed=1, anchor_id="anchor-0000", anchor_index=0,
                                repetition=0, condition="00", sim_seed=1, stream="discovery")
            self.assertEqual(ledger.launched_count("smoke"), 1)
            self.assertEqual(ledger.empty_data_rows(), 1)  # unchanged


class TestAtomicReserve(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "episode_ledger.csv"
        self.ledger = EpisodeLedger(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def _launch(self, scope="formal", phase="formal", cond="00", run="r1"):
        key = EpisodeKey(run_id=run, anchor_id="anchor-0000", repetition=0, condition=cond)
        return self.ledger.reserve_launch(
            key, run_id=run, phase=phase, method="WideExplore", master_seed=1,
            anchor_id="anchor-0000", anchor_index=0, repetition=0, condition=cond,
            sim_seed=1, stream="discovery", max_episodes=800, budget_scope=scope)

    def test_reserve_rejects_duplicate_key_before_sim(self):
        self._launch()
        # Same episode_key launched again in the same scope -> refused, no billing.
        with self.assertRaises(DuplicateLaunch):
            self._launch()
        self.assertEqual(self.ledger.launched_count_scope("formal"), 1)
        self.assertEqual(self.ledger.launched_count("formal"), 1)

    def test_reserve_honors_per_scope_independence(self):
        """Scope A capped at 2 must not block scope B (formal's 8 seeds need this)."""
        for i in range(2):
            self.ledger.reserve_launch(
                EpisodeKey(run_id=f"a{i}", anchor_id="anchor-0000", repetition=0, condition="00"),
                run_id=f"a{i}", phase="formal", method="WideExplore", master_seed=1,
                anchor_id="anchor-0000", anchor_index=0, repetition=0, condition="00",
                sim_seed=1, stream="discovery", max_episodes=2, budget_scope="formal|WideExplore|1")
        # Scope A is now exhausted...
        with self.assertRaises(BudgetExhausted):
            self.ledger.reserve_launch(
                EpisodeKey(run_id="aX", anchor_id="anchor-0000", repetition=0, condition="00"),
                run_id="aX", phase="formal", method="WideExplore", master_seed=1,
                anchor_id="anchor-0000", anchor_index=0, repetition=0, condition="00",
                sim_seed=1, stream="discovery", max_episodes=2, budget_scope="formal|WideExplore|1")
        # ...but scope B (a different seed) is still open.
        self.ledger.reserve_launch(
            EpisodeKey(run_id="b0", anchor_id="anchor-0000", repetition=0, condition="00"),
            run_id="b0", phase="formal", method="WideExplore", master_seed=2,
            anchor_id="anchor-0000", anchor_index=0, repetition=0, condition="00",
            sim_seed=1, stream="discovery", max_episodes=2, budget_scope="formal|WideExplore|2")
        self.assertEqual(self.ledger.launched_count_scope("formal|WideExplore|2"), 1)

    def test_reserve_exhaustion_raises_within_scope(self):
        for i in range(800):
            self.ledger.reserve_launch(
                EpisodeKey(run_id=f"x{i}", anchor_id="anchor-0000", repetition=0, condition="00"),
                run_id=f"x{i}", phase="formal", method="WideExplore", master_seed=1,
                anchor_id="anchor-0000", anchor_index=0, repetition=0, condition="00",
                sim_seed=1, stream="discovery", max_episodes=800, budget_scope="formal|WideExplore|1")
        self.assertEqual(self.ledger.launched_count_scope("formal|WideExplore|1"), 800)
        with self.assertRaises(BudgetExhausted):
            self.ledger.reserve_launch(
                EpisodeKey(run_id="over", anchor_id="anchor-0000", repetition=0, condition="00"),
                run_id="over", phase="formal", method="WideExplore", master_seed=1,
                anchor_id="anchor-0000", anchor_index=0, repetition=0, condition="00",
                sim_seed=1, stream="discovery", max_episodes=800, budget_scope="formal|WideExplore|1")

    def test_record_launch_defaults_to_phase_scope(self):
        key = EpisodeKey(run_id="r1", anchor_id="anchor-0000", repetition=0, condition="00")
        self.ledger.record_launch(
            key, run_id="r1", phase="pilot", method="WideExplore", master_seed=1,
            anchor_id="anchor-0000", anchor_index=0, repetition=0, condition="00",
            sim_seed=1, stream="discovery")
        self.assertEqual(self.ledger.launched_count_scope("pilot"), 1)
        self.assertEqual(self.ledger.launched_count("pilot"), 1)


class TestResumeReopensLedger(unittest.TestCase):
    """Resume must verify billing against the durable ledger, not a stale in-memory
    view. These tests re-open the ledger after each phase to prove no double billing
    and that the simulator (FakeAdapter) is not re-invoked for completed work."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _smoke_config(self):
        path = self.root / "dev.json"
        path.write_text(json.dumps({
            "dev_seed": 20261011,
            "smoke": {"max_episodes": 24, "wide_discovery_anchors": 3,
                      "verify_stage1_anchors": 2, "determinism_replay": True},
        }), encoding="utf-8")
        return path

    def _pilot_config(self):
        path = self.root / "dev.json"
        path.write_text(json.dumps({
            "dev_seed": 20261011,
            "pilot": {"max_episodes": 240, "wide_discovery_anchors": 15,
                      "wide_nominees": 3, "audit_quartets_per_nominee": 5,
                      "verify_stage1_anchors": 6, "verify_selected": 3,
                      "verify_extra_quartets": 3},
        }), encoding="utf-8")
        return path

    def test_smoke_resume_reopens_ledger_and_no_repeat_calls(self):
        cfg = self._smoke_config()
        adapter = FakeAdapter()
        run_smoke_phase(self.root, cfg, adapter=adapter)
        first_calls = len(adapter.calls)
        self.assertEqual(first_calls, 24)
        # Re-open the ledger fresh (not the driver's in-memory view).
        ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")
        self.assertEqual(ledger.launched_count("smoke"), 24)
        # Resume: must bill nothing new and call the simulator nothing more.
        run_smoke_phase(self.root, cfg, adapter=adapter)
        self.assertEqual(ledger.launched_count("smoke"), 24)
        self.assertEqual(len(adapter.calls), first_calls)

    def test_pilot_resume_reopens_ledger_and_no_repeat_calls(self):
        cfg = self._pilot_config()
        adapter = FakeAdapter()
        run_pilot_phase(self.root, cfg, adapter=adapter)
        first_calls = len(adapter.calls)
        self.assertEqual(first_calls, 240)
        ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")
        self.assertEqual(ledger.launched_count("pilot"), 240)
        run_pilot_phase(self.root, cfg, adapter=adapter)
        self.assertEqual(ledger.launched_count("pilot"), 240)
        self.assertEqual(len(adapter.calls), first_calls)


if __name__ == "__main__":
    unittest.main()


class TestLockFileOpenIsRetried(unittest.TestCase):
    """Regression for a Windows cross-process defect (2026-10-16).

    The lock sidecar's ``os.open`` (and the parent ``mkdir``) used to sit
    *outside* the retry/deadline machinery, unlike the byte-range lock itself.
    On Windows another process creating or deleting the same sidecar can make
    that call fail transiently with a sharing violation, and the error escaped
    as an **uncaught** ``PermissionError`` — observed as a cross-process cap
    test worker exiting with empty stdout (so only 4 of 6 workers reported).

    These tests fail against the pre-fix implementation: the first would raise
    ``PermissionError`` instead of acquiring, the second would raise
    ``PermissionError`` instead of the handled ``LedgerLockTimeout``.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.lock_path = Path(self._tmp.name) / "sub" / "episode_ledger.csv.lock"

    def tearDown(self):
        self._tmp.cleanup()

    def test_transient_open_failure_is_retried_then_succeeds(self):
        import os as _os

        real_open = _os.open
        state = {"n": 0}

        def flaky(path, flags, *args, **kwargs):
            if str(path).endswith(".lock"):
                state["n"] += 1
                if state["n"] <= 2:          # transient, like a sharing violation
                    raise PermissionError(13, "simulated transient sharing violation")
            return real_open(path, flags, *args, **kwargs)

        _os.open = flaky
        try:
            with _exclusive_file_lock(self.lock_path, timeout_s=5.0):
                acquired = True
        finally:
            _os.open = real_open

        self.assertTrue(acquired)
        self.assertGreaterEqual(state["n"], 3, "must have retried the open")

    def test_persistent_open_failure_raises_lock_timeout_not_permissionerror(self):
        import os as _os

        real_open = _os.open
        state = {"n": 0}

        def always_fail(path, flags, *args, **kwargs):
            if str(path).endswith(".lock"):
                state["n"] += 1
                raise PermissionError(13, "persistent sharing violation")
            return real_open(path, flags, *args, **kwargs)

        _os.open = always_fail
        try:
            with self.assertRaises(LedgerLockTimeout):
                with _exclusive_file_lock(self.lock_path, timeout_s=0.2):
                    pass
        finally:
            _os.open = real_open

        self.assertGreater(state["n"], 1, "must have retried before giving up")

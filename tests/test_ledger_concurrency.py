"""Cross-instance and cross-process ledger budget safety (no real episodes).

Reproduces and locks down the defect where two independent ``EpisodeLedger``
instances (or two OS processes) sharing one CSV could each pass their own
budget check and both append a launch, overspending a scope capped at 1.

These tests only touch the ledger; no simulator is imported and no episode is
launched.
"""
import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from safefliplab.ledger import (
    BudgetExhausted,
    DuplicateLaunch,
    EpisodeKey,
    EpisodeLedger,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKER = PROJECT_ROOT / "tests" / "ledger_proc_worker.py"


def _reserve(ledger, tag, *, scope="race", cap=1):
    key = EpisodeKey(run_id=tag, anchor_id="anchor-0000", repetition=0, condition="00")
    return ledger.reserve_launch(
        key, run_id=tag, phase="formal", method="WideExplore", master_seed=1,
        anchor_id="anchor-0000", anchor_index=0, repetition=0, condition="00",
        sim_seed=1, stream="discovery", max_episodes=cap, budget_scope=scope)


def _launch_rows(path: Path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r["row_type"] == "launch"]


class TestMultiInstanceBudget(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "runs" / "episode_ledger.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def test_two_instances_cannot_both_reserve_at_cap_one(self):
        # Both instances are created up-front, so both cache an empty scope.
        a = EpisodeLedger(self.path)
        b = EpisodeLedger(self.path)
        _reserve(a, "A")  # first wins
        with self.assertRaises(BudgetExhausted):
            _reserve(b, "B")  # second must be refused, not silently accepted
        self.assertEqual(len(_launch_rows(self.path)), 1)

    def test_stale_instance_refuses_after_other_writes(self):
        a = EpisodeLedger(self.path)
        b = EpisodeLedger(self.path)  # opened before a writes anything
        _reserve(a, "A")
        # b's in-memory view is stale; reconciliation under the lock must still
        # see a's row and refuse.
        with self.assertRaises(BudgetExhausted):
            _reserve(b, "B")

    def test_duplicate_key_across_instances_refused(self):
        a = EpisodeLedger(self.path)
        b = EpisodeLedger(self.path)
        key = EpisodeKey(run_id="dup", anchor_id="anchor-0000", repetition=0, condition="00")
        a.reserve_launch(key, run_id="dup", phase="formal", method="WideExplore",
                         master_seed=1, anchor_id="anchor-0000", anchor_index=0,
                         repetition=0, condition="00", sim_seed=1, stream="discovery",
                         max_episodes=10, budget_scope="race")
        with self.assertRaises(DuplicateLaunch):
            b.reserve_launch(key, run_id="dup", phase="formal", method="WideExplore",
                             master_seed=1, anchor_id="anchor-0000", anchor_index=0,
                             repetition=0, condition="00", sim_seed=1, stream="discovery",
                             max_episodes=10, budget_scope="race")
        self.assertEqual(len(_launch_rows(self.path)), 1)

    def test_ledger_has_single_header_and_is_append_only(self):
        a = EpisodeLedger(self.path)
        b = EpisodeLedger(self.path)
        _reserve(a, "A")                       # scope "race", cap 1
        _reserve(b, "A2b", scope="other")      # a different scope is still open
        lines = self.path.read_text(encoding="utf-8").splitlines()
        header_lines = [ln for ln in lines if ln.startswith("row_type,")]
        self.assertEqual(len(header_lines), 1)  # header written exactly once
        self.assertEqual(len(_launch_rows(self.path)), 2)


class TestCrossProcessBudget(unittest.TestCase):
    def test_only_one_of_many_processes_can_reserve(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs" / "episode_ledger.csv"
            env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
            procs = [
                subprocess.Popen(
                    [sys.executable, str(WORKER), str(path), f"P{i}"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                for i in range(6)
            ]
            outputs = [p.communicate() for p in procs]
            oks = sum(1 for out, _ in outputs if out.strip() == "OK")
            refused = sum(1 for out, _ in outputs if out.strip() == "REFUSED")
            self.assertEqual(oks, 1, f"exactly one process must win; got {oks}: {outputs}")
            self.assertEqual(refused, 5, f"all others must be refused; got {refused}")
            self.assertEqual(len(_launch_rows(path)), 1)


LEGACY_HEADER = [
    "row_type", "episode_key", "run_id", "phase", "method", "master_seed",
    "anchor_id", "anchor_index", "repetition", "condition", "stream",
    "sim_seed", "exit_status", "ego_collision", "termination", "error_type",
    "started_utc", "ended_utc", "wall_time_s", "raw_path",
]


class TestLegacyHeaderScopeRoundTrip(unittest.TestCase):
    """A pre-``budget_scope`` ledger (header is a prefix of COLUMNS) must not
    silently demote scoped launches to phase scope when re-read.

    Without the reader-side mapping, a fresh instance sees
    ``launched_count_scope("formal|method|seed") == 0`` even though the scope
    value sits in the 21st CSV field, so a resumed formal run could re-spend
    a per-(method, seed) 800-episode budget.
    """

    def test_scoped_launch_survives_re_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs" / "episode_ledger.csv"
            path.parent.mkdir(parents=True)
            with open(path, "w", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerow(LEGACY_HEADER)
            scope = "formal|WideExplore|999"
            led = EpisodeLedger(path)
            key = EpisodeKey(run_id="probe", anchor_id="anchor-0000",
                             repetition=0, condition="00")
            led.reserve_launch(key, run_id="probe", phase="formal",
                               method="WideExplore", master_seed=999,
                               anchor_id="anchor-0000", anchor_index=0,
                               repetition=0, condition="00", sim_seed=5,
                               stream="discovery", max_episodes=800,
                               budget_scope=scope)
            self.assertEqual(led.launched_count_scope(scope), 1)
            # fresh instance (new process semantics): scope must round-trip
            led2 = EpisodeLedger(path)
            self.assertEqual(led2.launched_count_scope(scope), 1)
            self.assertEqual(led2.launched_count("formal"), 1)
            # and the cap is now actually enforced on re-read
            with self.assertRaises(BudgetExhausted):
                key2 = EpisodeKey(run_id="probe2", anchor_id="anchor-0001",
                                  repetition=0, condition="00")
                led2.reserve_launch(key2, run_id="probe2", phase="formal",
                                    method="WideExplore", master_seed=999,
                                    anchor_id="anchor-0001", anchor_index=1,
                                    repetition=0, condition="00", sim_seed=6,
                                    stream="discovery", max_episodes=1,
                                    budget_scope=scope)


if __name__ == "__main__":
    unittest.main()

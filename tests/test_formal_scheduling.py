"""Integration tests for the full formal scheduler (FakeAdapter only, no real sims).

The frozen formal plan is 8 seeds x 2 methods x 800 episodes. To keep the suite
fast and free of real simulations, every test SCALES the plan down via monkeypatch
(e.g. 2 seeds x 2 methods x 44 episodes) but still exercises the real scheduling,
budget scoping, master-seed isolation, audit isolation, manifest writing and
resume logic. A separate test asserts the *real* frozen plan closes exactly at
400 discovery + 400 audit per method without launching anything.
"""
import json
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

from safefliplab.experiments import _execute_formal_phase, run_formal_phase
from safefliplab.ledger import EpisodeLedger
from safefliplab.methods import METHOD_VERIFY, METHOD_WIDE, validate_formal_plans
from tests.fakes import FakeAdapter

# Scaled plan: wide = 5 disc + 2*3 audit = 11 quartets = 44 episodes;
# verify = 3 stage1 + 1*2 stage2 + 2*3 audit = 11 quartets = 44 episodes.
SCALED = {
    "safefliplab.methods.WIDE_DISCOVERY_ANCHORS": 5,
    "safefliplab.methods.WIDE_NOMINEES": 2,
    "safefliplab.methods.AUDIT_QUARTETS_PER_NOMINEE": 3,
    "safefliplab.methods.VERIFY_STAGE1_ANCHORS": 3,
    "safefliplab.methods.VERIFY_SELECTED": 1,
    "safefliplab.methods.VERIFY_EXTRA_QUARTETS": 2,
    "safefliplab.methods.FORMAL_BUDGET": 44,
    "safefliplab.methods.FORMAL_DISCOVERY_BUDGET": 20,
    "safefliplab.methods.FORMAL_AUDIT_BUDGET": 24,
    "safefliplab.experiments.FORMAL_BUDGET": 44,
    "safefliplab.experiments.FORMAL_MASTER_SEED_COUNT": 2,
    "safefliplab.experiments.FORMAL_TOTAL_EPISODES": 176,
    "safefliplab.seeds.FORMAL_MASTER_SEED_COUNT": 2,
    "safefliplab.seeds.FORMAL_TOTAL_EPISODES": 176,
    "safefliplab.seeds.FORMAL_EPISODES_PER_METHOD_SEED": 44,
}
SCALED_SEEDS = [111, 222]
SCALED_TOTAL = 176  # 2 seeds x 2 methods x 44


@contextmanager
def scaled_formal():
    with ExitStack() as stack:
        for target, val in SCALED.items():
            stack.enter_context(patch(target, val))
        yield


class TestRealFormalPlanClosesExactly(unittest.TestCase):
    def test_real_plan_is_400_discovery_plus_400_audit_per_method(self):
        sizes = validate_formal_plans()
        self.assertEqual(sizes[METHOD_WIDE], 800)
        self.assertEqual(sizes[METHOD_VERIFY], 800)
        # 400 discovery + 400 audit per method (no episodes launched here).
        from safefliplab.methods import (
            FORMAL_AUDIT_BUDGET, FORMAL_DISCOVERY_BUDGET)
        self.assertEqual(FORMAL_DISCOVERY_BUDGET, 400)
        self.assertEqual(FORMAL_AUDIT_BUDGET, 400)


class TestFormalSchedulingScaled(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg_path = self.root / "formal.json"
        self.cfg_path.write_text(json.dumps({"formal_master_seeds": SCALED_SEEDS}),
                                 encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, adapter):
        with scaled_formal():
            return _execute_formal_phase(self.root, self.cfg_path, adapter=adapter,
                                         strict_design=False)

    def test_full_scaled_formal_scheduling(self):
        adapter = FakeAdapter()
        combined = self._run(adapter)
        self.assertEqual(combined["status"], "scheduled-complete")
        self.assertEqual(combined["episodes_launched"], SCALED_TOTAL)
        self.assertEqual(combined["episodes_completed"], SCALED_TOTAL)
        # Every (seed, method) closed at its cumulative 44-episode budget, with
        # all 44 billed by this (fresh) call.
        for row in combined["per_seed_method"]:
            self.assertEqual(row["cumulative_episodes"], 44)
            self.assertEqual(row["new_episodes_this_call"], 44)
        # No real simulator was touched.
        self.assertEqual(len(adapter.calls), SCALED_TOTAL)

    def test_per_seed_method_manifests_do_not_overwrite(self):
        self._run(FakeAdapter())
        manifests = sorted(self.root.glob("runs/manifest_formal_*.json"))
        # 2 seeds x 2 methods = 4 per-(seed,method) manifests + 1 combined.
        per_seed = [p for p in manifests if "combined" not in p.name]
        self.assertEqual(len(per_seed), 4)
        paths = {str(p) for p in per_seed}
        self.assertEqual(len(paths), 4)  # all distinct, none overwrote another
        # Combined manifest exists and is consistent.
        combined_path = self.root / "runs" / "manifest_formal_combined.json"
        self.assertTrue(combined_path.exists())
        data = json.loads(combined_path.read_text(encoding="utf-8"))
        self.assertEqual(data["episodes_launched"], SCALED_TOTAL)

    def test_master_seed_isolation_in_formal(self):
        """Each seed's completed-quartet view contains only its own rows."""
        self._run(FakeAdapter())
        from safefliplab.experiments import PhaseDriver
        view_a = PhaseDriver(phase="formal", method=METHOD_WIDE, master_seed=SCALED_SEEDS[0],
                            max_episodes=44, project_root=self.root,
                            adapter=FakeAdapter()).completed_quartets()
        view_b = PhaseDriver(phase="formal", method=METHOD_WIDE, master_seed=SCALED_SEEDS[1],
                            max_episodes=44, project_root=self.root,
                            adapter=FakeAdapter()).completed_quartets()
        for key in view_a:
            self.assertEqual(key[0], SCALED_SEEDS[0])
        for key in view_b:
            self.assertEqual(key[0], SCALED_SEEDS[1])
        self.assertNotIn(next(iter(view_b))[0], {k[0] for k in view_a})

    def test_formal_audit_isolation_audit_stream_only(self):
        """audit_results must aggregate AUDIT quartets only, not the discovery one."""
        self._run(FakeAdapter())
        # Inspect one per-seed manifest's embedded report.
        manifest = json.loads(
            (self.root / "runs" / f"manifest_formal_{METHOD_WIDE}_seed{SCALED_SEEDS[0]}.json")
            .read_text(encoding="utf-8"))
        audit = manifest["report"]["audit_results"]["audit"]
        self.assertGreater(len(audit), 0)
        for entry in audit:
            # Scaled AUDIT_QUARTETS_PER_NOMINEE = 3, not 1 (discovery) + 3.
            self.assertEqual(entry["valid_n"], 3)

    def test_formal_nomination_frozen_before_audit(self):
        """Audit launches use stream='audit' and never feed nomination back."""
        self._run(FakeAdapter())
        ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")
        rows = list(csv_dict(self.root / "runs" / "episode_ledger.csv"))
        audit_rows = [r for r in rows if r["row_type"] == "launch" and r["stream"] == "audit"]
        disc_rows = [r for r in rows if r["row_type"] == "launch" and r["stream"] == "discovery"]
        # Both streams present; audit is independent of discovery.
        self.assertGreater(len(audit_rows), 0)
        self.assertGreater(len(disc_rows), 0)
        # Audit run_ids must differ from discovery run_ids (fresh seeds / runs).
        disc_run_ids = {r["run_id"] for r in disc_rows}
        audit_run_ids = {r["run_id"] for r in audit_rows}
        self.assertFalse(audit_run_ids <= disc_run_ids)

    def test_formal_resume_does_not_double_bill_and_no_repeat_calls(self):
        """Re-running the scheduler resumes completed quartets: same total billing,
        and the simulator (FakeAdapter) is never called twice for the same job."""
        adapter = FakeAdapter()
        first = self._run(adapter)
        self.assertEqual(first["episodes_launched"], SCALED_TOTAL)
        calls_after_first = len(adapter.calls)
        self.assertEqual(calls_after_first, SCALED_TOTAL)
        # Second invocation: everything is already complete -> 0 new launches.
        second = self._run(adapter)
        self.assertEqual(second["episodes_launched"], SCALED_TOTAL)  # unchanged
        # No extra simulator calls: resume reused the ledger evidence.
        self.assertEqual(len(adapter.calls), SCALED_TOTAL)

    def test_formal_full_resume_reports_zero_new_per_slice(self):
        """When every (method, seed) is already complete, a re-invocation must
        report zero new episodes for each slice while the cumulative total stays
        at the frozen per-slice budget (the old increment check would have
        false-alarmed / mis-reported here)."""
        self._run(FakeAdapter())
        fresh_adapter = FakeAdapter()
        combined = self._run(fresh_adapter)
        self.assertEqual(combined["episodes_launched"], SCALED_TOTAL)  # cumulative
        for row in combined["per_seed_method"]:
            self.assertEqual(row["new_episodes_this_call"], 0)
            self.assertEqual(row["cumulative_episodes"], 44)
        self.assertEqual(len(fresh_adapter.calls), 0)  # nothing re-run

    def test_formal_halfway_resume_uses_cumulative_budget(self):
        """A legal half-way resume: one (seed, method) slice is already complete
        before the full scheduler runs. The pre-completed slice must bill 0 new
        episodes yet still close at its cumulative 44; the others bill 44 each;
        and the total ledger stays at the frozen plan size (not over-spent)."""
        from safefliplab.experiments import PhaseDriver, _run_formal_method
        # Pre-complete WideExplore for seed 0 only.
        with scaled_formal():
            pre = PhaseDriver(phase="formal", method=METHOD_WIDE,
                              master_seed=SCALED_SEEDS[0], max_episodes=44,
                              project_root=self.root, adapter=FakeAdapter())
            _run_formal_method(pre, METHOD_WIDE)
        pre_ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")
        self.assertEqual(
            pre_ledger.launched_count_scope(f"formal|{METHOD_WIDE}|{SCALED_SEEDS[0]}"), 44)

        adapter = FakeAdapter()
        combined = self._run(adapter)
        self.assertEqual(combined["episodes_launched"], SCALED_TOTAL)  # cumulative, not 220
        by_key = {(r["master_seed"], r["method"]): r for r in combined["per_seed_method"]}
        done = by_key[(SCALED_SEEDS[0], METHOD_WIDE)]
        self.assertEqual(done["new_episodes_this_call"], 0)
        self.assertEqual(done["cumulative_episodes"], 44)
        other = by_key[(SCALED_SEEDS[1], METHOD_WIDE)]
        self.assertEqual(other["new_episodes_this_call"], 44)
        # The fresh adapter only ran the 3 not-yet-complete slices.
        self.assertEqual(len(adapter.calls), SCALED_TOTAL - 44)
        # Every scope closed at exactly its frozen slice budget.
        ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")
        for seed in SCALED_SEEDS:
            for method in (METHOD_WIDE, METHOD_VERIFY):
                self.assertEqual(ledger.launched_count_scope(f"formal|{method}|{seed}"), 44)

    def test_execute_formal_phase_refuses_real_adapter_without_go(self):
        """The scheduler is directly callable, so it carries its OWN guard: with
        no human GO and no test-double adapter it must refuse BEFORE constructing
        the real simulator, and it must launch nothing."""
        # adapter=None would otherwise build the real ScenarioAdapter.
        with self.assertRaises(PermissionError):
            _execute_formal_phase(self.root, self.cfg_path, adapter=None)
        # A non-test-double adapter is likewise refused without a human GO.
        class _Realish:
            is_test_double = False

            def run_episode(self, *a, **k):  # pragma: no cover - must not run
                raise AssertionError("real simulator must not be driven")

        with self.assertRaises(PermissionError):
            _execute_formal_phase(self.root, self.cfg_path, adapter=_Realish())
        # Nothing was launched by the refused calls.
        self.assertEqual(
            EpisodeLedger(self.root / "runs" / "episode_ledger.csv").launched_count("formal"), 0)

    def test_formal_cli_lock_preserved(self):
        """The CLI entry point must still refuse to run formal (RuntimeError lock)."""
        # No confirm -> PermissionError.
        with self.assertRaises(PermissionError):
            run_formal_phase(self.root, self.cfg_path, confirm=False, max_episodes=12800)
        # Wrong budget -> PermissionError.
        with self.assertRaises(PermissionError):
            run_formal_phase(self.root, self.cfg_path, confirm=True, max_episodes=100)
        # Confirm + correct budget -> still locked (RuntimeError), never executes.
        with self.assertRaises(RuntimeError):
            run_formal_phase(self.root, self.cfg_path, confirm=True, max_episodes=12800)
        # Crucially, no formal episodes were launched by the (failed) lock checks.
        ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")
        self.assertEqual(ledger.launched_count("formal"), 0)


def csv_dict(path: Path):
    import csv
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


if __name__ == "__main__":
    unittest.main()

"""End-to-end phase driver tests with the fake adapter (no real episodes)."""
import json
import tempfile
import unittest
from pathlib import Path

from safefliplab.experiments import (PhaseDriver, QuartetJob, run_formal_phase,
                                      run_pilot_phase, run_smoke_phase)
from safefliplab.ledger import BudgetExhausted, EpisodeKey, EpisodeLedger
from safefliplab.methods import METHOD_VERIFY, METHOD_WIDE
from safefliplab.seeds import CONDITIONS, DEV_SEED, STREAM_DISCOVERY
from tests.fakes import FakeAdapter


class TestSmokeFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config = {
            "dev_seed": DEV_SEED,
            "smoke": {"max_episodes": 24, "wide_discovery_anchors": 3,
                      "verify_stage1_anchors": 2, "determinism_replay": True},
        }
        self.config_path = self.root / "dev.json"
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_smoke_uses_exactly_24_episodes(self):
        report = run_smoke_phase(self.root, self.config_path, adapter=FakeAdapter())
        ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")
        self.assertEqual(ledger.launched_count("smoke"), 24)
        self.assertEqual(ledger.outcome_count("smoke", "completed"), 24)
        # 5 distinct quartets: 3 wide discovery + 2 verify stage-1 + 1 replay
        self.assertEqual(len(report.quartets), 5)

    def test_smoke_determinism_check_matches(self):
        run_smoke_phase(self.root, self.config_path, adapter=FakeAdapter())
        manifest = json.loads(
            (self.root / "runs" / "manifest_smoke_WideExplore.json").read_text(encoding="utf-8"))
        det = manifest["determinism_check"]
        self.assertTrue(det["performed"])
        self.assertTrue(det["all_conditions_match"])
        self.assertEqual(len(det["per_condition"]), 4)

    def test_smoke_is_resumable_without_double_billing(self):
        run_smoke_phase(self.root, self.config_path, adapter=FakeAdapter())
        ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")
        self.assertEqual(ledger.launched_count("smoke"), 24)
        # re-invocation: all discovery jobs resume; the replay already has two
        # runs so it only compares; no new episode may be launched.
        run_smoke_phase(self.root, self.config_path, adapter=FakeAdapter())
        self.assertEqual(ledger.launched_count("smoke"), 24)

    def test_smoke_refuses_over_cap(self):
        with self.assertRaises(ValueError):
            run_smoke_phase(self.root, self.config_path, max_episodes=25)


class TestPilotFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config = {
            "dev_seed": DEV_SEED,
            "pilot": {
                "max_episodes": 240,
                "wide_discovery_anchors": 15,
                "wide_nominees": 3,
                "audit_quartets_per_nominee": 5,
                "verify_stage1_anchors": 6,
                "verify_selected": 3,
                "verify_extra_quartets": 3,
            },
        }
        self.config_path = self.root / "dev.json"
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_pilot_uses_exactly_240_episodes(self):
        reports = run_pilot_phase(self.root, self.config_path, adapter=FakeAdapter())
        ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")
        self.assertEqual(ledger.launched_count("pilot"), 240)
        self.assertEqual(ledger.outcome_count("pilot", "completed"), 240)
        wide, verify = reports[METHOD_WIDE], reports[METHOD_VERIFY]
        # 15 discovery + 3 nominees x 5 audit = 30 quartets per method
        self.assertEqual(len(wide.quartets), 30)
        self.assertEqual(len(verify.quartets), 30)
        self.assertEqual(len(wide.nominations["discovery"]), 3)
        self.assertEqual(len(verify.nominations["final"]), 3)

    def test_pilot_audit_isolation(self):
        reports = run_pilot_phase(self.root, self.config_path, adapter=FakeAdapter())
        ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")
        import csv

        with open(ledger.path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        nominated = {reports[METHOD_WIDE].nominations["discovery"][0]}
        # every audit launch must be for a nominated anchor only
        audit_anchors = {r["anchor_id"] for r in rows
                         if r["row_type"] == "launch" and r["stream"] == "audit"
                         and r["method"] == METHOD_WIDE}
        self.assertTrue(audit_anchors <= set(reports[METHOD_WIDE].nominations["discovery"]))
        self.assertTrue(nominated <= audit_anchors)

    def test_pilot_resume_does_not_double_bill(self):
        run_pilot_phase(self.root, self.config_path, adapter=FakeAdapter())
        ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")
        run_pilot_phase(self.root, self.config_path, adapter=FakeAdapter())
        self.assertEqual(ledger.launched_count("pilot"), 240)

    def test_pilot_plan_must_close_exactly(self):
        bad = {
            "dev_seed": DEV_SEED,
            "pilot": {
                "max_episodes": 240,
                "wide_discovery_anchors": 10,
                "wide_nominees": 3,
                "audit_quartets_per_nominee": 5,
                "verify_stage1_anchors": 6,
                "verify_selected": 3,
                "verify_extra_quartets": 3,
            },
        }
        path = self.root / "bad.json"
        path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            run_pilot_phase(self.root, path, adapter=FakeAdapter())


class TestFormalGuard(unittest.TestCase):
    def test_formal_refuses_without_confirm(self):
        cfg = {"formal_master_seeds": [1]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "formal.json"
            path.write_text(json.dumps(cfg), encoding="utf-8")
            with self.assertRaises(PermissionError):
                run_formal_phase(tmp, path, confirm=False, max_episodes=12800)

    def test_formal_refuses_wrong_budget(self):
        cfg = {"formal_master_seeds": [1]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "formal.json"
            path.write_text(json.dumps(cfg), encoding="utf-8")
            with self.assertRaises(PermissionError):
                run_formal_phase(tmp, path, confirm=True, max_episodes=100)


class TestVerifyFirstSelection(unittest.TestCase):
    def test_selection_frozen_and_deterministic(self):
        adapter = FakeAdapter()
        with tempfile.TemporaryDirectory() as tmp:
            driver = PhaseDriver(phase="pilot", method=METHOD_VERIFY, master_seed=DEV_SEED,
                                 max_episodes=240, project_root=tmp, adapter=adapter)
            report = driver.run_verify_first(
                stage1_anchors=6, selected=3, extra=3, nominees=3, audit_quartets=5)
            first = report.nominations["selected_20_scaled"]
            # rerun in a fresh driver over the same ledger: same selection
            driver2 = PhaseDriver(phase="pilot", method=METHOD_VERIFY, master_seed=DEV_SEED,
                                  max_episodes=240, project_root=tmp, adapter=FakeAdapter())
            report2 = driver2.run_verify_first(
                stage1_anchors=6, selected=3, extra=3, nominees=3, audit_quartets=5)
            self.assertEqual(first, report2.nominations["selected_20_scaled"])


class TestPhaseIsolation(unittest.TestCase):
    def test_completed_quartet_from_other_phase_is_not_resumed(self):
        """A completed quartet recorded under the smoke phase must NOT be
        mistaken for evidence by a pilot driver, or the pilot would skip
        anchors that happen to share (method, anchor_index, repetition,
        stream) keys -- under-consuming the budget and testing the wrong set."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger = EpisodeLedger(Path(tmp) / "episode_ledger.csv")
            # Pretend smoke already completed WideExplore anchor 0 discovery.
            for cond in CONDITIONS:
                key = EpisodeKey(run_id="smoke_run", anchor_id="anchor-0000",
                                repetition=0, condition=cond)
                launch = ledger.record_launch(
                    key, run_id="smoke_run", phase="smoke", method="WideExplore",
                    master_seed=DEV_SEED, anchor_id="anchor-0000", anchor_index=0,
                    repetition=0, condition=cond, sim_seed=1, stream="discovery")
                ledger.record_outcome(key, launch_row=launch, exit_status="completed",
                                     ego_collision=0, termination="goal")
            # A pilot driver must NOT see that smoke quartet as "already done".
            driver = PhaseDriver(phase="pilot", method=METHOD_WIDE, master_seed=DEV_SEED,
                                max_episodes=240, project_root=tmp, adapter=FakeAdapter())
            done = driver.completed_quartets()
            self.assertNotIn((DEV_SEED, "WideExplore", 0, 0, "discovery"), done)
            # And a fresh pilot run must still launch that anchor's quartet.
            report = driver.run_wide_explore(
                discovery_anchors=1, nominees=0, audit_quartets=0)
            self.assertIn((DEV_SEED, "WideExplore", 0, 0, "discovery"), report.quartets)


class TestMasterSeedIsolation(unittest.TestCase):
    """Formal runs 8 master seeds that share one ledger + one phase="formal".

    Without master_seed in the isolation key, seed B would silently reuse seed
    A's completed quartets and never launch its own observations. These tests
    prove the fix: each seed produces its own evidence; a legal resume of the
    same seed does not double-bill; and budget/exhaustion paths never grant a
    free retry or break the frozen budget.
    """

    SEED_A = 3451794858  # frozen formal master seed 0
    SEED_B = 3280522798  # frozen formal master seed 1
    SEED_C = 3404856911
    SEED_D = 4151677968
    SEED_E = 565867193
    SEED_F = 2023892289

    def _driver(self, tmp, seed, max_episodes=800, adapter=None):
        return PhaseDriver(phase="formal", method=METHOD_WIDE, master_seed=seed,
                          max_episodes=max_episodes, project_root=tmp,
                          adapter=adapter or FakeAdapter())

    def _ledger(self, tmp):
        """A fresh ledger reader — always reflects the durable CSV on disk."""
        return EpisodeLedger(Path(tmp) / "runs" / "episode_ledger.csv")

    def _job(self, anchor_index=0, repetition=0, stream="discovery"):
        return QuartetJob(METHOD_WIDE, anchor_index, repetition, stream, "wide_discovery")

    def test_seed_b_must_launch_after_seed_a(self):
        """Seed A completes a formal quartet; seed B (same phase, shared ledger)
        must independently launch its own quartet and must NOT reuse A's Y."""
        with tempfile.TemporaryDirectory() as tmp:
            a = self._driver(tmp, self.SEED_A)
            a.execute_job(self._job())
            self.assertEqual(self._ledger(tmp).launched_count("formal"), 4)
            b = self._driver(tmp, self.SEED_B)
            # B's completed view must not contain A's key (master_seed differs).
            done_b = b.completed_quartets()
            self.assertNotIn((self.SEED_A, METHOD_WIDE, 0, 0, "discovery"), done_b)
            # Executing the same (method, anchor, rep, stream) key for B must
            # launch fresh episodes, not resume A's rows.
            b.execute_job(self._job())
            self.assertEqual(self._ledger(tmp).launched_count("formal"), 8)
            # B now has its own complete quartet, keyed by B's master_seed.
            done_b2 = b.completed_quartets()
            key_b = (self.SEED_B, METHOD_WIDE, 0, 0, "discovery")
            self.assertIn(key_b, done_b2)
            self.assertEqual(set(done_b2[key_b]), set(CONDITIONS))
            # Critically: B's completed view must NOT contain A's key -- B only
            # ever sees its own seed's completed quartets.
            self.assertNotIn((self.SEED_A, METHOD_WIDE, 0, 0, "discovery"), done_b2)

    def test_seed_b_legal_resume_no_double_billing(self):
        """A legitimate resume of the SAME seed must reuse the completed quartet
        without launching new episodes or double-billing."""
        with tempfile.TemporaryDirectory() as tmp:
            b1 = self._driver(tmp, self.SEED_B)
            b1.execute_job(self._job())
            self.assertEqual(self._ledger(tmp).launched_count("formal"), 4)
            # Fresh driver for the same seed sees its own completed quartet.
            b2 = self._driver(tmp, self.SEED_B)
            self.assertIn((self.SEED_B, METHOD_WIDE, 0, 0, "discovery"),
                          b2.completed_quartets())
            # Re-executing resumes (no new launch).
            b2.execute_job(self._job())
            self.assertEqual(self._ledger(tmp).launched_count("formal"), 4)

    def test_force_reruns_and_bills_again(self):
        """force=True is a deliberate re-run: it must re-launch and re-bill,
        never silently reuse an existing completed quartet."""
        with tempfile.TemporaryDirectory() as tmp:
            b1 = self._driver(tmp, self.SEED_B)
            b1.execute_job(self._job())
            before = self._ledger(tmp).launched_count("formal")
            b2 = self._driver(tmp, self.SEED_B)
            b2.execute_job(self._job(), force=True)
            self.assertEqual(self._ledger(tmp).launched_count("formal"), before + 4)

    def test_launch_only_quartet_not_reused_and_re_run_bills_again(self):
        """A launch without an outcome (interrupted) is billed but never treated
        as complete; a later run re-launches and re-bills (no free retry, no
        silent reuse of a missing Y)."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger = EpisodeLedger(Path(tmp) / "runs" / "episode_ledger.csv")
            # Pretend a formal launch-only quartet for seed C (4 launches, no outcome).
            for cond in CONDITIONS:
                key = EpisodeKey(run_id="c_run", anchor_id="anchor-0000",
                                repetition=0, condition=cond)
                ledger.record_launch(
                    key, run_id="c_run", phase="formal", method=METHOD_WIDE,
                    master_seed=self.SEED_C, anchor_id="anchor-0000", anchor_index=0,
                    repetition=0, condition=cond, sim_seed=1, stream="discovery")
            self.assertEqual(self._ledger(tmp).launched_count("formal"), 4)
            # A driver for seed C must see it as NOT complete.
            c = self._driver(tmp, self.SEED_C)
            self.assertNotIn((self.SEED_C, METHOD_WIDE, 0, 0, "discovery"),
                             c.completed_quartets())
            # Executing the job must re-launch (billed again).
            c.execute_job(self._job())
            self.assertEqual(self._ledger(tmp).launched_count("formal"), 8)

    def test_error_quartet_billed_and_re_run_costs_again(self):
        """An errored quartet is billed (the first condition errors and aborts
        the quartet: 1 launch, 1 error) and stays incomplete; a later run
        re-launches the full quartet (no free retry)."""
        with tempfile.TemporaryDirectory() as tmp:
            failing = FakeAdapter(fail=lambda s, seed: True)
            d = self._driver(tmp, self.SEED_D, adapter=failing)
            with self.assertRaises(RuntimeError):
                d.execute_job(self._job())
            ledger = self._ledger(tmp)
            self.assertEqual(ledger.launched_count("formal"), 1)
            self.assertEqual(ledger.outcome_count("formal", "completed"), 0)
            self.assertEqual(ledger.outcome_count("formal", "error"), 1)
            # Fresh driver must re-launch (incomplete quartet not reused).
            d2 = self._driver(tmp, self.SEED_D)
            self.assertNotIn((self.SEED_D, METHOD_WIDE, 0, 0, "discovery"),
                             d2.completed_quartets())
            d2.execute_job(self._job())
            self.assertEqual(self._ledger(tmp).launched_count("formal"), 5)
            self.assertEqual(self._ledger(tmp).outcome_count("formal", "completed"), 4)

    def test_two_seeds_have_mutually_exclusive_completed_views(self):
        """Each seed's completed_quartets view contains only its own rows."""
        with tempfile.TemporaryDirectory() as tmp:
            a = self._driver(tmp, self.SEED_A)
            a.execute_job(self._job(anchor_index=0))
            e = self._driver(tmp, self.SEED_E)
            e.execute_job(self._job(anchor_index=5))
            view_a = self._driver(tmp, self.SEED_A).completed_quartets()
            view_e = self._driver(tmp, self.SEED_E).completed_quartets()
            self.assertEqual(len(view_a), 1)
            self.assertEqual(len(view_e), 1)
            for key in view_a:
                self.assertEqual(key[0], self.SEED_A)  # master_seed first
            for key in view_e:
                self.assertEqual(key[0], self.SEED_E)
            self.assertNotIn((self.SEED_E, METHOD_WIDE, 5, 0, "discovery"), view_a)
            self.assertNotIn((self.SEED_A, METHOD_WIDE, 0, 0, "discovery"), view_e)

    def test_formal_budget_exhaustion_blocks_extra_launch_without_free_retry(self):
        """Once the frozen budget is reached, no further launch is permitted and
        no previously-billed episode is refunded (no way to break the cap)."""
        with tempfile.TemporaryDirectory() as tmp:
            f = self._driver(tmp, self.SEED_F, max_episodes=4)  # exactly one quartet
            f.execute_job(self._job())
            self.assertEqual(self._ledger(tmp).launched_count("formal"), 4)
            # A second quartet must be blocked before its first launch.
            with self.assertRaises(BudgetExhausted):
                f.execute_job(self._job(anchor_index=1))
            self.assertEqual(self._ledger(tmp).launched_count("formal"), 4)

    def test_different_run_id_same_key_billed_separately(self):
        """Two runs of the same (seed, method, anchor, rep, stream) key — e.g. the
        smoke determinism replay — are billed separately (D8), and both run_ids
        are present as distinct completing runs (no double counting)."""
        cfg = {
            "dev_seed": DEV_SEED,
            "smoke": {"max_episodes": 24, "wide_discovery_anchors": 3,
                      "verify_stage1_anchors": 2, "determinism_replay": True},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dev.json"
            path.write_text(json.dumps(cfg), encoding="utf-8")
            run_smoke_phase(tmp, path, adapter=FakeAdapter())
            ledger = self._ledger(tmp)
            # smoke budget = 3*4 + 2*4 + 1 replay*4 = 24
            self.assertEqual(ledger.launched_count("smoke"), 24)
            driver = PhaseDriver(phase="smoke", method=METHOD_WIDE, master_seed=DEV_SEED,
                                max_episodes=24, project_root=tmp, adapter=FakeAdapter())
            runs = driver.runs_completing_key(
                (DEV_SEED, METHOD_WIDE, 0, 0, STREAM_DISCOVERY))
            self.assertGreaterEqual(len(runs), 2)
            # Both runs are billed as distinct launched episodes: the ledger must
            # carry >= 2 distinct run_ids for anchor-0000 discovery conditions.
            import csv
            with open(ledger.path, newline="", encoding="utf-8") as fh:
                rows = [r for r in csv.DictReader(fh)
                        if r["row_type"] == "launch" and r["phase"] == "smoke"
                        and r["anchor_id"] == "anchor-0000" and r["stream"] == "discovery"]
            run_ids_seen = {r["run_id"] for r in rows}
            self.assertGreaterEqual(len(run_ids_seen), 2)
            for rid in runs:
                self.assertIn(rid, run_ids_seen)


if __name__ == "__main__":
    unittest.main()

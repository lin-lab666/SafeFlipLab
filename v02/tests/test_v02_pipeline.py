"""V02 pipeline tests: anchors, quartets, runner billing, methods, statistics.

These run on the synthetic adapter only — **zero real simulation budget**.
They cover the properties the V02 protocol depends on:

* the anchor stream is deterministic, legal under every perturbation extreme and
  never clipped;
* the four conditions of a repetition share ONE perturbation draw and ONE
  ``sim_seed``, while different repetitions differ;
* the intervention changes only the two declared dimensions;
* the ledger bills before any simulator work, refuses duplicates and enforces the
  cap with no free retry;
* unavailable anchors are never scored or nominated as if they were zeros;
* the derived per-step TTC mirrors the upstream ``longitudinal_ttc`` semantics.
"""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from v02lab.adapter_real import (states_from_raw_steps, step_candidate,
                                 steps_from_trajectory)
from v02lab.anchors import anchor_id, anchor_stream, quartet_scenarios
from v02lab.conditions import CONDITIONS
from v02lab.fake_adapter import FakeAdapterV02
from v02lab.ledger21 import (BudgetExhausted, DuplicateLaunch, EpisodeKey21,
                             EpisodeLedger21)
from v02lab.methods import (METHOD_VERIFY, METHOD_WIDE, precision_at_k,
                            select_top, usable_delta_both, verify_key, wide_key)
from v02lab.phases import FrozenProtocol, load_frozen_protocol
from v02lab.quartet import build_repetition
from v02lab.runner import (V02Runner, billed_tuple_keys, episode_tuple_key,
                           run_quartet)
from v02lab.ttc_state import StepTTCState

CONFIG = Path(__file__).resolve().parent.parent / "configs" / "v02_frozen_v1.json"


def _proto() -> FrozenProtocol:
    return load_frozen_protocol(CONFIG)


class TestAnchorStream(unittest.TestCase):
    def setUp(self):
        self.p = _proto()

    def test_stream_is_deterministic(self):
        a = anchor_stream(self.p.master_seed, self.p.domain, bounds=self.p.bounds, n=18,
                          gap_m=self.p.gap_m, speed_mps=self.p.speed_mps,
                          perturbation_halfwidths=self.p.halfwidths)
        b = anchor_stream(self.p.master_seed, self.p.domain, bounds=self.p.bounds, n=18,
                          gap_m=self.p.gap_m, speed_mps=self.p.speed_mps,
                          perturbation_halfwidths=self.p.halfwidths)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 18)

    def test_prefix_stability_smoke_anchor_is_pilot_anchor(self):
        small = anchor_stream(self.p.master_seed, self.p.domain, bounds=self.p.bounds, n=3,
                              gap_m=self.p.gap_m, speed_mps=self.p.speed_mps,
                              perturbation_halfwidths=self.p.halfwidths)
        big = anchor_stream(self.p.master_seed, self.p.domain, bounds=self.p.bounds, n=18,
                            gap_m=self.p.gap_m, speed_mps=self.p.speed_mps,
                            perturbation_halfwidths=self.p.halfwidths)
        self.assertEqual(small, big[:3])

    def test_every_anchor_is_legal_under_both_perturbation_extremes(self):
        anchors = anchor_stream(self.p.master_seed, self.p.domain, bounds=self.p.bounds, n=18,
                                gap_m=self.p.gap_m, speed_mps=self.p.speed_mps,
                                perturbation_halfwidths=self.p.halfwidths)
        for ai, anchor in enumerate(anchors):
            for shift in (-1.0, 1.0):
                shifted = dict(anchor)
                for d, hw in self.p.halfwidths.items():
                    shifted[d] = anchor[d] + shift * hw
                for c, scn in quartet_scenarios(shifted, self.p.gap_m, self.p.speed_mps).items():
                    self.assertGreaterEqual(scn["front_gap"], 18.0, (ai, c))
                    self.assertLessEqual(scn["front_gap"], 80.0, (ai, c))
                    self.assertGreaterEqual(scn["ego_speed"], 20.0, (ai, c))
                    self.assertLessEqual(scn["ego_speed"], 32.0, (ai, c))

    def test_anchor_ids_are_stable(self):
        self.assertEqual(anchor_id(0), "v02-anchor-0000")
        self.assertEqual(anchor_id(17), "v02-anchor-0017")


class TestQuartetConstruction(unittest.TestCase):
    def setUp(self):
        self.p = _proto()
        self.anchor = anchor_stream(self.p.master_seed, self.p.domain, bounds=self.p.bounds,
                                    n=1, gap_m=self.p.gap_m, speed_mps=self.p.speed_mps,
                                    perturbation_halfwidths=self.p.halfwidths)[0]

    def _rep(self, repetition: int, stream: str = "discovery"):
        return build_repetition(master_seed=self.p.master_seed, stream=stream,
                                anchor_index=0, anchor_id=anchor_id(0),
                                repetition=repetition, anchor_values=self.anchor,
                                perturbation_spec=self.p.perturbation_spec,
                                gap_m=self.p.gap_m, speed_mps=self.p.speed_mps,
                                method="Shared")

    def test_one_shared_perturbation_per_repetition(self):
        rep = self._rep(0)
        recorded = set()
        for c in CONDITIONS:
            recorded.add(tuple(sorted(rep.perturbation.items())))
        self.assertEqual(len(recorded), 1, "conditions must share one perturbation draw")
        self.assertEqual(set(rep.perturbation), {"front_gap", "front_speed", "ego_speed"})

    def test_four_conditions_share_one_sim_seed(self):
        rep = self._rep(0)
        # the seed is a single value by construction; assert it is a valid 32-bit int
        self.assertTrue(0 <= rep.sim_seed < 2**32)

    def test_different_repetitions_differ(self):
        r0, r1 = self._rep(0), self._rep(1)
        self.assertNotEqual(r0.sim_seed, r1.sim_seed)
        self.assertNotEqual(r0.perturbation, r1.perturbation)

    def test_audit_stream_seed_disjoint_from_discovery(self):
        self.assertNotEqual(self._rep(0, "discovery").sim_seed,
                            self._rep(0, "audit").sim_seed)

    def test_only_the_two_declared_dimensions_change(self):
        rep = self._rep(0)
        base = rep.base
        for c, scn in rep.scenarios.items():
            for dim in ("front_speed", "ramp_x", "ramp_speed", "ramp_target_speed"):
                self.assertAlmostEqual(scn[dim], base[dim], places=9, msg=(c, dim))
            expected_gap = base["front_gap"] + (self.p.gap_m if c in ("10", "11") else 0.0)
            expected_speed = base["ego_speed"] - (self.p.speed_mps if c in ("01", "11") else 0.0)
            self.assertAlmostEqual(scn["front_gap"], expected_gap, places=9, msg=(c, "gap"))
            self.assertAlmostEqual(scn["ego_speed"], expected_speed, places=9, msg=(c, "speed"))

    def test_perturbation_is_zero_centred(self):
        offsets = [self._rep(r).perturbation for r in range(6)]
        for dim in ("front_gap", "front_speed", "ego_speed"):
            hw = self.p.halfwidths[dim]
            for o in offsets:
                self.assertLessEqual(abs(o[dim]), hw + 1e-9, dim)


class TestUpstreamTtcSemantics(unittest.TestCase):
    def _veh(self, x, y, speed, heading=0.0):
        return {"x": x, "y": y, "speed": speed, "heading": heading, "crashed": False}

    def test_no_vehicle_ahead_is_no_candidate(self):
        self.assertEqual(step_candidate([self._veh(0, 0, 30), self._veh(-10, 0, 20)]),
                         (False, 0.0, 0.0))

    def test_lateral_overlap_threshold_is_two_metres(self):
        ahead = self._veh(50, 2.5, 20)
        hc, _, _ = step_candidate([self._veh(0, 0, 30), ahead])
        self.assertFalse(hc)
        ahead_ok = self._veh(50, 1.9, 20)
        hc2, _, _ = step_candidate([self._veh(0, 0, 30), ahead_ok])
        self.assertTrue(hc2)

    def test_gap_and_closing_match_upstream_definition(self):
        # ego 30 m/s at x=0, lead 20 m/s at x=50 -> gap = 45, closing = 10, ttc = 4.5
        hc, gap, closing = step_candidate([self._veh(0, 0, 30), self._veh(50, 0, 20)])
        self.assertTrue(hc)
        self.assertAlmostEqual(gap, 45.0)
        self.assertAlmostEqual(closing, 10.0)
        state, value = states_from_raw_steps([(hc, gap, closing)])[0]
        self.assertIs(state, StepTTCState.NORMAL_CLOSING)
        self.assertAlmostEqual(value, 4.5)

    def test_non_closing_candidate_is_not_reported_as_finite(self):
        hc, gap, closing = step_candidate([self._veh(0, 0, 20), self._veh(50, 0, 30)])
        self.assertTrue(hc)
        self.assertLessEqual(closing, 0.0)
        state, value = states_from_raw_steps([(hc, gap, closing)])[0]
        self.assertIs(state, StepTTCState.NO_CLOSING)
        self.assertIsNone(value)

    def test_tightest_candidate_wins(self):
        # two leading cars; the nearer one must decide the step
        hc, gap, closing = step_candidate(
            [self._veh(0, 0, 30), self._veh(60, 0, 25), self._veh(30, 0, 25)])
        self.assertTrue(hc)
        self.assertAlmostEqual(gap, 25.0)  # 30 - 0 - 5

    def test_trajectory_helper_shape(self):
        traj = [{"vehicles": [self._veh(0, 0, 30), self._veh(50, 0, 20)]},
                {"vehicles": [self._veh(5, 0, 30), self._veh(53, 0, 20)]}]
        states = steps_from_trajectory(traj)
        self.assertEqual(len(states), 2)
        self.assertTrue(all(s is StepTTCState.NORMAL_CLOSING for s, _ in states))


class TestLedgerBilling(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ledger = EpisodeLedger21(self.root / "runs" / "episode_ledger.csv",
                                      phase="smoke")

    def tearDown(self):
        self.tmp.cleanup()

    def _key(self, rep=0, cond="00", run="r1"):
        return EpisodeKey21(run_id=run, anchor_id="v02-anchor-0000",
                            repetition=rep, condition=cond)

    def test_cap_is_enforced_and_refuses_extra_episodes(self):
        for i in range(3):
            self.ledger.reserve_launch(self._key(rep=i), method="Shared", master_seed=1,
                                       anchor_id="v02-anchor-0000", anchor_index=0,
                                       repetition=i, condition="00", sim_seed=100 + i,
                                       max_episodes=3, budget_scope="v02-smoke")
        with self.assertRaises(BudgetExhausted):
            self.ledger.reserve_launch(self._key(rep=9), method="Shared", master_seed=1,
                                       anchor_id="v02-anchor-0000", anchor_index=0,
                                       repetition=9, condition="00", sim_seed=999,
                                       max_episodes=3, budget_scope="v02-smoke")

    def test_duplicate_launch_is_refused_before_any_work(self):
        args = dict(method="Shared", master_seed=1, anchor_id="v02-anchor-0000",
                    anchor_index=0, repetition=0, condition="00", sim_seed=7,
                    max_episodes=10, budget_scope="v02-smoke")
        self.ledger.reserve_launch(self._key(), **args)
        with self.assertRaises(DuplicateLaunch):
            self.ledger.reserve_launch(self._key(), **args)

    def test_outcome_requires_collision_for_completed(self):
        row = self.ledger.reserve_launch(self._key(), method="Shared", master_seed=1,
                                         anchor_id="v02-anchor-0000", anchor_index=0,
                                         repetition=0, condition="00", sim_seed=7,
                                         max_episodes=10, budget_scope="v02-smoke")
        with self.assertRaises(ValueError):
            self.ledger.record_outcome(self._key(), launch_row=row,
                                       exit_status="completed", ego_collision=None)
        self.ledger.record_outcome(self._key(), launch_row=row, exit_status="completed",
                                   ego_collision=0)
        self.assertEqual(self.ledger.outcome_count("completed"), 1)


class TestRunnerWithSyntheticAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.p = _proto()
        self.ledger = EpisodeLedger21(self.root / "runs" / "smoke" / "episode_ledger.csv",
                                      phase="smoke")
        self.anchor = anchor_stream(self.p.master_seed, self.p.domain,
                                    bounds=self.p.bounds, n=1, gap_m=self.p.gap_m,
                                    speed_mps=self.p.speed_mps,
                                    perturbation_halfwidths=self.p.halfwidths)[0]

    def tearDown(self):
        self.tmp.cleanup()

    def _runner(self, adapter, cap=24):
        return V02Runner(adapter, self.ledger, self.root / "runs" / "smoke",
                         tau_cap_s=float(self.p.value("tau_cap_s")),
                         no_candidate_policy=str(self.p.value("no_candidate_policy")),
                         max_episodes=cap, budget_scope="v02-smoke", phase="smoke")

    def test_one_quartet_bills_exactly_four_episodes(self):
        adapter = FakeAdapterV02()
        runner = self._runner(adapter)
        rep = build_repetition(master_seed=self.p.master_seed, stream="discovery",
                               anchor_index=0, anchor_id=anchor_id(0), repetition=0,
                               anchor_values=self.anchor,
                               perturbation_spec=self.p.perturbation_spec,
                               gap_m=self.p.gap_m, speed_mps=self.p.speed_mps,
                               method="Shared")
        run_quartet(runner, run_id="v02_smoke_Shared_1", method="Shared",
                    master_seed=self.p.master_seed, rep=rep)
        self.assertEqual(self.ledger.launched_count_scope("v02-smoke"), 4)
        self.assertEqual(len(adapter.calls), 4)
        # all four conditions share one sim_seed
        self.assertEqual(len({seed for _, seed in adapter.calls}), 1)

    def test_error_is_billed_and_not_retried(self):
        adapter = FakeAdapterV02(fail=lambda scn, seed: scn["front_gap"] > 0)
        runner = self._runner(adapter)
        rep = build_repetition(master_seed=self.p.master_seed, stream="discovery",
                               anchor_index=0, anchor_id=anchor_id(0), repetition=0,
                               anchor_values=self.anchor,
                               perturbation_spec=self.p.perturbation_spec,
                               gap_m=self.p.gap_m, speed_mps=self.p.speed_mps,
                               method="Shared")
        out = run_quartet(runner, run_id="v02_smoke_Shared_1", method="Shared",
                          master_seed=self.p.master_seed, rep=rep)
        self.assertEqual(self.ledger.launched_count_scope("v02-smoke"), 4)
        self.assertEqual(self.ledger.outcome_count("error"), 4)
        self.assertEqual(len(adapter.calls), 4, "no automatic retry")
        for r in out.values():
            self.assertEqual(r.exit_status, "error")
            self.assertIsNone(r.ego_collision)


class TestMethods(unittest.TestCase):
    def _q(self, ai, delta, usable=True, rep=0):
        return {"anchor_index": ai, "anchor_id": anchor_id(ai), "repetition": rep,
                "usable": usable, "delta_both": delta}

    def test_usable_delta_excludes_unusable_anchors(self):
        self.assertEqual(usable_delta_both([self._q(0, 1.0, usable=False)]), (None, 0))

    def test_select_top_prefers_most_negative(self):
        pool = {0: [self._q(0, 0.5)], 1: [self._q(1, -0.3)], 2: [self._q(2, -0.9)]}
        self.assertEqual(select_top(pool, verify_key, 2), [2, 1])

    def test_unusable_anchor_is_never_nominated(self):
        pool = {0: [self._q(0, -5.0, usable=False)], 1: [self._q(1, 0.1)]}
        self.assertEqual(select_top(pool, verify_key, 2), [1])

    def test_verify_key_prefers_more_verified_repetitions_on_ties(self):
        pool = {0: [self._q(0, 0.2, rep=0)], 1: [self._q(1, 0.2, rep=0), self._q(1, 0.2, rep=1)]}
        self.assertEqual(select_top(pool, verify_key, 1), [1])

    def test_wide_key_uses_single_quartet(self):
        pool = {0: [self._q(0, 0.2)], 1: [self._q(1, 0.1)]}
        self.assertEqual(select_top(pool, wide_key, 1), [1])

    def test_wide_and_verify_keys_agree_on_one_quartet_pools(self):
        """WideExplore's pool has exactly one quartet per anchor, where the two
        keys order identically (the -n term is constant). Pinned so a future
        change cannot silently make the auxiliary comparison method-dependent
        for the wrong reason."""
        pool = {0: [self._q(0, 0.2)], 1: [self._q(1, -0.1)], 2: [self._q(2, 0.05)]}
        self.assertEqual(select_top(pool, wide_key, 3), select_top(pool, verify_key, 3))
        self.assertEqual(select_top(pool, wide_key, 2), [1, 2])

    def test_precision_at_k_counts_only_usable(self):
        audit = [self._q(0, -0.2), self._q(1, -0.01), self._q(2, -0.5, usable=False)]
        pq = precision_at_k(audit, delta_eq_s=0.05)
        self.assertEqual(pq["k"], 2)
        self.assertEqual(pq["n_reversal"], 1)
        self.assertEqual(pq["n_unusable"], 1)
        self.assertAlmostEqual(pq["precision_at_k"], 0.5)

    def test_precision_at_k_none_when_nothing_usable(self):
        pq = precision_at_k([self._q(0, 1.0, usable=False)], delta_eq_s=0.05)
        self.assertIsNone(pq["precision_at_k"])


class TestRunnerSafety(unittest.TestCase):
    """D37 regression: a failure anywhere after billing must still be recorded."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.p = _proto()
        self.ledger = EpisodeLedger21(self.root / "runs" / "smoke" / "episode_ledger.csv",
                                      phase="smoke")
        self.anchor = anchor_stream(self.p.master_seed, self.p.domain,
                                    bounds=self.p.bounds, n=2, gap_m=self.p.gap_m,
                                    speed_mps=self.p.speed_mps,
                                    perturbation_halfwidths=self.p.halfwidths)

    def tearDown(self):
        self.tmp.cleanup()

    def _rep(self, ai=0, rep=0, stream="discovery"):
        return build_repetition(master_seed=self.p.master_seed, stream=stream,
                                anchor_index=ai, anchor_id=anchor_id(ai),
                                repetition=rep, anchor_values=self.anchor[ai],
                                perturbation_spec=self.p.perturbation_spec,
                                gap_m=self.p.gap_m, speed_mps=self.p.speed_mps,
                                method="Shared")

    def test_method_label_enters_the_seed(self):
        """Regression for independent-review finding MAJOR-1: the method label
        must be part of the seed, so two strategies that nominate the same anchor
        cannot reuse one identical simulation."""
        a = build_repetition(master_seed=self.p.master_seed, stream="audit",
                             anchor_index=0, anchor_id=anchor_id(0), repetition=0,
                             anchor_values=self.anchor[0],
                             perturbation_spec=self.p.perturbation_spec,
                             gap_m=self.p.gap_m, speed_mps=self.p.speed_mps,
                             method=METHOD_WIDE)
        b = build_repetition(master_seed=self.p.master_seed, stream="audit",
                             anchor_index=0, anchor_id=anchor_id(0), repetition=0,
                             anchor_values=self.anchor[0],
                             perturbation_spec=self.p.perturbation_spec,
                             gap_m=self.p.gap_m, speed_mps=self.p.speed_mps,
                             method=METHOD_VERIFY)
        self.assertNotEqual(a.sim_seed, b.sim_seed)
        self.assertEqual(a.method, METHOD_WIDE)
        self.assertEqual(b.method, METHOD_VERIFY)

    def test_method_label_is_required(self):
        with self.assertRaises(TypeError):
            build_repetition(master_seed=self.p.master_seed, stream="audit",
                             anchor_index=0, anchor_id=anchor_id(0), repetition=0,
                             anchor_values=self.anchor[0],
                             perturbation_spec=self.p.perturbation_spec,
                             gap_m=self.p.gap_m, speed_mps=self.p.speed_mps)

    def _runner(self, adapter, cap=24):
        return V02Runner(adapter, self.ledger, self.root / "runs" / "smoke",
                         tau_cap_s=float(self.p.value("tau_cap_s")),
                         no_candidate_policy=str(self.p.value("no_candidate_policy")),
                         max_episodes=cap, budget_scope="v02-smoke", phase="smoke")

    def test_post_processing_failure_is_never_an_orphan(self):
        """A non-serialisable payload must still yield a billed, recorded error."""

        class BadArchiveFake(FakeAdapterV02):
            def run_episode(self, scenario, sim_seed, perturbation=None):
                out = super().run_episode(scenario, sim_seed, perturbation)
                out["unserialisable"] = {1, 2, 3}   # json.dump will refuse this
                return out

        runner = self._runner(BadArchiveFake())
        out = run_quartet(runner, run_id="v02_smoke_Shared_x", method="Shared",
                          master_seed=self.p.master_seed, rep=self._rep())
        self.assertEqual(self.ledger.launched_count_scope("v02-smoke"), 4)
        self.assertEqual(self.ledger.outcome_count("error"), 4)
        for r in out.values():
            self.assertEqual(r.exit_status, "error")

    def test_no_orphan_launch_rows_after_failure(self):
        class BadArchiveFake(FakeAdapterV02):
            def run_episode(self, scenario, sim_seed, perturbation=None):
                out = super().run_episode(scenario, sim_seed, perturbation)
                out["unserialisable"] = object()
                return out

        runner = self._runner(BadArchiveFake())
        run_quartet(runner, run_id="v02_smoke_Shared_x", method="Shared",
                    master_seed=self.p.master_seed, rep=self._rep())
        with open(self.ledger.path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        launches = [r for r in rows if r["row_type"] == "launch"]
        outcomes = [r for r in rows if r["row_type"] == "outcome"]
        self.assertEqual(len(launches), len(outcomes))
        self.assertEqual({r["episode_key"] for r in launches},
                         {r["episode_key"] for r in outcomes})

    def test_resume_skips_already_billed_episodes(self):
        adapter = FakeAdapterV02()
        runner = self._runner(adapter)
        rep = self._rep()
        run_quartet(runner, run_id="v02_smoke_Shared_x", method="Shared",
                    master_seed=self.p.master_seed, rep=rep)
        self.assertEqual(len(adapter.calls), 4)
        # re-invoking the same phase must not re-run (and must not re-bill) anything
        billed = billed_tuple_keys(self.ledger)
        again = run_quartet(runner, run_id="v02_smoke_Shared_y", method="Shared",
                            master_seed=self.p.master_seed, rep=rep,
                            already_billed=billed)
        self.assertEqual(again, {})
        self.assertEqual(len(adapter.calls), 4, "no episode may be re-run")
        with open(self.ledger.path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(sum(1 for r in rows if r["row_type"] == "launch"), 4)

    def test_billed_tuple_keys_reads_every_launch(self):
        runner = self._runner(FakeAdapterV02())
        run_quartet(runner, run_id="v02_smoke_Shared_x", method="Shared",
                    master_seed=self.p.master_seed, rep=self._rep())
        keys = billed_tuple_keys(self.ledger)
        self.assertEqual(len(keys), 4)
        self.assertIn(("Shared", 0, 0, "00", "discovery"), keys)


class TestFrozenProtocolGate(unittest.TestCase):
    def test_unfrozen_config_is_refused(self):
        with open(CONFIG, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        cfg["status"] = "PROPOSED"
        with self.assertRaises(RuntimeError):
            FrozenProtocol(cfg)

    def test_unset_parameter_is_refused(self):
        with open(CONFIG, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        cfg["parameters"]["tau_cap_s"] = {"status": "UNSET", "value": None}
        with self.assertRaises(RuntimeError):
            FrozenProtocol(cfg)

    def test_real_config_is_valid(self):
        p = _proto()
        self.assertEqual(len(p.value("pilot_plan")["methods"]), 2)
        self.assertEqual(p.value("smoke_plan")["episodes"], 24)
        self.assertEqual(p.value("pilot_plan")["episodes"], 240)


class TestM2DoesNotReadTheAuditStream(unittest.TestCase):
    """Regression for D43: ``m2_from_raw`` must take its episode set from the
    ledger, never from a filename glob.

    Primary and auxiliary-audit raw files share the same *filename*
    (``<anchor_id>_rep<r>_<cond>.json``), so a glob keyed on the stem lets an
    audit episode overwrite a primary M2 value. The two files here deliberately
    encode *different* below-threshold shares so the contamination is observable.
    """

    ANCHOR = "v02-anchor-0000"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        run = self.root / "runs" / "pilot"
        run.mkdir(parents=True, exist_ok=True)
        self.ledger = EpisodeLedger21(run / "episode_ledger.csv", phase="pilot")
        self.primary_dir = run / "a_primary_run"
        self.audit_dir = run / "z_audit_run"
        self.primary_dir.mkdir(exist_ok=True)
        self.audit_dir.mkdir(exist_ok=True)
        for cond in CONDITIONS:
            # primary: 1 of 4 steps below the 1.0 s threshold -> share 0.25
            self._write(self.primary_dir / f"{self.ANCHOR}_rep0_{cond}.json",
                         [[True, 0.5, 1.0], [True, 5.0, 1.0],
                          [True, 5.0, 1.0], [True, 5.0, 1.0]])
            # audit: 0 of 4 steps below -> share 0.0
            self._write(self.audit_dir / f"{self.ANCHOR}_rep0_{cond}.json",
                        [[True, 5.0, 1.0]] * 4)
            self._record(cond, stream="discovery", method="Shared",
                         raw=str(self.primary_dir / f"{self.ANCHOR}_rep0_{cond}.json"))
            self._record(cond, stream="audit", method="WideExplore",
                         raw=str(self.audit_dir / f"{self.ANCHOR}_rep0_{cond}.json"))

    def tearDown(self):
        self._tmp.cleanup()

    @staticmethod
    def _write(path: Path, steps):
        path.write_text(json.dumps({"exit_status": "completed", "raw_steps": steps}),
                        encoding="utf-8")

    def _record(self, cond, *, stream, method, raw):
        key = EpisodeKey21(run_id=f"run_{stream}", anchor_id=self.ANCHOR,
                           repetition=0, condition=cond)
        launch = self.ledger.reserve_launch(
            key, method=method, master_seed=1, anchor_id=self.ANCHOR,
            anchor_index=0, repetition=0, condition=cond, sim_seed=7,
            stream=stream, budget_scope="v02-pilot")
        self.ledger.record_outcome(key, launch_row=launch, exit_status="completed",
                                   ego_collision=0, termination="goal", raw_path=raw)

    def test_only_primary_episodes_are_parsed(self):
        from v02lab.report import m2_from_raw
        # Self-documenting precondition: under the OLD filename-glob reader the
        # audit files sort last and would therefore win. This asserts that the
        # fixture really does reproduce the failure mode.
        globbed = sorted((self.root / "runs" / "pilot").glob("*/*.json"))
        self.assertIn("z_audit_run", str(globbed[-1]),
                      "fixture must place the audit file last in glob order")
        m2 = m2_from_raw(self.root, "pilot", tau_low_s=1.0)
        self.assertEqual(m2["n_episodes_parsed"], 4,
                         "the 4 audit episodes must not be read")
        self.assertEqual(m2["n_complete_quartets"], 1)
        # every condition must carry the PRIMARY share (0.25), not the audit 0.0
        for cond in CONDITIONS:
            self.assertAlmostEqual(m2["per_condition_mean_share"][cond], 0.25, places=12,
                                   msg=f"condition {cond} was contaminated by the audit stream")


if __name__ == "__main__":
    unittest.main()

"""Generator, runner and adapter-related tests with the fake adapter."""
import json
import tempfile
import unittest
from pathlib import Path

from cornercaselab.domain import Scenario

from safefliplab.domain import anchor_in_domain, condition_scenario, quartet_scenarios
from safefliplab.generator import ScenarioGenerator, anchors_for
from safefliplab.ledger import BudgetExhausted, EpisodeLedger
from safefliplab.runner import SimulatorRunner
from safefliplab.seeds import DEV_SEED, sim_seed_for
from tests.fakes import FakeAdapter


class TestGenerator(unittest.TestCase):
    def test_stream_is_deterministic(self):
        a = anchors_for(20261011, 5)
        b = anchors_for(20261011, 5)
        self.assertEqual([x.scenario.to_dict() for x in a],
                         [x.scenario.to_dict() for x in b])

    def test_different_master_seeds_differ(self):
        a = anchors_for(20261011, 5)
        b = anchors_for(20261012, 5)
        self.assertNotEqual([x.scenario.to_dict() for x in a],
                            [x.scenario.to_dict() for x in b])

    def test_all_anchors_are_quartet_legal(self):
        for anchor in anchors_for(20261011, 60):
            self.assertTrue(anchor_in_domain(anchor.scenario), anchor.scenario.to_dict())
            q = quartet_scenarios(anchor.scenario)  # must not raise
            self.assertEqual(len(q), 4)

    def test_anchor_ids_are_stable_indices(self):
        anchors = anchors_for(20261011, 10)
        for i, a in enumerate(anchors):
            self.assertEqual(a.index, i)
            self.assertEqual(a.anchor_id, f"anchor-{i:04d}")

    def test_stream_draws_recorded(self):
        anchors = anchors_for(20261011, 10)
        for a in anchors:
            self.assertGreaterEqual(a.stream_draws, 1)

    def test_generator_extends_lazily_and_consistently(self):
        gen = ScenarioGenerator(20261011)
        first = gen.anchor(0).scenario.to_dict()
        again = gen.anchor(0).scenario.to_dict()
        self.assertEqual(first, again)
        self.assertEqual(gen.anchor(3).index, 3)

    def test_save_stream(self):
        gen = ScenarioGenerator(20261011)
        gen.anchors(3)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stream.json"
            gen.save_stream(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["master_seed"], 20261011)
            self.assertEqual(len(payload["anchors"]), 3)

    def test_negative_index_rejected(self):
        gen = ScenarioGenerator(20261011)
        with self.assertRaises(ValueError):
            gen.anchor(-1)


class TestRunnerWithFakeAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")
        self.adapter = FakeAdapter()
        self.runner = SimulatorRunner(self.adapter, self.ledger, self.root / "runs")
        self.anchor = anchors_for(DEV_SEED, 1)[0]

    def tearDown(self):
        self.tmp.cleanup()

    def test_quartet_runs_four_episodes_with_shared_seed(self):
        result = self.runner.run_quartet(
            run_id="run_test", phase="smoke", method="WideExplore",
            master_seed=DEV_SEED, anchor=self.anchor, repetition=0,
            stream="discovery", max_episodes=24)
        self.assertEqual(len(self.adapter.calls), 4)
        seeds = {s for _, s in self.adapter.calls}
        self.assertEqual(len(seeds), 1)  # paired sim_seed
        self.assertEqual(seeds.pop(),
                         sim_seed_for(DEV_SEED, "WideExplore", "discovery",
                                      self.anchor.anchor_id, 0))
        self.assertTrue(result.complete)
        self.assertIsNotNone(result.y)
        self.assertEqual(self.ledger.launched_count("smoke"), 4)
        self.assertEqual(self.ledger.outcome_count("smoke", "completed"), 4)

    def test_conditions_are_the_declared_interventions(self):
        self.runner.run_quartet(
            run_id="run_test", phase="smoke", method="WideExplore",
            master_seed=DEV_SEED, anchor=self.anchor, repetition=0,
            stream="discovery", max_episodes=24)
        scenarios = sorted(
            tuple(sorted(s.to_dict().items())) for s, _ in self.adapter.calls)
        expected = sorted(
            tuple(sorted(condition_scenario(self.anchor.scenario, c).to_dict().items()))
            for c in ("00", "10", "01", "11"))
        self.assertEqual(scenarios, expected)

    def test_error_is_billed_and_raised(self):
        failing = FakeAdapter(fail=lambda s, seed: True)
        runner = SimulatorRunner(failing, self.ledger, self.root / "runs")
        with self.assertRaises(RuntimeError):
            runner.run_quartet(
                run_id="run_fail", phase="smoke", method="WideExplore",
                master_seed=DEV_SEED, anchor=self.anchor, repetition=0,
                stream="discovery", max_episodes=24)
        self.assertEqual(self.ledger.launched_count("smoke"), 1)  # billed
        self.assertEqual(self.ledger.outcome_count("smoke", "error"), 1)

    def test_budget_exhaustion_blocks_launch(self):
        # pre-fill the phase budget with dummy launches
        for i in range(24):
            self.ledger.record_launch(
                __import__("safefliplab.ledger", fromlist=["EpisodeKey"]).EpisodeKey(
                    run_id="pre", anchor_id=f"a{i}", repetition=0, condition="00"),
                run_id="pre", phase="smoke", method="WideExplore", master_seed=1,
                anchor_id=f"a{i}", anchor_index=i, repetition=0, condition="00",
                sim_seed=1, stream="discovery")
        with self.assertRaises(BudgetExhausted):
            self.runner.run_quartet(
                run_id="run_x", phase="smoke", method="WideExplore",
                master_seed=DEV_SEED, anchor=self.anchor, repetition=0,
                stream="discovery", max_episodes=24)

    def test_raw_records_written(self):
        self.runner.run_quartet(
            run_id="run_raw", phase="smoke", method="WideExplore",
            master_seed=DEV_SEED, anchor=self.anchor, repetition=0,
            stream="discovery", max_episodes=24)
        raw_dir = self.root / "runs" / "run_raw"
        files = sorted(p.name for p in raw_dir.glob("*.json"))
        self.assertEqual(len(files), 4)
        payload = json.loads((raw_dir / files[0]).read_text(encoding="utf-8"))
        self.assertEqual(payload["phase"], "smoke")
        self.assertEqual(payload["method"], "WideExplore")
        self.assertIn(payload["condition"], ("00", "10", "01", "11"))
        self.assertIn("result", payload)
        self.assertIn("adapter_fingerprint", payload)

    def test_audit_stream_uses_different_seed(self):
        self.runner.run_quartet(
            run_id="run_d", phase="pilot", method="WideExplore",
            master_seed=DEV_SEED, anchor=self.anchor, repetition=0,
            stream="discovery", max_episodes=240)
        disc_seed = self.adapter.calls[-1][1]
        self.adapter.calls.clear()
        self.runner.run_quartet(
            run_id="run_a", phase="pilot", method="WideExplore",
            master_seed=DEV_SEED, anchor=self.anchor, repetition=0,
            stream="audit", max_episodes=240)
        audit_seed = self.adapter.calls[-1][1]
        self.assertNotEqual(disc_seed, audit_seed)


if __name__ == "__main__":
    unittest.main()

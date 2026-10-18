"""Report regression tests: master_seed / run_id isolation and truthfulness.

Reproduces and locks down the defect where ``load_phase_data`` grouped by
``(method, anchor_id, repetition, stream)`` only, so two master seeds with the
same anchor collapsed into a single (wrongly merged) quartet.

Also covers: cross-run_id replays excluded from primary evidence, incomplete
quartets recorded truthfully, strict discovery/audit separation, and per
(master_seed, method) audit results. No simulator is imported.
"""
import tempfile
import unittest
from pathlib import Path

from safefliplab.ledger import EpisodeKey, EpisodeLedger
from safefliplab.report import load_phase_data, write_report
from safefliplab.seeds import CONDITIONS


def _add_quartet(ledger, *, seed, method, anchor_id, anchor_index, repetition, stream,
                 y, run_id, status="completed"):
    for cond in CONDITIONS:
        key = EpisodeKey(run_id=run_id, anchor_id=anchor_id, repetition=repetition,
                         condition=cond)
        launch = ledger.record_launch(
            key, run_id=run_id, phase="formal", method=method, master_seed=seed,
            anchor_id=anchor_id, anchor_index=anchor_index, repetition=repetition,
            condition=cond, sim_seed=7, stream=stream)
        if status == "completed":
            ledger.record_outcome(key, launch_row=launch, exit_status="completed",
                                  ego_collision=y[cond], termination="collision" if y[cond] else "goal")
        else:
            ledger.record_outcome(key, launch_row=launch, exit_status=status,
                                  ego_collision=None, error_type="Injected")


class TestMultiMasterSeedReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "runs").mkdir(parents=True)
        self.ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def _two_seeds_same_anchor(self):
        for seed in (111, 222):
            _add_quartet(self.ledger, seed=seed, method="WideExplore",
                         anchor_id="anchor-0000", anchor_index=0, repetition=0,
                         stream="discovery", y={"00": 0, "10": 0, "01": 0, "11": 1},
                         run_id=f"run{seed}")

    def test_two_master_seeds_yield_two_quartets(self):
        self._two_seeds_same_anchor()
        data = load_phase_data(self.root, "formal")
        self.assertEqual(len(data.quartets), 2)
        self.assertEqual(sorted(q["master_seed"] for q in data.quartets), [111, 222])
        # Each quartet's four conditions come from its own run_id.
        for q in data.quartets:
            self.assertEqual(q["run_id"], f"run{q['master_seed']}")

    def test_no_cross_seed_mixing(self):
        self._two_seeds_same_anchor()
        data = load_phase_data(self.root, "formal")
        seeds = {q["master_seed"] for q in data.quartets}
        self.assertEqual(seeds, {111, 222})
        # The two quartets are distinct objects with distinct seed labels.
        self.assertNotEqual(data.quartets[0]["master_seed"], data.quartets[1]["master_seed"])

    def test_cross_run_id_is_a_replay_not_primary(self):
        self._two_seeds_same_anchor()
        # A second run of the SAME key for seed 111 (like the smoke replay).
        _add_quartet(self.ledger, seed=111, method="WideExplore",
                     anchor_id="anchor-0000", anchor_index=0, repetition=0,
                     stream="discovery", y={"00": 1, "10": 1, "01": 1, "11": 1},
                     run_id="run111_replay")
        data = load_phase_data(self.root, "formal")
        # Still exactly two PRIMARY quartets (one per seed); the extra run is a replay.
        self.assertEqual(len(data.quartets), 2)
        self.assertEqual(len(data.replays), 1)
        self.assertTrue(data.replays[0]["is_replay"])
        self.assertEqual(data.replays[0]["run_id"], "run111_replay")
        # The primary for seed 111 stays the earliest run.
        primary_111 = [q for q in data.quartets if q["master_seed"] == 111][0]
        self.assertEqual(primary_111["run_id"], "run111")

    def test_incomplete_quartet_recorded_not_counted(self):
        self._two_seeds_same_anchor()
        # A key with only three completed conditions -> incomplete, not a quartet.
        for cond in ("00", "10", "01"):
            key = EpisodeKey(run_id="inc", anchor_id="anchor-0009", repetition=0,
                             condition=cond)
            launch = self.ledger.record_launch(
                key, run_id="inc", phase="formal", method="WideExplore", master_seed=333,
                anchor_id="anchor-0009", anchor_index=9, repetition=0, condition=cond,
                sim_seed=9, stream="discovery")
            self.ledger.record_outcome(key, launch_row=launch, exit_status="completed",
                                       ego_collision=0, termination="goal")
        # ...and the fourth condition errored.
        key = EpisodeKey(run_id="inc", anchor_id="anchor-0009", repetition=0, condition="11")
        launch = self.ledger.record_launch(
            key, run_id="inc", phase="formal", method="WideExplore", master_seed=333,
            anchor_id="anchor-0009", anchor_index=9, repetition=0, condition="11",
            sim_seed=9, stream="discovery")
        self.ledger.record_outcome(key, launch_row=launch, exit_status="error",
                                   ego_collision=None, error_type="Boom")

        data = load_phase_data(self.root, "formal")
        self.assertEqual(len(data.quartets), 2)          # unchanged: still 2 valid seeds
        self.assertEqual(len(data.incomplete), 1)
        inc = data.incomplete[0]
        self.assertEqual(inc["master_seed"], 333)
        self.assertEqual(inc["anchor_id"], "anchor-0009")
        self.assertEqual(inc["runs"]["inc"]["11"], "error")
        self.assertEqual(data.errored, 1)

    def test_discovery_and_audit_are_strictly_separate(self):
        self._two_seeds_same_anchor()
        _add_quartet(self.ledger, seed=111, method="WideExplore", anchor_id="anchor-0000",
                     anchor_index=0, repetition=0, stream="audit",
                     y={"00": 1, "10": 0, "01": 0, "11": 0}, run_id="audit111")
        data = load_phase_data(self.root, "formal")
        disc = [q for q in data.quartets if q["stream"] == "discovery"]
        aud = [q for q in data.quartets if q["stream"] == "audit"]
        self.assertEqual(len(disc), 2)   # two seeds
        self.assertEqual(len(aud), 1)    # one audit quartet (seed 111)
        self.assertEqual(aud[0]["master_seed"], 111)
        self.assertEqual(aud[0]["run_id"], "audit111")

    def test_per_seed_method_structure_and_audit_results(self):
        self._two_seeds_same_anchor()
        _add_quartet(self.ledger, seed=111, method="WideExplore", anchor_id="anchor-0000",
                     anchor_index=0, repetition=0, stream="audit",
                     y={"00": 1, "10": 0, "01": 0, "11": 0}, run_id="audit111")
        summary = write_report(self.root, "formal")
        self.assertEqual(summary["status"], "OK")
        self.assertEqual(summary["complete_quartets"], 3)
        per = summary["by_seed_method"]
        self.assertIn("seed=111|method=WideExplore", per)
        self.assertIn("seed=222|method=WideExplore", per)
        e111 = per["seed=111|method=WideExplore"]
        self.assertIsNotNone(e111["discovery"])
        self.assertIsNotNone(e111["audit"])
        self.assertEqual(e111["paired_contrast"]["discovery"]["mean_delta_both"], 1.0)
        self.assertEqual(len(e111["audit_results"]), 1)
        self.assertEqual(e111["audit_results"][0]["anchor_id"], "anchor-0000")
        # cross-seed noisy summary exists and is labelled exploratory
        self.assertIn("note", summary["cross_seed"])

    def test_two_master_seeds_method_summary_not_merged_by_seed(self):
        """The pooled method/stream summary is fine, but per-seed entries exist."""
        self._two_seeds_same_anchor()
        summary = write_report(self.root, "formal")
        # pooled across seeds: 2 quartets, both delta_both = 1
        self.assertEqual(summary["by_method_stream"]["WideExplore/discovery"]["n_quartets"], 2)
        keys = set(summary["by_seed_method"])
        self.assertEqual(keys, {"seed=111|method=WideExplore", "seed=222|method=WideExplore"})


if __name__ == "__main__":
    unittest.main()

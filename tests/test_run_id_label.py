"""Regression: the run id must name the method that is actually recorded.

Defect D27 (found 2026-10-15 by the structured-output audit):``run_smoke``
drives BOTH methods through a single ``PhaseDriver`` constructed with
``method=METHOD_WIDE``, while ``_new_run_id`` derived the id from
``self.method``. The two VerifyFirst stage-1 quartets of the historical smoke
phase therefore got a ``smoke_WideExplore_...`` run id even though every
ledger row, ``sim_seed`` and raw record said ``VerifyFirst``.

The historical rows are left untouched (append-only history); these tests pin
the corrected behaviour so no future phase can repeat it.
"""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from safefliplab.experiments import PhaseDriver, run_smoke_phase
from safefliplab.methods import METHOD_VERIFY, METHOD_WIDE
from safefliplab.seeds import DEV_SEED, sim_seed_for
from tests.fakes import FakeAdapter


def _embedded_method(run_id: str) -> str:
    """``smoke_VerifyFirst_20261011_...`` -> ``VerifyFirst``."""
    return run_id.split("_")[1]


class TestRunIdNamesTheRecordedMethod(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config_path = self.root / "dev.json"
        self.config_path.write_text(json.dumps({
            "dev_seed": DEV_SEED,
            "smoke": {"max_episodes": 24, "wide_discovery_anchors": 3,
                      "verify_stage1_anchors": 2, "determinism_replay": True},
        }), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _ledger_rows(self):
        path = self.root / "runs" / "episode_ledger.csv"
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def test_every_run_id_names_its_recorded_method(self):
        run_smoke_phase(self.root, self.config_path, adapter=FakeAdapter())
        rows = self._ledger_rows()
        self.assertEqual(len(rows), 48)  # 24 episodes x (launch + outcome)
        for row in rows:
            self.assertEqual(
                _embedded_method(row["run_id"]), row["method"],
                f"run id {row['run_id']} disagrees with method {row['method']}")
        mismatch = [r for r in rows if _embedded_method(r["run_id"]) != r["method"]]
        self.assertEqual(mismatch, [])

    def test_smoke_phase_records_both_methods(self):
        run_smoke_phase(self.root, self.config_path, adapter=FakeAdapter())
        methods = {r["method"] for r in self._ledger_rows()}
        self.assertEqual(methods, {METHOD_WIDE, METHOD_VERIFY})

    def test_sim_seed_always_matches_the_recorded_method(self):
        run_smoke_phase(self.root, self.config_path, adapter=FakeAdapter())
        for row in self._ledger_rows():
            expected = sim_seed_for(int(row["master_seed"]), row["method"],
                                    row["stream"], row["anchor_id"],
                                    int(row["repetition"]))
            self.assertEqual(int(row["sim_seed"]), expected, row["episode_key"])

    def test_direct_job_run_id_uses_the_job_method(self):
        """A VerifyFirst job run by a WideExplore driver is labelled VerifyFirst."""
        from safefliplab.methods import verify_stage1_jobs

        driver = PhaseDriver(phase="pilot", method=METHOD_WIDE,
                             master_seed=DEV_SEED, max_episodes=240,
                             project_root=self.root, adapter=FakeAdapter())
        driver.execute_job(verify_stage1_jobs(1)[0])
        verify_rows = [r for r in self._ledger_rows() if r["method"] == METHOD_VERIFY]
        self.assertEqual(len(verify_rows), 8)  # 4 conditions x (launch + outcome)
        for row in verify_rows:
            self.assertEqual(_embedded_method(row["run_id"]), METHOD_VERIFY)


if __name__ == "__main__":
    unittest.main()

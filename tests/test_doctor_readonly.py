"""GH-2 regression (DOCTOR-01): ``doctor`` must be genuinely read-only.

Before GH-2, ``run_doctor`` constructed ``EpisodeLedger(PROJECT_ROOT/runs/
episode_ledger.csv)`` to read the budget state. Constructing the ledger on a
missing path creates ``runs/`` and writes an empty header, so a supposedly
read-only command left a residue — which then made
``test_ledger_safety.test_legacy_activity_ledger_reads_compat`` fail on the
next full test run (``0 != 24``).

These tests pin the fixed behaviour. They redirect ``doctor.PROJECT_ROOT`` at a
scratch directory, so the *other* doctor checks (config/interface files) will
naturally report NO-GO there — that is irrelevant here; the assertions focus on
(a) nothing is created on disk and (b) the ledger branch is the "absent" one
(or the read one when a ledger exists).
"""
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from safefliplab import doctor

HEADER = (
    "row_type,episode_key,run_id,phase,method,master_seed,anchor_id,"
    "anchor_index,repetition,condition,stream,sim_seed,exit_status,"
    "ego_collision,termination,error_type,started_utc,ended_utc,"
    "wall_time_s,raw_path,budget_scope\n"
)


class TestDoctorIsReadOnly(unittest.TestCase):
    def _run(self, root: Path) -> tuple[int, str]:
        buf = io.StringIO()
        with mock.patch.object(doctor, "PROJECT_ROOT", root), redirect_stdout(buf):
            code = doctor.run_doctor(verbose=True)
        return code, buf.getvalue()

    def test_doctor_creates_no_runs_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, out = self._run(root)
            self.assertIn(code, (0, 1), "doctor returns GO/NO-GO; both are fine here")
            self.assertIn("no ledger in this checkout", out)
            self.assertFalse((root / "runs").exists(),
                             "doctor must not create runs/")
            self.assertFalse((root / "runs" / "episode_ledger.csv").exists(),
                             "doctor must not create an episode ledger")

    def test_doctor_reads_an_existing_ledger_without_touching_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runs").mkdir()
            ledger = root / "runs" / "episode_ledger.csv"
            ledger.write_text(HEADER, encoding="utf-8")
            before = ledger.read_bytes()
            code, out = self._run(root)
            self.assertIn(code, (0, 1))
            self.assertIn("launched=0/24", out, "the real ledger branch must run")
            self.assertEqual(ledger.read_bytes(), before,
                             "doctor must not rewrite the ledger")


if __name__ == "__main__":
    unittest.main()

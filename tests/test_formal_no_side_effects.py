"""GH-2 regression: the formal refusal path must not touch the filesystem.

Before GH-2, ``run_formal_phase`` constructed a ``PhaseDriver`` *before* the
refusal was raised, and ``PhaseDriver.__init__`` creates ``runs/`` plus an empty
ledger (``mkdir`` + header write). The CLI guard test therefore left a
``runs/episode_ledger.csv`` residue in the project root, and the next full test
run failed ``test_ledger_safety.test_legacy_activity_ledger_reads_compat``
(``0 != 24``).

These tests pin the fixed behaviour: the refusal happens first, explicitly,
and nothing is created on disk.
"""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from safefliplab import cli
from safefliplab.experiments import run_formal_phase
from safefliplab.seeds import FORMAL_TOTAL_EPISODES

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_FORMAL_CONFIG = PROJECT_ROOT / "configs" / "formal_v01.json"


class TestFormalRefusalHasNoSideEffects(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.config = self.root / "formal.json"
        self.config.write_text(json.dumps({"formal_master_seeds": [1]}),
                               encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _assert_no_runs(self):
        self.assertFalse((self.root / "runs").exists(),
                         "refusal must not create runs/")
        self.assertFalse((self.root / "runs" / "episode_ledger.csv").exists(),
                         "refusal must not create an episode ledger")

    def test_refusal_with_correct_flags_creates_nothing(self):
        with self.assertRaises(RuntimeError):
            run_formal_phase(self.root, self.config, confirm=True,
                             max_episodes=FORMAL_TOTAL_EPISODES)
        self._assert_no_runs()

    def test_refusal_without_confirm_creates_nothing(self):
        with self.assertRaises(PermissionError):
            run_formal_phase(self.root, self.config, confirm=False,
                             max_episodes=FORMAL_TOTAL_EPISODES)
        self._assert_no_runs()

    def test_refusal_with_wrong_budget_creates_nothing(self):
        with self.assertRaises(PermissionError):
            run_formal_phase(self.root, self.config, confirm=True, max_episodes=100)
        self._assert_no_runs()

    def test_cli_formal_refusal_creates_nothing_under_project_root(self):
        # Redirect the CLI's PROJECT_ROOT at a scratch directory and point the
        # config lookup at the real frozen config (read-only). The refusal must
        # return EXIT 2 and leave the scratch root untouched.
        with mock.patch.object(cli, "PROJECT_ROOT", self.root), \
                mock.patch.object(cli, "_config_path",
                                  return_value=REAL_FORMAL_CONFIG):
            code = cli.main(["formal", "--confirm", "--max-episodes", "12800"])
        self.assertEqual(code, 2)
        self._assert_no_runs()

    def test_cli_formal_refusal_message_semantics_preserved(self):
        # GH-2 changed only the *order* (refuse before side effects); the
        # refusal message keeps its meaning: it must mention the required flags
        # and that nothing was launched.
        buf = io.StringIO()
        with mock.patch.object(cli, "PROJECT_ROOT", self.root), \
                mock.patch.object(cli, "_config_path",
                                  return_value=REAL_FORMAL_CONFIG), \
                redirect_stderr(buf):
            code = cli.main(["formal", "--confirm", "--max-episodes", "12800"])
        self.assertEqual(code, 2)
        text = buf.getvalue()
        self.assertIn("REFUSED", text)
        self.assertIn("_execute_formal_phase", text)
        self.assertIn("Plan:", text)
        self._assert_no_runs()


if __name__ == "__main__":
    unittest.main()

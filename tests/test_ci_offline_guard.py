"""Negative + positive tests for the CI offline guard.

Proves, in an executable way, that ``scripts/ci_offline_guard.py``:

  * does NOT flag the legitimate FakeAdapter / refusal-path suites (positive),
  * DOES flag a planted real-simulator invocation of each blocked kind
    (negative) — so the guard is not a no-op and cannot silently stop working.

These tests never import the simulator and never launch an episode. They call
the guard's pure ``_scan_text`` / ``scan`` functions directly on strings and
throwaway temp files.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import scripts.ci_offline_guard as guard


class TestOfflineGuardPositive(unittest.TestCase):
    """The legitimate test trees must pass (no false positives)."""

    def test_scan_current_tests_is_clean(self):
        root = Path(__file__).resolve().parent  # tests/
        # The refusal-path files are excluded from the CLI-list check but their
        # subprocess/adapter/import content must still be clean.
        violations = guard.scan(root)
        self.assertEqual(violations, [])

    def test_domain_import_is_allowed(self):
        v = guard._scan_text(
            Path("t.py"),
            "from cornercaselab.domain import Scenario, BOUNDS\n",
        )
        self.assertEqual(v, [])

    def test_fake_adapter_is_allowed(self):
        text = (
            "from safefliplab.experiments import run_smoke_phase\n"
            "run_smoke_phase(root, cfg, adapter=FakeAdapter())\n"
        )
        v = guard._scan_text(Path("t.py"), text)
        self.assertEqual(v, [])


class TestOfflineGuardNegative(unittest.TestCase):
    """Each blocked kind must be caught (the guard is real, not a no-op)."""

    def test_subprocess_smoke_is_blocked(self):
        text = (
            'import subprocess\n'
            'subprocess.run(["python", "-m", "safefliplab", "smoke", '
            '"--max-episodes", "24"])\n'
        )
        v = guard._scan_text(Path("t.py"), text)
        self.assertTrue(any("billed phase" in x for x in v), v)

    def test_cli_list_pilot_is_blocked_outside_refusal_files(self):
        text = 'from safefliplab.cli import main\nmain(["pilot", "--max-episodes", "240"])\n'
        v = guard._scan_text(Path("t_evil.py"), text)
        self.assertTrue(any("CLI phase entrypoint" in x for x in v), v)

    def test_real_adapter_construction_is_blocked(self):
        text = "from safefliplab.adapter import ScenarioAdapter\nadapter = ScenarioAdapter()\n"
        v = guard._scan_text(Path("t.py"), text)
        self.assertTrue(any("real adapter" in x for x in v), v)

    def test_real_simulator_import_is_blocked(self):
        text = "from cornercaselab.simulator import HighwayEnvAdapter\n"
        v = guard._scan_text(Path("t.py"), text)
        self.assertTrue(any("simulator import" in x for x in v), v)


class TestOfflineGuardScriptExit(unittest.TestCase):
    """End-to-end: the script exits 1 on a planted violation, 0 on a clean tree."""

    def test_main_exit_codes(self):
        with tempfile.TemporaryDirectory() as td:
            good = Path(td) / "good.py"
            good.write_text("x = 1\n", encoding="utf-8")
            self.assertEqual(guard.main([td]), 0)

            evil = Path(td) / "evil.py"
            evil.write_text(
                'import subprocess\nsubprocess.run(["python","-m","safefliplab","formal","--confirm"])\n',
                encoding="utf-8",
            )
            self.assertEqual(guard.main([td]), 1)


if __name__ == "__main__":
    unittest.main()

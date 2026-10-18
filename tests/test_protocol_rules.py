"""Protocol rule freezing, methods-consistency, and formal safety boundary.

Covers:
* the frozen nomination/selection rule descriptions equal the config's strings;
* ``validate_method_rules`` cross-checks the declared rules against the ACTUAL
  sort keys in ``safefliplab.methods`` (so editing either one alone fails);
* ``validate_formal_config`` surfaces that drift;
* ``strict_design=False`` is refused for anything that is not an explicit test
  double, so it can never be used to run a real formal simulation.

No simulator is imported and no episode is launched.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from safefliplab import methods, protocol
from safefliplab.experiments import _execute_formal_phase
from safefliplab.protocol import (
    FROZEN_DESIGN,
    FormalConfigError,
    validate_formal_config,
    validate_method_rules,
)
from tests.fakes import FakeAdapter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_CONFIG = PROJECT_ROOT / "configs" / "formal_v01.json"


def real_config() -> dict:
    return json.loads(REAL_CONFIG.read_text(encoding="utf-8"))


class TestFrozenRuleDescriptions(unittest.TestCase):
    def test_config_rule_strings_equal_frozen(self):
        cfg = real_config()
        self.assertEqual(cfg["wide_explore"]["nomination_rule"],
                         protocol.WIDE_NOMINATION_RULE)
        self.assertEqual(cfg["verify_first"]["selection_rule"],
                         protocol.VERIFY_SELECTION_RULE)
        self.assertEqual(cfg["verify_first"]["nomination_pool"],
                         protocol.VERIFY_NOMINATION_POOL)
        self.assertEqual(cfg["verify_first"]["nomination_rule"],
                         protocol.VERIFY_NOMINATION_RULE)

    def test_frozen_design_carries_rule_strings(self):
        self.assertEqual(FROZEN_DESIGN["wide_explore"]["nomination_rule"],
                         protocol.WIDE_NOMINATION_RULE)
        self.assertEqual(FROZEN_DESIGN["verify_first"]["selection_rule"],
                         protocol.VERIFY_SELECTION_RULE)

    def test_real_config_valid_and_rules_consistent(self):
        self.assertEqual(validate_method_rules(), [])
        self.assertTrue(validate_formal_config(real_config())["valid"])

    def test_rule_text_drift_is_rejected(self):
        cfg = real_config()
        cfg["wide_explore"]["nomination_rule"] = "shortened description"
        with self.assertRaises(FormalConfigError) as ctx:
            validate_formal_config(cfg)
        self.assertTrue(any("wide_explore" in i for i in ctx.exception.issues))

    def test_fingerprint_covers_rule_text(self):
        cfg = real_config()
        before = protocol.formal_config_fingerprint(cfg)
        cfg["verify_first"]["selection_rule"] = "changed"
        self.assertNotEqual(protocol.formal_config_fingerprint(cfg), before)


class TestMethodsConsistency(unittest.TestCase):
    def test_implementation_drift_is_detected(self):
        """If the methods sort key changes without the declared rule (or vice
        versa) the cross-check must fail loudly."""
        def wrong_key(record):
            # swapped tie-break: anchor_id before first_seen
            return (-record.mean_delta("11"), record.anchor_id, record.index)

        with patch.object(methods, "wide_nomination_key", wrong_key):
            issues = validate_method_rules()
        self.assertTrue(any("wide_nomination" in i for i in issues), issues)

    def test_drift_surfaces_through_config_validation(self):
        def wrong_key(record):
            return (-record.mean_delta("11"), record.anchor_id, record.index)

        with patch.object(methods, "wide_nomination_key", wrong_key):
            with self.assertRaises(FormalConfigError) as ctx:
                validate_formal_config(real_config())
        self.assertTrue(any("rule" in i for i in ctx.exception.issues))

    def test_all_three_rule_functions_present(self):
        for rule in protocol.FROZEN_RULES.values():
            self.assertTrue(hasattr(methods, rule["methods_key"]))


class TestStrictDesignBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg_path = self.root / "formal.json"
        self.cfg_path.write_text(json.dumps({"formal_master_seeds": [111, 222]}),
                                 encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_non_test_double_refused_with_relaxed_design(self):
        class _Realish:
            is_test_double = False

            def run_episode(self, *a, **k):  # pragma: no cover - must not run
                raise AssertionError("real simulator must not be driven")

        with self.assertRaises(PermissionError):
            _execute_formal_phase(self.root, self.cfg_path, adapter=_Realish(),
                                  strict_design=False)

    def test_none_adapter_refused_with_relaxed_design(self):
        with self.assertRaises(PermissionError):
            _execute_formal_phase(self.root, self.cfg_path, adapter=None,
                                  strict_design=False)

    def test_test_double_allowed_with_relaxed_design(self):
        # A test double is the sole legitimate user of strict_design=False.
        # (Plan sizes are not scaled here, so this just proves the guard passes
        #  and validation is reached; it does not run to completion.)
        from safefliplab.protocol import validate_formal_config as vfc
        self.assertTrue(vfc({"formal_master_seeds": [111, 222]},
                            strict_design=False, expected_master_seed_count=2)["valid"])
        self.assertTrue(getattr(FakeAdapter(), "is_test_double", False))


if __name__ == "__main__":
    unittest.main()

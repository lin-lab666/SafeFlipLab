"""Frozen formal-config drift guard (no episodes launched, no simulator used).

Formal config validation must catch: wrong seed count, duplicate seeds,
reordered / altered frozen seeds, altered budget / plan / simulator values,
wrong protocol id, and a mismatched protocol fingerprint. It must also allow the
scaled FakeAdapter integration plan through in non-strict mode.
"""
import copy
import json
import unittest
from pathlib import Path

from safefliplab.protocol import (
    FormalConfigError,
    formal_config_fingerprint,
    frozen_protocol_fingerprint,
    validate_formal_config,
)
from safefliplab.seeds import FORMAL_MASTER_SEED_COUNT, formal_master_seeds

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_CONFIG = PROJECT_ROOT / "configs" / "formal_v01.json"


def real_config() -> dict:
    return json.loads(REAL_CONFIG.read_text(encoding="utf-8"))


class TestFrozenFormalConfig(unittest.TestCase):
    def test_real_config_is_valid_and_frozen(self):
        cfg = real_config()
        result = validate_formal_config(cfg)
        self.assertTrue(result["valid"])
        self.assertTrue(result["strict"])
        # The design of the on-disk config must match the code-frozen design.
        self.assertEqual(result["fingerprint"], frozen_protocol_fingerprint())
        self.assertEqual(result["seeds"], formal_master_seeds())
        self.assertEqual(len(result["seeds"]), FORMAL_MASTER_SEED_COUNT)

    def test_fingerprint_is_stable(self):
        self.assertEqual(frozen_protocol_fingerprint(), frozen_protocol_fingerprint())
        self.assertEqual(len(frozen_protocol_fingerprint()), 64)

    def test_duplicate_seeds_rejected(self):
        cfg = real_config()
        cfg["formal_master_seeds"][1] = cfg["formal_master_seeds"][0]
        with self.assertRaises(FormalConfigError) as ctx:
            validate_formal_config(cfg)
        self.assertTrue(any("unique" in i for i in ctx.exception.issues))

    def test_reordered_seeds_rejected(self):
        cfg = real_config()
        cfg["formal_master_seeds"][0], cfg["formal_master_seeds"][1] = (
            cfg["formal_master_seeds"][1], cfg["formal_master_seeds"][0])
        with self.assertRaises(FormalConfigError) as ctx:
            validate_formal_config(cfg)
        self.assertTrue(any("order" in i or "derivation" in i for i in ctx.exception.issues))

    def test_modified_seed_value_rejected(self):
        cfg = real_config()
        cfg["formal_master_seeds"][3] = 123456789
        with self.assertRaises(FormalConfigError):
            validate_formal_config(cfg)

    def test_wrong_seed_count_rejected(self):
        cfg = real_config()
        cfg["formal_master_seeds"] = cfg["formal_master_seeds"][:4]
        with self.assertRaises(FormalConfigError) as ctx:
            validate_formal_config(cfg)
        self.assertTrue(any("master seeds" in i for i in ctx.exception.issues))

    def test_non_int_seeds_rejected(self):
        cfg = real_config()
        cfg["formal_master_seeds"][0] = "3451794858"
        with self.assertRaises(FormalConfigError):
            validate_formal_config(cfg)

    def test_modified_budget_rejected(self):
        cfg = real_config()
        cfg["budget"]["episodes_per_method_seed"] = 799
        with self.assertRaises(FormalConfigError) as ctx:
            validate_formal_config(cfg)
        self.assertTrue(any("budget" in i for i in ctx.exception.issues))

    def test_modified_plan_rejected(self):
        cfg = real_config()
        cfg["wide_explore"]["discovery_anchors"] = 99
        with self.assertRaises(FormalConfigError) as ctx:
            validate_formal_config(cfg)
        self.assertTrue(any("wide_explore" in i for i in ctx.exception.issues))

        cfg2 = real_config()
        cfg2["verify_first"]["extra_quartets_per_selected"] = 4
        with self.assertRaises(FormalConfigError):
            validate_formal_config(cfg2)

    def test_modified_simulator_cadence_rejected(self):
        cfg = real_config()
        cfg["simulator"]["simulation_hz"] = 10
        with self.assertRaises(FormalConfigError) as ctx:
            validate_formal_config(cfg)
        self.assertTrue(any("simulator" in i for i in ctx.exception.issues))

    def test_wrong_protocol_id_rejected(self):
        cfg = real_config()
        cfg["protocol"] = "SafeFlipLab-v02"
        with self.assertRaises(FormalConfigError) as ctx:
            validate_formal_config(cfg)
        self.assertTrue(any("protocol" in i for i in ctx.exception.issues))

    def test_wrong_controller_policy_rejected(self):
        cfg = real_config()
        cfg["controller_policy"] = "aggressive"
        with self.assertRaises(FormalConfigError):
            validate_formal_config(cfg)

    def test_declared_fingerprint_mismatch_rejected(self):
        cfg = real_config()
        cfg["protocol_fingerprint"] = "0" * 64
        with self.assertRaises(FormalConfigError) as ctx:
            validate_formal_config(cfg)
        self.assertTrue(any("fingerprint" in i for i in ctx.exception.issues))

    def test_declared_fingerprint_match_accepted(self):
        cfg = real_config()
        cfg["protocol_fingerprint"] = frozen_protocol_fingerprint()
        result = validate_formal_config(cfg)
        self.assertTrue(result["valid"])

    def test_fingerprint_changes_when_design_changes(self):
        cfg = real_config()
        before = formal_config_fingerprint(cfg)
        cfg["budget"]["total_episodes"] = 12801
        self.assertNotEqual(formal_config_fingerprint(cfg), before)


class TestNonStrictScaledConfig(unittest.TestCase):
    """The scaled integration tests opt out of frozen-design comparison but must
    still get the structural guards (count, uniqueness, int type)."""

    def test_scaled_seed_list_accepted(self):
        cfg = {"formal_master_seeds": [111, 222]}
        result = validate_formal_config(cfg, strict_design=False,
                                        expected_master_seed_count=2)
        self.assertTrue(result["valid"])
        self.assertFalse(result["strict"])

    def test_scaled_duplicate_still_rejected(self):
        cfg = {"formal_master_seeds": [111, 111]}
        with self.assertRaises(FormalConfigError):
            validate_formal_config(cfg, strict_design=False,
                                   expected_master_seed_count=2)

    def test_scaled_wrong_count_still_rejected(self):
        cfg = {"formal_master_seeds": [111]}
        with self.assertRaises(FormalConfigError):
            validate_formal_config(cfg, strict_design=False,
                                   expected_master_seed_count=2)

    def test_scaled_non_int_still_rejected(self):
        cfg = {"formal_master_seeds": [111, 222.5]}
        with self.assertRaises(FormalConfigError):
            validate_formal_config(cfg, strict_design=False,
                                   expected_master_seed_count=2)


class TestRealConfigFileUntouched(unittest.TestCase):
    def test_real_config_still_has_eight_frozen_seeds(self):
        cfg = real_config()
        self.assertEqual(cfg["formal_master_seeds"], formal_master_seeds())
        self.assertEqual(cfg["budget"]["total_episodes"], 12800)
        # a deep copy round-trip must not mutate the file
        copy.deepcopy(cfg)


if __name__ == "__main__":
    unittest.main()

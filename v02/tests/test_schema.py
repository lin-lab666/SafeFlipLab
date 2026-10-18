"""Config schema tests: explicit statuses, UNSET gating, strict extras."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v02lab import schema  # noqa: E402

CFG_DIR = Path(__file__).resolve().parents[1] / "configs"


def _load():
    sc = schema.load_json(CFG_DIR / "v02_proposed_schema.json")
    cfg = schema.load_json(CFG_DIR / "v02_proposed_config.json")
    return cfg, sc


class TestShippedConfig(unittest.TestCase):
    def test_shipped_config_is_valid(self):
        cfg, sc = _load()
        self.assertEqual(schema.validate_config(cfg, sc), [])

    def test_no_silent_defaults(self):
        cfg, _ = _load()
        schema.assert_no_silent_defaults(cfg)

    def test_unset_has_null_value(self):
        cfg, _ = _load()
        self.assertIsNone(cfg["parameters"]["tau_cap_s"]["value"])
        self.assertEqual(cfg["parameters"]["tau_cap_s"]["status"], "UNSET")


class TestResolve(unittest.TestCase):
    def test_resolve_unset_raises(self):
        cfg, _ = _load()
        with self.assertRaises(schema.UnsetParameterError):
            schema.resolve(cfg, "tau_cap_s")

    def test_resolve_proposed_returns_value(self):
        cfg, _ = _load()
        self.assertEqual(schema.resolve(cfg, "gap_intervention_m"), 2.0)

    def test_require_frozen_rejects_proposed(self):
        cfg, _ = _load()
        with self.assertRaises(schema.UnsetParameterError):
            schema.require_frozen(cfg, "gap_intervention_m")

    def test_status_of(self):
        cfg, _ = _load()
        self.assertEqual(schema.status_of(cfg, "tau_cap_s"), "UNSET")
        self.assertEqual(schema.status_of(cfg, "alpha"), "PROPOSED")


class TestValidationRules(unittest.TestCase):
    def setUp(self):
        cfg, sc = _load()
        # shallow copies good enough for structural edits
        self.cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in cfg.items()}
        self.cfg["parameters"] = {k: dict(v) for k, v in cfg["parameters"].items()}
        self.sc = sc

    def test_missing_status_is_violation(self):
        self.cfg["parameters"]["alpha"] = {"value": 0.05}
        self.assertTrue(any("status" in p for p in schema.validate_config(self.cfg, self.sc)))

    def test_unset_with_value_is_violation(self):
        self.cfg["parameters"]["tau_cap_s"] = {"status": "UNSET", "value": 30.0}
        self.assertTrue(any("UNSET requires value=null" in p
                            for p in schema.validate_config(self.cfg, self.sc)))

    def test_wrong_type_is_violation(self):
        self.cfg["parameters"]["alpha"] = {"status": "PROPOSED", "value": "high"}
        self.assertTrue(any("declared type" in p for p in schema.validate_config(self.cfg, self.sc)))

    def test_extra_parameter_is_violation(self):
        self.cfg["parameters"]["mystery"] = {"status": "PROPOSED", "value": 1}
        self.assertTrue(any("absent from schema" in p for p in schema.validate_config(self.cfg, self.sc)))

    def test_allowed_value_enforced(self):
        self.cfg["parameters"]["no_candidate_policy"] = {"status": "PROPOSED", "value": "guess"}
        self.assertTrue(any("not in allowed" in p for p in schema.validate_config(self.cfg, self.sc)))


if __name__ == "__main__":
    unittest.main()

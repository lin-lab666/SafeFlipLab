"""Four-condition legality, shared perturbation and SHA-256 derivation (pure)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v02lab import conditions as C  # noqa: E402
from v02lab.schema import UnsetParameterError  # noqa: E402

BOUNDS = {
    "front_gap": (18.0, 80.0),
    "ego_speed": (20.0, 32.0),
    "front_speed": (15.0, 32.0),
}


class TestConditions(unittest.TestCase):
    def test_offsets(self):
        self.assertEqual(C.condition_offsets("00", 2.0, 1.0), (0.0, 0.0))
        self.assertEqual(C.condition_offsets("10", 2.0, 1.0), (2.0, 0.0))
        self.assertEqual(C.condition_offsets("01", 2.0, 1.0), (0.0, -1.0))
        self.assertEqual(C.condition_offsets("11", 2.0, 1.0), (2.0, -1.0))

    def test_bad_condition(self):
        with self.assertRaises(ValueError):
            C.condition_offsets("99", 2.0, 1.0)

    def test_apply_does_not_mutate(self):
        a = {"front_gap": 30.0, "ego_speed": 25.0}
        b = C.apply_condition(a, "11", 2.0, 1.0)
        self.assertEqual(a, {"front_gap": 30.0, "ego_speed": 25.0})
        self.assertEqual(b, {"front_gap": 32.0, "ego_speed": 24.0})

    def test_quartet_legality_ok(self):
        ok, per = C.quartet_legality({"front_gap": 40.0, "ego_speed": 25.0, "front_speed": 25.0},
                                     2.0, 1.0, BOUNDS)
        self.assertTrue(ok)
        self.assertEqual(per["11"], [])

    def test_quartet_legality_detects_out_of_bounds(self):
        # gap 79 + 2 = 81 > 80 -> illegal for condition 10/11
        ok, per = C.quartet_legality({"front_gap": 79.0, "ego_speed": 25.0, "front_speed": 25.0},
                                     2.0, 1.0, BOUNDS)
        self.assertFalse(ok)
        self.assertTrue(per["00"] == [])
        self.assertTrue(any("front_gap" in r for r in per["11"]))

    def test_legality_reports_missing(self):
        reasons = C.legality_reasons({"front_gap": 30.0}, BOUNDS)
        self.assertTrue(any("missing" in r for r in reasons))


class TestDerivation(unittest.TestCase):
    def test_derive_deterministic(self):
        self.assertEqual(C.derive_seed(7, "a", "b"), C.derive_seed(7, "a", "b"))

    def test_derive_label_sensitive(self):
        self.assertNotEqual(C.derive_seed(7, "a"), C.derive_seed(7, "b"))

    def test_derive_seed_range(self):
        self.assertTrue(0 <= C.derive_seed(7, "x") < 2**32)

    def test_sim_seed_ignores_condition_but_tracks_stream(self):
        a = C.sim_seed_for(1, "WideExplore", "discovery", "anchor-0000", 0)
        # condition is not a label -> two conditions of one quartet share the seed
        b = C.sim_seed_for(1, "WideExplore", "discovery", "anchor-0000", 0)
        c = C.sim_seed_for(1, "WideExplore", "audit", "anchor-0000", 0)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_sim_seed_rejects_bad_stream(self):
        with self.assertRaises(ValueError):
            C.sim_seed_for(1, "m", "bogus", "anchor-0000", 0)


class TestSharedPerturbation(unittest.TestCase):
    SPEC = {"lead_speed": {"low": -0.5, "high": 0.5},
            "front_gap": {"low": -2.0, "high": 2.0}}

    def test_draws_deterministic(self):
        kw = dict(anchor_index=3, repetition=1, stream="discovery", spec=self.SPEC)
        self.assertEqual(C.perturbation_draws(11, **kw), C.perturbation_draws(11, **kw))

    def test_draws_bounded(self):
        d = C.perturbation_draws(11, anchor_index=3, repetition=1, stream="discovery", spec=self.SPEC)
        self.assertTrue(-0.5 <= d["lead_speed"] <= 0.5)
        self.assertTrue(-2.0 <= d["front_gap"] <= 2.0)

    def test_shared_alias_matches(self):
        kw = dict(anchor_index=3, repetition=1, stream="discovery", spec=self.SPEC)
        self.assertEqual(C.shared_perturbation_for_quartet(11, **kw),
                         C.perturbation_draws(11, **kw))

    def test_unset_bound_raises(self):
        bad = {"lead_speed": {"low": None, "high": 0.5}}
        with self.assertRaises(UnsetParameterError):
            C.perturbation_draws(11, anchor_index=0, repetition=0, stream="discovery", spec=bad)


if __name__ == "__main__":
    unittest.main()

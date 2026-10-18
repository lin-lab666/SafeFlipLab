"""Domain, quartet and legality tests (no simulator involved)."""
import unittest

from cornercaselab.domain import BOUNDS, Scenario

from safefliplab.domain import (
    ANCHOR_BOUNDS,
    GAP_INTERVENTION_M,
    SPEED_INTERVENTION_MPS,
    anchor_bounds_report,
    anchor_in_domain,
    condition_scenario,
    quartet_scenarios,
)


def make(**kw):
    base = dict(ego_speed=27.0, front_gap=45.0, front_speed=25.0,
                ramp_x=110.0, ramp_speed=20.0, ramp_target_speed=30.0)
    base.update(kw)
    return Scenario(**base)


class TestAnchorDomain(unittest.TestCase):
    def test_anchor_bounds_tighten_intervened_dims(self):
        self.assertEqual(ANCHOR_BOUNDS["front_gap"],
                         (BOUNDS["front_gap"][0], BOUNDS["front_gap"][1] - 2.0))
        self.assertEqual(ANCHOR_BOUNDS["ego_speed"],
                         (BOUNDS["ego_speed"][0] + 1.0, BOUNDS["ego_speed"][1]))
        # untouched dims keep upstream bounds
        for dim in ("front_speed", "ramp_x", "ramp_speed", "ramp_target_speed"):
            self.assertEqual(ANCHOR_BOUNDS[dim], BOUNDS[dim])

    def test_legal_anchor(self):
        self.assertTrue(anchor_in_domain(make(front_gap=78.0, ego_speed=21.0)))

    def test_illegal_anchor_gap(self):
        # inside upstream bounds [18, 80] but outside the tightened anchor
        # domain [18, 78]: the +2 m intervention would leave the domain.
        self.assertFalse(anchor_in_domain(make(front_gap=78.5)))
        self.assertFalse(anchor_in_domain(make(front_gap=80.0)))

    def test_illegal_anchor_speed(self):
        self.assertFalse(anchor_in_domain(make(ego_speed=20.5)))
        self.assertFalse(anchor_in_domain(make(ego_speed=20.0)))

    def test_bounds_report(self):
        report = anchor_bounds_report()
        self.assertEqual(set(report), set(BOUNDS))
        self.assertEqual(report["front_gap"]["anchor_high"], 78.0)
        self.assertEqual(report["ego_speed"]["anchor_low"], 21.0)


class TestQuartet(unittest.TestCase):
    def test_condition_00_is_identity(self):
        anchor = make()
        self.assertEqual(condition_scenario(anchor, "00"), anchor)

    def test_condition_10_only_gap(self):
        anchor = make(front_gap=40.0, ego_speed=27.0)
        s = condition_scenario(anchor, "10")
        self.assertAlmostEqual(s.front_gap, 42.0)
        self.assertAlmostEqual(s.ego_speed, 27.0)

    def test_condition_01_only_speed(self):
        anchor = make(front_gap=40.0, ego_speed=27.0)
        s = condition_scenario(anchor, "01")
        self.assertAlmostEqual(s.ego_speed, 26.0)
        self.assertAlmostEqual(s.front_gap, 40.0)

    def test_condition_11_both(self):
        anchor = make(front_gap=40.0, ego_speed=27.0)
        s = condition_scenario(anchor, "11")
        self.assertAlmostEqual(s.front_gap, 42.0)
        self.assertAlmostEqual(s.ego_speed, 26.0)

    def test_other_dims_unchanged(self):
        anchor = make()
        q = quartet_scenarios(anchor)
        for cond, s in q.items():
            self.assertEqual(s.front_speed, anchor.front_speed)
            self.assertEqual(s.ramp_x, anchor.ramp_x)
            self.assertEqual(s.ramp_speed, anchor.ramp_speed)
            self.assertEqual(s.ramp_target_speed, anchor.ramp_target_speed)

    def test_no_clipping_raises_instead(self):
        """An anchor whose intervention would leave the upstream domain must
        not be clipped: building the illegal condition must raise."""
        gap_edge = make(front_gap=79.0)   # upstream-legal, anchor-illegal
        with self.assertRaises(ValueError):
            condition_scenario(gap_edge, "10")
        speed_edge = make(ego_speed=20.5)  # upstream-legal, anchor-illegal
        with self.assertRaises(ValueError):
            condition_scenario(speed_edge, "01")

    def test_illegal_condition_raises(self):
        with self.assertRaises(ValueError):
            condition_scenario(make(), "99")

    def test_quartet_has_all_four_conditions(self):
        q = quartet_scenarios(make())
        self.assertEqual(sorted(q), ["00", "01", "10", "11"])

    def test_intervention_sizes(self):
        self.assertEqual(GAP_INTERVENTION_M, 2.0)
        self.assertEqual(SPEED_INTERVENTION_MPS, 1.0)


if __name__ == "__main__":
    unittest.main()

"""Tests for the anchor-level sample-size derivation (no research defaults)."""
import unittest

from v02lab.power import (Z_975, adjusted_alpha, anchor_sd, mde_at_n,
                          normal_quantile, plan, required_anchors)


class TestNormalQuantile(unittest.TestCase):
    def test_known_values(self):
        self.assertAlmostEqual(normal_quantile(0.975), Z_975, places=6)
        self.assertAlmostEqual(normal_quantile(0.5), 0.0, places=6)
        self.assertAlmostEqual(normal_quantile(0.80), 0.8416212, places=5)

    def test_domain(self):
        for bad in (0.0, 1.0, -0.1, 1.1):
            with self.assertRaises(ValueError):
                normal_quantile(bad)


class TestSizing(unittest.TestCase):
    def test_monotone_in_mde_and_sd(self):
        small = required_anchors(sd=0.1, mde=0.1, alpha=0.05, power=0.8)
        big = required_anchors(sd=0.1, mde=0.05, alpha=0.05, power=0.8)
        self.assertGreater(big, small)
        more_sd = required_anchors(sd=0.2, mde=0.1, alpha=0.05, power=0.8)
        self.assertGreater(more_sd, small)
        # quadrupling sd quadruples n (n is proportional to sd^2)
        self.assertAlmostEqual(more_sd / small, 4.0, delta=0.5)

    def test_alpha_and_power_direction(self):
        strict = required_anchors(sd=0.15, mde=0.1, alpha=0.0125, power=0.8)
        loose = required_anchors(sd=0.15, mde=0.1, alpha=0.05, power=0.8)
        self.assertGreater(strict, loose)
        high_power = required_anchors(sd=0.15, mde=0.1, alpha=0.05, power=0.95)
        self.assertGreater(high_power, loose)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            required_anchors(sd=0.0, mde=0.1, alpha=0.05, power=0.8)
        with self.assertRaises(ValueError):
            required_anchors(sd=0.1, mde=0.0, alpha=0.05, power=0.8)
        with self.assertRaises(ValueError):
            required_anchors(sd=0.1, mde=0.1, alpha=1.0, power=0.8)

    def test_mde_at_n_is_inverse_of_sizing(self):
        n = required_anchors(sd=0.12, mde=0.08, alpha=0.05, power=0.8)
        back = mde_at_n(sd=0.12, n=n, alpha=0.05, power=0.8)
        self.assertLessEqual(back, 0.08 + 1e-12)

    def test_no_defaults_multiplicity(self):
        self.assertAlmostEqual(adjusted_alpha(0.05, 4, "bonferroni"), 0.0125)
        self.assertAlmostEqual(adjusted_alpha(0.05, 4, "holm_worst_case"), 0.0125)
        self.assertAlmostEqual(adjusted_alpha(0.05, 4, "none"), 0.05)
        with self.assertRaises(ValueError):
            adjusted_alpha(0.05, 4, "unknown_rule")


class TestAnchorSd(unittest.TestCase):
    def test_sample_sd(self):
        self.assertAlmostEqual(anchor_sd([1.0, 3.0]), 2.0 ** 0.5, places=9)

    def test_ignores_none_and_needs_two(self):
        self.assertIsNone(anchor_sd([1.0, None]))
        self.assertIsNone(anchor_sd([]))

    def test_plan_reports_required_anchors_and_episodes(self):
        p = plan(contrast_sd={"delta_both": 0.10, "i_lin": 0.20}, mde=0.10,
                 alpha=0.05, power=0.8, rule="holm_worst_case",
                 repetitions=3, methods=1, seeds=1)
        self.assertEqual(p["family_size"], 2)
        self.assertAlmostEqual(p["alpha_per_contrast"], 0.025)
        # i_lin has twice the sd, so needs ~4x the anchors
        nb = p["per_contrast"]["delta_both"]["n_anchors"]
        ni = p["per_contrast"]["i_lin"]["n_anchors"]
        self.assertGreater(ni, nb)
        self.assertEqual(p["required_anchors"], max(nb, ni))
        self.assertEqual(p["required_episodes"], p["required_anchors"] * 3 * 4)

    def test_plan_rejects_bad_scale(self):
        with self.assertRaises(ValueError):
            plan(contrast_sd={"a": 0.1}, mde=0.1, alpha=0.05, power=0.8,
                 rule="none", repetitions=0, methods=1, seeds=1)


if __name__ == "__main__":
    unittest.main()

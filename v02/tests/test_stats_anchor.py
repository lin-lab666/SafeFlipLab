"""Anchor-level estimates and GATED confirmatory tests (pure)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v02lab.stats_anchor import (  # noqa: E402
    SamplingAssumption,
    anchor_contrast,
    cluster_bootstrap_ci,
    confirmatory_status,
    estimate,
    max_t_test,
    sign_flip_test,
    unproven_assumption,
)


class TestAnchorContrast(unittest.TestCase):
    def test_delta_both_mean_over_reps(self):
        reps = [{"00": 3, "10": 4, "01": 4, "11": 5}, {"00": 1, "10": 2, "01": 2, "11": 3}]
        self.assertAlmostEqual(anchor_contrast(reps, "delta_both"), 2.0)

    def test_i_lin(self):
        reps = [{"00": 3, "10": 4, "01": 4, "11": 5}, {"00": 1, "10": 2, "01": 2, "11": 3}]
        # per rep: 0 and 0
        self.assertAlmostEqual(anchor_contrast(reps, "i_lin"), 0.0)

    def test_missing_rep_skipped(self):
        reps = [{"00": 3, "10": 4, "01": 4, "11": 5},
                {"00": None, "10": 2, "01": 2, "11": 3}]
        self.assertAlmostEqual(anchor_contrast(reps, "delta_both"), 2.0)

    def test_all_missing_is_none(self):
        reps = [{"00": None, "10": None, "01": None, "11": None}]
        self.assertIsNone(anchor_contrast(reps, "delta_both"))

    def test_bad_contrast(self):
        with self.assertRaises(ValueError):
            anchor_contrast([], "nope")


class TestBootstrap(unittest.TestCase):
    def test_deterministic_and_ordered(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        a = cluster_bootstrap_ci(vals, b_resamples=500, alpha=0.05, seed=7)
        b = cluster_bootstrap_ci(vals, b_resamples=500, alpha=0.05, seed=7)
        self.assertEqual(a, b)
        self.assertLessEqual(a[0], a[1])

    def test_too_few(self):
        self.assertEqual(cluster_bootstrap_ci([1.0], b_resamples=100, alpha=0.05, seed=1),
                         (None, None))

    def test_estimate_zero_variance_note(self):
        est = estimate("delta_both", [2.0, 2.0, 2.0], b_resamples=200, alpha=0.05, seed=3)
        self.assertIn("zero variance", est.note)

    def test_estimate_insufficient_note(self):
        est = estimate("delta_both", [1.0, None], b_resamples=200, alpha=0.05, seed=3)
        self.assertIn("not estimable", est.note)


class TestGating(unittest.TestCase):
    def test_sign_flip_default_pending(self):
        t = sign_flip_test([1.0, -1.0, 2.0, -2.0], b_resamples=200, seed=1, assumption=None)
        self.assertEqual(t.status, "PENDING")
        self.assertIsNone(t.p_value)

    def test_sign_flip_unproven_pending(self):
        t = sign_flip_test([1.0, -1.0, 2.0, -2.0], b_resamples=200, seed=1,
                           assumption=unproven_assumption())
        self.assertEqual(t.status, "PENDING")
        self.assertIsNone(t.p_value)

    def test_sign_flip_eligible_produces_p(self):
        assumed = SamplingAssumption(unit="anchor", basis="A", justification_ref="PRE-REG#1",
                                     status="FROZEN")
        t = sign_flip_test([1.0, -1.0, 2.0, -2.0], b_resamples=400, seed=1, assumption=assumed)
        self.assertEqual(t.status, "OK")
        self.assertIsNotNone(t.p_value)
        self.assertTrue(0.0 < t.p_value <= 1.0)

    def test_max_t_gated(self):
        t = max_t_test({"delta_both": [1.0, 2.0, 3.0], "i_lin": [0.0, 1.0, -1.0]},
                       b_resamples=200, seed=1, assumption=None)
        self.assertEqual(t.status, "PENDING")
        self.assertIsNone(t.p_value)

    def test_confirmatory_status(self):
        self.assertEqual(confirmatory_status(None), "PENDING")
        assumed = SamplingAssumption(unit="anchor", basis="B", justification_ref="REF",
                                     status="FROZEN")
        self.assertEqual(confirmatory_status(assumed), "ELIGIBLE")


if __name__ == "__main__":
    unittest.main()

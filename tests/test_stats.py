"""Statistics tests: empty results, no-reversal cases, paired metrics."""
import unittest

from safefliplab.stats import (
    aggregate,
    paired_delta_series,
    quartet_metrics,
    summarise_conditions,
)

ALL_ZERO = {"00": 0, "10": 0, "01": 0, "11": 0}
REVERSE = {"00": 0, "10": 0, "01": 0, "11": 1}
RESCUE = {"00": 1, "10": 1, "01": 1, "11": 0}
MIXED = {"00": 1, "10": 0, "01": 1, "11": 0}
INTERACTING = {"00": 0, "10": 1, "01": 1, "11": 0}


class TestQuartetMetrics(unittest.TestCase):
    def test_all_zero(self):
        m = quartet_metrics(ALL_ZERO)
        self.assertEqual((m.delta_both, m.delta_gap, m.delta_speed, m.interaction), (0, 0, 0, 0))
        self.assertEqual((m.reverse, m.rescue), (0, 0))

    def test_reverse_pair(self):
        m = quartet_metrics(REVERSE)
        self.assertEqual(m.delta_both, 1)
        self.assertEqual(m.reverse, 1)
        self.assertEqual(m.rescue, 0)

    def test_rescue_pair(self):
        m = quartet_metrics(RESCUE)
        self.assertEqual(m.delta_both, -1)
        self.assertEqual(m.rescue, 1)
        self.assertEqual(m.reverse, 0)

    def test_interaction_sign(self):
        m = quartet_metrics(INTERACTING)  # 0,1,1,0 -> -1-1+0+... check formula
        # interaction = Y11 - Y10 - Y01 + Y00 = 0 - 1 - 1 + 0 = -2
        self.assertEqual(m.interaction, -2)
        self.assertEqual(m.delta_both, 0)

    def test_incomplete_rejected(self):
        with self.assertRaises(ValueError):
            quartet_metrics({"00": 0, "10": 0, "01": 0})
        with self.assertRaises(ValueError):
            quartet_metrics({"00": 2, "10": 0, "01": 0, "11": 0})


class TestAggregate(unittest.TestCase):
    def test_empty_is_none_not_zero(self):
        agg = aggregate([])
        self.assertEqual(agg.n_quartets, 0)
        self.assertIsNone(agg.mean_delta_both)
        self.assertIsNone(agg.mean_delta_gap)
        self.assertIsNone(agg.mean_delta_speed)
        self.assertIsNone(agg.mean_interaction)
        self.assertEqual(agg.reverse_pairs, 0)
        self.assertEqual(agg.rescue_pairs, 0)
        self.assertEqual(set(agg.collision_rate.values()), {None})

    def test_incomplete_quartets_excluded(self):
        agg = aggregate([ALL_ZERO, {"00": 0, "10": 1, "01": 0}])
        self.assertEqual(agg.n_quartets, 1)
        self.assertEqual(agg.mean_delta_both, 0)

    def test_means_and_counts(self):
        agg = aggregate([REVERSE, RESCUE, ALL_ZERO])
        self.assertEqual(agg.n_quartets, 3)
        self.assertAlmostEqual(agg.mean_delta_both, 0.0)
        self.assertEqual(agg.reverse_pairs, 1)
        self.assertEqual(agg.rescue_pairs, 1)
        self.assertAlmostEqual(agg.collision_rate["00"], 1 / 3)
        self.assertAlmostEqual(agg.collision_rate["11"], 1 / 3)

    def test_summarise_conditions_matches(self):
        rates = summarise_conditions([REVERSE, RESCUE])
        self.assertAlmostEqual(rates["00"], 0.5)
        self.assertAlmostEqual(rates["11"], 0.5)


class TestPairedSeries(unittest.TestCase):
    def test_series_per_condition(self):
        self.assertEqual(paired_delta_series([REVERSE, RESCUE], "11"), [1.0, -1.0])
        self.assertEqual(paired_delta_series([REVERSE, RESCUE], "10"), [0.0, 0.0])
        self.assertEqual(paired_delta_series([MIXED], "10"), [-1.0])

    def test_series_rejects_condition_00(self):
        with self.assertRaises(ValueError):
            paired_delta_series([REVERSE], "00")


if __name__ == "__main__":
    unittest.main()

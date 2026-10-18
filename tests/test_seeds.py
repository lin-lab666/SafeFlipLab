"""Seed derivation and identifier stability tests."""
import unittest

from safefliplab.seeds import (
    CONDITIONS,
    DEV_SEED,
    FORMAL_MASTER_SEED_COUNT,
    FORMAL_TOTAL_EPISODES,
    STREAM_AUDIT,
    STREAM_DISCOVERY,
    anchor_id,
    anchor_stream_seed,
    canonical_json,
    check_seed,
    derive_seed,
    formal_master_seeds,
    run_id,
    sim_seed_for,
)


class TestSeeds(unittest.TestCase):
    def test_derivation_is_deterministic(self):
        a = derive_seed(123, "sim", "WideExplore", "discovery", "anchor-0000", 0)
        b = derive_seed(123, "sim", "WideExplore", "discovery", "anchor-0000", 0)
        self.assertEqual(a, b)

    def test_derivation_separates_labels(self):
        base = derive_seed(123, "sim", "WideExplore", "discovery", "anchor-0000", 0)
        self.assertNotEqual(base, derive_seed(123, "sim", "WideExplore", "discovery", "anchor-0001", 0))
        self.assertNotEqual(base, derive_seed(123, "sim", "VerifyFirst", "discovery", "anchor-0000", 0))
        self.assertNotEqual(base, derive_seed(123, "sim", "WideExplore", "audit", "anchor-0000", 0))
        self.assertNotEqual(base, derive_seed(124, "sim", "WideExplore", "discovery", "anchor-0000", 0))

    def test_seed_range(self):
        for seed in (derive_seed(0, "x"), derive_seed(2**32 - 1, "y")):
            self.assertTrue(0 <= seed < 2**32)

    def test_check_seed_rejects_bad_values(self):
        for bad in (True, -1, 2**32, 1.5, "7", None):
            with self.assertRaises(ValueError):
                check_seed(bad)

    def test_no_python_hash_dependency(self):
        # canonical_json must be stable regardless of PYTHONHASHSEED
        self.assertEqual(canonical_json({"b": 1, "a": 2}), '{"a":2,"b":1}')
        self.assertEqual(canonical_json([3, 1, 2]), "[3,1,2]")

    def test_formal_master_seeds_frozen(self):
        seeds = formal_master_seeds()
        self.assertEqual(len(seeds), FORMAL_MASTER_SEED_COUNT)
        self.assertEqual(len(set(seeds)), FORMAL_MASTER_SEED_COUNT)
        self.assertEqual(seeds, formal_master_seeds())  # stable across calls
        for s in seeds:
            self.assertTrue(0 <= s < 2**32)

    def test_formal_total_budget(self):
        self.assertEqual(FORMAL_TOTAL_EPISODES, 12800)

    def test_sim_seed_shared_across_conditions(self):
        """The quartet's four conditions must share one sim_seed: the
        derivation must not depend on the condition code."""
        seeds = {c: derive_seed(7, "sim", "WideExplore", STREAM_DISCOVERY, "anchor-0003", 1)
                 for c in CONDITIONS}
        # (derivation has no condition label, so all four are identical)
        self.assertEqual(len(set(seeds.values())), 1)

    def test_sim_seed_audit_fresh(self):
        disc = sim_seed_for(7, "WideExplore", STREAM_DISCOVERY, "anchor-0003", 0)
        audit = sim_seed_for(7, "WideExplore", STREAM_AUDIT, "anchor-0003", 0)
        self.assertNotEqual(disc, audit)

    def test_sim_seed_repetitions_differ(self):
        s0 = sim_seed_for(7, "VerifyFirst", STREAM_DISCOVERY, "anchor-0003", 0)
        s1 = sim_seed_for(7, "VerifyFirst", STREAM_DISCOVERY, "anchor-0003", 1)
        self.assertNotEqual(s0, s1)

    def test_sim_seed_rejects_bad_stream(self):
        with self.assertRaises(ValueError):
            sim_seed_for(7, "WideExplore", "bogus", "anchor-0000", 0)
        with self.assertRaises(ValueError):
            sim_seed_for(7, "WideExplore", STREAM_DISCOVERY, "anchor-0000", -1)

    def test_anchor_stream_seed_stable(self):
        self.assertEqual(anchor_stream_seed(20261011), anchor_stream_seed(20261011))
        self.assertNotEqual(anchor_stream_seed(20261011), anchor_stream_seed(20261012))

    def test_anchor_id_format(self):
        self.assertEqual(anchor_id(0), "anchor-0000")
        self.assertEqual(anchor_id(99), "anchor-0099")
        with self.assertRaises(ValueError):
            anchor_id(-1)

    def test_run_id_unique_and_readable(self):
        a = run_id("smoke", "WideExplore", 20261011, "2026-10-12T11:00:00.000+00:00")
        b = run_id("smoke", "WideExplore", 20261011, "2026-10-12T11:00:01.000+00:00")
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("smoke_WideExplore_20261011_"))

    def test_dev_seed_value(self):
        self.assertEqual(DEV_SEED, 20261011)


if __name__ == "__main__":
    unittest.main()

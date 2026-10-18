"""Method logic tests: tie-breaks, nomination, audit isolation, exact budgets."""
import unittest

from safefliplab.methods import (
    AUDIT_QUARTETS_PER_NOMINEE,
    FORMAL_AUDIT_BUDGET,
    FORMAL_BUDGET,
    FORMAL_DISCOVERY_BUDGET,
    METHOD_VERIFY,
    METHOD_WIDE,
    VERIFY_EXTRA_QUARTETS,
    VERIFY_SELECTED,
    VERIFY_STAGE1_ANCHORS,
    WIDE_DISCOVERY_ANCHORS,
    WIDE_NOMINEES,
    AnchorRecord,
    MethodError,
    add_quartet,
    audit_jobs,
    budget_check,
    select_top,
    validate_formal_plans,
    verify_final_key,
    verify_select_key,
    verify_stage2_jobs,
    wide_discovery_jobs,
    wide_nomination_key,
)

ALL_ZERO = {"00": 0, "10": 0, "01": 0, "11": 0}
REVERSE = {"00": 0, "10": 0, "01": 0, "11": 1}
RESCUE = {"00": 1, "10": 1, "01": 1, "11": 0}
GAP_ONLY = {"00": 0, "10": 1, "01": 0, "11": 1}
SPEED_ONLY = {"00": 0, "10": 0, "01": 1, "11": 1}


def record(index, quartets):
    rec = AnchorRecord(anchor_id=f"anchor-{index:04d}", index=index)
    for q in quartets:
        add_quartet(rec, q)
    return rec


class TestQuartetValidation(unittest.TestCase):
    def test_add_quartet_requires_complete(self):
        rec = AnchorRecord(anchor_id="anchor-0000", index=0)
        with self.assertRaises(MethodError):
            add_quartet(rec, {"00": 0, "10": 0, "01": 0})
        with self.assertRaises(MethodError):
            add_quartet(rec, {"00": 2, "10": 0, "01": 0, "11": 0})


class TestTieBreaks(unittest.TestCase):
    def test_wide_nomination_orders_by_delta_both(self):
        recs = [record(0, [ALL_ZERO]), record(1, [REVERSE]), record(2, [GAP_ONLY])]
        top = select_top(recs, wide_nomination_key, 2)
        self.assertEqual([r.index for r in top], [1, 2])

    def test_wide_tie_break_first_seen_then_anchor_id(self):
        # two anchors with identical delta_both: earlier stream index wins
        recs = [record(5, [REVERSE]), record(2, [REVERSE])]
        top = select_top(recs, wide_nomination_key, 1)
        self.assertEqual(top[0].index, 2)

    def test_verify_select_uses_single_factor_deltas_as_tiebreak(self):
        # equal delta_both; gap-driven reverse should outrank speed-driven one
        recs = [record(0, [SPEED_ONLY]), record(1, [GAP_ONLY])]
        top = select_top(recs, verify_select_key, 1)
        self.assertEqual(top[0].index, 1)

    def test_verify_final_key_uses_valid_n_as_tiebreak(self):
        weak = record(0, [REVERSE, RESCUE])          # mean 0, n=2
        strong = record(1, [REVERSE, REVERSE])       # mean 1, n=2
        single = record(2, [REVERSE])                # mean 1, n=1
        top = select_top([weak, strong, single], verify_final_key, 2)
        self.assertEqual([r.index for r in top], [1, 2])

    def test_select_top_cannot_over_nominate(self):
        with self.assertRaises(MethodError):
            select_top([record(0, [REVERSE])], wide_nomination_key, 2)

    def test_empty_pool_rejected(self):
        with self.assertRaises(MethodError):
            select_top([], wide_nomination_key, 1)


class TestFormalBudget(unittest.TestCase):
    def test_formal_plans_close_exactly(self):
        per_method = validate_formal_plans()
        self.assertEqual(per_method[METHOD_WIDE], 800)
        self.assertEqual(per_method[METHOD_VERIFY], 800)

    def test_wide_discovery_plan(self):
        jobs = wide_discovery_jobs(WIDE_DISCOVERY_ANCHORS)
        self.assertEqual(len(jobs), 100)
        budget_check("wide discovery", jobs, FORMAL_DISCOVERY_BUDGET)
        for job in jobs:
            self.assertEqual(job.method, METHOD_WIDE)
            self.assertEqual(job.repetition, 0)
            self.assertEqual(job.stream, "discovery")

    def test_verify_stage2_plan(self):
        jobs = verify_stage2_jobs(list(range(VERIFY_SELECTED)), VERIFY_EXTRA_QUARTETS)
        self.assertEqual(len(jobs), 20 * 3)
        budget_check("verify stage2", jobs, 240)

    def test_audit_plan_uses_fresh_stream(self):
        jobs = audit_jobs(METHOD_WIDE, list(range(WIDE_NOMINEES)),
                          AUDIT_QUARTETS_PER_NOMINEE)
        self.assertEqual(len(jobs), 5 * 20)
        budget_check("wide audit", jobs, FORMAL_AUDIT_BUDGET)
        for job in jobs:
            self.assertEqual(job.stream, "audit")
            self.assertEqual(job.method, METHOD_WIDE)

    def test_budget_check_rejects_partial_plans(self):
        jobs = wide_discovery_jobs(10)  # 40 episodes, not 400
        with self.assertRaises(MethodError):
            budget_check("partial", jobs, FORMAL_DISCOVERY_BUDGET)

    def test_audit_seeds_never_reused_from_discovery(self):
        """Structural isolation: audit jobs carry the audit stream tag, so the
        seed derivation can never collide with a discovery seed."""
        disc = wide_discovery_jobs(3)
        aud = audit_jobs(METHOD_WIDE, [0, 1, 2], 5)
        disc_keys = {(j.method, j.anchor_index, j.repetition, j.stream) for j in disc}
        aud_keys = {(j.method, j.anchor_index, j.repetition, j.stream) for j in aud}
        self.assertEqual(disc_keys & aud_keys, set())


if __name__ == "__main__":
    unittest.main()

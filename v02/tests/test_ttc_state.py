"""TTC three-layer state model and I_log domain handling (pure)."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v02lab.schema import UnsetParameterError  # noqa: E402
from v02lab.ttc_state import (  # noqa: E402
    EpisodeTTCCategory,
    ILogStatus,
    PairStatus,
    StepTTCState,
    TerminationClass,
    aggregate_episode,
    log_interaction,
    quartet_pair_status,
    step_ttc_state,
    termination_from_exit,
)

NC = StepTTCState.NORMAL_CLOSING
NCL = StepTTCState.NO_CLOSING
NOC = StepTTCState.NO_CANDIDATE
TAU = 30.0


def ep(steps, term=TerminationClass.HORIZON_REACHED, policy="assign_cap"):
    return aggregate_episode(steps, termination=term, tau_cap=TAU, no_candidate_policy=policy)


class TestStepState(unittest.TestCase):
    def test_no_candidate(self):
        self.assertEqual(step_ttc_state(has_candidate=False, gap=70.0, closing=0.0), (NOC, None))

    def test_no_closing(self):
        self.assertEqual(step_ttc_state(has_candidate=True, gap=20.0, closing=-1.0), (NCL, None))
        self.assertEqual(step_ttc_state(has_candidate=True, gap=20.0, closing=0.0), (NCL, None))

    def test_gap_nonpositive_is_zero_not_inf(self):
        self.assertEqual(step_ttc_state(has_candidate=True, gap=-1.0, closing=2.0), (NC, 0.0))

    def test_normal(self):
        self.assertEqual(step_ttc_state(has_candidate=True, gap=10.0, closing=2.0), (NC, 5.0))


class TestAggregate(unittest.TestCase):
    def test_finite_min(self):
        e = ep([(NC, 6.0), (NC, 3.0), (NC, 7.0)])
        self.assertEqual(e.category, EpisodeTTCCategory.FINITE)
        self.assertAlmostEqual(e.value, 3.0)
        self.assertEqual(e.n_normal, 3)
        self.assertFalse(e.censored)

    def test_finite_with_partial_censoring(self):
        e = ep([(NC, 3.0), (NCL, None)])
        self.assertEqual(e.category, EpisodeTTCCategory.FINITE)
        self.assertTrue(e.censored)
        self.assertEqual(e.n_no_closing, 1)

    def test_censored(self):
        e = ep([(NCL, None), (NCL, None)])
        self.assertEqual(e.category, EpisodeTTCCategory.CENSORED)
        self.assertEqual(e.value, TAU)
        self.assertTrue(e.censored)

    def test_no_candidate_assign_cap(self):
        e = ep([(NOC, None), (NOC, None)], policy="assign_cap")
        self.assertEqual(e.category, EpisodeTTCCategory.NO_CANDIDATE)
        self.assertEqual(e.value, TAU)

    def test_no_candidate_exclude(self):
        e = ep([(NOC, None)], policy="exclude")
        self.assertEqual(e.category, EpisodeTTCCategory.NO_CANDIDATE)
        self.assertIsNone(e.value)

    def test_technical_failure_is_missing(self):
        e = ep([(NC, 3.0)], term=TerminationClass.TECHNICAL_FAILURE)
        self.assertEqual(e.category, EpisodeTTCCategory.MISSING)
        self.assertIsNone(e.value)
        self.assertTrue(e.is_missing)

    def test_empty_is_missing(self):
        e = ep([])
        self.assertEqual(e.category, EpisodeTTCCategory.MISSING)

    def test_tau_cap_required(self):
        with self.assertRaises(UnsetParameterError):
            aggregate_episode([(NC, 1.0)], termination=TerminationClass.HORIZON_REACHED,
                              tau_cap=None, no_candidate_policy="assign_cap")

    def test_bad_policy(self):
        with self.assertRaises(ValueError):
            aggregate_episode([(NC, 1.0)], termination=TerminationClass.HORIZON_REACHED,
                              tau_cap=TAU, no_candidate_policy="guess")


class TestPairStatus(unittest.TestCase):
    def test_ok(self):
        q = {c: ep([(NC, 3.0)]) for c in ("00", "10", "01", "11")}
        self.assertEqual(quartet_pair_status(q), PairStatus.OK)

    def test_censoring_affected(self):
        q = {c: ep([(NC, 3.0)]) for c in ("00", "10", "01", "11")}
        q["11"] = ep([(NCL, None)])
        self.assertEqual(quartet_pair_status(q), PairStatus.CENSORING_AFFECTED)

    def test_pair_missing(self):
        q = {c: ep([(NC, 3.0)]) for c in ("00", "10", "01", "11")}
        q["10"] = ep([(NC, 3.0)], term=TerminationClass.TECHNICAL_FAILURE)
        self.assertEqual(quartet_pair_status(q), PairStatus.PAIR_MISSING)

    def test_missing_key(self):
        q = {c: ep([(NC, 3.0)]) for c in ("00", "10", "01")}
        self.assertEqual(quartet_pair_status(q), PairStatus.PAIR_MISSING)


class TestILog(unittest.TestCase):
    def test_defined(self):
        r = log_interaction({"00": 4.0, "10": 5.0, "01": 6.0, "11": 8.0})
        self.assertEqual(r.status, ILogStatus.DEFINED)
        self.assertAlmostEqual(r.value, math.log(8) - math.log(5) - math.log(6) + math.log(4))
        self.assertIsNone(r.floored_value)

    def test_zero_ttc_undefined_without_floor(self):
        r = log_interaction({"00": 0.0, "10": 5.0, "01": 6.0, "11": 8.0})
        self.assertEqual(r.status, ILogStatus.ZERO_TTC)
        self.assertIsNone(r.value)
        self.assertIsNone(r.floored_value)

    def test_zero_ttc_floor_only_when_supplied(self):
        r = log_interaction({"00": 0.0, "10": 5.0, "01": 6.0, "11": 8.0}, floor=0.5)
        self.assertEqual(r.status, ILogStatus.ZERO_TTC)
        self.assertIsNotNone(r.floored_value)

    def test_censored_infinity(self):
        vals = {"00": 4.0, "10": 5.0, "01": 6.0, "11": ep([(NCL, None)])}
        self.assertEqual(log_interaction(vals).status, ILogStatus.CENSORED_INFINITY)

    def test_missing(self):
        vals = {"00": 4.0, "10": 5.0, "01": 6.0, "11": None}
        self.assertEqual(log_interaction(vals).status, ILogStatus.MISSING)

    def test_missing_takes_priority(self):
        vals = {"00": 0.0, "10": 5.0, "01": 6.0, "11": None}
        self.assertEqual(log_interaction(vals).status, ILogStatus.MISSING)


class TestTermination(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(termination_from_exit("error"), TerminationClass.TECHNICAL_FAILURE)
        self.assertEqual(termination_from_exit("interrupted"), TerminationClass.TECHNICAL_FAILURE)
        self.assertEqual(termination_from_exit("completed", "collision"), TerminationClass.TERMINAL_EVENT)
        self.assertEqual(termination_from_exit("completed", "goal"), TerminationClass.TERMINAL_EVENT)
        self.assertEqual(termination_from_exit("completed", ""), TerminationClass.HORIZON_REACHED)


if __name__ == "__main__":
    unittest.main()

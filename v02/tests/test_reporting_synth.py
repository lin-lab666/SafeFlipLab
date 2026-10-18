"""Reporting / statistics interfaces over synthetic data (FakeAdapterV02)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v02lab.fake_adapter import FakeAdapterV02, synthetic_scenario  # noqa: E402
from v02lab.reporting import (  # noqa: E402
    build_report,
    figure_axis_range,
    record_from_trace,
    summarise_records,
)
from v02lab.ttc_state import EpisodeTTCCategory, TerminationClass  # noqa: E402

TAU = 30.0
POLICY = "assign_cap"


def _trace_finite():
    return {"steps": [(True, 20.0, 3.0), (True, 15.0, 2.0)], "ego_collision": 0}


def _trace_no_candidate():
    return {"steps": [(False, 70.0, 0.0)], "ego_collision": 0}


def _trace_censored():
    return {"steps": [(True, 20.0, -1.0)], "ego_collision": 0}


class TestRecordFromTrace(unittest.TestCase):
    def test_finite(self):
        r = record_from_trace(_trace_finite(), anchor_id="A", repetition=0, condition="00",
                              tau_cap=TAU, no_candidate_policy=POLICY)
        self.assertEqual(r["category"], EpisodeTTCCategory.FINITE.value)
        self.assertAlmostEqual(r["m1"], 20.0 / 3.0)

    def test_no_candidate_assign_cap(self):
        r = record_from_trace(_trace_no_candidate(), anchor_id="A", repetition=0, condition="00",
                              tau_cap=TAU, no_candidate_policy=POLICY)
        self.assertEqual(r["category"], EpisodeTTCCategory.NO_CANDIDATE.value)
        self.assertEqual(r["m1"], TAU)

    def test_censored(self):
        r = record_from_trace(_trace_censored(), anchor_id="A", repetition=0, condition="00",
                              tau_cap=TAU, no_candidate_policy=POLICY)
        self.assertEqual(r["category"], EpisodeTTCCategory.CENSORED.value)

    def test_technical_failure_is_missing(self):
        r = record_from_trace(_trace_finite(), anchor_id="A", repetition=0, condition="00",
                              tau_cap=TAU, no_candidate_policy=POLICY,
                              termination=TerminationClass.TECHNICAL_FAILURE)
        self.assertEqual(r["category"], EpisodeTTCCategory.MISSING.value)
        self.assertIsNone(r["m1"])


class TestFakeAdapter(unittest.TestCase):
    def test_deterministic(self):
        a = FakeAdapterV02()
        scn = synthetic_scenario(front_gap=30.0, ego_speed=25.0, front_speed=22.0)
        r1 = a.run_episode(scn, 123)
        r2 = a.run_episode(scn, 123)
        self.assertEqual(r1["trace_sha256"], r2["trace_sha256"])

    def test_seed_sensitive(self):
        a = FakeAdapterV02()
        scn = synthetic_scenario(front_gap=30.0, ego_speed=25.0, front_speed=22.0)
        self.assertNotEqual(a.run_episode(scn, 1)["trace_sha256"],
                            a.run_episode(scn, 2)["trace_sha256"])

    def test_collision_possible(self):
        a = FakeAdapterV02()
        scn = synthetic_scenario(front_gap=20.0, ego_speed=30.0, front_speed=15.0)
        r = a.run_episode(scn, 5)
        self.assertIn(r["termination"], ("collision", "horizon"))


class TestFigureAxis(unittest.TestCase):
    def test_degenerate_zero(self):
        self.assertEqual(figure_axis_range([0.0, 0.0]), (-0.5, 0.5))

    def test_tiny_noise_snaps(self):
        self.assertEqual(figure_axis_range([1e-17]), (-0.5, 0.5))

    def test_real_spread(self):
        lo, hi = figure_axis_range([-0.2, 0.0, 0.3])
        self.assertLess(lo, -0.2)
        self.assertGreater(hi, 0.3)

    def test_empty(self):
        self.assertEqual(figure_axis_range([]), (-0.5, 0.5))


def _manual_records():
    data = {
        ("A", 0): {"00": 5.0, "10": 7.0, "01": 6.0, "11": 9.0},
        ("A", 1): {"00": 4.0, "10": 6.0, "01": 6.0, "11": 8.0},
        ("B", 0): {"00": 6.0, "10": 7.0, "01": 7.0, "11": 7.0},
        ("B", 1): {"00": 5.0, "10": 6.0, "01": 6.0, "11": 6.0},
    }
    out = []
    for (aid, rep), conds in data.items():
        for c, v in conds.items():
            out.append({"anchor_id": aid, "repetition": rep, "condition": c, "m1": v,
                        "category": EpisodeTTCCategory.FINITE.value, "censored": False,
                        "termination": "HORIZON_REACHED", "ego_collision": 0})
    return out


class TestBuildReport(unittest.TestCase):
    def test_summary(self):
        s = summarise_records(_manual_records())
        self.assertEqual(s["n_records"], 16)
        self.assertEqual(s["per_condition"]["00"]["n"], 4)

    def test_no_ci_without_params(self):
        rep = build_report(_manual_records())
        est = rep["estimates"]["delta_both"]
        self.assertIsNone(est["ci_low"])
        self.assertIn("no CI", est["note"])

    def test_ci_with_params(self):
        rep = build_report(_manual_records(), b_resamples=300, alpha=0.05, seed=1)
        est = rep["estimates"]["delta_both"]
        self.assertIsNotNone(est["ci_low"])
        self.assertLessEqual(est["ci_low"], est["ci_high"])
        self.assertAlmostEqual(est["point"], 2.5)

    def test_confirmatory_is_pending(self):
        rep = build_report(_manual_records(), b_resamples=100, alpha=0.05, seed=1)
        self.assertEqual(rep["confirmatory_status"], "PENDING")
        self.assertNotIn("p_value", rep)


if __name__ == "__main__":
    unittest.main()

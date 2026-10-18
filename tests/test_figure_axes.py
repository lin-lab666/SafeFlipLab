"""Figure axis regression tests: degenerate zero-variance data must never
produce matplotlib's floating-point +/-1e-17 auto-range with a spurious
``1e-17`` offset, and point-estimate figures must not masquerade as
confidence-interval forest plots.

No simulator is imported; quartets are synthetic ledger rows.
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import matplotlib
matplotlib.use("Agg")
import matplotlib.figure  # noqa: F401  (patched via matplotlib.figure.Figure)

from safefliplab.ledger import EpisodeKey, EpisodeLedger
from safefliplab.report import (
    _sane_value_axis,
    _wrap_title,
    figure_discovery_to_audit,
    figure_forest,
    load_phase_data,
)
from safefliplab.seeds import CONDITIONS


def _add_quartet(ledger, *, seed, method, anchor_id, anchor_index, repetition,
                 stream, y, run_id):
    for cond in CONDITIONS:
        key = EpisodeKey(run_id=run_id, anchor_id=anchor_id, repetition=repetition,
                         condition=cond)
        launch = ledger.record_launch(
            key, run_id=run_id, phase="pilot", method=method, master_seed=seed,
            anchor_id=anchor_id, anchor_index=anchor_index, repetition=repetition,
            condition=cond, sim_seed=7, stream=stream)
        ledger.record_outcome(key, launch_row=launch, exit_status="completed",
                              ego_collision=y[cond],
                              termination="collision" if y[cond] else "goal")


def _capture_axes(fn, *args, **kwargs):
    """Run a figure function, returning (path, first_axes) via a savefig spy."""
    captured = {}
    orig = matplotlib.figure.Figure.savefig

    def spy(self, *a, **k):
        captured["ax"] = self.axes[0] if self.axes else None
        return orig(self, *a, **k)

    with mock.patch.object(matplotlib.figure.Figure, "savefig", spy):
        path = fn(*args, **kwargs)
    return path, captured.get("ax")


class TestSaneValueAxis(unittest.TestCase):
    def setUp(self):
        import matplotlib.pyplot as plt
        self.plt = plt
        self.fig, self.ax = plt.subplots()

    def tearDown(self):
        self.plt.close(self.fig)

    def test_all_zero_gets_readable_range_and_no_offset(self):
        degenerate = _sane_value_axis(self.ax, [0.0, 0.0, 0.0], axis="y")
        self.assertTrue(degenerate)
        lo, hi = self.ax.get_ylim()
        self.assertGreater(hi - lo, 0.1)  # not a +/-1e-17 sliver
        self.assertEqual(self.ax.yaxis.get_offset_text().get_text(), "")

    def test_tiny_float_noise_is_snapped(self):
        # values that differ only by ~1e-17 must be treated as identical
        degenerate = _sane_value_axis(
            self.ax, [0.0, 1e-17, -3e-17, 0.0], axis="x")
        self.assertTrue(degenerate)
        lo, hi = self.ax.get_xlim()
        self.assertGreater(hi - lo, 0.1)
        self.assertEqual(self.ax.xaxis.get_offset_text().get_text(), "")

    def test_real_spread_keeps_data_limits(self):
        before = self.ax.get_ylim()
        _sane_value_axis(self.ax, [-0.3, 0.1, 0.45], axis="y")
        # non-degenerate data: limits are NOT forced, only offset is disabled
        self.assertEqual(self.ax.get_ylim(), before)
        self.assertEqual(self.ax.yaxis.get_offset_text().get_text(), "")

    def test_empty_values_are_noop(self):
        before = self.ax.get_ylim()
        self.assertFalse(_sane_value_axis(self.ax, [], axis="y"))
        self.assertEqual(self.ax.get_ylim(), before)


class TestFiguresOnZeroVarianceData(unittest.TestCase):
    """The real pilot situation: every collision delta is exactly 0."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "runs").mkdir(parents=True)
        self.ledger = EpisodeLedger(self.root / "runs" / "episode_ledger.csv")
        zero = {"00": 0, "10": 0, "01": 0, "11": 0}
        for method in ("WideExplore", "VerifyFirst"):
            for i in range(3):
                _add_quartet(self.ledger, seed=20261011, method=method,
                             anchor_id=f"anchor-{i:04d}", anchor_index=i,
                             repetition=0, stream="discovery", y=zero,
                             run_id=f"disc-{method}-{i}")
            for i in range(3):
                _add_quartet(self.ledger, seed=20261011, method=method,
                             anchor_id=f"anchor-{i:04d}", anchor_index=i,
                             repetition=0, stream="audit", y=zero,
                             run_id=f"aud-{method}-{i}")
        self.data = load_phase_data(self.root, "pilot")

    def tearDown(self):
        self.tmp.cleanup()

    def test_forest_point_estimates_no_offset(self):
        path, ax = _capture_axes(figure_forest, self.root, self.data)
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        lo, hi = ax.get_xlim()
        self.assertGreater(hi - lo, 0.1)
        self.assertEqual(ax.xaxis.get_offset_text().get_text(), "")

    def test_discovery_to_audit_no_offset(self):
        path, ax = _capture_axes(figure_discovery_to_audit, self.root, self.data)
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        lo, hi = ax.get_ylim()
        self.assertGreater(hi - lo, 0.1)
        self.assertEqual(ax.yaxis.get_offset_text().get_text(), "")


class TestTitleWrap(unittest.TestCase):
    """Long English titles must be wrapped so they cannot run off the canvas."""

    def test_long_title_wrapped_within_width(self):
        text = ("Discovery to independent audit, point estimates (phase=pilot); "
                "all deltas = 0 (zero collisions), no CI estimable")
        wrapped = _wrap_title(text, width=70)
        self.assertIn("\n", wrapped)
        self.assertTrue(all(len(line) <= 70 for line in wrapped.split("\n")))

    def test_wrap_preserves_words(self):
        text = "Exploratory forward-TTC margin difference point estimates no CI"
        wrapped = _wrap_title(text, width=30)
        self.assertEqual(wrapped.split(), text.split())

    def test_short_title_unchanged(self):
        self.assertEqual(_wrap_title("Short title", width=70), "Short title")

    def test_real_figure_title_is_wrapped(self):
        # Figure 3's title is long; it must come out on more than one line.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runs").mkdir(parents=True)
            ledger = EpisodeLedger(root / "runs" / "episode_ledger.csv")
            zero = {"00": 0, "10": 0, "01": 0, "11": 0}
            for i in range(3):
                _add_quartet(ledger, seed=20261011, method="WideExplore",
                             anchor_id=f"anchor-{i:04d}", anchor_index=i,
                             repetition=0, stream="audit", y=zero,
                             run_id=f"aud-{i}")
            data = load_phase_data(root, "pilot")
            _, ax = _capture_axes(figure_discovery_to_audit, root, data)
            self.assertIn("\n", ax.get_title())


if __name__ == "__main__":
    unittest.main()

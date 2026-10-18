"""F-01 acceptance: legacy (20-column) vs current (21-column) ledger schema.

These tests are the independent acceptance for the ``budget_scope`` reader fix.
Every test uses a throwaway temp ledger; the real historic ledger under
``runs/`` is never opened for writing and no simulator is imported (so no real
episode can be launched).

Covered scenarios (all on temp ledgers):

1. full round-trip: legacy 20-col header -> append a new 21-field scoped row ->
   close -> reopen -> counts/scope restored;
2. ``budget_scope`` is written to the CSV *and* restored on reopen;
3. per ``(method, master_seed)`` formal scopes stay independent after reopen;
4. many OS processes sharing one ledger cannot exceed a scope cap;
5. no free retry: a launch with no outcome is still billed; a re-attempt of the
   same key is refused; a force-rerun (fresh run_id) is billed again;
6. an incompatible header (extra/reordered/non-prefix columns) is *rejected*
   with ``LedgerFormatError`` rather than silently dropping columns.
"""
import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from safefliplab.ledger import (
    BudgetExhausted,
    COLUMNS,
    DuplicateLaunch,
    EpisodeKey,
    EpisodeLedger,
    LedgerFormatError,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKER = PROJECT_ROOT / "tests" / "ledger_proc_worker.py"

#: The exact 20-column header written by the ledger before ``budget_scope``
#: existed (verified against the real ``runs/episode_ledger.csv`` header).
LEGACY_HEADER = COLUMNS[:20]


def _write_legacy(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow(LEGACY_HEADER)


def _field_counts(path: Path) -> list[int]:
    with open(path, encoding="utf-8") as fh:
        return [len(line.rstrip("\n").split(",")) for line in fh.read().splitlines() if line.strip()]


def _reserve(ledger, *, run_id, method, seed, scope, cap, anchor="anchor-0000",
             cond="00", phase="formal"):
    key = EpisodeKey(run_id=run_id, anchor_id=anchor, repetition=0, condition=cond)
    return ledger.reserve_launch(
        key, run_id=run_id, phase=phase, method=method, master_seed=seed,
        anchor_id=anchor, anchor_index=0, repetition=0, condition=cond,
        sim_seed=seed, stream="discovery", max_episodes=cap, budget_scope=scope)


class TestScenario1_2_FullRoundTrip(unittest.TestCase):
    """Legacy header + new 21-field row survives close/reopen, scope intact."""

    def test_append_then_reopen_restores_scope_and_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs" / "episode_ledger.csv"
            _write_legacy(path)
            scope = "formal|WideExplore|999"

            led = EpisodeLedger(path)
            self.assertEqual(led.launched_count("formal"), 0)
            _reserve(led, run_id="r1", method="WideExplore", seed=999,
                     scope=scope, cap=800)
            self.assertEqual(led.launched_count_scope(scope), 1)
            self.assertEqual(led.launched_count("formal"), 1)
            del led  # "close": drop the instance

            # On disk: header stays 20 fields, the appended row is 21 fields,
            # and the 21st field carries the scope value.
            counts = _field_counts(path)
            self.assertEqual(counts[0], 20)          # legacy header untouched
            self.assertEqual(counts[1], 21)          # new row is full width
            with open(path, newline="", encoding="utf-8") as fh:
                last = list(csv.reader(fh))[-1]
            self.assertEqual(last[-1], scope)        # budget_scope persisted

            led2 = EpisodeLedger(path)               # fresh process semantics
            self.assertEqual(led2.launched_count_scope(scope), 1)
            self.assertEqual(led2.launched_count("formal"), 1)
            # cap is now actually enforced on the reopened instance
            with self.assertRaises(BudgetExhausted):
                _reserve(led2, run_id="r1b", method="WideExplore", seed=999,
                         scope=scope, cap=1, anchor="anchor-0001")

    def test_repeated_reopen_is_stable_and_does_not_double_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs" / "episode_ledger.csv"
            _write_legacy(path)
            scope = "formal|VerifyFirst|7"
            led = EpisodeLedger(path)
            _reserve(led, run_id="r1", method="VerifyFirst", seed=7, scope=scope, cap=800)
            del led
            for _ in range(3):  # open/close several times
                led = EpisodeLedger(path)
                self.assertEqual(led.launched_count_scope(scope), 1)
                self.assertEqual(led.launched_count("formal"), 1)
                del led

    def test_legacy_20_field_row_falls_back_to_phase_scope(self):
        """An old 20-field data row has no budget_scope -> phase scope."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs" / "episode_ledger.csv"
            _write_legacy(path)
            row = ["launch", "old|anchor-0000|r0|00", "old", "smoke", "WideExplore",
                   "1", "anchor-0000", "0", "0", "00", "discovery", "1", "pending",
                   "", "", "", "2026-01-01T00:00:00.000Z", "", "", ""]
            self.assertEqual(len(row), 20)
            with open(path, "a", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerow(row)
            led = EpisodeLedger(path)
            self.assertEqual(led.launched_count("smoke"), 1)
            self.assertEqual(led.launched_count_scope("smoke"), 1)  # same as phase


class TestScenario3_ScopedIndependence(unittest.TestCase):
    """Per (method, seed) formal budget scopes stay independent after reopen."""

    def test_method_seed_scopes_independent_after_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs" / "episode_ledger.csv"
            _write_legacy(path)
            cap = 3
            led = EpisodeLedger(path)
            # fill scope A exactly to its cap
            for i in range(cap):
                _reserve(led, run_id=f"a{i}", method="WideExplore", seed=1,
                         scope="formal|WideExplore|1", cap=cap, anchor=f"anchor-{i:04d}")
            with self.assertRaises(BudgetExhausted):
                _reserve(led, run_id="aX", method="WideExplore", seed=1,
                         scope="formal|WideExplore|1", cap=cap, anchor="anchor-9999")
            # a different method, and a different seed, are still open
            _reserve(led, run_id="b0", method="VerifyFirst", seed=1,
                     scope="formal|VerifyFirst|1", cap=cap)
            _reserve(led, run_id="c0", method="WideExplore", seed=2,
                     scope="formal|WideExplore|2", cap=cap)
            del led

            led2 = EpisodeLedger(path)  # reopen: scopes must survive
            self.assertEqual(led2.launched_count_scope("formal|WideExplore|1"), 3)
            self.assertEqual(led2.launched_count_scope("formal|VerifyFirst|1"), 1)
            self.assertEqual(led2.launched_count_scope("formal|WideExplore|2"), 1)
            self.assertEqual(led2.launched_count("formal"), 5)
            # Scope A is still exhausted; scope C still open.
            with self.assertRaises(BudgetExhausted):
                _reserve(led2, run_id="aX2", method="WideExplore", seed=1,
                         scope="formal|WideExplore|1", cap=cap, anchor="anchor-8888")
            _reserve(led2, run_id="c1", method="WideExplore", seed=2,
                     scope="formal|WideExplore|2", cap=cap, anchor="anchor-0001")
            self.assertEqual(led2.launched_count_scope("formal|WideExplore|2"), 2)


class TestScenario5_NoFreeRetry(unittest.TestCase):
    """A billed launch always consumes budget; duplicates never re-launch free."""

    def test_launch_without_outcome_is_still_billed_after_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs" / "episode_ledger.csv"
            _write_legacy(path)
            scope = "formal|WideExplore|1"
            led = EpisodeLedger(path)
            _reserve(led, run_id="crash", method="WideExplore", seed=1,
                     scope=scope, cap=800)
            # process dies here: no outcome row is ever written
            del led
            led2 = EpisodeLedger(path)
            self.assertEqual(led2.launched_count("formal"), 1)     # billed
            self.assertEqual(led2.outcome_count("formal"), 0)      # no outcome
            # Re-attempting the SAME key is refused before any simulator work.
            with self.assertRaises(DuplicateLaunch):
                _reserve(led2, run_id="crash", method="WideExplore", seed=1,
                         scope=scope, cap=800)

    def test_force_rerun_with_new_run_id_is_billed_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs" / "episode_ledger.csv"
            _write_legacy(path)
            scope = "formal|WideExplore|1"
            led = EpisodeLedger(path)
            _reserve(led, run_id="run1", method="WideExplore", seed=1, scope=scope, cap=800)
            # A deliberate force-rerun gets a fresh run_id -> fresh key -> billed.
            _reserve(led, run_id="run2", method="WideExplore", seed=1, scope=scope, cap=800)
            del led
            led2 = EpisodeLedger(path)
            self.assertEqual(led2.launched_count_scope(scope), 2)  # no free retry

    def test_cap_counts_every_attempt_without_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs" / "episode_ledger.csv"
            _write_legacy(path)
            scope = "formal|WideExplore|1"
            led = EpisodeLedger(path)
            cap = 2
            for i in range(cap):
                _reserve(led, run_id=f"r{i}", method="WideExplore", seed=1,
                         scope=scope, cap=cap, anchor=f"anchor-{i:04d}")
            # every attempt counts even though none completed -> cap reached
            del led
            led2 = EpisodeLedger(path)
            self.assertEqual(led2.outcome_count("formal"), 0)
            with self.assertRaises(BudgetExhausted):
                _reserve(led2, run_id="rX", method="WideExplore", seed=1,
                         scope=scope, cap=cap, anchor="anchor-9999")


class TestScenario6_FormatRejection(unittest.TestCase):
    """Incompatible headers are refused, never silently misread."""

    def _open_expect_error(self, header_cols):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "episode_ledger.csv"
            path.write_text(",".join(header_cols) + "\n", encoding="utf-8")
            with self.assertRaises(LedgerFormatError):
                EpisodeLedger(path)

    def test_extra_trailing_column_rejected(self):
        self._open_expect_error(COLUMNS + ["extra_col"])

    def test_reordered_columns_rejected(self):
        cols = list(COLUMNS)
        cols[4], cols[5] = cols[5], cols[4]
        self._open_expect_error(cols)

    def test_unknown_non_prefix_header_rejected(self):
        self._open_expect_error(["foo", "bar", "baz"])

    def test_wrong_name_same_width_rejected(self):
        cols = list(COLUMNS)
        cols[3] = "not_phase"
        self._open_expect_error(cols)

    def test_legacy_prefix_is_accepted_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "episode_ledger.csv"
            path.write_text(",".join(LEGACY_HEADER) + "\n", encoding="utf-8")
            led = EpisodeLedger(path)  # must NOT raise
            self.assertEqual(led.launched_count("formal"), 0)

    def test_row_wider_than_resolved_header_is_rejected(self):
        """A data row with more fields than COLUMNS must not drop the surplus."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "episode_ledger.csv"
            path.write_text(",".join(COLUMNS) + "\n", encoding="utf-8")
            with open(path, "a", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerow(["x"] * (len(COLUMNS) + 1))
            with self.assertRaises(LedgerFormatError):
                EpisodeLedger(path)


class TestScenario4_CrossProcessCap(unittest.TestCase):
    """Many OS processes sharing one legacy ledger cannot exceed the cap."""

    def _run(self, path: Path, cap: int, n: int, scope: str = "race"):
        env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
        procs = [
            subprocess.Popen(
                [sys.executable, str(WORKER), str(path), f"P{i}", str(cap), scope],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            for i in range(n)
        ]
        results = [p.communicate() for p in procs]
        outs = [o.strip() for o, _ in results]
        # Diagnostics: if a worker crashes before printing, its stdout is empty and
        # the ONLY place the cause appears is its stderr + exit code. Capture them
        # so a failure message is actionable instead of an opaque "" entry.
        # (This does not weaken any assertion; it only makes failures explicable.)
        self._last_diag = [
            {"out": o.strip(), "rc": p.returncode,
             "stderr_tail": (e or "").strip().splitlines()[-8:]}
            for (o, e), p in zip(results, procs)
        ]
        return outs

    def _explain(self, outs: list[str]) -> str:
        diag = getattr(self, "_last_diag", None)
        if not diag:
            return repr(outs)
        silent = [d for d in diag if not d["out"]]
        if not silent:
            return repr(outs)
        lines = [f"{repr(outs)}  <-- {len(silent)} worker(s) printed nothing:"]
        for d in silent:
            lines.append(f"    rc={d['rc']} stderr_tail={d['stderr_tail']}")
        return "\n".join(lines)

    def test_cap_one_legacy_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs" / "episode_ledger.csv"
            _write_legacy(path)
            outs = self._run(path, cap=1, n=6)
            self.assertEqual(sum(o == "OK" for o in outs), 1, self._explain(outs))
            self.assertEqual(sum(o == "REFUSED" for o in outs), 5, self._explain(outs))
            led = EpisodeLedger(path)  # fresh read (legacy header)
            self.assertEqual(led.launched_count_scope("race"), 1)
            self.assertEqual(led.launched_count("formal"), 1)

    def test_cap_three_legacy_ledger_no_overspend(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runs" / "episode_ledger.csv"
            _write_legacy(path)
            scope = "formal|WideExplore|1"
            outs = self._run(path, cap=3, n=8, scope=scope)
            self.assertEqual(sum(o == "OK" for o in outs), 3, self._explain(outs))
            self.assertEqual(sum(o == "REFUSED" for o in outs), 5, self._explain(outs))
            # scope preserved across processes; exactly cap billed
            led = EpisodeLedger(path)  # fresh read (legacy header)
            self.assertEqual(led.launched_count_scope(scope), 3)
            self.assertEqual(led.launched_count("formal"), 3)


if __name__ == "__main__":
    unittest.main()

"""Offline guard: fail if a test or example could launch a real simulator episode.

This is the *executable* form of the CI "static offline guard" step. It scans
the unit-test trees and the examples for the specific patterns that would start
a real, billed HighwayEnv episode, and exits non-zero if any is found. It is
used two ways:

  * in CI (``.github/workflows/ci.yml``) as a pre-test gate, and
  * by ``tests/test_ci_offline_guard.py`` to prove — via a negative test — that
    the guard actually catches a planted real-simulator invocation.

What it blocks (and why):

  1. **Subprocess launch** — ``subprocess`` / ``os.system`` / ``Popen`` (or
     ``.run([...])``) invoking ``safefliplab``/``v02lab`` with a
     ``smoke``/``pilot``/``formal`` phase. Running these as a child process
     bypasses every in-process safety gate and immediately bills episodes.

  2. **CLI entrypoint list form** — ``main(["smoke", ...])`` /
     ``cli.main(["pilot", ...])`` style calls, EXCEPT inside the two refusal-path
     test files that are *designed* to exercise the guard itself
     (``tests/test_report_cli.py``, ``tests/test_formal_no_side_effects.py``).
     Those tests assert the refusal, and are mock/FakeAdapter-only.

  3. **Real adapter construction** — ``ScenarioAdapter(`` and
     ``RealAdapterV02(`` (an open parenthesis = an actual construction call;
     this deliberately does not match prose/docstring mentions such as
     "drop-in replacement for ScenarioAdapter").

  4. **Real simulator import** — ``cornercaselab.simulator`` (the HighwayEnv
     adapter). ``cornercaselab.domain`` (the pure scenario schema) is allowed.

It does NOT do symbol-level "call X means launch" analysis: the FakeAdapter /
mock suites legitimately import ``run_smoke_phase`` etc. and drive them with
``adapter=FakeAdapter()``; the in-process formal gate then refuses to touch a
non-test-double adapter. Blocking those names would be a false positive. The
real defences against accidental episodes remain (a) manual-only CI trigger,
(b) read-only token + no secrets, (c) the in-process formal GO gate.

Exit code: 0 = no violation; 1 = at least one violation (with file:line).

Usage:  python scripts/ci_offline_guard.py [root...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Files that legitimately mention the CLI phase names because they test the
# *refusal* path (mock/FakeAdapter only, no simulator).
_REFUSAL_PATH_FILES = {
    "test_report_cli.py",
    "test_formal_no_side_effects.py",
}

# Files that are *this guard's own* tests: they deliberately embed real-simulator
# strings as negative fixtures, so scanning them would be a false positive. They
# are excluded from directory scans (but still run as normal unit tests).
_SELF_TEST_FILES = {
    "test_ci_offline_guard.py",
}

# Phase names that, once launched, bill real episodes.
_PHASES = r"smoke|pilot|formal"

# 1. Subprocess / shell launch of a phase (billed immediately).
_RE_SUBPROCESS = re.compile(
    rf"(?:subprocess\.|os\.system\s*\(|Popen\s*\(|\.run\s*\().*?"
    rf"(?:safefliplab|v02lab).*?(?:{_PHASES})",
    re.IGNORECASE | re.DOTALL,
)

# 2. CLI entrypoint list form, e.g. main(["smoke", ...]).
_RE_CLI_LIST = re.compile(
    rf"(?:main|cli\.main)\s*\(\s*\[.*?[\"']({_PHASES})[\"']",
    re.IGNORECASE | re.DOTALL,
)

# 3. Real adapter construction (open paren = actual call).
_RE_REAL_ADAPTER = re.compile(
    r"ScenarioAdapter\s*\(|RealAdapterV02\s*\(",
)

# 4. Real simulator import (HighwayEnv adapter), excluding the pure domain schema.
_RE_SIM_IMPORT = re.compile(
    r"(?:from\s+cornercaselab\.simulator|import\s+cornercaselab\.simulator)",
)


def _scan_text(path: Path, text: str) -> list[str]:
    """Return a list of 'path:line: reason' violation strings."""
    violations: list[str] = []
    lines = text.splitlines()

    if _RE_SIM_IMPORT.search(text):
        violations.append(f"{path}: real simulator import (cornercaselab.simulator)")

    for i, line in enumerate(lines, 1):
        if _RE_SUBPROCESS.search(line):
            violations.append(f"{path}:{i}: subprocess/launch of a billed phase")
        if _RE_REAL_ADAPTER.search(line):
            # Skip the known docstring/comments (they have no '(' after the name).
            violations.append(f"{path}:{i}: real adapter construction")

    # CLI list form — skip the refusal-path test files entirely.
    if path.name not in _REFUSAL_PATH_FILES:
        for i, line in enumerate(lines, 1):
            if _RE_CLI_LIST.search(line):
                violations.append(f"{path}:{i}: CLI phase entrypoint (list form)")

    return violations


def scan(root: Path) -> list[str]:
    """Scan a root (tests/, examples/, ...) for simulator-launch patterns."""
    violations: list[str] = []
    if not root.is_dir():
        return violations
    for p in sorted(root.rglob("*.py")):
        if p.name in _SELF_TEST_FILES:
            continue  # this guard's own negative-fixture strings
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        violations.extend(_scan_text(p, text))
    return violations


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv] or [
        Path("tests"),
        Path("v02") / "tests",
        Path("examples"),
    ]
    all_violations: list[str] = []
    for root in roots:
        all_violations.extend(scan(root))

    if all_violations:
        print("OFFLINE GUARD: FAIL — the following would launch a real episode:")
        for v in all_violations:
            print(f"  {v}")
        return 1

    print("OFFLINE GUARD: OK (no real-simulator launch patterns in tests/examples)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

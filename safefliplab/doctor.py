"""Read-only environment and simulation-interface verification.

``doctor`` launches **no** simulation episodes. It checks the interpreter,
the pinned dependency versions, the cornercaselab scenario schema, the
frozen controller and constructs (without resetting) the parameterised
HighwayEnv merge environment, so a GO/NO-GO decision can be made before any
budget is spent.
"""
from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_doctor(verbose: bool = False) -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    # interpreter / platform
    py_ok = sys.version_info[:2] == (3, 13)
    check("python 3.13", py_ok, platform.python_version())
    check("platform windows", platform.system() == "Windows", platform.system())

    # dependency versions
    import importlib.metadata as md

    expected = {
        "cornercaselab": "0.3.0",
        "highway-env": "1.10.2",
        "gymnasium": "1.2.2",
    }
    for pkg, want in expected.items():
        try:
            got = md.version(pkg)
        except Exception:
            got = "MISSING"
        check(f"{pkg}=={want}", got == want, f"installed={got}")

    # project layout
    for rel in ("safefliplab", "configs", "tests", "docs", "reports"):
        check(f"dir {rel}/", (PROJECT_ROOT / rel).is_dir())

    # adapter verification (schema, controller, fields) - no episodes
    try:
        from .adapter import ScenarioAdapter, fingerprint

        adapter = ScenarioAdapter()
        fp = fingerprint().to_dict()
        check("adapter interface verification", True, json_dumps(fp))
        del adapter
    except Exception as exc:
        check("adapter interface verification", False, f"{type(exc).__name__}: {exc}")

    # environment construction without reset (no episode launched)
    try:
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        from cornercaselab.domain import Scenario
        from cornercaselab.simulator import make_environment

        from .adapter import SIM_SETTINGS
        from .domain import ANCHOR_BOUNDS, anchor_in_domain, quartet_scenarios

        env = make_environment(Scenario(), SIM_SETTINGS, None)
        env.close()
        check("highway-env env construction (no reset)", True, "ParameterisedMerge")
        probe = Scenario(ego_speed=27.0, front_gap=45.0, front_speed=25.0,
                         ramp_x=110.0, ramp_speed=20.0, ramp_target_speed=30.0)
        check("anchor legality domain", anchor_in_domain(probe), json_dumps(ANCHOR_BOUNDS))
        q = quartet_scenarios(probe)
        check("quartet construction (no clipping)",
              all(c in q for c in ("00", "10", "01", "11")),
              f"ego_speed: {q['00'].ego_speed}/{q['01'].ego_speed}, "
              f"front_gap: {q['00'].front_gap}/{q['10'].front_gap}")
    except Exception as exc:
        check("highway-env env construction (no reset)", False, f"{type(exc).__name__}: {exc}")

    # budget state from the ledger (read-only)
    try:
        from .ledger import EpisodeLedger

        ledger = EpisodeLedger(PROJECT_ROOT / "runs" / "episode_ledger.csv")
        for phase, cap in (("smoke", 24), ("pilot", 240), ("formal", 12800)):
            used = ledger.launched_count(phase)
            check(f"budget {phase}", used <= cap, f"launched={used}/{cap}")
    except Exception as exc:
        check("ledger read", False, f"{type(exc).__name__}: {exc}")

    print("SafeFlipLab doctor")
    print("==================")
    failures = 0
    for name, ok, detail in checks:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        line = f"[{mark}] {name}"
        if detail and (verbose or not ok):
            line += f"  ({detail})"
        print(line)
    print("------------------")
    print(f"{len(checks) - failures}/{len(checks)} checks passed")
    if failures:
        print("VERDICT: NO-GO (see failures above; no episodes may be launched)")
        return 1
    print("VERDICT: GO (interface verified; no episodes launched by doctor)")
    return 0


def json_dumps(obj) -> str:
    import json

    return json.dumps(obj, sort_keys=True)

"""V02 command line interface.

    python -m v02lab doctor
    python -m v02lab smoke  --max-episodes 24
    python -m v02lab pilot  --max-episodes 240
    python -m v02lab report --phase smoke|pilot

Budgets are protocol caps: ``smoke`` refuses more than 24 and ``pilot`` more
than 240. There is deliberately **no** formal/12800 entry point in V02.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

V02_ROOT = Path(__file__).resolve().parent.parent
CONFIG = V02_ROOT / "configs" / "v02_frozen_v1.json"

SMOKE_CAP = 24
PILOT_CAP = 240


def cmd_doctor(args: argparse.Namespace) -> int:
    from .adapter_real import HORIZON_S, POLICY_HZ, SIMULATION_HZ, RealAdapterV02
    from .anchors import DIMS, anchor_stream
    from .phases import load_frozen_protocol

    print("SafeFlipLab V02 doctor")
    print("======================")
    checks: list[tuple[str, bool, str]] = []

    proto = load_frozen_protocol(CONFIG)
    checks.append(("frozen protocol config", True, f"hash={proto.protocol_hash[:16]}..."))

    ok = True
    try:
        RealAdapterV02()
    except Exception as exc:  # pragma: no cover - environment failure
        ok = False
        checks.append(("adapter interface", False, str(exc)))
    if ok:
        checks.append(("adapter interface", True, "cornercaselab 0.3.0 / boundary"))

    # domain margins: every anchor must keep all four conditions inside BOUNDS
    margins_ok = True
    detail = []
    for dim in DIMS:
        lo, hi = proto.domain[dim]
        blow, bhigh = proto.bounds[dim]
        tol_lo, tol_hi = lo, hi
        if dim == "front_gap":
            tol_lo, tol_hi = lo - proto.halfwidths["front_gap"], hi + proto.halfwidths["front_gap"] + proto.gap_m
        elif dim == "ego_speed":
            tol_lo, tol_hi = lo - proto.halfwidths["ego_speed"] - proto.speed_mps, hi + proto.halfwidths["ego_speed"]
        elif dim == "front_speed":
            tol_lo, tol_hi = lo - proto.halfwidths["front_speed"], hi + proto.halfwidths["front_speed"]
        if tol_lo < blow - 1e-9 or tol_hi > bhigh + 1e-9:
            margins_ok = False
            detail.append(f"{dim}: [{tol_lo:.2f},{tol_hi:.2f}] vs [{blow},{bhigh}]")
    checks.append(("anchor domain stays inside upstream BOUNDS", margins_ok,
                   "; ".join(detail) or "all dimensions legal under extremes"))

    anchors = anchor_stream(proto.master_seed, proto.domain, bounds=proto.bounds, n=18,
                            gap_m=proto.gap_m, speed_mps=proto.speed_mps,
                            perturbation_halfwidths=proto.halfwidths)
    checks.append(("anchor stream reproducibility (18 anchors)", len(anchors) == 18,
                   f"first={anchors[0]}"))

    budget_ok = SMOKE_CAP == 24 and PILOT_CAP == 240
    checks.append(("budget caps", budget_ok, f"smoke={SMOKE_CAP}, pilot={PILOT_CAP}"))

    from .ledger21 import COLUMNS21
    checks.append(("21-column canonical ledger schema", len(COLUMNS21) == 21,
                   f"{len(COLUMNS21)} columns"))

    p = proto.params
    unset = [k for k, v in p.items() if v.get("status") != "FROZEN"]
    checks.append(("no UNSET research parameter", not unset, json.dumps(unset)))

    for name, ok_, detail_ in checks:
        print(f"[{'PASS' if ok_ else 'FAIL'}] {name}: {detail_}")
    total = len(checks)
    passed = sum(1 for _, ok_, _ in checks if ok_)
    print("------------------")
    print(f"{passed}/{total} checks passed")
    print("VERDICT: " + ("GO (interface verified; no episodes launched by doctor)"
                         if passed == total else "NO-GO"))
    print(f"simulator settings: horizon={HORIZON_S}s sim={SIMULATION_HZ}Hz policy={POLICY_HZ}Hz")
    return 0 if passed == total else 2


def cmd_smoke(args: argparse.Namespace) -> int:
    from .adapter_real import RealAdapterV02
    from .phases import load_frozen_protocol, run_smoke

    cap = args.max_episodes if args.max_episodes is not None else SMOKE_CAP
    if cap > SMOKE_CAP:
        print(f"V02 smoke budget is capped at {SMOKE_CAP} episodes by the protocol",
              file=sys.stderr)
        return 2
    proto = load_frozen_protocol(CONFIG)
    try:
        summary = run_smoke(V02_ROOT, proto, adapter=RealAdapterV02(), cap=cap)
    except RuntimeError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: v for k, v in summary.items() if k != "quartets"},
                     indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_pilot(args: argparse.Namespace) -> int:
    from .adapter_real import RealAdapterV02
    from .phases import load_frozen_protocol, run_pilot

    cap = args.max_episodes if args.max_episodes is not None else PILOT_CAP
    if cap > PILOT_CAP:
        print(f"V02 pilot budget is capped at {PILOT_CAP} episodes by the protocol",
              file=sys.stderr)
        return 2
    proto = load_frozen_protocol(CONFIG)
    try:
        summary = run_pilot(V02_ROOT, proto, adapter=RealAdapterV02(), cap=cap)
    except RuntimeError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("primary_quartets", "aux")},
                     indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from .report import write_report

    summary = write_report(V02_ROOT, args.phase)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="v02lab", description="SafeFlipLab V02 pilot CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="read-only interface and protocol verification")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("smoke", help="run at most 24 real episodes (V02 budget)")
    p.add_argument("--max-episodes", type=int, default=None)
    p.set_defaults(func=cmd_smoke)

    p = sub.add_parser("pilot", help="run at most 240 real episodes (V02 budget)")
    p.add_argument("--max-episodes", type=int, default=None)
    p.set_defaults(func=cmd_pilot)

    p = sub.add_parser("report", help="write the phase report from real records")
    p.add_argument("--phase", choices=["smoke", "pilot"], required=True)
    p.set_defaults(func=cmd_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

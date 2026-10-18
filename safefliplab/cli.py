"""SafeFlipLab command line interface.

Commands
--------
``doctor``   read-only environment / interface verification (no episodes)
``smoke``    at most 24 real episodes (pipeline validation)
``pilot``    at most 240 real episodes (structural pilot, NOT formal)
``report``   markdown + CSV + figures for a completed phase
``formal``   prepared only: requires BOTH --confirm and --max-episodes 12800
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .seeds import FORMAL_TOTAL_EPISODES

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _config_path(name: str) -> Path:
    return PROJECT_ROOT / "configs" / name


def cmd_doctor(args: argparse.Namespace) -> int:
    from .doctor import run_doctor

    return run_doctor(verbose=args.verbose)


def cmd_smoke(args: argparse.Namespace) -> int:
    from .experiments import run_smoke_phase

    cap = args.max_episodes if args.max_episodes is not None else 24
    if cap > 24:
        print("smoke budget is capped at 24 episodes by the protocol", file=sys.stderr)
        return 2
    report = run_smoke_phase(PROJECT_ROOT, _config_path("dev_v01.json"), max_episodes=cap)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0


def cmd_pilot(args: argparse.Namespace) -> int:
    from .experiments import run_pilot_phase

    cap = args.max_episodes if args.max_episodes is not None else 240
    if cap > 240:
        print("pilot budget is capped at 240 episodes by the protocol", file=sys.stderr)
        return 2
    reports = run_pilot_phase(PROJECT_ROOT, _config_path("dev_v01.json"), max_episodes=cap)
    out = {method: rep.to_dict() for method, rep in reports.items()}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from .report import write_report

    summary = write_report(PROJECT_ROOT, args.phase)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def cmd_formal(args: argparse.Namespace) -> int:
    from .experiments import run_formal_phase

    if not args.confirm or args.max_episodes != FORMAL_TOTAL_EPISODES:
        print(
            "REFUSED: the formal phase needs explicit human GO. It requires BOTH "
            "--confirm and --max-episodes 12800. Nothing was launched.",
            file=sys.stderr,
        )
        return 2
    try:
        run_formal_phase(PROJECT_ROOT, _config_path("formal_v01.json"),
                         confirm=True, max_episodes=args.max_episodes)
    except RuntimeError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="safefliplab",
        description="SafeFlipLab: budgeted counterfactual safety-reversal testing")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="read-only environment and interface verification")
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("smoke", help="run at most 24 real episodes")
    p.add_argument("--max-episodes", type=int, default=None)
    p.set_defaults(func=cmd_smoke)

    p = sub.add_parser("pilot", help="run at most 240 real episodes")
    p.add_argument("--max-episodes", type=int, default=None)
    p.set_defaults(func=cmd_pilot)

    p = sub.add_parser("report", help="write phase report from real records")
    p.add_argument("--phase", choices=["smoke", "pilot", "formal"], required=True)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("formal", help="prepared formal run (requires human GO)")
    p.add_argument("--confirm", action="store_true")
    p.add_argument("--max-episodes", type=int, default=None)
    p.set_defaults(func=cmd_formal)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

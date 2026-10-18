"""Subprocess worker for the cross-process ledger budget test.

This is NOT a test module (``unittest discover`` only collects ``test*.py``); it
is a tiny standalone process that bills ONE launch into a shared ledger scope
and prints the outcome. It imports nothing from the simulator.

Usage: ``worker.py <ledger_path> <tag> [<cap>] [<scope>]``.
"""
import sys
from pathlib import Path

from safefliplab.ledger import (
    BudgetExhausted,
    DuplicateLaunch,
    EpisodeKey,
    EpisodeLedger,
    LedgerFormatError,
    LedgerLockTimeout,
)


def main() -> int:
    path = Path(sys.argv[1])
    tag = sys.argv[2]
    cap = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    scope = sys.argv[4] if len(sys.argv) > 4 else "race"
    ledger = EpisodeLedger(path)
    # A unique anchor per tag so each process bills a *distinct* episode_key
    # (concurrency, not the duplicate guard).
    anchor = f"anchor-{tag}"
    key = EpisodeKey(run_id=tag, anchor_id=anchor, repetition=0, condition="00")
    try:
        ledger.reserve_launch(
            key, run_id=tag, phase="formal", method="WideExplore", master_seed=1,
            anchor_id=anchor, anchor_index=0, repetition=0, condition="00",
            sim_seed=1, stream="discovery", max_episodes=cap, budget_scope=scope)
        print("OK")
        return 0
    except BudgetExhausted:
        print("REFUSED")
        return 0
    except DuplicateLaunch:
        print("DUPLICATE")
        return 0
    except LedgerFormatError:
        print("FORMAT")
        return 1
    except LedgerLockTimeout:
        print("TIMEOUT")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

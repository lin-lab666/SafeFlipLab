"""Subprocess worker for the V02 ledger cross-process budget test.

NOT a test module (``unittest discover`` only collects ``test*.py``). It bills
ONE launch into a shared ledger scope and prints the outcome.

Usage: ``ledger21_worker.py <ledger_path> <tag> <cap> <scope>``.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v02lab.ledger21 import (  # noqa: E402
    BudgetExhausted,
    DuplicateLaunch,
    EpisodeKey21,
    EpisodeLedger21,
    LedgerFormatError,
    LedgerLockTimeout,
)


def main() -> int:
    path, tag, cap, scope = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    ledger = EpisodeLedger21(path, phase="formal")
    anchor = f"anchor-{tag}"
    key = EpisodeKey21(run_id=tag, anchor_id=anchor, repetition=0, condition="00")
    try:
        ledger.reserve_launch(key, method="WideExplore", master_seed=1, anchor_id=anchor,
                              anchor_index=0, repetition=0, condition="00", sim_seed=1,
                              stream="discovery", max_episodes=cap, budget_scope=scope)
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

"""F-06 forensic audit: does the ledger's ``method`` column or the embedded
``run_id`` label tell the truth?

Decision rule: ``sim_seed`` is derived by SHA-256 *including the method*, so for
every row we recompute ``sim_seed_for(master_seed, method, stream, anchor_id,
repetition)`` using the ledger's ``method`` column. A match proves the recorded
method is the one that actually drove the episode. Run:

    .venv\\Scripts\\python.exe .workbuddy\\tmp_audit\\runid_audit_20261015.py

Read-only: writes nothing to runs/ or reports/.
"""
import collections
import csv
import json
import sys
from pathlib import Path

#: project root derived from this file's location (scripts/ -> project root)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from safefliplab.seeds import sim_seed_for

LEDGER = ROOT / "runs" / "episode_ledger.csv"


def embedded_method(run_id: str) -> str:
    return run_id.split("_")[1]


def main() -> None:
    rows = list(csv.DictReader(open(LEDGER, newline="", encoding="utf-8")))
    print(f"ledger            : {LEDGER}")
    print(f"data rows         : {len(rows)}")
    print(f"header columns    : {len(rows[0])} (legacy 20-col form: "
          f"{'budget_scope' not in rows[0]})")
    print()

    sim_ok = sim_bad = 0
    bad_sim = []
    for r in rows:
        expected = sim_seed_for(int(r["master_seed"]), r["method"], r["stream"],
                                r["anchor_id"], int(r["repetition"]))
        if expected == int(r["sim_seed"]):
            sim_ok += 1
        else:
            sim_bad += 1
            bad_sim.append((r["episode_key"], r["method"], int(r["sim_seed"]), expected))

    print("A) sim_seed reproduces from the ledger `method` column?")
    print(f"   consistent rows : {sim_ok}")
    print(f"   inconsistent    : {sim_bad}")
    for e in bad_sim[:10]:
        print(f"     {e}")
    print("   => the recorded `method` is the one that really drove the episode."
          if sim_bad == 0 else "   => INVESTIGATE")
    print()

    seen = {}
    for r in rows:
        seen.setdefault(r["run_id"], set()).add(r["method"])
    mismatched = [(rid, sorted(ms)) for rid, ms in seen.items()
                  if embedded_method(rid) != sorted(ms)[0]]
    print("B) run_id label vs ledger method")
    print(f"   distinct run_ids      : {len(seen)}")
    print(f"   label mismatches      : {len(mismatched)}")
    for rid, ms in mismatched:
        print(f"     run_id  = {rid}")
        print(f"       embedded label = {embedded_method(rid)} / recorded method = {ms[0]}")
    print()

    print("C) proof for the first mismatch (method-dependent seed)")
    if mismatched:
        rid = mismatched[0][0]
        row = next(r for r in rows if r["run_id"] == rid)
        print(f"   observed sim_seed                      = {row['sim_seed']}")
        for m in ("WideExplore", "VerifyFirst"):
            v = sim_seed_for(int(row["master_seed"]), m, row["stream"],
                             row["anchor_id"], int(row["repetition"]))
            verdict = "MATCH" if str(v) == row["sim_seed"] else "no"
            print(f"   sim_seed_for({m:<11}) = {v}  -> {verdict}")
        print()

    byphase = collections.Counter()
    for rid in mismatched:
        byphase[rid[0].split("_")[0]] += 1
    print(f"D) label mismatches by phase: {dict(byphase)}")
    print()
    print("VERDICT: the `method` column is authoritative; the affected run_id "
          "strings are a cosmetic labelling defect (F-06)." if sim_bad == 0
          else "VERDICT: unresolved")


if __name__ == "__main__":
    main()

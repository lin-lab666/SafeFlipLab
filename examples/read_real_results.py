#!/usr/bin/env python3
"""Read-only viewer for SafeFlipLab V02 real historical results.

WHAT THIS IS
  A pure-Python, fully offline script that reads the *already-published*
  summary artefacts in ``v02/reports/`` (JSON + CSV + Markdown) and prints a
  structured result summary, then renders one concise matplotlib figure.
  It launches **zero** episodes, imports **no** simulator, calls **no**
  evaluator, and writes **nothing** except the optional PNG figure.

WHAT THIS IS NOT
  It is not a new experiment, not a re-run, and not a synthesised demo. The
  numbers below are the real, frozen, exploratory, INCONCLUSIVE V02 results.
  It must not be confused with ``examples/offline_demo.py``, which prints
  synthetic toy output only.

Run:
    python examples/read_real_results.py                 # pilot, writes docs/assets/result_summary.png
    python examples/read_real_results.py --phase smoke    # smoke series (same schema)
    python examples/read_real_results.py --no-plot        # text summary only
    python examples/read_real_results.py --output path.png

================================================================================
CONTENT PROVENANCE — FOUR CATEGORIES (kept explicitly separate below)
================================================================================
[1] SYNTHETIC
    None in this script. This script contains *no* synthetic data.
    Synthetic output lives only in ``examples/offline_demo.py`` and stays there.

[2] REAL HISTORICAL
    Values read directly, verbatim, from the published summary artefacts in
    ``v02/reports/``: the M1 anchor-level point estimates + bootstrap CIs, the
    M2 per-condition mean shares, the binary (C13) collision event counts, the
    anchor counts and the sample sizes. These are the frozen V02 exploratory
    results and are NOT recomputed here from raw trajectories.

[3] RECOMPUTABLE
    Descriptive statistics that can be independently reproduced from the
    *public* summary CSVs, with no access to private runs/ data. Concretely
    this script recomputes, from ``<phase>_anchors.csv``: the per-anchor mean
    ``delta_gap`` and their cross-anchor mean (which must equal the stored M1
    ``delta_gap`` point estimate), plus whether each 95% CI crosses zero.

[4] REQUIRES PRIVATE DATA
    A *full* independent recomputation of every endpoint from first principles
    (per-step min-TTC from the raw 1D trajectories, M2 step shares, all
    bootstrap draws, G-gates) is NOT possible from the public summary files
    alone. ``scripts/independent_verify_all.py`` (the full re-computer) needs
    the private ledger + the raw per-episode JSON under ``runs/``, which are
    deliberately absent from this public workspace. This script only reads the
    already-aggregated, already-published CSV/JSON/MD and does not attempt that.

================================================================================
REAL HISTORICAL RESULTS — READ ONLY — NOT SYNTHETIC, NOT A NEW EXPERIMENT
================================================================================
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "v02" / "reports"

# Fixed display order for the four contrasts / conditions (public schema).
CONTRAST_ORDER = ("delta_gap", "delta_speed", "delta_both", "i_lin")
CONDITION_ORDER = ("00", "10", "01", "11")

BANNER = "REAL HISTORICAL RESULTS — READ ONLY — NOT SYNTHETIC, NOT A NEW EXPERIMENT"


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_phase(phase: str) -> dict:
    """Load all published artefacts for a phase and return a structured dict."""
    summary = _read_json(REPORTS_DIR / f"{phase}_summary.json")
    anchors = _read_csv_rows(REPORTS_DIR / f"{phase}_anchors.csv")
    contrasts = _read_csv_rows(REPORTS_DIR / f"{phase}_contrasts.csv")
    report_md = (REPORTS_DIR / f"{phase}_report.md").read_text(encoding="utf-8")

    estimates = summary["estimates"]
    m2 = summary.get("m2_secondary", {})
    binary = summary.get("binary_counts", {})

    return {
        "phase": phase,
        "protocol": summary.get("protocol"),
        "protocol_hash": summary.get("protocol_hash"),
        "confirmatory_status": summary.get("confirmatory_status"),
        "launched": summary.get("launched"),
        "completed": summary.get("completed"),
        "errored": summary.get("errored"),
        "interrupted": summary.get("interrupted"),
        "wall_time_s": summary.get("wall_time_s"),
        "n_anchors": summary.get("n_anchors"),
        "n_primary_quartets": summary.get("n_primary_quartets"),
        "n_usable_quartets": summary.get("n_usable_quartets"),
        "estimates": estimates,
        "heterogeneity": summary.get("heterogeneity", {}),
        "m2": m2,
        "binary": binary,
        "anchors": anchors,
        "contrasts": contrasts,
        "report_md": report_md,
        "summary_json_path": REPORTS_DIR / f"{phase}_summary.json",
        "anchors_csv_path": REPORTS_DIR / f"{phase}_anchors.csv",
        "contrasts_csv_path": REPORTS_DIR / f"{phase}_contrasts.csv",
        "report_md_path": REPORTS_DIR / f"{phase}_report.md",
    }


def _crosses_zero(ci_low: float, ci_high: float) -> bool:
    return ci_low <= 0.0 <= ci_high


def recompute_anchor_delta_gap(anchors: list[dict]) -> dict:
    """[RECOMPUTABLE] Recompute per-anchor mean delta_gap from the public CSV."""
    per_anchor = []
    for row in anchors:
        per_anchor.append(
            {
                "anchor_id": row["anchor_id"],
                "anchor_index": int(row["anchor_index"]),
                "mean_delta_gap": float(row["mean_delta_gap"]),
                "n_usable": int(row["n_usable"]),
            }
        )
    per_anchor.sort(key=lambda d: d["anchor_index"])
    values = [d["mean_delta_gap"] for d in per_anchor]
    mean = sum(values) / len(values) if values else float("nan")
    return {"per_anchor": per_anchor, "mean_delta_gap": mean}


def print_summary(data: dict) -> None:
    """Print the structured, provenance-labelled result summary."""
    phase = data["phase"]
    est = data["estimates"]
    m2 = data["m2"]
    binary = data["binary"]
    rec = recompute_anchor_delta_gap(data["anchors"])

    print("=" * 78)
    print(BANNER)
    print("=" * 78)
    print(f"[phase] {phase}  |  protocol {data['protocol']} "
          f"(hash {data['protocol_hash'][:16]}…, FROZEN)")
    print(f"[confirmatory status] {data['confirmatory_status']}  "
          f"(sampling assumptions unproven -> no p-values are produced)")
    print()
    print("Sources read (public, read-only):")
    print(f"  JSON  : {data['summary_json_path']}")
    print(f"  CSV   : {data['anchors_csv_path']}")
    print(f"  CSV   : {data['contrasts_csv_path']}")
    print(f"  MD    : {data['report_md_path']}")
    print()

    print("-" * 78)
    print("[REAL HISTORICAL] Sample sizes")
    print("-" * 78)
    print(f"  episodes launched : {data['launched']}  (all billed)")
    print(f"  episodes completed: {data['completed']}  "
          f"errored={data['errored']} interrupted={data['interrupted']}")
    print(f"  wall time         : {data['wall_time_s']} s")
    print(f"  anchors (indep. unit): {data['n_anchors']}")
    print(f"  primary quartets  : {data['n_primary_quartets']}  "
          f"(usable {data['n_usable_quartets']})")
    if "n_episodes_parsed" in m2:
        print(f"  M2 episodes parsed: {m2['n_episodes_parsed']}  "
              f"complete quartets {m2['n_complete_quartets']}  "
              f"tau_low={m2.get('tau_low_s')} s")
    print()

    print("-" * 78)
    print("[REAL HISTORICAL] M1 = per-episode min forward TTC (s).")
    print("  Delta = anchor-level paired-difference mean; CI = anchor-level "
          "cluster bootstrap.")
    print("  NEGATIVE delta = intervention reduced safety margin (reversal).")
    print("-" * 78)
    print(f"  {'contrast':<12} {'label':<14} {'point (s)':>10} "
          f"{'95% CI (s)':>22} {'anchors':>8}  crosses 0")
    for key in CONTRAST_ORDER:
        e = est[key]
        crosses = _crosses_zero(e["ci_low"], e["ci_high"])
        print(f"  {key:<12} {e['label']:<14} {e['point']:>10.4f} "
              f"[{e['ci_low']:>8.4f}, {e['ci_high']:>8.4f}]"
              f"{e['n_anchors']:>8}  {'YES' if crosses else 'NO '}")
    print()

    print("-" * 78)
    print("[REAL HISTORICAL] M2 = share of policy steps with forward TTC below "
          "tau_low.")
    print("  DIRECTION WARNING (D43): smaller M2 = safer -> negative delta = "
          "safer,")
    print("  OPPOSITE sign convention to M1. Do not compare signs across "
          "endpoints.")
    print("-" * 78)
    per_cond = m2.get("per_condition_mean_share", {})
    print("  per-condition mean share:")
    for cond in CONDITION_ORDER:
        v = per_cond.get(cond)
        if v is None:
            continue
        print(f"    {cond} = {v:.4f}")
    if "anchor_level_contrasts" in m2:
        print("  anchor-level contrasts (point | 95% CI):")
        for key in CONTRAST_ORDER:
            c = m2["anchor_level_contrasts"].get(key)
            if c is None:
                continue
            crosses = _crosses_zero(c["ci_low"], c["ci_high"])
            print(f"    {key:<12} {c['point']:>8.4f}  "
                  f"[{c['ci_low']:>8.4f}, {c['ci_high']:>8.4f}]  "
                  f"crosses 0: {'YES' if crosses else 'NO '}")
    print()

    print("-" * 78)
    print("[REAL HISTORICAL] C13 binary collision endpoint (descriptive only).")
    print("-" * 78)
    events = binary.get("per_condition_events", {})
    print(f"  complete quartets      : {binary.get('n_quartets')}")
    print("  per-condition events   : "
          + ", ".join(f"{c}={events.get(c)}" for c in CONDITION_ORDER))
    print(f"  reverse_pairs (Y00=0,Y11=1): {binary.get('reverse_pairs')}")
    print(f"  rescue_pairs (Y00=1,Y11=0): {binary.get('rescue_pairs')}")
    print("  note: 0 events => no collision-rate claim (rule of three not "
          "applied;")
    print("        its iid assumption does not hold at the episode level).")
    print()

    print("-" * 78)
    print("[RECOMPUTABLE] Cross-check from public summary CSV "
          f"({data['anchors_csv_path'].name})")
    print("-" * 78)
    print(f"  anchors in CSV               : {len(rec['per_anchor'])}")
    print(f"  recomputed mean(delta_gap)   : {rec['mean_delta_gap']:.12f}")
    print(f"  stored M1 delta_gap point    : {est['delta_gap']['point']:.12f}")
    print("  match: these two must agree; the CSV anchor-level means are the "
          "exact")
    print("  inputs to the stored aggregate point estimate.")
    print()

    print("-" * 78)
    print("[REQUIRES PRIVATE DATA] Full first-principles recomputation")
    print("-" * 78)
    print("  The per-step min-TTC, M2 step shares, all bootstrap draws and the")
    print("  G-gates cannot be recomputed from these public summaries alone.")
    print("  scripts/independent_verify_all.py needs the private ledger + the")
    print("  raw per-episode JSON under runs/, which are NOT in this public")
    print("  workspace. This script reads only the already-published aggregate")
    print("  CSV/JSON/MD and does not attempt that.")
    print()
    print("=" * 78)
    print(BANNER)
    print("=" * 78)


def render_figure(data: dict, out_path: Path) -> None:
    """Render one concise summary figure (forest + per-anchor dot plot)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    phase = data["phase"]
    est = data["estimates"]
    rec = recompute_anchor_delta_gap(data["anchors"])

    fig, (ax_forest, ax_anchor) = plt.subplots(
        1, 2, figsize=(12.5, 5.2), gridspec_kw={"width_ratios": [1.0, 1.25]}
    )

    # --- Panel A: M1 forest plot (anchor-level point estimate + bootstrap CI).
    keys = list(CONTRAST_ORDER)
    labels = [est[k]["label"] for k in keys]
    ys = list(range(len(keys)))[::-1]
    for y, key in zip(ys, keys):
        e = est[key]
        crosses = _crosses_zero(e["ci_low"], e["ci_high"])
        color = "#888888" if crosses else "#c0392b"
        ax_forest.errorbar(
            e["point"],
            y,
            xerr=[[e["point"] - e["ci_low"]], [e["ci_high"] - e["point"]]],
            fmt="o",
            color=color,
            ecolor=color,
            elinewidth=1.6,
            capsize=4,
            markersize=5,
        )
    ax_forest.axvline(0.0, color="#333333", linewidth=0.9, linestyle="--")
    ax_forest.set_yticks(ys)
    ax_forest.set_yticklabels(labels, fontsize=9)
    ax_forest.set_xlabel("M1 delta (s)  —  negative = reduced safety margin",
                         fontsize=9)
    ax_forest.set_title(f"V02 {phase} — M1 anchor-level estimates\n"
                        "(point + 95% anchor cluster bootstrap CI)",
                        fontsize=10)
    ax_forest.grid(axis="x", alpha=0.25, linewidth=0.6)
    ax_forest.annotate(
        "grey = CI crosses 0\nred  = CI excludes 0",
        xy=(0.02, 0.98),
        xycoords="axes fraction",
        ha="left",
        va="top",
        fontsize=8,
        color="#444444",
    )

    # --- Panel B: per-anchor mean delta_gap (recomputable from public CSV).
    per = rec["per_anchor"]
    xs = [d["mean_delta_gap"] for d in per]
    idx = [d["anchor_index"] for d in per]
    ax_anchor.scatter(xs, idx, s=28, color="#2c6fbb", alpha=0.85, zorder=3)
    ax_anchor.axvline(0.0, color="#333333", linewidth=0.9, linestyle="--",
                      zorder=1)
    ax_anchor.axvline(rec["mean_delta_gap"], color="#c0392b", linewidth=1.4,
                      linestyle="-", zorder=2,
                      label=f"mean = {rec['mean_delta_gap']:+.4f} s")
    ax_anchor.axvline(est["delta_gap"]["point"], color="#e67e22", linewidth=1.2,
                      linestyle=":", zorder=2,
                      label=f"stored = {est['delta_gap']['point']:+.4f} s")
    ax_anchor.set_xlabel("per-anchor mean delta_gap (s)", fontsize=9)
    ax_anchor.set_ylabel("anchor index", fontsize=9)
    ax_anchor.set_title(
        f"V02 {phase} — per-anchor mean delta_gap\n"
        f"(n={len(per)} anchors; recomputed from {data['anchors_csv_path'].name})",
        fontsize=10,
    )
    ax_anchor.grid(axis="x", alpha=0.25, linewidth=0.6)
    ax_anchor.legend(fontsize=8, loc="upper right", framealpha=0.9)

    fig.suptitle(
        "SafeFlipLab V02 — REAL HISTORICAL RESULTS (read-only, NOT synthetic)",
        fontsize=12,
        y=1.02,
    )
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[figure] wrote {out_path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only viewer for SafeFlipLab V02 real historical "
                    "results (no simulator, no episodes, no runs/ writes)."
    )
    parser.add_argument(
        "--phase",
        choices=("pilot", "smoke"),
        default="pilot",
        help="which frozen report series to read (default: pilot)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs" / "assets" / "result_summary.png",
        help="output path for the summary PNG "
             "(default: docs/assets/result_summary.png)",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="skip rendering the matplotlib figure",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    data = load_phase(args.phase)
    print_summary(data)
    if not args.no_plot:
        render_figure(data, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())

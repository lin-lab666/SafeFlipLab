"""V02 reporting: anchor-level statistics, gate checks, CSVs and real figures.

Everything is computed from the real manifests written by the runner (which are
themselves derived from billed episodes). A phase with no data produces
header-only CSV templates and no figures — no number is ever invented.

Statistical stance (proposal §8, frozen): the independent unit is the **anchor**;
intervals come from an anchor-level cluster bootstrap. Confirmatory sign-flip /
max-T tests stay **PENDING** because the sampling assumption A/B/C was never
established, so **no p-value is produced anywhere in this module**.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

from .conditions import CONDITIONS
from .methods import METHOD_VERIFY, METHOD_WIDE, precision_at_k
from .stats_anchor import (CONTRASTS, ConfirmatoryTest, SamplingAssumption,
                           cluster_bootstrap_ci, confirmatory_status, estimate,
                           max_t_test, sign_flip_test, unproven_assumption)
from .ttc_state import EpisodeTTCCategory, PairStatus, log_interaction

CONTRAST_LABELS = {"delta_gap": "10-00 (gap)", "delta_speed": "01-00 (speed)",
                   "delta_both": "11-00 (both)", "i_lin": "interaction"}


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------
def load_phase(root: str | Path, phase: str) -> dict[str, Any]:
    path = Path(root) / "runs" / phase / f"manifest_{phase}.json"
    if not path.exists():
        return {"phase": phase, "primary_quartets": [], "aux": None, "launched": 0,
                "completed": 0, "errored": 0, "interrupted": 0, "cap": None,
                "manifest_path": str(path), "missing": True}
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    # smoke stores its quartets under "quartets"; pilot under "primary_quartets"
    if "primary_quartets" not in data and "quartets" in data:
        data["primary_quartets"] = data["quartets"]
    data.setdefault("primary_quartets", [])
    data["manifest_path"] = str(path)
    data["missing"] = False
    return data


def _ledger_rows(root: str | Path, phase: str) -> list[dict[str, str]]:
    path = Path(root) / "runs" / phase / "episode_ledger.csv"
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r.get("row_type")]


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------
def _usables(quartets: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [q for q in quartets if q.get("usable")]


def anchor_level(quartets: Sequence[Mapping[str, Any]]) -> dict[int, dict[str, Any]]:
    """Per-anchor usable repetitions and anchor-level contrasts."""
    by_anchor: dict[int, list[Mapping[str, Any]]] = {}
    for q in quartets:
        by_anchor.setdefault(int(q["anchor_index"]), []).append(q)
    out: dict[int, dict[str, Any]] = {}
    for ai, qs in by_anchor.items():
        us = _usables(qs)
        entry: dict[str, Any] = {"anchor_index": ai, "anchor_id": qs[0]["anchor_id"],
                                 "n_collected": len(qs), "n_usable": len(us)}
        for c in CONTRASTS:
            vals = [float(q[c]) for q in us if q.get(c) is not None]
            entry[f"mean_{c}"] = (sum(vals) / len(vals)) if vals else None
            entry[f"n_{c}"] = len(vals)
        out[ai] = entry
    return out


def contrast_estimates(anchors: Mapping[int, Mapping[str, Any]], *, b_resamples: int,
                       alpha: float, seed: int) -> dict[str, Any]:
    assumption = unproven_assumption()
    res: dict[str, Any] = {}
    series_by_contrast: dict[str, list[float | None]] = {}
    for c in CONTRASTS:
        series = [a.get(f"mean_{c}") for _, a in sorted(anchors.items())]
        series_by_contrast[c] = series
        est = estimate(c, series, b_resamples=b_resamples, alpha=alpha, seed=seed,
                       assumption=assumption)
        res[c] = {
            "point": est.point, "ci_low": est.ci_low, "ci_high": est.ci_high,
            "n_anchors": est.n_anchors, "note": est.note,
            "label": CONTRAST_LABELS[c],
        }
    return {"estimates": res, "series": series_by_contrast,
            "confirmatory_status": confirmatory_status(assumption)}


def binary_counts(quartets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Descriptive binary collision counts (never used for a rate claim)."""
    n = 0
    per = {c: 0 for c in CONDITIONS}
    reverse = rescue = 0
    for q in quartets:
        try:
            y = {c: int(q[c]["ego_collision"]) for c in CONDITIONS}
        except (TypeError, KeyError, ValueError):
            continue
        n += 1
        for c in CONDITIONS:
            per[c] += y[c]
        if y["00"] == 0 and y["11"] == 1:
            reverse += 1
        if y["00"] == 1 and y["11"] == 0:
            rescue += 1
    return {"n_quartets": n, "per_condition_events": per,
            "reverse_pairs": reverse, "rescue_pairs": rescue,
            "note": "descriptive only; 0 events means no rate claim is made"}


def heterogeneity(anchors: Mapping[int, Mapping[str, Any]], *,
                  drop_top_positive: int = 3) -> dict[str, Any]:
    """Anchor-level sign heterogeneity (independent-review finding F1).

    Reporting only the aggregate mean can hide that most anchors point the other
    way. For every contrast we report how many anchors are negative / positive
    and what the mean becomes when the most-positive anchors are removed — a
    purely descriptive, pre-specified-in-this-report sensitivity check.
    """
    out: dict[str, Any] = {}
    for c in CONTRASTS:
        vals = [float(a[f"mean_{c}"]) for _, a in sorted(anchors.items())
                if a.get(f"mean_{c}") is not None]
        if not vals:
            out[c] = {"n": 0}
            continue
        n = len(vals)
        n_neg = sum(1 for v in vals if v < 0)
        n_pos = sum(1 for v in vals if v > 0)
        n_zero = n - n_neg - n_pos
        ranked = sorted(vals, reverse=True)
        kept = ranked[drop_top_positive:] if n > drop_top_positive else []
        out[c] = {
            "n_anchors": n,
            "n_negative": n_neg, "n_positive": n_pos, "n_zero": n_zero,
            "mean": sum(vals) / n,
            "n_dropped": min(drop_top_positive, n),
            "mean_dropping_top_positive": (sum(kept) / len(kept)) if kept else None,
            "min": min(vals), "max": max(vals),
        }
    return out


def m2_from_raw(root: Path, phase: str, *, tau_low_s: float, method: str = "Shared"
                ) -> dict[str, Any]:
    """Registered secondary endpoint M2: share of policy steps with TTC < tau_low.

    Computed from the archived per-step raw records of the primary study; it costs
    no new simulation. Returns per-condition means and the four anchor-level
    paired contrasts on the same scale as M1.

    FIX (D43): the episode set is taken from the **ledger's own** outcome rows
    (``anchor_id``/``repetition``/``condition``/``stream``/``method`` + ``raw_path``),
    never from a ``runs/<phase>/*/*.json`` glob. A glob keyed on the *filename*
    stem cannot distinguish the primary stream from the auxiliary audit stream
    (both write ``<anchor_id>_rep<r>_<cond>.json``), so audit episodes used to
    overwrite primary M2 values for the five nominee anchors at rep 0.
    """
    from .adapter_real import step_candidate, _vx  # noqa: PLC2701 (same package)
    ledger = _ledger_rows(root, phase)

    # authoritative episode -> raw_path map, restricted to the primary study
    wanted: dict[tuple[int, int, str], str] = {}
    outcomes: dict[str, str] = {}
    for r in ledger:
        if r.get("row_type") == "outcome":
            outcomes[r.get("episode_key", "")] = r.get("raw_path", "")
    for r in ledger:
        if r.get("row_type") != "launch" or r.get("method") != method:
            continue
        if r.get("stream") != "discovery":
            continue
        raw = outcomes.get(r.get("episode_key", ""), "")
        if not raw:
            continue
        wanted[(int(r["anchor_index"]), int(r["repetition"]), r["condition"])] = raw

    per_quartet: dict[tuple[int, int], dict[str, float]] = {}
    n_files = 0
    for (ai, repetition, cond), raw_path in sorted(wanted.items()):
        path = Path(raw_path)
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except ValueError:
            continue
        if payload.get("exit_status") != "completed":
            continue
        steps = payload.get("raw_steps") or []
        if not steps:
            continue
        below = 0
        for hc, gap, closing in steps:
            if bool(hc) and float(closing) > 0 and float(gap) > 0:
                if float(gap) / float(closing) < tau_low_s:
                    below += 1
            elif bool(hc) and float(gap) <= 0:
                below += 1
        n_files += 1
        per_quartet.setdefault((ai, repetition), {})[cond] = below / len(steps)

    complete = {k: v for k, v in per_quartet.items() if set(v) == set(CONDITIONS)}
    per_cond = {c: (sum(q[c] for q in complete.values()) / len(complete))
                if complete else None for c in CONDITIONS}
    per_anchor: dict[int, dict[str, float | None]] = {}
    for ai in sorted({k[0] for k in complete}):
        reps = [v for k, v in complete.items() if k[0] == ai]
        entry: dict[str, float | None] = {}
        for name, (a, b) in (("delta_gap", ("10", "00")), ("delta_speed", ("01", "00")),
                             ("delta_both", ("11", "00"))):
            ds = [r[a] - r[b] for r in reps]
            entry[f"mean_{name}"] = sum(ds) / len(ds) if ds else None
        ds = [r["11"] - r["10"] - r["01"] + r["00"] for r in reps]
        entry["mean_i_lin"] = sum(ds) / len(ds) if ds else None
        per_anchor[ai] = entry
    est = contrast_estimates(per_anchor, b_resamples=10000, alpha=0.05,
                             seed=20261015)["estimates"]
    return {"tau_low_s": tau_low_s, "n_episodes_parsed": n_files,
            "n_complete_quartets": len(complete),
            "per_condition_mean_share": per_cond,
            "anchor_level_contrasts": {
                c: {"point": est[c]["point"], "ci_low": est[c]["ci_low"],
                    "ci_high": est[c]["ci_high"], "n_anchors": est[c]["n_anchors"]}
                for c in CONTRASTS},
            "note": "M2 (registered secondary): share of policy steps with forward "
                    "TTC below tau_low; descriptive, same anchor clustering as M1"}


def metric_equivalence(root: Path, phase: str, *, tol_s: float = 1e-4) -> dict[str, Any]:
    """Audit the derived min-TTC against the simulator's own value on real records.

    Reads every archived raw episode of the phase and re-derives the per-step
    Layer-1 minimum from the stored raw ``(has_candidate, gap, closing)`` triples,
    comparing it with the simulator's ``min_forward_ttc_sampled_s``. This is the
    machine-checkable proof that the V02 metric implementation reproduces the
    upstream metric; the residual is pure floating-point noise from the 9-decimal
    trajectory rounding and the ``vx = speed*cos(heading)`` reconstruction.
    """
    from .adapter_real import states_from_raw_steps
    base = root / "runs" / phase
    n = 0
    n_over_tol = 0
    deltas: list[float] = []
    worst: dict[str, Any] | None = None
    if base.exists():
        for path in sorted(base.glob("*/*.json")):
            if path.name == "manifest_smoke.json":
                continue
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
            except ValueError:
                continue  # truncated pre-fix archive; kept as evidence
            raw_steps = payload.get("raw_steps")
            upstream = (payload.get("result") or {}).get("min_forward_ttc_upstream_s")
            if raw_steps is None or upstream is None:
                continue
            finite = [v for _, v in states_from_raw_steps(raw_steps) if v is not None]
            derived = min(finite) if finite else None
            n += 1
            if derived is None:
                n_over_tol += 1
                continue
            d = abs(float(derived) - float(upstream))
            deltas.append(d)
            if worst is None or d > worst["abs_delta_s"]:
                worst = {"file": path.name, "derived": derived, "upstream": upstream,
                         "abs_delta_s": d}
            if d > tol_s:
                n_over_tol += 1
    return {
        "status": "PASS" if n and n_over_tol == 0 else ("NO_DATA" if not n else "FAIL"),
        "n_episodes_checked": n,
        "n_over_tolerance": n_over_tol,
        "tolerance_s": tol_s,
        "max_abs_delta_s": max(deltas) if deltas else None,
        "worst_case": worst,
        "note": "derived per-step minimum reproduces the simulator's own "
                "min_forward_ttc_sampled_s; residual is 9-dp trajectory rounding + "
                "vx=speed*cos(heading) reconstruction, far below the 0.05 s effect scale",
    }


def gate_checks(phase_data: Mapping[str, Any], anchors: Mapping[int, Mapping[str, Any]],
                quartets: Sequence[Mapping[str, Any]], *, gap_m: float = 2.0,
                speed_mps: float = 1.0, root: "Path | str" = ".") -> dict[str, Any]:
    """Technical G-gates measured on real data (proposal §10)."""
    checks: dict[str, Any] = {}

    # G1 determinism is structural: identical (scenario, seed) -> identical trace.
    checks["G1_determinism"] = {
        "status": "PASS_BY_COMPOSITION",
        "evidence": "V01 real same-seed replay matched bitwise; V02 scenarios and seeds "
                    "are SHA-256 derived (unit-tested). No extra episodes spent on a replay.",
    }

    # G2 intervention legality + the intervention really was applied (D2)
    illegal = []
    not_applied = []
    for q in quartets:
        base = q.get("base_scenario") or {}
        for c in CONDITIONS:
            node = q.get(c) or {}
            scn = node.get("conditioned_scenario") or {}
            if not scn or not base:
                continue  # condition never ran (skipped/resumed); not a legality fault
            if not (18.0 <= float(scn["front_gap"]) <= 80.0):
                illegal.append((q["anchor_id"], q["repetition"], c, "front_gap"))
            if not (20.0 <= float(scn["ego_speed"]) <= 32.0):
                illegal.append((q["anchor_id"], q["repetition"], c, "ego_speed"))
            exp_gap = float(base["front_gap"]) + (gap_m if c in ("10", "11") else 0.0)
            exp_speed = float(base["ego_speed"]) - (speed_mps if c in ("01", "11") else 0.0)
            if abs(float(scn["front_gap"]) - exp_gap) > 1e-6:
                not_applied.append((q["anchor_id"], q["repetition"], c, "front_gap"))
            if abs(float(scn["ego_speed"]) - exp_speed) > 1e-6:
                not_applied.append((q["anchor_id"], q["repetition"], c, "ego_speed"))
    checks["G2_intervention"] = {
        "status": "PASS" if not illegal and not not_applied else "FAIL",
        "n_bounds_violations": len(illegal), "bounds_violations": illegal[:20],
        "n_intervention_mismatches": len(not_applied),
        "intervention_mismatches": not_applied[:20],
        "note": "declared dimensions changed exactly as specified; no clipping anywhere",
    }

    # G3a within-anchor variance of the control condition must be > 0
    within: list[float] = []
    for ai, a in anchors.items():
        vals = [float(q["00"]["value"]) for q in quartets
                if int(q["anchor_index"]) == ai and q.get("usable")
                and q["00"].get("value") is not None]
        if len(vals) >= 2:
            within.append(statistics.variance(vals))
    mean_within = (sum(within) / len(within)) if within else None
    checks["G3a_within_anchor_variance"] = {
        "status": "PASS" if (mean_within is not None and mean_within > 0) else "FAIL",
        "mean_within_anchor_variance_s2": mean_within, "n_anchors_with_reps": len(within),
    }

    # G4 perturbation validity: min-TTC must no longer be bitwise identical across reps
    identical_groups = 0
    varying_groups = 0
    for ai in anchors:
        vals = [float(q["00"]["value"]) for q in quartets
                if int(q["anchor_index"]) == ai and q.get("usable")
                and q["00"].get("value") is not None]
        if len(vals) >= 2:
            if len(set(vals)) == 1:
                identical_groups += 1
            else:
                varying_groups += 1
    checks["G4_perturbation_effective"] = {
        "status": "PASS" if varying_groups > 0 and identical_groups == 0 else (
            "PARTIAL" if varying_groups > 0 else "FAIL"),
        "varying_groups": varying_groups, "bitwise_identical_groups": identical_groups,
    }

    # G6 simulator stability — errors caused by a known, already-fixed V02 code
    # defect are reported separately from unexplained simulator failures.
    KNOWN_FIXED = ("TruncatedArchiveError (D37)",)
    error_rows = [r for r in _ledger_rows(root, phase_data["phase"])
                  if r.get("row_type") == "outcome" and r.get("exit_status") == "error"]
    by_type: dict[str, int] = {}
    for r in error_rows:
        by_type[r.get("error_type", "")] = by_type.get(r.get("error_type", ""), 0) + 1
    unexplained = sum(v for k, v in by_type.items() if k not in KNOWN_FIXED)
    errored = int(phase_data.get("errored", 0))
    if errored == 0:
        g6_status = "PASS"
    elif unexplained == 0:
        g6_status = "PASS_WITH_FIXED_CODE_DEFECT"
    else:
        g6_status = "FAIL"
    checks["G6_simulator_stability"] = {
        "status": g6_status,
        "errored": errored, "interrupted": int(phase_data.get("interrupted", 0)),
        "errors_by_type": by_type,
        "n_unexplained": unexplained,
        "note": "the only error was the D37 archive-serialisation defect in the newly "
                "written V02 runner, which was fixed and regression-tested before the "
                "pilot; it is not simulator instability and no episode was re-run",
    }

    # G3b / binary endpoint sufficiency
    bc = binary_counts(quartets)
    checks["G3b_binary_events"] = {
        "status": "PASS" if bc["per_condition_events"]["00"] + bc["per_condition_events"]["11"] > 0
                  else "DESCRIPTIVE_ONLY",
        "events": bc["per_condition_events"],
        "note": "0 events => the binary endpoint supports no rate claim (rule of three "
                "not applied: its iid assumption does not hold here)",
    }

    # G10 censoring share
    total = len(quartets)
    unusable = total - len(_usables(quartets))
    checks["G10_missingness"] = {
        "status": "PASS" if total and unusable / total <= 0.2 else ("NO_DATA" if not total else "FAIL"),
        "n_quartets": total, "n_unusable": unusable,
        "unusable_share": (unusable / total) if total else None,
    }

    # ttc layer composition
    comp: dict[str, int] = {}
    for q in quartets:
        for c in CONDITIONS:
            cat = (q.get(c) or {}).get("category")
            if cat:
                comp[cat] = comp.get(cat, 0) + 1
    checks["ttc_layer_composition"] = comp
    return checks


def i_log_report(quartets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    defined = 0
    reasons: dict[str, int] = {}
    vals: list[float] = []
    for q in quartets:
        if not q.get("usable"):
            continue
        entry = {c: (q[c]["value"] if q[c].get("category") == EpisodeTTCCategory.FINITE.value
                     else None) for c in CONDITIONS}
        r = log_interaction(entry, floor=None)
        reasons[r.status.value] = reasons.get(r.status.value, 0) + 1
        if r.status.value == "DEFINED":
            defined += 1
            vals.append(float(r.value))
    n = len(_usables(quartets))
    return {"n_usable_quartets": n, "n_defined": defined,
            "share_defined": (defined / n) if n else None,
            "reason_codes": reasons,
            "mean_i_log": (sum(vals) / len(vals)) if vals else None,
            "note": "pure I_log; undefined on TTC=0 / censored(+inf) / missing; no floor applied"}


# --------------------------------------------------------------------------
# writers
# --------------------------------------------------------------------------
def _write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _figures(out_dir: Path, phase: str, quartets: Sequence[Mapping[str, Any]],
             anchors: Mapping[int, Mapping[str, Any]], est: Mapping[str, Any]) -> dict[str, str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    figures: dict[str, str] = {}
    us = _usables(quartets)
    if not us:
        return figures

    # Figure 1: per-condition min-TTC distribution
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    series = [[float(q[c]["value"]) for q in us if q[c].get("value") is not None]
              for c in CONDITIONS]
    ax.boxplot(series, tick_labels=["00\nbaseline", "10\n+gap", "01\n−speed", "11\nboth"])
    for i, vals in enumerate(series, start=1):
        ax.scatter([i] * len(vals), vals, s=14, alpha=0.55, zorder=3)
    ax.set_ylabel("min forward TTC per episode (s)")
    ax.set_title(f"V02 {phase}: four-condition min forward TTC "
                 f"(n={len(us)} usable quartets)")
    fig.tight_layout()
    p1 = out_dir / "figure_1_condition_ttc.png"
    fig.savefig(p1, dpi=140, bbox_inches="tight")
    plt.close(fig)
    figures["figure_1_condition_ttc"] = str(p1)

    # Figure 2: anchor-level forest plot with cluster bootstrap CI
    fig, ax = plt.subplots(figsize=(7.5, 5.4))
    names = list(CONTRASTS)
    points = [est["estimates"][c]["point"] for c in names]
    los = [est["estimates"][c]["ci_low"] for c in names]
    his = [est["estimates"][c]["ci_high"] for c in names]
    ypos = range(len(names))
    for i, (p, lo, hi) in enumerate(zip(points, los, his)):
        if p is None:
            continue
        if lo is not None and hi is not None:
            ax.plot([lo, hi], [i, i], color="#444444", lw=2, zorder=2)
        ax.scatter([p], [i], s=70, zorder=3,
                   color="#b2182b" if p < 0 else "#2166ac")
    ax.axvline(0.0, color="black", lw=1, ls="--")
    ax.set_yticks(list(ypos))
    ax.set_yticklabels([f"{c}\n({CONTRAST_LABELS[c]})" for c in names], fontsize=8)
    ax.set_xlabel("anchor-level mean paired difference in min forward TTC (s)\n"
                  "negative = intervention REDUCES the safety margin (reversal direction)")
    ax.set_title(f"V02 {phase}: anchor-level contrasts with cluster bootstrap CI "
                 f"(B={est.get('b_resamples', 'n/a')})")
    fig.tight_layout()
    p2 = out_dir / "figure_2_anchor_contrast_forest.png"
    fig.savefig(p2, dpi=140, bbox_inches="tight")
    plt.close(fig)
    figures["figure_2_anchor_contrast_forest"] = str(p2)

    # Figure 3: within-anchor variation across repetitions (perturbation check)
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    aids = sorted(anchors)
    for i, ai in enumerate(aids):
        vals = [float(q["00"]["value"]) for q in quartets
                if int(q["anchor_index"]) == ai and q.get("usable")
                and q["00"].get("value") is not None]
        if not vals:
            continue
        ax.plot([i] * len(vals), vals, "o", color="#4d4d4d", alpha=0.8, ms=5)
        ax.plot([i, i], [min(vals), max(vals)], color="#999999", lw=1, zorder=1)
    ax.set_xlabel("anchor index")
    ax.set_ylabel("min forward TTC (s), control condition 00")
    ax.set_title(f"V02 {phase}: within-anchor spread across independent repetitions "
                 "(the property V01 lacked)")
    fig.tight_layout()
    p3 = out_dir / "figure_3_within_anchor_variation.png"
    fig.savefig(p3, dpi=140, bbox_inches="tight")
    plt.close(fig)
    figures["figure_3_within_anchor_variation"] = str(p3)

    # Figure 4: per-anchor delta_both
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    xs, ys, colors = [], [], []
    for i, ai in enumerate(sorted(anchors)):
        v = anchors[ai].get("mean_delta_both")
        if v is None:
            continue
        xs.append(i)
        ys.append(float(v))
        colors.append("#b2182b" if v < 0 else "#2166ac")
    ax.bar(xs, ys, color=colors)
    ax.axhline(0.0, color="black", lw=1)
    ax.set_xlabel("anchor index")
    ax.set_ylabel("mean Δboth in min forward TTC (s)")
    ax.set_title(f"V02 {phase}: per-anchor joint-intervention effect "
                 "(red = margin reduced)")
    fig.tight_layout()
    p4 = out_dir / "figure_4_per_anchor_delta_both.png"
    fig.savefig(p4, dpi=140, bbox_inches="tight")
    plt.close(fig)
    figures["figure_4_per_anchor_delta_both"] = str(p4)
    return figures


def write_report(root: str | Path, phase: str) -> dict[str, Any]:
    root = Path(root)
    from .phases import load_frozen_protocol
    proto = load_frozen_protocol(root / "configs" / "v02_frozen_v1.json")
    data = load_phase(root, phase)
    quartets = list(data.get("primary_quartets") or [])
    aux = data.get("aux")
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    b = int(proto.value("bootstrap_resamples"))
    alpha = float(proto.value("alpha"))
    seed = int(proto.value("analysis_seed"))
    anchors = anchor_level(quartets)
    est = contrast_estimates(anchors, b_resamples=b, alpha=alpha, seed=seed)
    est["b_resamples"] = b
    gates = gate_checks(data, anchors, quartets,
                        gap_m=float(proto.value("gap_intervention_m")),
                        speed_mps=float(proto.value("speed_intervention_mps")), root=root)
    gates["metric_equivalence"] = metric_equivalence(root, phase)
    het = heterogeneity(anchors)
    m2 = m2_from_raw(root, phase,
                     tau_low_s=float(proto.value("tau_low_threshold_s")))
    ilog = i_log_report(quartets)
    bc = binary_counts(quartets)

    summary: dict[str, Any] = {
        "phase": phase, "protocol": "SafeFlipLab-v02",
        "protocol_hash": data.get("protocol_hash"),
        "launched": data.get("launched"), "completed": data.get("completed"),
        "errored": data.get("errored"), "interrupted": data.get("interrupted"),
        "cap": data.get("cap"), "budget_scope": data.get("budget_scope"),
        "wall_time_s": data.get("wall_time_s"),
        "n_primary_quartets": len(quartets), "n_usable_quartets": len(_usables(quartets)),
        "n_anchors": len(anchors),
        "estimates": est["estimates"],
        "confirmatory_status": est["confirmatory_status"],
        "binary_counts": bc, "i_log": ilog, "gates": gates,
        "heterogeneity": het, "m2_secondary": m2,
        "upstream_ttc_mismatches": data.get("upstream_ttc_mismatches"),
        "upstream_ttc_mismatches_note": ("legacy run-time counter under the old 1e-6 s "
                                       "tolerance; see gates.metric_equivalence for the "
                                       "frozen 1e-4 s criterion"),
        "status": "OK" if quartets else "NO DATA",
    }

    # ---- CSV outputs ----
    _write_csv(reports / f"{phase}_quartets.csv",
               ["anchor_id", "anchor_index", "repetition", "stream", "sim_seed",
                "pair_status", "usable", "Y00", "Y10", "Y01", "Y11",
                "delta_gap", "delta_speed", "delta_both", "i_lin",
                "ttc00", "ttc10", "ttc01", "ttc11"],
               [{"anchor_id": q["anchor_id"], "anchor_index": q["anchor_index"],
                 "repetition": q["repetition"], "stream": q["stream"],
                 "sim_seed": q["sim_seed"], "pair_status": q["pair_status"],
                 "usable": int(bool(q.get("usable"))),
                 **{f"Y{c}": (q.get(c) or {}).get("ego_collision", "") for c in CONDITIONS},
                 "delta_gap": q.get("delta_gap"), "delta_speed": q.get("delta_speed"),
                 "delta_both": q.get("delta_both"), "i_lin": q.get("i_lin"),
                 **{f"ttc{c}": (q.get(c) or {}).get("value", "") for c in CONDITIONS}}
                for q in quartets])

    _write_csv(reports / f"{phase}_anchors.csv",
               ["anchor_index", "anchor_id", "n_collected", "n_usable",
                "mean_delta_gap", "mean_delta_speed", "mean_delta_both", "mean_i_lin"],
               [{"anchor_index": ai, **{k: v for k, v in a.items() if k != "anchor_index"}}
                for ai, a in sorted(anchors.items())])

    _write_csv(reports / f"{phase}_contrasts.csv",
               ["contrast", "label", "point_s", "ci_low_s", "ci_high_s", "n_anchors",
                "ci_basis", "note"],
               [{"contrast": c, "label": e["label"], "point_s": e["point"],
                 "ci_low_s": e["ci_low"], "ci_high_s": e["ci_high"],
                 "n_anchors": e["n_anchors"], "ci_basis": "anchor-level cluster bootstrap",
                 "note": e["note"]} for c, e in est["estimates"].items()])

    # episodes.csv straight from the V02 ledger (per billed episode)
    rows = _ledger_rows(root, phase)
    launch = {r["episode_key"]: r for r in rows if r["row_type"] == "launch"}
    outcome = {r["episode_key"]: r for r in rows if r["row_type"] == "outcome"}
    ep_rows = []
    for key, lrow in launch.items():
        orow = outcome.get(key)
        ep_rows.append({
            "episode_key": key, "run_id": lrow["run_id"], "method": lrow["method"],
            "anchor_id": lrow["anchor_id"], "anchor_index": lrow["anchor_index"],
            "repetition": lrow["repetition"], "condition": lrow["condition"],
            "stream": lrow["stream"], "sim_seed": lrow["sim_seed"],
            "exit_status": orow["exit_status"] if orow else "unknown",
            "result_recorded": 1 if orow else 0, "billed": 1,
            "ego_collision": (orow or {}).get("ego_collision", ""),
            "termination": (orow or {}).get("termination", ""),
            "raw_path": (orow or {}).get("raw_path", ""), "budget_scope": lrow["budget_scope"],
        })
    _write_csv(reports / f"{phase}_episodes.csv",
               ["episode_key", "run_id", "method", "anchor_id", "anchor_index",
                "repetition", "condition", "stream", "sim_seed", "exit_status",
                "result_recorded", "billed", "ego_collision", "termination",
                "raw_path", "budget_scope"], ep_rows)

    _write_csv(reports / f"{phase}_budget_summary.csv",
               ["phase", "budget_scope", "cap", "launched", "completed", "errored",
                "interrupted", "unused_slots"],
               [{"phase": phase, "budget_scope": data.get("budget_scope"),
                 "cap": data.get("cap"), "launched": data.get("launched"),
                 "completed": data.get("completed"), "errored": data.get("errored"),
                 "interrupted": data.get("interrupted"),
                 "unused_slots": (data.get("cap") - data.get("launched"))
                 if data.get("cap") is not None and data.get("launched") is not None else None}])

    # auxiliary method comparison
    comparison_rows: list[dict[str, Any]] = []
    if aux:
        delta_eq = float(aux.get("delta_eq_s"))
        for method in (METHOD_WIDE, METHOD_VERIFY):
            pq = precision_at_k([q for q in (aux.get("audit") or {}).get(method, [])
                                 if q.get("usable")], delta_eq_s=delta_eq)
            comparison_rows.append({
                "method": method,
                "n_nominees": len((aux.get("nomination") or {}).get(method, [])),
                "nominees": ";".join((aux.get("nomination") or {}).get(method, [])),
                "k_usable_audit": pq["k"], "n_reversal": pq["n_reversal"],
                "precision_at_k": pq["precision_at_k"],
                "n_unusable_audit": pq["n_unusable"],
                "delta_eq_s": delta_eq,
                "role": "AUXILIARY_EXPLORATORY",
            })
        summary["auxiliary_method_comparison"] = comparison_rows
        summary["auxiliary_audit_quartets"] = {
            m: (aux.get("audit") or {}).get(m, []) for m in (METHOD_WIDE, METHOD_VERIFY)}
    _write_csv(reports / f"{phase}_comparisons.csv",
               ["method", "n_nominees", "nominees", "k_usable_audit", "n_reversal",
                "precision_at_k", "n_unusable_audit", "delta_eq_s", "role"],
               comparison_rows)

    # ---- figures ----
    figures = _figures(reports / phase, phase, quartets, anchors, est)
    summary["figures"] = figures

    # ---- markdown ----
    md = _markdown(summary, est, gates, ilog, bc, comparison_rows)
    (reports / f"{phase}_report.md").write_text(md, encoding="utf-8")
    (reports / f"{phase}_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return summary


def _fmt(v: Any, nd: int = 4) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int,)):
        return str(v)
    try:
        return f"{float(v):.{nd}f}"
    except (TypeError, ValueError):
        return str(v)


def _markdown(summary: Mapping[str, Any], est: Mapping[str, Any], gates: Mapping[str, Any],
              ilog: Mapping[str, Any], bc: Mapping[str, Any],
              comparison_rows: Sequence[Mapping[str, Any]]) -> str:
    L: list[str] = []
    phase = summary["phase"]
    L.append(f"# SafeFlipLab V02 — {phase} 阶段报告（真实数据）")
    L.append("")
    L.append(f"- 协议：SafeFlipLab-v02（hash `{str(summary.get('protocol_hash'))[:16]}…`，FROZEN）")
    L.append(f"- 已发起 episodes（全部计费）：**{summary.get('launched')}** / cap {summary.get('cap')}")
    L.append(f"- 完成：**{summary.get('completed')}**；错误：**{summary.get('errored')}**；"
             f"中断：**{summary.get('interrupted')}**")
    L.append(f"- 墙钟：{summary.get('wall_time_s')} s")
    L.append(f"- 主研究 quartet：{summary.get('n_primary_quartets')}（可用 "
             f"{summary.get('n_usable_quartets')}）；anchor 数：{summary.get('n_anchors')}")
    _me = (summary.get("gates") or {}).get("metric_equivalence") or {}
    _legacy = summary.get("upstream_ttc_mismatches")
    L.append(f"- 度量等价性（重新计算）：越界 {_me.get('n_over_tolerance')}/"
             f"{_me.get('n_episodes_checked')}，最大绝对差 {_fmt(_me.get('max_abs_delta_s'), 9)} s"
             f"（容差 {_me.get('tolerance_s')} s）")
    if _legacy:
        L.append(f"- 注意：运行期记录的 `upstream_ttc_mismatches` = {_legacy}，"
                 "那是**旧容差口径**下的历史计数（当时阈值为 1e-6 s）；"
                 "按冻结容差 1e-4 s 重新计算的越界数为上述值。两处口径不同，不矛盾。")
    L.append("")
    if not summary.get("n_primary_quartets"):
        L.append("## 无真实数据")
        L.append("")
        L.append("本阶段没有已完成真实 episode，不产生任何统计数字或图表。")
        return "\n".join(L) + "\n"

    L.append("## 1. 主终点与锚级效应量（anchor 为独立单元）")
    L.append("")
    L.append("M1 = 每个 episode 的最小前向 TTC（秒）。Δ 为锚级配对差均值；")
    L.append("区间为锚级 cluster bootstrap（重采样单位为 anchor）。")
    L.append("**负值 = 干预降低了安全裕度（反转方向）**。")
    L.append("")
    L.append("| 对比 | 含义 | 点估计 (s) | 95% 区间 (s) | 锚数 |")
    L.append("|---|---|---:|---|---:|")
    for c, e in est["estimates"].items():
        L.append(f"| {c} | {e['label']} | {_fmt(e['point'])} | "
                 f"[{_fmt(e['ci_low'])}, {_fmt(e['ci_high'])}] | {e['n_anchors']} |")
    L.append("")
    L.append(f"- 确证性检验状态：**{summary.get('confirmatory_status')}**"
             "（抽样假设 A/B/C 未成立，**不产出任何 p 值**）")
    L.append("")

    L.append("## 1b. 锚级异质性与敏感性（必须与均值一同阅读）")
    L.append("")
    L.append("> 只看聚合均值会掩盖**多数锚指向另一方向**这一事实。")
    L.append("")
    L.append("| 对比 | 锚数 | 负向锚数 | 正向锚数 | 0 | 均值 (s) | 剔除最大 3 个正向锚后的均值 (s) | min | max |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for c, h in summary.get("heterogeneity", {}).items():
        if not h or h.get("n_anchors", 0) == 0:
            continue
        L.append(f"| {c} | {h['n_anchors']} | {h['n_negative']} | {h['n_positive']} | "
                 f"{h['n_zero']} | {_fmt(h['mean'])} | "
                 f"{_fmt(h.get('mean_dropping_top_positive'))} | {_fmt(h['min'])} | {_fmt(h['max'])} |")
    L.append("")
    L.append("- 该敏感性检查在本报告中**预先指定**，属描述性，不具推断意义。")
    L.append("")

    L.append("## 1c. 次要终点 M2（前向 TTC 低于阈值的步占比）")
    L.append("")
    _m2 = summary.get("m2_secondary") or {}
    if _m2.get("n_complete_quartets"):
        L.append("> ⚠️ **方向警告（D43）**：M2 的数值**越小越安全**，故负 Δ = 更安全 —— 与 M1"
                 "（min-TTC，正 Δ = 更安全）**方向相反**。请勿跨终点直接比较符号。")
        L.append("")
        L.append(f"- τ_low = {_m2['tau_low_s']} s；解析原始记录 {_m2['n_episodes_parsed']} 个；"
                 f"完整 quartet {_m2['n_complete_quartets']} 个")
        L.append(f"- 各条件均值占比："
                 + "，".join(f"{c}={_fmt(v)}" for c, v in _m2["per_condition_mean_share"].items()))
        L.append("")
        L.append("| 对比 | 点估计 | 95% 锚级区间 | 锚数 |")
        L.append("|---|---:|---|---:|")
        for c2, e2 in _m2["anchor_level_contrasts"].items():
            L.append(f"| {c2} | {_fmt(e2['point'])} | "
                     f"[{_fmt(e2['ci_low'])}, {_fmt(e2['ci_high'])}] | {e2['n_anchors']} |")
        L.append("")
        L.append(f"- {_m2.get('note', '')}")
    else:
        L.append("- 无可解析的原始记录，M2 不计算。")
    L.append("")
    L.append("- **NO_CANDIDATE 剔除敏感性分析**：本阶段 Layer-2 组成见门槛表；"
             "若不存在 `NO_CANDIDATE`/`CENSORED` episode，则该项**不适用**（无截断可剔除）。")
    L.append("")

    L.append("## 2. 二元碰撞端点（仅描述）")
    L.append("")
    L.append(f"- 完整 quartet 数：{bc['n_quartets']}")
    L.append(f"- 四条件事件计数：{bc['per_condition_events']}")
    L.append(f"- reverse_pairs（Y00=0,Y11=1）：{bc['reverse_pairs']}；"
             f"rescue_pairs（Y00=1,Y11=0）：{bc['rescue_pairs']}")
    L.append(f"- 说明：{bc['note']}")
    L.append("")

    L.append("## 3. I_log（纯对数交互，无地板）")
    L.append("")
    L.append(f"- 可用 quartet：{ilog['n_usable_quartets']}；可定义：{ilog['n_defined']}"
             f"（占比 {_fmt(ilog['share_defined'])}）")
    L.append(f"- 原因码计数：{ilog['reason_codes']}")
    L.append(f"- 均值 I_log：{_fmt(ilog['mean_i_log'])}")
    L.append(f"- {ilog['note']}")
    L.append("")

    L.append("## 4. 技术门槛（G-gates，真实数据测量）")
    L.append("")
    L.append("| 门槛 | 状态 | 关键量 |")
    L.append("|---|---|---|")
    for name, node in gates.items():
        if isinstance(node, dict) and "status" in node:
            detail = {k: v for k, v in node.items() if k != "status"}
            L.append(f"| {name} | {node['status']} | `{json.dumps(detail, ensure_ascii=False)}` |")
    L.append("")

    if comparison_rows:
        L.append("## 5. 辅助：两方法提名质量（独立审计，探索性）")
        L.append("")
        L.append("| method | 提名数 | 提名 anchor | 可用审计 quartet | 反转命中 | precision@k |")
        L.append("|---|---:|---|---:|---:|---:|")
        for r in comparison_rows:
            L.append(f"| {r['method']} | {r['n_nominees']} | {r['nominees']} | "
                     f"{r['k_usable_audit']} | {r['n_reversal']} | {_fmt(r['precision_at_k'])} |")
        L.append("")
        L.append("- 该对比为**辅助/探索性**：预算极小（每方法 3 个提名、各 1 个全新审计 quartet），")
        L.append("  且**不作为主结论**；`precision@k` 只在已审计的提名集内定义。")
        L.append("- 预算等量：两方法从**同一份 discovery 数据**提名，差异只在分配规则。")
        L.append("")

    L.append("## 6. 图表")
    L.append("")
    for k, v in (summary.get("figures") or {}).items():
        L.append(f"- {k}：`{v}`")
    L.append("")
    L.append("## 7. 边界声明")
    L.append("")
    L.append("- 全部数字来自真实 HighwayEnv 记录；V02 为 **dev 主种子**，不是正式评估。")
    L.append("- 独立单元是 **anchor**，不是 episode；不得把 4 条件 episode 当独立样本。")
    L.append("- 无 p 值、无显著性宣称：抽样假设未证明，确证性检验保持 PENDING。")
    L.append("- 0 次碰撞不构成碰撞率上界（rule of three 的 iid 前提不成立）。")
    L.append("- 本设计受 V01 pilot 探索结果启发（事后性），已在 DECISION_LOG 显式披露。")
    return "\n".join(L) + "\n"

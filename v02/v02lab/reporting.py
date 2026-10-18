"""Reporting / statistics interfaces over synthetic data (offline).

Ties the pure state model (``ttc_state``) and anchor-level statistics
(``stats_anchor``) into a report the tests can exercise with a
``FakeAdapterV02``. Honesty rules mirrored from V01:

* when an interval cannot be estimated (fewer than 2 anchors, or zero variance)
  the report says so and **never** fabricates a confidence interval;
* confirmatory tests are reported as **PENDING** while the sampling assumption is
  unproven (proposal section 8.3) — no p-value is emitted.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .stats_anchor import (
    CONTRASTS,
    SamplingAssumption,
    anchor_contrasts,
    confirmatory_status,
    estimate,
    unproven_assumption,
)
from .ttc_state import (
    EpisodeTTCCategory,
    TerminationClass,
    aggregate_episode,
    quartet_pair_status,
    step_ttc_state,
)


def figure_axis_range(values: Sequence[float | None]) -> tuple[float, float]:
    """Anti-degenerate axis range (mirrors V01 ``_sane_value_axis``).

    Sub-1e-12 noise snaps to 0; a degenerate range yields (-0.5, 0.5) instead of
    a meaningless 1e-17-scale axis.
    """
    vals = [0.0 if v is None else float(v) for v in values]
    vals = [0.0 if abs(v) < 1e-12 else v for v in vals]
    if not vals:
        return (-0.5, 0.5)
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-12:
        return (-0.5, 0.5)
    pad = (hi - lo) * 0.05
    return (lo - pad, hi + pad)


def record_from_trace(trace: Mapping[str, Any], *, anchor_id: str, repetition: int,
                      condition: str, tau_cap: float, no_candidate_policy: str,
                      termination: TerminationClass | None = None) -> dict[str, Any]:
    """Turn one synthetic adapter trace into a report record via the state model."""
    term = termination or TerminationClass.HORIZON_REACHED
    steps = [step_ttc_state(has_candidate=bool(hc), gap=float(g), closing=float(cl))
             for (hc, g, cl) in trace["steps"]]
    ep = aggregate_episode(steps, termination=term, tau_cap=tau_cap,
                           no_candidate_policy=no_candidate_policy)
    return {
        "anchor_id": anchor_id,
        "repetition": repetition,
        "condition": condition,
        "m1": ep.value,
        "category": ep.category.value,
        "censored": ep.censored,
        "termination": ep.termination.value,
        "ego_collision": trace.get("ego_collision"),
    }


def _is_missing(rec: Mapping[str, Any]) -> bool:
    return rec.get("category") == EpisodeTTCCategory.MISSING.value or rec.get("m1") is None


def summarise_records(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_condition: dict[str, list[Mapping[str, Any]]] = {}
    cat_counts: dict[str, int] = {}
    for r in records:
        by_condition.setdefault(r["condition"], []).append(r)
        cat_counts[r.get("category", "UNKNOWN")] = cat_counts.get(r.get("category", "UNKNOWN"), 0) + 1
    n = len(records)
    censored = sum(1 for r in records if r.get("censored"))
    per_condition = {}
    for c, rs in by_condition.items():
        finite = [float(r["m1"]) for r in rs if not _is_missing(r)]
        per_condition[c] = {
            "n": len(rs),
            "n_usable": len(finite),
            "mean_m1": (sum(finite) / len(finite)) if finite else None,
            "collisions": sum(1 for r in rs if r.get("ego_collision") == 1),
        }
    return {
        "n_records": n,
        "category_counts": cat_counts,
        "censored_fraction": (censored / n) if n else None,
        "per_condition": per_condition,
    }


def build_report(records: Sequence[Mapping[str, Any]], *, b_resamples: int | None = None,
                 alpha: float | None = None, seed: int | None = None,
                 assumption: SamplingAssumption | None = None) -> dict[str, Any]:
    """Full synthetic report: summary + anchor-level estimates + PENDING confirmatory."""
    assumption = assumption or unproven_assumption()
    summary = summarise_records(records)

    # group by anchor -> per-repetition {condition: m1}
    anchors: dict[str, dict[int, dict[str, float | None]]] = {}
    for r in records:
        anchors.setdefault(r["anchor_id"], {}).setdefault(int(r["repetition"]), {})[r["condition"]] = r.get("m1")

    anchor_contrast_values: dict[str, list[float | None]] = {c: [] for c in CONTRASTS}
    for _aid, reps in anchors.items():
        contrasts = anchor_contrasts(list(reps.values()))
        for c in CONTRASTS:
            anchor_contrast_values[c].append(contrasts[c])

    estimates: dict[str, Any] = {}
    for c in CONTRASTS:
        if b_resamples is not None and alpha is not None and seed is not None:
            est = estimate(c, anchor_contrast_values[c], b_resamples=b_resamples, alpha=alpha,
                           seed=seed, assumption=assumption)
            estimates[c] = {"point": est.point, "ci_low": est.ci_low, "ci_high": est.ci_high,
                            "n_anchors": est.n_anchors, "note": est.note}
        else:
            vals = [v for v in anchor_contrast_values[c] if v is not None]
            estimates[c] = {"point": (sum(vals) / len(vals)) if vals else None,
                            "ci_low": None, "ci_high": None, "n_anchors": len(vals),
                            "note": "no CI: b_resamples/alpha/seed not supplied (refusing to default)"}

    return {
        "summary": summary,
        "estimates": estimates,
        "figure_axis": {c: figure_axis_range(anchor_contrast_values[c]) for c in CONTRASTS},
        "confirmatory_status": confirmatory_status(assumption),
        "assumption": {"unit": assumption.unit, "basis": assumption.basis,
                       "status": assumption.status, "justification_ref": assumption.justification_ref},
        "n_anchors": len(anchors),
    }

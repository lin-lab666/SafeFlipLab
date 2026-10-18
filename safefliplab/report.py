"""Reports and figures for completed phases.

Everything in this module is computed from the real EpisodeLedger and the raw
episode records. If a phase has no completed episodes the report says so and no
figure is produced: no number is ever invented.

Quartet formation (fixed here)
------------------------------
A *complete quartet* is the four-condition tuple Y00/Y10/Y01/Y11 for one
``(master_seed, method, anchor_id, repetition, stream)`` **and one run_id**.
All four conditions of a quartet must come from the same run (same paired
``sim_seed``); Y values from different master seeds or different run batches are
never mixed. When two runs complete the same key (e.g. the smoke determinism
replay), the earliest run is the *primary* quartet and later runs are recorded
separately as *replays* — replays are NOT counted as additional independent
scientific evidence.

Discovery and audit streams are kept strictly separate in every aggregate.
Failed / interrupted / incomplete quartets are recorded truthfully and never
silently dropped or imputed.
"""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .ledger import VALID_PHASES
from .margins import (EXPLORATORY_MARGIN_NOTE, MarginData, load_margin_data,
                      margin_quartet_rows, margin_summary)
from .methods import METHOD_VERIFY, METHOD_WIDE, METHODS
from .seeds import (CONDITIONS, FORMAL_EPISODES_PER_METHOD_SEED,
                    FORMAL_TOTAL_EPISODES)
from .stats import aggregate, quartet_metrics

REPORTS_DIRNAME = "reports"
RUNS_DIRNAME = "runs"

EXPLORATORY_NOTE = (
    "跨主种子的池化统计仅为探索性参考：正式设计只有少量主种子，样本很小，"
    "不提供正式的置信区间或显著性结论；单个 reverse/rescue 配对不构成稳定反转。"
)

#: Frozen protocol episode caps. ``configs/dev_v01.json`` mirrors the smoke/pilot
#: values; the formal cap is the frozen 2 x 8 x 800 total.
PHASE_CAPS: dict[str, int] = {
    "smoke": 24,
    "pilot": 240,
    "formal": FORMAL_TOTAL_EPISODES,
}

#: Formal design requires 5 audited anchors per (method, master_seed).
FORMAL_AUDIT_ANCHOR_COUNT = 5


@dataclass
class PhaseData:
    phase: str
    quartets: list[dict[str, Any]]     # primary (non-replay) complete quartets
    replays: list[dict[str, Any]]      # complete quartets from a secondary run of a key
    incomplete: list[dict[str, Any]]   # keys with no fully-completed run
    launched: int
    completed: int
    errored: int
    interrupted: int

    @property
    def has_data(self) -> bool:
        return bool(self.quartets)

    @property
    def interrupted_or_unknown(self) -> int:
        return max(self.launched - self.completed - self.errored, 0)


def _group_key(row: dict[str, str]) -> tuple[int, str, str, int, str]:
    """Isolation key for a quartet: seed + method + anchor + repetition + stream."""
    return (int(row["master_seed"]), row["method"], row["anchor_id"],
            int(row["repetition"]), row["stream"])


def load_phase_data(project_root: str | Path, phase: str) -> PhaseData:
    """Collect complete quartets of a phase from the ledger + raw records.

    Grouping now includes ``master_seed`` and ``run_id`` so different seeds and
    different run batches can never have their Y00/Y10/Y01/Y11 combined.
    """
    if phase not in VALID_PHASES:
        raise ValueError(f"unknown phase {phase!r}")
    root = Path(project_root)
    ledger_path = root / RUNS_DIRNAME / "episode_ledger.csv"
    quartets: list[dict[str, Any]] = []
    replays: list[dict[str, Any]] = []
    incomplete: list[dict[str, Any]] = []
    launched = completed = errored = interrupted = 0
    if ledger_path.exists():
        with open(ledger_path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        phase_rows = [r for r in rows if r["phase"] == phase]
        launched = len({r["episode_key"] for r in phase_rows if r["row_type"] == "launch"})
        completed = len({r["episode_key"] for r in phase_rows
                         if r["row_type"] == "outcome" and r["exit_status"] == "completed"})
        errored = len({r["episode_key"] for r in phase_rows
                       if r["row_type"] == "outcome" and r["exit_status"] == "error"})
        interrupted = len({r["episode_key"] for r in phase_rows
                           if r["row_type"] == "outcome" and r["exit_status"] == "interrupted"})

        # Two views, both keyed by the full isolation key:
        #   * y_by_run   : completed outcomes with a valid 0/1 Y (for quartet Y);
        #   * status_by_run : every outcome's status (to reveal incomplete keys).
        y_by_run: dict[tuple, dict[str, dict[str, str]]] = {}
        status_by_run: dict[tuple, dict[str, dict[str, str]]] = {}
        for r in phase_rows:
            if r["row_type"] != "outcome":
                continue
            gkey = _group_key(r)
            status_by_run.setdefault(gkey, {}).setdefault(r["run_id"], {})[r["condition"]] = (
                r["exit_status"])
            if r["exit_status"] == "completed" and r["ego_collision"] in ("0", "1"):
                y_by_run.setdefault(gkey, {}).setdefault(r["run_id"], {})[r["condition"]] = (
                    r["ego_collision"])

        # A launch with no outcome row at all is a *billed* attempt whose result
        # never landed on disk (crash / power loss / kill). It must never vanish
        # from the report: the protocol treats such attempts as conservatively
        # UNKNOWN and still spent, so they are surfaced here as incomplete and
        # excluded from every scored statistic.
        for r in phase_rows:
            if r["row_type"] != "launch":
                continue
            per_run = status_by_run.setdefault(_group_key(r), {}).setdefault(r["run_id"], {})
            per_run.setdefault(r["condition"], "unknown")

        def _mk(gkey, run_id, is_replay: bool) -> dict[str, Any]:
            ms, method, anchor_id, rep, stream = gkey
            y = {c: int(y_by_run[gkey][run_id][c]) for c in CONDITIONS}
            return {
                "master_seed": ms,
                "method": method,
                "anchor_id": anchor_id,
                "repetition": rep,
                "stream": stream,
                "run_id": run_id,
                "is_replay": is_replay,
                "y": y,
                "metrics": asdict(quartet_metrics(y)),
            }

        for gkey, by_status in status_by_run.items():
            per_run_y = y_by_run.get(gkey, {})
            complete_runs = [rid for rid, conds in per_run_y.items()
                             if set(conds) == set(CONDITIONS)]
            if complete_runs:
                # Earliest complete run (file order) is the primary quartet.
                quartets.append(_mk(gkey, complete_runs[0], False))
                for rid in complete_runs[1:]:
                    replays.append(_mk(gkey, rid, True))
            else:
                ms, method, anchor_id, rep, stream = gkey
                incomplete.append({
                    "master_seed": ms, "method": method, "anchor_id": anchor_id,
                    "repetition": rep, "stream": stream,
                    "runs": {
                        rid: {c: by_status[rid].get(c, "missing") for c in CONDITIONS}
                        for rid in by_status
                    },
                })

    quartets.sort(key=lambda q: (q["master_seed"], q["method"], q["stream"],
                                 q["anchor_id"], q["repetition"]))
    replays.sort(key=lambda q: (q["master_seed"], q["method"], q["stream"],
                                q["anchor_id"], q["repetition"], q["run_id"]))
    incomplete.sort(key=lambda q: (q["master_seed"], q["method"], q["stream"],
                                   q["anchor_id"], q["repetition"]))
    return PhaseData(
        phase=phase,
        quartets=quartets,
        replays=replays,
        incomplete=incomplete,
        launched=launched,
        completed=completed,
        errored=errored,
        interrupted=interrupted,
    )


def _matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _figures_dir(project_root: str | Path, phase: str) -> Path:
    path = Path(project_root) / REPORTS_DIRNAME / phase
    path.mkdir(parents=True, exist_ok=True)
    return path


#: Magnitudes below this are float noise, not signal (e.g. 1e-17 residuals of
#: an all-zero series). They must never set an axis scale.
_TINY = 1e-12


def _wrap_title(text: str, width: int = 70) -> str:
    """Wrap a long English title so it cannot run off the figure canvas.

    Matplotlib's ``tight_layout`` does not account for a title wider than the
    axes, so a long single-line title gets clipped at the right edge. Wrapping
    the text onto several lines keeps the whole title inside the canvas.
    """
    import textwrap

    return "\n".join(textwrap.wrap(text, width=width)) or text


def _sane_value_axis(ax, values: Iterable[float], *, axis: str = "y") -> bool:
    """Guard against degenerate auto-scaled axes on zero-variance data.

    All-zero (or bit-identical) values make matplotlib's autoscale+margins
    produce ranges like +/-1e-17 (pure floating-point noise), which renders as
    a meaningless ``1e-17`` axis offset over ticks that are multiples of 1e-17.
    Snap tiny magnitudes to zero; when the spread is degenerate, set an
    explicit readable range; always disable offset notation so tiny residuals
    can never masquerade as scale. Returns True when the data was degenerate.
    """
    import math

    finite = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not finite:
        return False
    snapped = [0.0 if abs(v) < _TINY else v for v in finite]
    lo, hi = min(snapped), max(snapped)
    degenerate = (hi - lo) < _TINY
    if degenerate:
        pad = 0.5 if lo == 0.0 else max(abs(lo), 1.0) * 0.5
        if axis == "y":
            ax.set_ylim(lo - pad, hi + pad)
        else:
            ax.set_xlim(lo - pad, hi + pad)
    if axis == "y":
        ax.ticklabel_format(axis="y", useOffset=False)
    else:
        ax.ticklabel_format(axis="x", useOffset=False)
    return degenerate


def figure_paired_outcomes(project_root: str | Path, data: PhaseData) -> Path | None:
    """Figure 1: four-condition paired outcomes per anchor (primary discovery)."""
    discovery = [q for q in data.quartets if q["stream"] == "discovery"]
    if not discovery:
        return None
    plt = _matplotlib()
    anchors = sorted({(q["master_seed"], q["anchor_id"]) for q in discovery})
    if not anchors:
        return None
    fig, ax = plt.subplots(figsize=(max(8, 0.5 * len(anchors)), 4.2))
    cond_order = list(CONDITIONS)
    for q in discovery:
        x = anchors.index((q["master_seed"], q["anchor_id"]))
        for ci, cond in enumerate(cond_order):
            if q["y"][cond] == 1:
                ax.plot(x, ci, marker="s", color="#c0392b", markersize=9)
            else:
                ax.plot(x, ci, marker="o", color="#7f8c8d", markersize=5, alpha=0.55)
    ax.set_xticks(range(len(anchors)))
    ax.set_xticklabels([f"{a}\ns{s}" for s, a in anchors], rotation=90, fontsize=6)
    ax.set_yticks(range(4))
    ax.set_yticklabels(["Y00 (anchor)", "Y10 (+gap)", "Y01 (-speed)", "Y11 (both)"], fontsize=8)
    ax.set_title(_wrap_title(
        f"Paired four-condition outcomes (discovery quartets, phase={data.phase})"),
        fontsize=9)
    ax.set_xlabel("anchor (per master seed)")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    out = _figures_dir(project_root, data.phase) / "figure_1_paired_condition_outcomes.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def figure_forest(project_root: str | Path, data: PhaseData) -> Path | None:
    """Figure 2: per-(seed, method, stream, anchor) risk-difference **point
    estimates** (NOT a confidence-interval forest plot).

    No interval is drawn: with zero collisions every paired delta is exactly
    0.0, so no interval is estimable from this data. Drawing whiskers here
    would be fabricated precision.
    """
    if not data.has_data:
        return None
    plt = _matplotlib()
    per_anchor: dict[tuple[int, str, str, str], list[float]] = {}
    for q in data.quartets:
        per_anchor.setdefault(
            (q["master_seed"], q["method"], q["stream"], q["anchor_id"]), []).append(
                q["metrics"]["delta_both"])
    keys = sorted(per_anchor)
    if not keys:
        return None
    means = [sum(v) / len(v) for v in (per_anchor[k] for k in keys)]
    fig, ax = plt.subplots(figsize=(8, max(4, 0.32 * len(keys))))
    ys = []
    for i, key in enumerate(keys):
        vals = per_anchor[key]
        mean = sum(vals) / len(vals)
        ax.plot([0, mean], [i, i], color="#34495e", linewidth=1.2)
        ax.plot([mean], [i], marker="D", color="#c0392b", markersize=6)
        ys.append(i)
    ax.axvline(0, color="#2c3e50", linewidth=1)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"s{ms} {m}/{s}/{a}" for ms, m, s, a in keys], fontsize=6.5)
    ax.set_xlabel("delta_both = mean(Y11 - Y00)  [positive = higher collision risk]")
    title = f"Per-anchor paired risk difference, point estimates (phase={data.phase})"
    if _sane_value_axis(ax, means, axis="x"):
        title += "; zero variance - no CI estimable"
    ax.set_title(_wrap_title(title), fontsize=9)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    out = _figures_dir(project_root, data.phase) / "figure_2_forest_delta_both.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def figure_discovery_to_audit(project_root: str | Path, data: PhaseData) -> Path | None:
    """Figure 3: discovery vs held-out audit for nominated anchors, per method/seed.

    Point estimates only (no CI): with zero collisions every delta is exactly
    0.0 and no interval is estimable. The y-axis is explicitly guarded against
    matplotlib's degenerate +/-1e-17 auto-range on zero-variance data.
    """
    if not data.has_data:
        return None
    plt = _matplotlib()
    fig, ax = plt.subplots(figsize=(8, 4.6))
    tick_positions, tick_labels = [], []
    pos = 0
    any_pair = False
    plotted: list[float] = []
    for method in (METHOD_WIDE, METHOD_VERIFY):
        seeds = sorted({q["master_seed"] for q in data.quartets if q["method"] == method})
        for seed in seeds:
            disc = [q for q in data.quartets
                    if q["method"] == method and q["master_seed"] == seed
                    and q["stream"] == "discovery"]
            aud = [q for q in data.quartets
                   if q["method"] == method and q["master_seed"] == seed
                   and q["stream"] == "audit"]
            if not aud:
                continue
            any_pair = True
            by_anchor_disc: dict[str, list[float]] = {}
            for q in disc:
                by_anchor_disc.setdefault(q["anchor_id"], []).append(q["metrics"]["delta_both"])
            by_anchor_aud: dict[str, list[float]] = {}
            for q in aud:
                by_anchor_aud.setdefault(q["anchor_id"], []).append(q["metrics"]["delta_both"])
            anchors = sorted(by_anchor_aud)
            for a in anchors:
                d = by_anchor_disc.get(a, [])
                av = by_anchor_aud.get(a, [])
                d_mean = sum(d) / len(d) if d else float("nan")
                a_mean = sum(av) / len(av) if av else float("nan")
                plotted.extend([d_mean, a_mean])
                ax.plot([pos - 0.18], [d_mean], marker="o", color="#2980b9", markersize=7)
                ax.plot([pos + 0.18], [a_mean], marker="s", color="#c0392b", markersize=7)
                ax.plot([pos - 0.18, pos + 0.18], [d_mean, a_mean], color="#95a5a6",
                        linewidth=1, linestyle="--")
                tick_positions.append(pos)
                tick_labels.append(f"{method}\ns{seed}\n{a}")
                pos += 1
            pos += 0.8
    if not any_pair:
        plt.close(fig)
        return None
    degenerate = _sane_value_axis(ax, plotted, axis="y")
    ax.axhline(0, color="#2c3e50", linewidth=1)
    ax.plot([], [], marker="o", color="#2980b9", label="discovery mean delta_both")
    ax.plot([], [], marker="s", color="#c0392b", label="independent audit mean delta_both")
    ax.legend(fontsize=8)
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, fontsize=6)
    ax.set_ylabel("delta_both")
    title = f"Discovery to independent audit, point estimates (phase={data.phase})"
    if degenerate:
        title += "; all deltas = 0 (zero collisions), no CI estimable"
    ax.set_title(_wrap_title(title), fontsize=9)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    out = _figures_dir(project_root, data.phase) / "figure_3_discovery_to_audit.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def figure_margin_forest(project_root: str | Path, data: PhaseData,
                         margin_data: MarginData) -> Path | None:
    """Figure 4 (exploratory, NON-PROTOCOL): per-(seed, method, stream, anchor)
    paired ``min_forward_ttc_sampled_s`` difference d(11)-d(00).

    Point estimates only (bar chart, not a CI forest plot): within one anchor
    the paired difference is bit-identical across repetitions (the sim seed
    only re-randomises the ramp nuisance vehicle), so no repetition-level
    interval exists. Only produced when real complete quartets exist. Negative
    values mean the combined intervention reduced the continuous forward-TTC
    safety proxy in these episodes.
    """
    if not margin_data.has_data:
        return None
    plt = _matplotlib()
    per_anchor: dict[tuple[int, str, str, str], list[float]] = {}
    for q in margin_data.quartets:
        d = q.delta("min_forward_ttc_sampled_s", "11", "00")
        if d is None:
            continue
        per_anchor.setdefault(
            (q.master_seed, q.method, q.stream, q.anchor_id), []).append(d)
    keys = sorted(per_anchor)
    if not keys:
        return None
    means = [sum(v) / len(v) for v in (per_anchor[k] for k in keys)]
    fig, ax = plt.subplots(figsize=(8, max(4, 0.32 * len(keys))))
    ys = range(len(keys))
    colors = ["#c0392b" if m < 0 else "#27ae60" for m in means]
    ax.barh(list(ys), means, color=colors, alpha=0.75)
    _sane_value_axis(ax, means, axis="x")
    ax.axvline(0, color="#2c3e50", linewidth=1)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([f"s{k[0]} {k[1]} {k[2]} {k[3]}" for k in keys], fontsize=6)
    ax.set_xlabel("mean paired ΔTTC = TTC(11) − TTC(00)  [s]")
    ax.set_title(_wrap_title(
        f"Exploratory forward-TTC margin difference, point estimates "
        f"(phase={data.phase}; NON-PROTOCOL, no CI)"), fontsize=9)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    out = _figures_dir(project_root, data.phase) / "figure_4_margin_forest_ttc.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def _agg_dict(agg) -> dict[str, Any]:
    return {
        "n_quartets": agg.n_quartets,
        "mean_delta_both": agg.mean_delta_both,
        "mean_delta_gap": agg.mean_delta_gap,
        "mean_delta_speed": agg.mean_delta_speed,
        "mean_interaction": agg.mean_interaction,
        "reverse_pairs": agg.reverse_pairs,
        "rescue_pairs": agg.rescue_pairs,
        "collision_rate": agg.collision_rate,
    }


def _mean(xs: Iterable[float]) -> float | None:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def _sample_stdev(xs: Iterable[float]) -> float | None:
    xs = list(xs)
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def _build_per_seed_method(quartets: list[dict[str, Any]]) -> dict[str, Any]:
    """Independent per (master_seed, method) results, discovery/audit separated,
    with per-nominee audit aggregates and the paired contrast per stream."""
    seeds = sorted({q["master_seed"] for q in quartets})
    per: dict[str, Any] = {}
    for ms in seeds:
        for method in METHODS:
            entry: dict[str, Any] = {
                "master_seed": ms, "method": method,
                "discovery": None, "audit": None, "audit_results": [],
                "paired_contrast": {"discovery": None, "audit": None},
            }
            for stream in ("discovery", "audit"):
                qs = [q for q in quartets
                      if q["master_seed"] == ms and q["method"] == method
                      and q["stream"] == stream]
                if qs:
                    agg = _agg_dict(aggregate([q["y"] for q in qs]))
                    entry[stream] = agg
                    entry["paired_contrast"][stream] = {
                        "mean_delta_both": agg["mean_delta_both"],
                        "mean_delta_gap": agg["mean_delta_gap"],
                        "mean_delta_speed": agg["mean_delta_speed"],
                        "mean_interaction": agg["mean_interaction"],
                    }
            aud = [q for q in quartets
                   if q["master_seed"] == ms and q["method"] == method
                   and q["stream"] == "audit"]
            by_anchor: dict[str, list[dict[str, Any]]] = {}
            for q in aud:
                by_anchor.setdefault(q["anchor_id"], []).append(q)
            entry["audit_results"] = [
                {"anchor_id": a, **_agg_dict(aggregate([q["y"] for q in qs_]))}
                for a, qs_ in sorted(by_anchor.items())
            ]
            if entry["discovery"] or entry["audit"]:
                per[f"seed={ms}|method={method}"] = entry
    return per


def _build_cross_seed(quartets: list[dict[str, Any]]) -> dict[str, Any]:
    """Pooled-across-seeds summary (exploratory) with per-seed dispersion."""
    seeds = sorted({q["master_seed"] for q in quartets})
    methods = sorted({q["method"] for q in quartets})
    cross: dict[str, Any] = {"master_seeds": seeds, "methods": methods, "note": EXPLORATORY_NOTE}
    for method in methods:
        for stream in ("discovery", "audit"):
            per_seed_means: dict[str, float] = {}
            pooled: list[dict[str, int]] = []
            for ms in seeds:
                qs = [q for q in quartets
                      if q["master_seed"] == ms and q["method"] == method
                      and q["stream"] == stream]
                if not qs:
                    continue
                values = [q["metrics"]["delta_both"] for q in qs]
                per_seed_means[str(ms)] = sum(values) / len(values)
                pooled.extend(q["y"] for q in qs)
            if not pooled:
                continue
            cross[f"{method}|{stream}"] = {
                "n_seeds_with_data": len(per_seed_means),
                "pooled": _agg_dict(aggregate(pooled)),
                "per_seed_mean_delta_both": per_seed_means,
                "across_seed_mean_delta_both": _mean(per_seed_means.values()),
                "across_seed_stdev_delta_both": _sample_stdev(per_seed_means.values()),
            }
    return cross


def _safe_int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _anchor_index_of(anchor_id: str) -> int:
    """``anchor-0007`` -> 7; anything unexpected -> -1 (never silently zero)."""
    prefix, _, suffix = (anchor_id or "").partition("-")
    if prefix != "anchor" or not suffix.isdigit():
        return -1
    return int(suffix)


def _read_ledger_rows(project_root: str | Path) -> list[dict[str, str]]:
    ledger_path = Path(project_root) / RUNS_DIRNAME / "episode_ledger.csv"
    if not ledger_path.exists():
        return []
    with open(ledger_path, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r.get("row_type")]


def _phase_episode_records(project_root: str | Path, phase: str) -> list[dict[str, Any]]:
    """One record per *billed* episode of the phase, straight from the ledger.

    A launch row is the authoritative enumeration of what was billed, so an
    episode whose launch exists but whose outcome row does not is reported with
    ``exit_status="unknown"`` and ``result_recorded=0`` — conservatively billed,
    never counted as a safe (0) observation.
    """
    rows = [r for r in _read_ledger_rows(project_root) if r.get("phase") == phase]
    launches: dict[str, dict[str, str]] = {}
    outcomes: dict[str, dict[str, str]] = {}
    for r in rows:
        key = r.get("episode_key") or ""
        if not key:
            continue
        if r["row_type"] == "launch":
            launches.setdefault(key, r)
        elif r["row_type"] == "outcome":
            outcomes[key] = r

    records: list[dict[str, Any]] = []
    for key, launch in launches.items():
        outcome = outcomes.get(key)
        src = outcome if outcome is not None else launch

        def _g(name: str) -> str:
            return (src.get(name) or "").strip()

        records.append({
            "episode_key": key,
            "run_id": _g("run_id"),
            "phase": _g("phase"),
            "method": _g("method"),
            "master_seed": _g("master_seed"),
            "anchor_index": _safe_int(launch.get("anchor_index")),
            "anchor_id": _g("anchor_id"),
            "repetition": _safe_int(launch.get("repetition")),
            "condition": _g("condition"),
            "stream": _g("stream"),
            "sim_seed": _g("sim_seed"),
            "exit_status": _g("exit_status") if outcome is not None else "unknown",
            "result_recorded": 1 if outcome is not None else 0,
            "billed": 1,
            "ego_collision": _g("ego_collision"),
            "termination": _g("termination"),
            "error_type": _g("error_type"),
            "started_utc": _g("started_utc"),
            "ended_utc": _g("ended_utc"),
            "wall_time_s": _g("wall_time_s"),
            "raw_path": _g("raw_path"),
        })
    records.sort(key=lambda r: (r["method"], r["stream"], r["anchor_index"],
                                r["repetition"], r["condition"], r["episode_key"]))
    return records


def _anchor_records(data: PhaseData) -> list[dict[str, Any]]:
    """Per (master_seed, method, stream, anchor) collision counts, denominators,
    rates and paired risk differences — complete quartets only."""
    buckets: dict[tuple, dict[str, Any]] = {}

    def _slot(ms: int, method: str, stream: str, anchor_id: str) -> dict[str, Any]:
        key = (ms, method, stream, anchor_id)
        if key not in buckets:
            buckets[key] = {
                "master_seed": ms, "method": method, "stream": stream,
                "anchor_id": anchor_id, "anchor_index": _anchor_index_of(anchor_id),
                "n_complete_quartets": 0, "n_replays": 0, "n_incomplete_quartets": 0,
                "counts": {c: 0 for c in CONDITIONS},
                "reverse_pairs": 0, "rescue_pairs": 0,
                "_series": {k: [] for k in
                            ("delta_both", "delta_gap", "delta_speed", "interaction")},
            }
        return buckets[key]

    for q in data.quartets:
        slot = _slot(q["master_seed"], q["method"], q["stream"], q["anchor_id"])
        slot["n_complete_quartets"] += 1
        for c in CONDITIONS:
            slot["counts"][c] += int(q["y"][c])
        metrics = q["metrics"]
        for name in slot["_series"]:
            slot["_series"][name].append(float(metrics[name]))
        slot["reverse_pairs"] += int(metrics["reverse"])
        slot["rescue_pairs"] += int(metrics["rescue"])
    for q in data.replays:
        _slot(q["master_seed"], q["method"], q["stream"], q["anchor_id"])["n_replays"] += 1
    for inc in data.incomplete:
        _slot(inc["master_seed"], inc["method"], inc["stream"],
              inc["anchor_id"])["n_incomplete_quartets"] += 1

    out: list[dict[str, Any]] = []
    for key in sorted(buckets):
        slot = buckets[key]
        n = slot["n_complete_quartets"]
        row: dict[str, Any] = {
            "master_seed": slot["master_seed"], "method": slot["method"],
            "stream": slot["stream"], "anchor_id": slot["anchor_id"],
            "anchor_index": slot["anchor_index"],
            "n_complete_quartets": n,
            "n_incomplete_quartets": slot["n_incomplete_quartets"],
            "n_replays": slot["n_replays"],
        }
        for c in CONDITIONS:
            row[f"Y{c}_count"] = slot["counts"][c]
        row["denominator"] = n
        for c in CONDITIONS:
            row[f"rate_{c}"] = (slot["counts"][c] / n) if n else None
        for name in ("delta_both", "delta_gap", "delta_speed", "interaction"):
            row[f"mean_{name}"] = _mean(slot["_series"][name])
        row["reverse_pairs"] = slot["reverse_pairs"]
        row["rescue_pairs"] = slot["rescue_pairs"]
        out.append(row)
    return out


def _cap_for_scope(phase: str, scope: str) -> int | None:
    if scope == phase:
        return PHASE_CAPS.get(phase)
    if scope.startswith("formal|"):
        return FORMAL_EPISODES_PER_METHOD_SEED
    return None


def _budget_records(project_root: str | Path, phase: str) -> list[dict[str, Any]]:
    """Per-budget-scope accounting: launched, completed, error, interrupted,
    unknown (launched with no outcome) and *unused* slots. Failures and
    unknowns are always billed."""
    rows = [r for r in _read_ledger_rows(project_root) if r.get("phase") == phase]
    scopes: dict[str, dict[str, set[str]]] = {}
    for r in rows:
        scope = (r.get("budget_scope") or r.get("phase") or phase).strip()
        state = scopes.setdefault(scope, {"launched": set(), "completed": set(),
                                          "error": set(), "interrupted": set(),
                                          "other_outcome": set()})
        key = r.get("episode_key") or ""
        if not key:
            continue
        if r["row_type"] == "launch":
            state["launched"].add(key)
        elif r["row_type"] == "outcome":
            status = (r.get("exit_status") or "").strip()
            bucket = {"completed": "completed", "error": "error",
                      "interrupted": "interrupted"}.get(status, "other_outcome")
            state[bucket].add(key)

    out: list[dict[str, Any]] = []
    for scope in sorted(scopes):
        state = scopes[scope]
        launched = len(state["launched"])
        completed = len(state["completed"])
        errored = len(state["error"])
        interrupted = len(state["interrupted"])
        pending = launched - completed - errored - interrupted
        cap = _cap_for_scope(phase, scope)
        out.append({
            "phase": phase,
            "budget_scope": scope,
            "cap": cap,
            "launched": launched,
            "completed": completed,
            "error": errored,
            "interrupted": interrupted,
            "pending_or_unknown": max(pending, 0),
            "unused_slots": (cap - launched) if cap is not None else None,
            "billing_note": ("failed / interrupted / unknown attempts are billed; "
                             "no free retry"),
        })
    return out


def _comparison_records(data: PhaseData) -> list[dict[str, Any]]:
    """Per-master_seed method contrast.

    Protocol metric (§6): per master seed, the mean ``delta_both`` over that
    method's **audited** anchors, then ``VerifyFirst - WideExplore``. Discovery
    rows are emitted alongside, explicitly labelled exploratory.
    """
    seeds = sorted({q["master_seed"] for q in data.quartets})
    out: list[dict[str, Any]] = []
    for ms in seeds:
        for stream, role in (("audit", "PROTOCOL_AUDIT"),
                             ("discovery", "EXPLORATORY_DISCOVERY")):
            n_anchor: dict[str, int] = {}
            per_method: dict[str, float | None] = {}
            for method in (METHOD_WIDE, METHOD_VERIFY):
                qs = [q for q in data.quartets
                      if q["master_seed"] == ms and q["method"] == method
                      and q["stream"] == stream]
                by_anchor: dict[str, list[float]] = {}
                for q in qs:
                    by_anchor.setdefault(q["anchor_id"], []).append(
                        float(q["metrics"]["delta_both"]))
                n_anchor[method] = len(by_anchor)
                per_method[method] = _mean(
                    [m for m in (_mean(v) for v in by_anchor.values()) if m is not None])
            wide = per_method[METHOD_WIDE]
            verify = per_method[METHOD_VERIFY]
            computable = wide is not None and verify is not None
            meets = (stream == "audit"
                     and n_anchor[METHOD_WIDE] >= FORMAL_AUDIT_ANCHOR_COUNT
                     and n_anchor[METHOD_VERIFY] >= FORMAL_AUDIT_ANCHOR_COUNT)
            if stream == "audit":
                note = ("formal design requires >=5 audited anchors per method"
                        if not meets else "meets the frozen formal audit design")
            else:
                note = "discovery-only; NOT the protocol method-comparison metric"
            out.append({
                "master_seed": ms,
                "stream": stream,
                "metric_role": role,
                "n_audited_anchors_wide": n_anchor[METHOD_WIDE],
                "n_audited_anchors_verify": n_anchor[METHOD_VERIFY],
                "mean_delta_both_wide": wide,
                "mean_delta_both_verify": verify,
                "contrast_verify_minus_wide": (verify - wide) if computable else None,
                "required_audited_anchors": FORMAL_AUDIT_ANCHOR_COUNT,
                "meets_formal_anchor_requirement": int(meets),
                "computable": int(computable),
                "note": note,
            })
    return out


def _write_rows_csv(path: Path, columns: list[str],
                    rows: list[dict[str, Any]]) -> None:
    """Write a CSV with a stable header, even when there are no rows (the empty
    template is the honest output for a phase with no real data)."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


EPISODE_COLUMNS = [
    "episode_key", "run_id", "phase", "method", "master_seed", "anchor_index",
    "anchor_id", "repetition", "condition", "stream", "sim_seed", "exit_status",
    "result_recorded", "billed", "ego_collision", "termination", "error_type",
    "started_utc", "ended_utc", "wall_time_s", "raw_path",
]

ANCHOR_COLUMNS = [
    "master_seed", "method", "stream", "anchor_id", "anchor_index",
    "n_complete_quartets", "n_incomplete_quartets", "n_replays",
    "Y00_count", "Y10_count", "Y01_count", "Y11_count", "denominator",
    "rate_00", "rate_10", "rate_01", "rate_11",
    "mean_delta_both", "mean_delta_gap", "mean_delta_speed", "mean_interaction",
    "reverse_pairs", "rescue_pairs",
]

BUDGET_COLUMNS = [
    "phase", "budget_scope", "cap", "launched", "completed", "error",
    "interrupted", "pending_or_unknown", "unused_slots", "billing_note",
]

COMPARISON_COLUMNS = [
    "master_seed", "stream", "metric_role", "n_audited_anchors_wide",
    "n_audited_anchors_verify", "mean_delta_both_wide", "mean_delta_both_verify",
    "contrast_verify_minus_wide", "required_audited_anchors",
    "meets_formal_anchor_requirement", "computable", "note",
]


def write_structured_outputs(project_root: str | Path, phase: str,
                             data: PhaseData,
                             budgets: list[dict[str, Any]] | None = None
                             ) -> dict[str, str]:
    """Write the §6 structured outputs: episodes (csv + jsonl), anchors,
    budget summary and comparisons. Every value comes from the real ledger and
    real raw records; a phase with no data yields header-only templates."""
    reports_dir = Path(project_root) / REPORTS_DIRNAME
    reports_dir.mkdir(parents=True, exist_ok=True)
    episodes = _phase_episode_records(project_root, phase)
    anchors = _anchor_records(data)
    if budgets is None:
        budgets = _budget_records(project_root, phase)
    comparisons = _comparison_records(data)

    episodes_csv = reports_dir / f"{phase}_episodes.csv"
    _write_rows_csv(episodes_csv, EPISODE_COLUMNS, episodes)

    episodes_jsonl = reports_dir / f"{phase}_episodes.jsonl"
    with open(episodes_jsonl, "w", encoding="utf-8") as fh:
        for record in episodes:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

    anchors_csv = reports_dir / f"{phase}_anchors.csv"
    _write_rows_csv(anchors_csv, ANCHOR_COLUMNS, anchors)

    budget_csv = reports_dir / f"{phase}_budget_summary.csv"
    _write_rows_csv(budget_csv, BUDGET_COLUMNS, budgets)

    comparisons_csv = reports_dir / f"{phase}_comparisons.csv"
    _write_rows_csv(comparisons_csv, COMPARISON_COLUMNS, comparisons)

    return {
        "episodes_csv": str(episodes_csv),
        "episodes_jsonl": str(episodes_jsonl),
        "anchors_csv": str(anchors_csv),
        "budget_summary_csv": str(budget_csv),
        "comparisons_csv": str(comparisons_csv),
    }


def write_report(project_root: str | Path, phase: str) -> dict[str, Any]:
    """Write the phase report (markdown + CSV + figures when data exists)."""
    data = load_phase_data(project_root, phase)
    margin_data = load_margin_data(project_root, phase)
    reports_dir = Path(project_root) / REPORTS_DIRNAME
    reports_dir.mkdir(parents=True, exist_ok=True)
    figures: dict[str, str] = {}
    summary: dict[str, Any] = {
        "phase": phase,
        "episodes_launched": data.launched,
        "episodes_completed": data.completed,
        "episodes_errored": data.errored,
        "episodes_interrupted": data.interrupted,
        "episodes_interrupted_or_unknown": data.interrupted_or_unknown,
        "complete_quartets": len(data.quartets),
        "replay_quartets": len(data.replays),
        "incomplete_quartets": len(data.incomplete),
    }

    # §6 structured outputs (episodes / anchors / budget / comparisons)
    budget_records = _budget_records(project_root, phase)
    summary.update(write_structured_outputs(project_root, phase, data,
                                            budgets=budget_records))

    # raw quartet CSV (primary quartets only; replays/incomplete listed separately)
    csv_path = reports_dir / f"{phase}_quartets.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["master_seed", "method", "stream", "anchor_id", "repetition",
                         "Y00", "Y10", "Y01", "Y11", "delta_both", "delta_gap",
                         "delta_speed", "interaction", "reverse", "rescue", "run_id"])
        for q in data.quartets:
            m = q["metrics"]
            writer.writerow([q["master_seed"], q["method"], q["stream"], q["anchor_id"],
                             q["repetition"], q["y"]["00"], q["y"]["10"], q["y"]["01"],
                             q["y"]["11"], m["delta_both"], m["delta_gap"], m["delta_speed"],
                             m["interaction"], m["reverse"], m["rescue"], q["run_id"]])

    lines: list[str] = []
    lines.append(f"# SafeFlipLab {phase} 阶段报告")
    lines.append("")
    lines.append(f"- 已发起 episodes（含失败/中断，全部计费）：**{data.launched}**")
    lines.append(f"- 成功完成 episodes：**{data.completed}**")
    lines.append(f"- 错误 episodes：**{data.errored}**")
    lines.append(f"- 中断 episodes：**{data.interrupted}**")
    lines.append(f"- 中断/未知 episodes：**{data.interrupted_or_unknown}**")
    lines.append(f"- 完整 quartets（主）：**{len(data.quartets)}**")
    lines.append(f"- 重放 quartets（同 key 的二次运行，非独立证据）：**{len(data.replays)}**")
    lines.append(f"- 不完整 quartets：**{len(data.incomplete)}**")
    lines.append("")
    if not data.has_data:
        lines.append("## 无真实数据")
        lines.append("")
        lines.append("本阶段没有已完成真实 episode，因此不产生任何统计数字或图表。")
        lines.append("缺失的 quartet 不得视为无碰撞或碰撞。")
        summary["status"] = "NO DATA"
        summary["figures"] = {}
    else:
        lines.append("## 方法 / 流汇总（池化跨主种子，仅完整主 quartet）")
        lines.append("")
        lines.append("| method | stream | quartets | mean delta_both | mean delta_gap | "
                     "mean delta_speed | mean interaction | reverse | rescue |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
        method_summary: dict[str, Any] = {}
        for method in (METHOD_WIDE, METHOD_VERIFY):
            for stream in ("discovery", "audit"):
                qs = [q for q in data.quartets
                      if q["method"] == method and q["stream"] == stream]
                if not qs:
                    continue
                agg = aggregate([q["y"] for q in qs])
                lines.append(
                    f"| {method} | {stream} | {agg.n_quartets} | "
                    f"{_fmt(agg.mean_delta_both)} | {_fmt(agg.mean_delta_gap)} | "
                    f"{_fmt(agg.mean_delta_speed)} | {_fmt(agg.mean_interaction)} | "
                    f"{agg.reverse_pairs} | {agg.rescue_pairs} |")
                method_summary[f"{method}/{stream}"] = _agg_dict(agg)
        lines.append("")
        lines.append("碰撞率按条件（完整主 quartet 内，池化）：")
        lines.append("")
        for method in (METHOD_WIDE, METHOD_VERIFY):
            for stream in ("discovery", "audit"):
                qs = [q for q in data.quartets
                      if q["method"] == method and q["stream"] == stream]
                if not qs:
                    continue
                agg = aggregate([q["y"] for q in qs])
                rates = ", ".join(f"{c}={_fmt(agg.collision_rate[c])}" for c in CONDITIONS)
                lines.append(f"- {method} / {stream}: {rates}")

        # -- per (master_seed, method) independent results --------------------
        per_seed_method = _build_per_seed_method(data.quartets)
        lines.append("")
        lines.append("## 每个 master_seed × method 的独立结果（discovery/audit 严格分离）")
        lines.append("")
        lines.append("| master_seed | method | stream | quartets | mean delta_both | "
                     "mean delta_gap | mean delta_speed | mean interaction | reverse | rescue |")
        lines.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|")
        for entry in per_seed_method.values():
            for stream in ("discovery", "audit"):
                a = entry[stream]
                if a is None:
                    continue
                lines.append(
                    f"| {entry['master_seed']} | {entry['method']} | {stream} | {a['n_quartets']} | "
                    f"{_fmt(a['mean_delta_both'])} | {_fmt(a['mean_delta_gap'])} | "
                    f"{_fmt(a['mean_delta_speed'])} | {_fmt(a['mean_interaction'])} | "
                    f"{a['reverse_pairs']} | {a['rescue_pairs']} |")

        lines.append("")
        lines.append("每个 master_seed × method 的独立审计（audit 流，按提名 anchor）：")
        lines.append("")
        for entry in per_seed_method.values():
            if not entry["audit_results"]:
                continue
            lines.append(f"- **seed {entry['master_seed']} / {entry['method']}**：")
            for ar in entry["audit_results"]:
                lines.append(
                    f"  - {ar['anchor_id']}：n={ar['n_quartets']}，"
                    f"mean delta_both={_fmt(ar['mean_delta_both'])}，"
                    f"reverse={ar['reverse_pairs']}，rescue={ar['rescue_pairs']}")

        # -- cross-seed exploratory summary ----------------------------------
        cross_seed = _build_cross_seed(data.quartets)
        lines.append("")
        lines.append("## 跨主种子汇总（探索性）")
        lines.append("")
        lines.append(f"> {EXPLORATORY_NOTE}")
        lines.append("")
        for key, block in cross_seed.items():
            if key in ("master_seeds", "methods", "note"):
                continue
            p = block["pooled"]
            lines.append(
                f"- {key}：种子数={block['n_seeds_with_data']}，"
                f"池化 mean delta_both={_fmt(p['mean_delta_both'])}，"
                f"跨种子均值={_fmt(block['across_seed_mean_delta_both'])}，"
                f"跨种子样本标准差={_fmt(block['across_seed_stdev_delta_both'])}")
            lines.append(f"  - 每种子 mean delta_both：{ {k: round(v, 4) for k, v in block['per_seed_mean_delta_both'].items()} }")

        # -- truthfulness section --------------------------------------------
        lines.append("")
        lines.append("## 失败 / 中断 / 不完整 quartet（如实记录）")
        lines.append("")
        lines.append(f"- 错误 episodes：**{data.errored}**；中断 episodes：**{data.interrupted}**；"
                     f"已发起但无结果：**{data.interrupted_or_unknown}**")
        if data.incomplete:
            lines.append(f"- 不完整 quartet 数：**{len(data.incomplete)}**（其四条件未在同一 run 内全部完成）")
            for inc in data.incomplete[:20]:
                run_parts = []
                for rid, cond_status in inc["runs"].items():
                    detail = ",".join(f"{c}:{cond_status[c]}" for c in CONDITIONS)
                    run_parts.append(f"{rid}[{detail}]")
                runs = "; ".join(run_parts)
                lines.append(
                    f"  - seed {inc['master_seed']} / {inc['method']} / {inc['stream']} / "
                    f"{inc['anchor_id']} rep {inc['repetition']}：{runs}")
            if len(data.incomplete) > 20:
                lines.append(f"  - …另有 {len(data.incomplete) - 20} 条未列出")
        else:
            lines.append("- 不完整 quartet：**0**")
        if data.replays:
            lines.append("")
            lines.append("### 重复运行（不作为独立科学证据）")
            lines.append("")
            lines.append(f"- 同 (master_seed, method, anchor, repetition, stream) 的二次完整运行："
                         f"**{len(data.replays)}**（如 smoke 确定性重放）。已在主统计中排除。")
            for q in data.replays[:20]:
                lines.append(f"  - seed {q['master_seed']} / {q['method']} / {q['stream']} / "
                             f"{q['anchor_id']} rep {q['repetition']} run_id={q['run_id']}")

        lines.append("")
        lines.append("## 图表")
        lines.append("")
        for name, fn in (
            ("四条件配对结果", figure_paired_outcomes),
            ("每 anchor 风险差点估计图（无置信区间：零方差）", figure_forest),
            ("discovery 到独立审计点估计对比", figure_discovery_to_audit),
        ):
            path = fn(project_root, data)
            if path is None:
                lines.append(f"- {name}：数据不足，未生成（不编造数值）")
            else:
                lines.append(f"- {name}：`{path}`")
                figures[name] = str(path)

        # -- exploratory continuous safety-margin analysis (NON-PROTOCOL) -----
        lines.append("")
        lines.append("## 探索性连续安全裕度分析（非协议指标）")
        lines.append("")
        lines.append(f"> {EXPLORATORY_MARGIN_NOTE}")
        lines.append("")
        if not margin_data.has_data:
            lines.append("本阶段没有可读取的完整 quartet 原始记录，不产生任何裕度数字。")
        else:
            msum = margin_summary(margin_data)
            lines.append("| method | stream | quartets | mean TTC(00) | mean TTC(10) | "
                         "mean TTC(01) | mean TTC(11) | mean ΔTTC(both) | "
                         "mean ΔTTC(gap) | mean ΔTTC(speed) |")
            lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
            for key, block in msum.items():
                t = block["mean_min_forward_ttc_sampled_s"]
                lines.append(
                    f"| {key.split('/')[0]} | {key.split('/')[1]} | {block['n_quartets']} | "
                    f"{_fmt(t['00'])} | {_fmt(t['10'])} | {_fmt(t['01'])} | {_fmt(t['11'])} | "
                    f"{_fmt(block['d_min_forward_ttc_sampled_s_both'])} | "
                    f"{_fmt(block['d_min_forward_ttc_sampled_s_gap'])} | "
                    f"{_fmt(block['d_min_forward_ttc_sampled_s_speed'])} |")
            lines.append("")
            lines.append("- ΔTTC(both) = TTC(11) − TTC(00) 的逐 quartet 配对差均值；"
                         "负值表示组合干预降低了最小前向 TTC（更接近碰撞但不等于碰撞）。")
            lines.append("- 该分析只重读已付费产生的原始 episode 记录，未启动任何新仿真。")
            # descriptive across-anchor spread of the per-anchor mean ΔTTC(both)
            per_key_both: dict[str, list[float]] = {}
            for q in margin_data.quartets:
                d = q.delta("min_forward_ttc_sampled_s", "11", "00")
                if d is None:
                    continue
                per_key_both.setdefault(f"{q.method}/{q.stream}", []).append(d)
            if per_key_both:
                spans = []
                for key in sorted(per_key_both):
                    vals = per_key_both[key]
                    spans.append(f"{key}: [{min(vals):.4f}, {max(vals):.4f}]")
                lines.append("- ΔTTC(both) 逐锚点描述范围（min–max，**非置信区间**）："
                             + "；".join(spans) + "。")
            lines.append("- **种子无关性警示**：本场景中 sim_seed 只随机化 ramp 车的 IDM 指数；"
                         "最小前向 TTC 恒由 lead 车决定且发生在种子无关的时间窗内，"
                         "因此同一 (anchor, condition) 的 ΔTTC 在不同 repetition 间逐位相同——"
                         "重复种子不构成对 TTC 指标的独立重采样。")
            if margin_data.replays:
                lines.append(f"- 同 isolation key 的二次完整运行（如 smoke 确定性重放）："
                             f"**{len(margin_data.replays)}** 个，已按主统计规则排除，"
                             "不计入独立证据。")
            if margin_data.missing_raw:
                lines.append(f"- 原始记录缺失/不可读的 completed episodes：**{margin_data.missing_raw}**"
                             "（未纳入，不插补）。")
            if margin_data.incomplete:
                lines.append(f"- 四条件未齐的原始记录组：**{len(margin_data.incomplete)}**"
                             "（未纳入，不插补）。")
            margin_csv = reports_dir / f"{phase}_margins.csv"
            with open(margin_csv, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(margin_quartet_rows(margin_data)[0].keys()))
                writer.writeheader()
                for row in margin_quartet_rows(margin_data):
                    writer.writerow(row)
            summary["margins_csv"] = str(margin_csv)
            summary["exploratory_margins"] = msum
            fig4 = figure_margin_forest(project_root, data, margin_data)
            if fig4 is None:
                lines.append("- 探索性 TTC 裕度点估计图：数据不足，未生成（不编造数值）")
            else:
                lines.append(f"- 探索性 TTC 裕度点估计图（非协议，无置信区间）：`{fig4}`")
                figures["探索性 TTC 裕度点估计图（非协议）"] = str(fig4)

        lines.append("")
        lines.append("## 边界声明")
        lines.append("")
        lines.append("- 以上数字只来自真实 HighwayEnv 仿真记录；dev_seed 结果不是正式证据。")
        lines.append("- quartet 仅由同一 run 内的四条件组成；不同 master_seed 或不同 run 批次不混并。")
        lines.append("- discovery 与 audit 严格分离，审计从不回灌提名。")
        lines.append("- 重复运行（如 smoke 确定性重放）不计入独立科学证据。")
        lines.append("- 单个 reverse pair 不构成稳定反转；请同时查看 rescue 对照。")
        lines.append("- 缺失/不完整 quartet 已排除，不计入分子或分母。")
        lines.append("- 探索性连续安全裕度（TTC 等）不是协议指标：负 ΔTTC 不等于碰撞，"
                     "不得作为正式证据或真实道路安全结论；ΔTTC 是确定性闭环节点的属性"
                     "（种子只随机化 ramp nuisance 车），不是随机碰撞风险的反转。")
        summary["status"] = "OK"
        summary["by_method_stream"] = method_summary
        summary["by_seed_method"] = per_seed_method
        summary["cross_seed"] = cross_seed
        summary["figures"] = figures

    # -- budget accounting appendix (always rendered, from the real ledger) --
    lines.append("")
    lines.append("## 预算账附录（真实账本；失败/中断/未知同样计费）")
    lines.append("")
    lines.append("| phase | scope | cap | launched | completed | error | interrupted "
                 "| pending/unknown | unused slots |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    if budget_records:
        for b in budget_records:
            cap = "n/a" if b["cap"] is None else b["cap"]
            unused = "n/a" if b["unused_slots"] is None else b["unused_slots"]
            lines.append(
                f"| {b['phase']} | {b['budget_scope']} | {cap} | {b['launched']} | "
                f"{b['completed']} | {b['error']} | {b['interrupted']} | "
                f"{b['pending_or_unknown']} | {unused} |")
    else:
        lines.append("| （本阶段无已计费 episode） | | | | | | | | |")
    lines.append("")
    lines.append("- 未用 slots 不得挪用；已发起但无结果的尝试保守记为 pending/unknown 并计费。")

    report_path = reports_dir / f"{phase}_report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary["report_markdown"] = str(report_path)
    summary["quartets_csv"] = str(csv_path)
    (reports_dir / f"{phase}_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"

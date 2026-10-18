"""Exploratory continuous safety-margin analysis (NON-PROTOCOL).

The frozen protocol (docs/PROTOCOL_V01.md) defines its primary metrics on the
**collision binary** ``Y``. In the dev_seed smoke/pilot sample the boundary
controller never crashed the ego vehicle, so every collision-based delta is
exactly 0 and the binary metrics cannot show *any* difference between
conditions. That does **not** mean the interventions had no effect: the raw
episode records also contain a continuous safety-margin proxy,
``min_forward_ttc_sampled_s`` (the smallest sampled forward time-to-collision
over the episode), plus ``reward_sum`` / ``policy_steps`` / ``sim_time_s``.

This module computes **exploratory, descriptive** paired differences of those
continuous proxies per quartet, using the same quartet isolation rule as the
primary statistics (same master_seed, method, anchor, repetition, stream **and**
run_id; four conditions in one run).

Hard boundaries (do not violate):

* This is NOT part of the frozen protocol and NOT formal evidence.
* It never launches an episode; it only re-reads records that were already
  produced and paid for.
* It is only computed when real complete quartets exist; missing records are
  reported as missing, never imputed.
* A negative paired TTC difference means "the intervention moved the ego
  *closer* to collision" in this one simulated episode; it is not a real-world
  safety claim and not a collision.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .ledger import VALID_PHASES
from .seeds import CONDITIONS

RUNS_DIRNAME = "runs"

#: Continuous proxies read from the raw episode records.
MARGIN_FIELDS = ("min_forward_ttc_sampled_s", "reward_sum", "policy_steps", "sim_time_s")

EXPLORATORY_MARGIN_NOTE = (
    "探索性连续安全裕度分析：不是冻结协议的指标，不是正式证据，不构成真实道路安全结论。"
    "它只描述 dev_seed 样本下已付费产生的真实 episode 中，连续代理量（最小前向 TTC 等）"
    "的条件间配对差。负的 TTC 差表示该干预在这一个仿真 episode 中使自车更接近碰撞，"
    "但不等于发生碰撞，也不得外推到其他场景或真实世界。"
)


@dataclass
class MarginQuartet:
    """Paired continuous-proxy observations for one complete quartet."""

    master_seed: int
    method: str
    anchor_id: str
    repetition: int
    stream: str
    run_id: str
    values: dict[str, dict[str, float]] = field(default_factory=dict)

    def delta(self, field_name: str, condition_a: str, condition_b: str) -> float | None:
        """value(a) - value(b) for one proxy, or None when a side is missing."""
        va = self.values.get(condition_a, {}).get(field_name)
        vb = self.values.get(condition_b, {}).get(field_name)
        if va is None or vb is None:
            return None
        return float(va) - float(vb)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "master_seed": self.master_seed,
            "method": self.method,
            "anchor_id": self.anchor_id,
            "repetition": self.repetition,
            "stream": self.stream,
            "run_id": self.run_id,
        }
        for fname in MARGIN_FIELDS:
            out[f"d_{fname}_both"] = self.delta(fname, "11", "00")
            out[f"d_{fname}_gap"] = self.delta(fname, "10", "00")
            out[f"d_{fname}_speed"] = self.delta(fname, "01", "00")
        return out


@dataclass
class MarginData:
    phase: str
    quartets: list[MarginQuartet]
    replays: list[MarginQuartet]
    incomplete: list[dict[str, Any]]
    missing_raw: int

    @property
    def has_data(self) -> bool:
        return bool(self.quartets)


def _load_raw(path: str) -> dict[str, Any] | None:
    p = Path(path)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _proxy_from_raw(raw: dict[str, Any]) -> dict[str, float]:
    result = raw.get("result") if isinstance(raw, dict) else None
    if not isinstance(result, dict):
        return {}
    out: dict[str, float] = {}
    for fname in MARGIN_FIELDS:
        v = result.get(fname)
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            out[fname] = float(v)
    return out


def load_margin_data(project_root: str | Path, phase: str) -> MarginData:
    """Collect per-quartet continuous proxies from the ledger + raw records.

    Quartet isolation matches :func:`safefliplab.report.load_phase_data`:
    ``(master_seed, method, anchor_id, repetition, stream)`` **and** one
    ``run_id`` must supply all four conditions. When two runs complete the
    same isolation key (e.g. the smoke determinism replay), the earliest
    complete run (ledger file order) is the *primary* quartet and later runs
    are recorded separately as *replays* — replays are NOT counted as
    additional independent evidence. Only completed episodes with a readable
    raw record contribute; anything else is recorded as incomplete/missing,
    never imputed.
    """
    if phase not in VALID_PHASES:
        raise ValueError(f"unknown phase {phase!r}")
    root = Path(project_root)
    ledger_path = root / RUNS_DIRNAME / "episode_ledger.csv"
    quartets: list[MarginQuartet] = []
    replays: list[MarginQuartet] = []
    incomplete: list[dict[str, Any]] = []
    missing_raw = 0
    if not ledger_path.exists():
        return MarginData(phase=phase, quartets=[], replays=[], incomplete=[],
                          missing_raw=0)

    with open(ledger_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    phase_rows = [r for r in rows if r["phase"] == phase and r["row_type"] == "outcome"]

    # (seed, method, anchor, rep, stream, run_id) -> {condition: proxy dict}
    grouped: dict[tuple, dict[str, dict[str, float]]] = {}
    status: dict[tuple, dict[str, dict[str, str]]] = {}
    for r in phase_rows:
        key = (int(r["master_seed"]), r["method"], r["anchor_id"],
               int(r["repetition"]), r["stream"], r["run_id"])
        status.setdefault(key, {}).setdefault(r["condition"], r["exit_status"])
        if r["exit_status"] != "completed":
            continue
        raw = _load_raw(r.get("raw_path", ""))
        if raw is None:
            missing_raw += 1
            continue
        proxy = _proxy_from_raw(raw)
        if not proxy:
            missing_raw += 1
            continue
        grouped.setdefault(key, {})[r["condition"]] = proxy

    def _mk(key: tuple, per_cond: dict[str, dict[str, float]]) -> MarginQuartet:
        ms, method, anchor_id, rep, stream, run_id = key
        return MarginQuartet(
            master_seed=ms, method=method, anchor_id=anchor_id,
            repetition=rep, stream=stream, run_id=run_id,
            values={c: dict(per_cond[c]) for c in CONDITIONS},
        )

    # Group complete runs by the isolation key (without run_id); the earliest
    # complete run in ledger order is primary, later ones are replays.
    complete_by_isokey: dict[tuple, list[tuple]] = {}
    for key, per_cond in grouped.items():
        if set(per_cond) == set(CONDITIONS):
            isokey = key[:5]
            complete_by_isokey.setdefault(isokey, []).append(key)

    for isokey, run_keys in complete_by_isokey.items():
        ordered = sorted(run_keys, key=lambda k: k[5])  # run_id, ledger order
        quartets.append(_mk(ordered[0], grouped[ordered[0]]))
        for rk in ordered[1:]:
            replays.append(_mk(rk, grouped[rk]))

    for key, per_cond in grouped.items():
        if set(per_cond) != set(CONDITIONS):
            ms, method, anchor_id, rep, stream, run_id = key
            incomplete.append({
                "master_seed": ms, "method": method, "anchor_id": anchor_id,
                "repetition": rep, "stream": stream, "run_id": run_id,
                "conditions_present": sorted(per_cond),
                "status": status.get(key, {}),
            })

    quartets.sort(key=lambda q: (q.master_seed, q.method, q.stream,
                                 q.anchor_id, q.repetition, q.run_id))
    replays.sort(key=lambda q: (q.master_seed, q.method, q.stream,
                                q.anchor_id, q.repetition, q.run_id))
    incomplete.sort(key=lambda q: (q["master_seed"], q["method"], q["stream"],
                                   q["anchor_id"], q["repetition"], q["run_id"]))
    return MarginData(phase=phase, quartets=quartets, replays=replays,
                      incomplete=incomplete, missing_raw=missing_raw)


def _mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def margin_summary(data: MarginData) -> dict[str, Any]:
    """Aggregate exploratory margin deltas by (method, stream).

    ``d_<field>_both`` is value(11) - value(00) per quartet; a negative value
    means the combined intervention reduced the continuous safety proxy.
    """
    summary: dict[str, Any] = {}
    for method in ("WideExplore", "VerifyFirst"):
        for stream in ("discovery", "audit"):
            qs = [q for q in data.quartets if q.method == method and q.stream == stream]
            if not qs:
                continue
            block: dict[str, Any] = {"n_quartets": len(qs)}
            for fname in MARGIN_FIELDS:
                conds = {c: [q.values[c][fname] for q in qs if fname in q.values[c]]
                         for c in CONDITIONS}
                block[f"mean_{fname}"] = {c: _mean(v) for c, v in conds.items()}
                block[f"d_{fname}_both"] = _mean(
                    [d for q in qs for d in [q.delta(fname, "11", "00")] if d is not None])
                block[f"d_{fname}_gap"] = _mean(
                    [d for q in qs for d in [q.delta(fname, "10", "00")] if d is not None])
                block[f"d_{fname}_speed"] = _mean(
                    [d for q in qs for d in [q.delta(fname, "01", "00")] if d is not None])
            summary[f"{method}/{stream}"] = block
    return summary


def margin_quartet_rows(data: MarginData) -> list[dict[str, Any]]:
    """Per-quartet exploratory rows (for CSV)."""
    return [q.to_dict() for q in data.quartets]

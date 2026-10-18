"""Four-condition legality, shared perturbation draws and SHA-256 seed derivation.

Pure functions only (standard library). No research constant is hard-coded as a
default: intervention sizes (Delta g / Delta v), upstream bounds and perturbation
specs must all be passed in explicitly. An UNSET perturbation bound raises
:class:`~v02lab.schema.UnsetParameterError` instead of silently defaulting.

Interventions (structural, role-fixed — see proposal section 5):

* condition ``10``: only ``front_gap += gap_m``
* condition ``01``: only ``ego_speed -= speed_mps``
* condition ``11``: both
* condition ``00``: the untouched anchor

The four conditions of one anchor-repetition share **one** perturbation draw and
**one** ``sim_seed`` (``condition`` is deliberately absent from the seed labels),
so conditions are paired.
"""
from __future__ import annotations

import hashlib
import json
import random
from typing import Any, Mapping

from .schema import UnsetParameterError

PROTOCOL_ID = "SafeFlipLab-v02"
CONDITIONS = ("00", "10", "01", "11")
GAP_DIM = "front_gap"
SPEED_DIM = "ego_speed"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _check_seed(seed: int) -> int:
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32:
        raise ValueError(f"seed must be an int in [0, 2**32), got {seed!r}")
    return seed


def derive_seed(master_seed: int, *labels: Any) -> int:
    """Deterministic 32-bit seed from a master seed and explicit labels."""
    _check_seed(master_seed)
    payload = canonical_json([PROTOCOL_ID, "seed", master_seed, *[str(x) for x in labels]])
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:4], "big")


def sim_seed_for(master_seed: int, method: str, stream: str, anchor_id: str,
                 repetition: int) -> int:
    """Paired sim_seed for one anchor-repetition (shared by all 4 conditions).

    ``condition`` is intentionally NOT a label: the four conditions must share a
    single paired seed. ``stream`` (discovery/audit) IS a label so audit never
    reuses a discovery draw.
    """
    if stream not in ("discovery", "audit"):
        raise ValueError(f"stream must be discovery/audit, got {stream!r}")
    if isinstance(repetition, bool) or not isinstance(repetition, int) or repetition < 0:
        raise ValueError(f"repetition must be a non-negative int, got {repetition!r}")
    return derive_seed(master_seed, "sim", method, stream, anchor_id, repetition)


def anchor_stream_seed(master_seed: int, stream_tag: str) -> int:
    """Seed of one anchor stream (discovery / audit / population / confirm)."""
    return derive_seed(master_seed, "anchor-stream", stream_tag)


def condition_offsets(condition: str, gap_m: float, speed_mps: float) -> tuple[float, float]:
    """(gap_delta, speed_delta) for one condition. No clipping/reordering."""
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}, got {condition!r}")
    gap_delta = float(gap_m) if condition in ("10", "11") else 0.0
    speed_delta = -float(speed_mps) if condition in ("01", "11") else 0.0
    return gap_delta, speed_delta


def apply_condition(values: Mapping[str, float], condition: str, gap_m: float,
                    speed_mps: float) -> dict[str, float]:
    """Return a NEW dict with the condition applied (never mutates the anchor)."""
    gap_delta, speed_delta = condition_offsets(condition, gap_m, speed_mps)
    if GAP_DIM not in values or SPEED_DIM not in values:
        raise KeyError(f"anchor must contain {GAP_DIM!r} and {SPEED_DIM!r}")
    out = dict(values)
    out[GAP_DIM] = float(values[GAP_DIM]) + gap_delta
    out[SPEED_DIM] = float(values[SPEED_DIM]) + speed_delta
    return out


def quartet_values(anchor_values: Mapping[str, float], gap_m: float,
                   speed_mps: float) -> dict[str, dict[str, float]]:
    return {c: apply_condition(anchor_values, c, gap_m, speed_mps) for c in CONDITIONS}


def legality_reasons(values: Mapping[str, float], bounds: Mapping[str, tuple[float, float]]) -> list[str]:
    reasons: list[str] = []
    for name, (low, high) in bounds.items():
        v = values.get(name)
        if v is None:
            reasons.append(f"{name}: missing")
            continue
        if not low <= v <= high:
            reasons.append(f"{name}={v} outside [{low}, {high}]")
    return reasons


def quartet_legality(anchor_values: Mapping[str, float], gap_m: float, speed_mps: float,
                     bounds: Mapping[str, tuple[float, float]]) -> tuple[bool, dict[str, list[str]]]:
    """True iff all four conditions stay inside ``bounds`` (no clipping)."""
    per: dict[str, list[str]] = {}
    ok = True
    for c in CONDITIONS:
        reasons = legality_reasons(apply_condition(anchor_values, c, gap_m, speed_mps), bounds)
        per[c] = reasons
        if reasons:
            ok = False
    return ok, per


def perturbation_draws(master_seed: int, *, anchor_index: int, repetition: int, stream: str,
                       spec: Mapping[str, Any]) -> dict[str, float]:
    """Draw the bounded perturbation ONCE per (anchor, repetition, stream).

    ``spec`` maps a dimension name to ``{"low": float, "high": float}`` (both
    REQUIRED; an UNSET/None bound raises rather than defaulting). Draws are
    deterministic (Mersenne Twister seeded by a SHA-256 derived seed), drawn in
    **sorted dimension order** so the result does not depend on dict insertion
    order, and rounded to 6 decimals.

    The returned mapping is **shared by all four conditions** of the quartet
    (call once per quartet; never re-draw per condition).
    """
    if stream not in ("discovery", "audit", "population", "confirm"):
        raise ValueError(f"unknown stream {stream!r}")
    for dim, b in spec.items():
        if b is None or b.get("low") is None or b.get("high") is None:
            raise UnsetParameterError(
                f"perturbation dimension {dim!r} has UNSET bounds; refusing to fabricate a default")
        if not b["low"] <= b["high"]:
            raise ValueError(f"perturbation dim {dim!r}: low > high")
    seed = derive_seed(master_seed, "perturb", stream, anchor_index, repetition)
    rng = random.Random(seed)
    return {dim: round(rng.uniform(spec[dim]["low"], spec[dim]["high"]), 6)
            for dim in sorted(spec)}


def shared_perturbation_for_quartet(master_seed: int, *, anchor_index: int, repetition: int,
                                    stream: str, spec: Mapping[str, Any]) -> dict[str, float]:
    """Explicit alias documenting that the quartet shares ONE draw (all conditions).

    Provided so callers cannot accidentally re-draw per condition; the value is
    identical for every condition by construction (``condition`` is not a label).
    """
    return perturbation_draws(master_seed, anchor_index=anchor_index, repetition=repetition,
                              stream=stream, spec=spec)

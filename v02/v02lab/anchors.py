"""V02 anchor domain, deterministic anchor stream and quartet construction.

The anchor is a **nominal** scenario inside the frozen V02 domain
(``anchor_domain`` in ``configs/v02_frozen_v1.json``). A *repetition* is the
anchor plus one shared perturbation draw (see :mod:`v02lab.quartet`), and a
*condition* applies the frozen structural intervention on top of that.

Anchors come from a deterministic SHA-256-seeded rejection stream inside the
V02 domain, so the stream is reproducible and never result-picked. Rejection
happens inside the domain (not the upstream bounds) and no value is ever
clipped.
"""
from __future__ import annotations

import random
from typing import Any, Mapping

from .conditions import CONDITIONS, apply_condition, derive_seed, quartet_legality

DIMS = ("ego_speed", "front_gap", "front_speed", "ramp_x", "ramp_speed",
        "ramp_target_speed")


def anchor_id(index: int) -> str:
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ValueError(f"anchor index must be a non-negative int, got {index!r}")
    return f"v02-anchor-{index:04d}"


def sample_anchor(master_seed: int, index: int, domain: Mapping[str, list[float]]) -> dict[str, float]:
    """Draw one anchor deterministically from the V02 domain."""
    seed = derive_seed(master_seed, "anchor", index)
    rng = random.Random(seed)
    return {d: round(rng.uniform(domain[d][0], domain[d][1]), 6) for d in DIMS}


def anchor_stream(master_seed: int, domain: Mapping[str, list[float]], *,
                  bounds: Mapping[str, tuple[float, float]], n: int,
                  gap_m: float, speed_mps: float,
                  perturbation_halfwidths: Mapping[str, float],
                  max_draws: int | None = None) -> list[dict[str, float]]:
    """First ``n`` anchors whose *every* condition + perturbation stays legal.

    Legality is checked against the upstream ``bounds`` for all four conditions
    under the most extreme perturbation the repetition can receive, so the
    rejection stream guarantees **zero clipping** later. Draws are deterministic
    and independent of ``n`` (anchor ``i`` is always the same anchor), which is
    what lets smoke and pilot share a stream prefix.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    limit = max_draws if max_draws is not None else n * 200 + 1000
    safe_domain = _shrink(domain, perturbation_halfwidths)
    out: list[dict[str, float]] = []
    for i in range(limit):
        if len(out) >= n:
            break
        candidate = sample_anchor(master_seed, i, safe_domain)
        if _legal_under_extremes(candidate, bounds, gap_m, speed_mps,
                                 perturbation_halfwidths):
            out.append(candidate)
    if len(out) < n:
        raise RuntimeError(
            f"anchor stream produced only {len(out)}/{n} legal anchors in {limit} draws")
    return out


def _shrink(domain: Mapping[str, list[float]],
            halfwidths: Mapping[str, float]) -> dict[str, list[float]]:
    """Shrink the nominal domain by the perturbation half-width so every draw of
    a repetition still lands inside the V02 domain as well."""
    out: dict[str, list[float]] = {}
    for d in DIMS:
        lo, hi = float(domain[d][0]), float(domain[d][1])
        hw = float(halfwidths.get(d, 0.0))
        if hi - lo < 2 * hw:
            raise ValueError(f"domain for {d!r} is narrower than the perturbation")
        out[d] = [lo + hw, hi - hw]
    return out


def _legal_under_extremes(values: Mapping[str, float],
                          bounds: Mapping[str, tuple[float, float]],
                          gap_m: float, speed_mps: float,
                          halfwidths: Mapping[str, float]) -> bool:
    """True iff all four conditions stay in ``bounds`` for BOTH perturbation
    extremes of every perturbed dimension (conservative corner check)."""
    extreme_shifts = [0.0]
    for d, hw in halfwidths.items():
        if hw:
            extreme_shifts.extend([-hw, hw])
    for shift in extreme_shifts:
        shifted = {d: float(v) + (shift if d in halfwidths else 0.0)
                   for d, v in values.items()}
        ok, _ = quartet_legality(shifted, gap_m, speed_mps, bounds)
        if not ok:
            return False
    return True


def quartet_scenarios(base_values: Mapping[str, float], gap_m: float,
                      speed_mps: float) -> dict[str, dict[str, float]]:
    """The four conditioned scenarios of one repetition (00/10/01/11)."""
    return {c: apply_condition(base_values, c, gap_m, speed_mps) for c in CONDITIONS}


def quartet_legality_report(base_values: Mapping[str, float], gap_m: float,
                            speed_mps: float,
                            bounds: Mapping[str, tuple[float, float]]
                            ) -> tuple[bool, dict[str, list[str]]]:
    return quartet_legality(base_values, gap_m, speed_mps, bounds)

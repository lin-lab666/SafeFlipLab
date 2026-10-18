"""Quartet construction: shared perturbation draw + four conditions + seeds.

One **repetition** of an anchor is:

    base = anchor_nominal + one shared perturbation draw   (drawn once)

and its four conditions apply the frozen structural intervention on top:

    ``00`` = base                     ``10`` = base + front_gap
    ``01`` = base - ego_speed         ``11`` = base + front_gap - ego_speed

All four conditions of one repetition share the **same** perturbation draw and
the **same** ``sim_seed`` (``condition`` is never a seed label), so conditions
are paired. Different repetitions get different draws *and* different
``sim_seed`` values, which is exactly what makes a repetition carry new
information — the property V01 lacked.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .conditions import CONDITIONS, apply_condition, perturbation_draws, sim_seed_for


@dataclass(frozen=True)
class Repetition:
    """One (anchor, repetition): shared base scenario + four conditioned scenarios."""
    master_seed: int
    stream: str
    method: str
    anchor_index: int
    anchor_id: str
    repetition: int
    sim_seed: int
    perturbation: dict[str, float]
    base: dict[str, float]
    scenarios: dict[str, dict[str, float]]


def build_repetition(*, master_seed: int, stream: str, anchor_index: int,
                     anchor_id: str, repetition: int, anchor_values: Mapping[str, float],
                     perturbation_spec: Mapping[str, Mapping[str, float | None]],
                     gap_m: float, speed_mps: float, method: str) -> Repetition:
    """Draw the shared perturbation once and build the four conditioned scenarios.

    ``perturbation_spec`` maps a dimension to ``{"halfwidth": h}``; the draw is
    *zero-centred* around the anchor nominal, so the anchor remains the mean of
    its repetition distribution.

    ``method`` is **required** and enters the seed labels. It used to be hardcoded
    as ``"shared"`` (independent-review finding MAJOR-1), which made the two
    allocation strategies' audits of a shared anchor reuse one identical
    simulation. The primary study passes ``"Shared"`` (preserving the seeds of the
    episodes already recorded); an audit passes the real strategy name so the two
    strategies can never share a draw for the same anchor.
    """
    if not method:
        raise ValueError("method label must be supplied explicitly (never defaulted)")
    spec = {}
    for dim, node in perturbation_spec.items():
        hw = node.get("halfwidth")
        if hw is None:
            from .schema import UnsetParameterError
            raise UnsetParameterError(
                f"perturbation half-width for {dim!r} is UNSET; refusing to default")
        spec[dim] = {"low": -float(hw), "high": float(hw)}

    offsets = perturbation_draws(master_seed, anchor_index=anchor_index,
                                 repetition=repetition, stream=stream, spec=spec)
    base = dict(anchor_values)
    for dim, delta in offsets.items():
        base[dim] = round(float(base[dim]) + float(delta), 6)

    return Repetition(
        master_seed=master_seed,
        stream=stream,
        method=method,
        anchor_index=anchor_index,
        anchor_id=anchor_id,
        repetition=repetition,
        sim_seed=sim_seed_for(master_seed, method, stream, anchor_id, repetition),
        perturbation={k: round(v, 6) for k, v in offsets.items()},
        base=base,
        scenarios={c: apply_condition(base, c, gap_m, speed_mps) for c in CONDITIONS},
    )


def repetition_seed_payload(rep: Repetition) -> dict[str, Any]:
    """Compact, JSON-serialisable fingerprint of a repetition (for the raw archive)."""
    return {
        "master_seed": rep.master_seed,
        "stream": rep.stream,
        "anchor_id": rep.anchor_id,
        "anchor_index": rep.anchor_index,
        "repetition": rep.repetition,
        "sim_seed": rep.sim_seed,
        "perturbation": rep.perturbation,
        "base_scenario": rep.base,
        "condition_scenarios": rep.scenarios,
    }

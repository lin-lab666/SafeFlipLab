"""Scenario domain, four-condition quartet definition and legality checks.

The scenario schema is the public ``cornercaselab`` 0.3.0 ``merge-scenario-v1``
(six dimensions with explicit bounds). SafeFlipLab does NOT redefine it: the
upstream bounds are read from the installed package at import time so a
version drift fails loudly instead of silently changing semantics.

Interventions (frozen by the research protocol, docs/PROTOCOL_V01.md):

* condition ``10``: only ``front_gap += 2.0 m``
* condition ``01``: only ``ego_speed -= 1.0 m/s``
* condition ``11``: both interventions
* condition ``00``: the untouched anchor

An anchor is *quartet-legal* only if all four conditions lie inside the
upstream bounds. Values are never clipped: clipping would forge a comparable
control and is forbidden by the protocol.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from cornercaselab.domain import BOUNDS as UPSTREAM_BOUNDS
from cornercaselab.domain import SCHEMA as UPSTREAM_SCHEMA
from cornercaselab.domain import Scenario

from .seeds import CONDITIONS

# Frozen intervention sizes (metres / metres-per-second).
GAP_INTERVENTION_M = 2.0
SPEED_INTERVENTION_MPS = 1.0

# The two intervened dimensions must leave room for the intervention inside
# the upstream bounds, otherwise the quartet cannot be run without clipping.
_ANCHOR_EXTRA_BOUNDS: dict[str, tuple[float, float]] = {
    "front_gap": (
        UPSTREAM_BOUNDS["front_gap"][0],
        UPSTREAM_BOUNDS["front_gap"][1] - GAP_INTERVENTION_M,
    ),
    "ego_speed": (
        UPSTREAM_BOUNDS["ego_speed"][0] + SPEED_INTERVENTION_MPS,
        UPSTREAM_BOUNDS["ego_speed"][1],
    ),
}

#: Feasible anchor domain = upstream bounds tightened on the two intervened dims.
ANCHOR_BOUNDS: dict[str, tuple[float, float]] = dict(UPSTREAM_BOUNDS)
ANCHOR_BOUNDS.update(_ANCHOR_EXTRA_BOUNDS)

SCENARIO_SCHEMA = UPSTREAM_SCHEMA
SCENARIO_DIMENSIONS = tuple(sorted(UPSTREAM_BOUNDS))


def anchor_in_domain(scenario: Scenario) -> bool:
    """True iff every quartet condition stays inside the upstream bounds."""
    for name, (low, high) in ANCHOR_BOUNDS.items():
        value = getattr(scenario, name)
        if not low <= value <= high:
            return False
    return True


def condition_scenario(anchor: Scenario, condition: str) -> Scenario:
    """Build one quartet condition. Raises (no clipping) if out of bounds."""
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}, got {condition!r}")
    gap_delta = GAP_INTERVENTION_M if condition in ("10", "11") else 0.0
    speed_delta = -SPEED_INTERVENTION_MPS if condition in ("01", "11") else 0.0
    # Scenario.__post_init__ re-validates against upstream bounds; an illegal
    # condition therefore raises instead of being silently clipped.
    return replace(
        anchor,
        front_gap=anchor.front_gap + gap_delta,
        ego_speed=anchor.ego_speed + speed_delta,
    )


def quartet_scenarios(anchor: Scenario) -> dict[str, Scenario]:
    """All four conditions of one anchor, keyed by condition code."""
    return {c: condition_scenario(anchor, c) for c in CONDITIONS}


@dataclass(frozen=True)
class Anchor:
    """A quartet-legal anchor with its stable stream identity."""

    index: int
    scenario: Scenario
    stream_draws: int  # uniform draws consumed to obtain this legal anchor

    @property
    def anchor_id(self) -> str:
        from .seeds import anchor_id

        return anchor_id(self.index)

    @property
    def scenario_uid(self) -> str:
        return self.scenario.uid

    def to_dict(self) -> dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "index": self.index,
            "scenario_uid": self.scenario_uid,
            "scenario": self.scenario.to_dict(),
            "stream_draws": self.stream_draws,
        }


def anchor_bounds_report() -> dict[str, dict[str, float]]:
    """Upstream vs tightened anchor bounds, for docs and doctor output."""
    return {
        name: {
            "upstream_low": UPSTREAM_BOUNDS[name][0],
            "upstream_high": UPSTREAM_BOUNDS[name][1],
            "anchor_low": ANCHOR_BOUNDS[name][0],
            "anchor_high": ANCHOR_BOUNDS[name][1],
        }
        for name in sorted(UPSTREAM_BOUNDS)
    }

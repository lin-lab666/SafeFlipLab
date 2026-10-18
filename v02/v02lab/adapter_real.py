"""Real V02 adapter over the frozen cornercaselab 0.3.0 / HighwayEnv interface.

Design (see ``docs/AUTONOMOUS_DECISIONS.md`` D31):

* the *simulator* is the frozen upstream one — :func:`cornercaselab.simulator.evaluate`
  with ``policy="boundary"`` and ``SimSettings(25 s, 15 Hz, 5 Hz)``. Nothing about
  the physics, the controller or the environment construction is re-implemented,
  so the V02 perturbation is **purely scenario-level** and the simulator semantics
  are unchanged;
* the per-policy-step forward-candidate / closing quantities are **derived from
  the returned trajectory** using the upstream ``longitudinal_ttc`` semantics
  (ahead + lateral overlap <= 2.0 m, 5 m vehicle length, constant-x-velocity).
  :func:`verify_against_upstream` re-derives the upstream episode minimum from
  those steps and compares it with the simulator's own
  ``min_forward_ttc_sampled_s`` — a machine-checkable equivalence proof of the
  V02 metric implementation.

This module is the only V02 module that imports the simulator.
"""
from __future__ import annotations

import math
from typing import Any, Sequence

from .ttc_state import (LATERAL_OVERLAP_M, VEHICLE_LENGTH_M, StepTTCState,
                        step_ttc_state)

CONTROLLER_POLICY = "boundary"
HORIZON_S = 25.0
SIMULATION_HZ = 15
POLICY_HZ = 5
REQUIRED_CORNERCASELAB_VERSION = "0.3.0"


def _settings():
    from cornercaselab.simulator import SimSettings
    return SimSettings(horizon_s=HORIZON_S, simulation_hz=SIMULATION_HZ, policy_hz=POLICY_HZ)


def _vx(speed: float, heading: float) -> float:
    """Longitudinal velocity component, matching the upstream Kinematics observation."""
    return float(speed) * math.cos(float(heading))


def step_candidate(vehicles: Sequence[dict[str, Any]]) -> tuple[bool, float, float]:
    """(has_candidate, gap, closing) of the *tightest* forward candidate.

    Mirrors ``cornercaselab.metrics.longitudinal_ttc`` exactly: a candidate is a
    vehicle strictly ahead (``ox > x``) and laterally overlapping
    (``|oy - y| <= 2.0``); ``gap = ox - x - 5.0`` and ``closing = vx - ovx``;
    a candidate with ``closing <= 0`` and ``gap > 0`` yields no finite TTC and is
    only reported when no finite-TTC candidate exists.

    Numeric triples are returned for every step (the shared adapter contract used
    by :mod:`v02lab.fake_adapter` too); ``has_candidate=False`` steps carry
    ``(0.0, 0.0)`` and are classified as ``NO_CANDIDATE`` downstream.
    """
    if not vehicles:
        return False, 0.0, 0.0
    ego = vehicles[0]
    x, y = float(ego["x"]), float(ego["y"])
    vx = _vx(ego["speed"], ego["heading"])
    has_candidate = False
    best: tuple[float, float, float] | None = None
    non_closing: tuple[float, float] | None = None
    for other in vehicles[1:]:
        ox, oy = float(other["x"]), float(other["y"])
        if ox <= x or abs(oy - y) > LATERAL_OVERLAP_M:
            continue
        has_candidate = True
        gap = ox - x - VEHICLE_LENGTH_M
        closing = vx - _vx(other["speed"], other["heading"])
        if gap <= 0.0:
            ttc = 0.0
        elif closing > 0.0:
            ttc = gap / closing
        else:
            if non_closing is None or gap < non_closing[0]:
                non_closing = (gap, closing)
            continue
        if best is None or ttc < best[0]:
            best = (ttc, gap, closing)
    if best is not None:
        return True, best[1], best[2]
    if non_closing is not None:
        return True, non_closing[0], non_closing[1]
    return has_candidate, 0.0, 0.0


def raw_steps_from_trajectory(trajectory: Sequence[dict[str, Any]]
                              ) -> list[tuple[bool, float, float]]:
    """Per-policy-step raw (has_candidate, gap, closing) triples."""
    return [step_candidate(snap.get("vehicles", [])) for snap in trajectory]


def states_from_raw_steps(raw_steps: Sequence[Sequence[Any]]
                          ) -> list[tuple[StepTTCState, float | None]]:
    """Convert the shared raw-triple contract to Layer-1 (state, value) pairs."""
    out: list[tuple[StepTTCState, float | None]] = []
    for hc, gap, closing in raw_steps:
        out.append(step_ttc_state(has_candidate=bool(hc), gap=float(gap),
                                  closing=float(closing)))
    return out


def steps_from_trajectory(trajectory: Sequence[dict[str, Any]]
                          ) -> list[tuple[StepTTCState, float | None]]:
    """Per-policy-step Layer-1 states derived from a real trajectory."""
    return states_from_raw_steps(raw_steps_from_trajectory(trajectory))


def verify_against_upstream(result: dict[str, Any]) -> dict[str, Any]:
    """Cross-check the derived per-step minimum against the simulator's own value."""
    steps = states_from_raw_steps(result.get("steps", []))
    finite = [v for _, v in steps if v is not None]
    derived = min(finite) if finite else None
    upstream = result.get("min_forward_ttc_sampled_s")
    if derived is None or upstream is None:
        match = derived is None and upstream is None
        delta = None
    else:
        delta = abs(float(derived) - float(upstream))
        match = delta <= 1e-6
    return {"derived_min_ttc_s": derived, "upstream_min_ttc_s": upstream,
            "abs_delta_s": delta, "match": bool(match)}


class RealAdapterV02:
    """Runs exactly one real HighwayEnv episode per call. Never a test double."""

    is_test_double = False

    def __init__(self) -> None:
        self._verify_interface()

    def _verify_interface(self) -> None:
        import importlib.metadata as md
        version = md.version("cornercaselab")
        if version != REQUIRED_CORNERCASELAB_VERSION:
            raise RuntimeError(
                f"cornercaselab {version} installed but V02 requires "
                f"{REQUIRED_CORNERCASELAB_VERSION}; refusing to run episodes")
        from cornercaselab import domain as up_domain
        from cornercaselab.policy import POLICIES
        if CONTROLLER_POLICY not in POLICIES:
            raise RuntimeError(f"policy {CONTROLLER_POLICY!r} unavailable in upstream")
        expected = {"ego_speed", "front_gap", "front_speed", "ramp_x", "ramp_speed",
                    "ramp_target_speed"}
        if set(up_domain.BOUNDS) != expected:
            raise RuntimeError(f"upstream scenario dimensions drifted: {sorted(up_domain.BOUNDS)}")

    def run_episode(self, scenario: dict[str, float], sim_seed: int) -> dict[str, Any]:
        """Run one real episode; return the V02 adapter record (FakeAdapterV02 shape)."""
        from cornercaselab.domain import Scenario
        from cornercaselab.simulator import evaluate

        scn = Scenario.from_dict(dict(scenario))
        result = evaluate(scn, int(sim_seed), policy=CONTROLLER_POLICY, settings=_settings())
        return {
            "steps": raw_steps_from_trajectory(result["trajectory"]),
            "exit_status": "completed",
            "termination": str(result["termination"]),
            "ego_collision": 1 if result["ego_collision"] else 0,
            "goal_reached": bool(result["goal_reached"]),
            "npc_collisions": int(result["npc_collisions"]),
            "sim_time_s": float(result["sim_time_s"]),
            "policy_steps": int(result["policy_steps"]),
            "min_forward_ttc_upstream_s": result["min_forward_ttc_sampled_s"],
            "reward_sum": float(result["reward_sum"]),
            "wall_time_s": float(result["wall_time_s"]),
            "trace_sha256_rounded_9dp": str(result["trace_sha256_rounded_9dp"]),
            "initial_npc_delta": list(result.get("initial_npc_delta", [])),
            "trajectory": result["trajectory"],
        }

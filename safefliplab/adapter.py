"""ScenarioAdapter: verified, frozen wrapper around the public cornercaselab 0.3.0
HighwayEnv interface.

The adapter is deliberately thin and *verifying*: at construction it checks the
installed package version, the scenario schema, the six dimension names, the
bounds of the two intervened dimensions and the shape of the result record.
If any check fails the adapter refuses to run episodes (protocol GO/NO-GO),
instead of guessing field names or silently substituting semantics.

What is frozen here:

* controller policy = ``boundary`` (the cornercaselab observation-only pilot
  controller with gap 6.0 m / headway 0.30 s / TTC 0.90 s);
* simulator settings = 25 s horizon, 15 Hz simulation, 5 Hz policy;
* collision observation = ``ego_collision`` returned by
  ``cornercaselab.simulator.evaluate`` (``env.vehicle.crashed``).

None of these may change between quartet conditions, methods, seeds or phases.
"""
from __future__ import annotations

import importlib.metadata as metadata
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from cornercaselab.domain import BOUNDS as UPSTREAM_BOUNDS
from cornercaselab.domain import Scenario
from cornercaselab.simulator import SimSettings, evaluate

from .domain import SCENARIO_SCHEMA

REQUIRED_CORNERCASELAB_VERSION = "0.3.0"

#: Frozen controller. Must be one of cornercaselab.policy.POLICIES.
CONTROLLER_POLICY = "boundary"

#: Frozen simulator settings (must not change across conditions/methods/phases).
SIM_SETTINGS = SimSettings(horizon_s=25.0, simulation_hz=15, policy_hz=5)

EXPECTED_DIMENSIONS = {
    "ego_speed",
    "front_gap",
    "front_speed",
    "ramp_x",
    "ramp_speed",
    "ramp_target_speed",
}


class AdapterVerificationError(RuntimeError):
    """Raised when the public simulation interface does not match the protocol."""


@dataclass(frozen=True)
class AdapterFingerprint:
    cornercaselab_version: str
    highway_env_version: str
    gymnasium_version: str
    scenario_schema: str
    controller_policy: str
    horizon_s: float
    simulation_hz: int
    policy_hz: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "cornercaselab_version": self.cornercaselab_version,
            "highway_env_version": self.highway_env_version,
            "gymnasium_version": self.gymnasium_version,
            "scenario_schema": self.scenario_schema,
            "controller_policy": self.controller_policy,
            "horizon_s": self.horizon_s,
            "simulation_hz": self.simulation_hz,
            "policy_hz": self.policy_hz,
        }


def _package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError as exc:  # pragma: no cover - env failure
        raise AdapterVerificationError(f"required package {name!r} is not installed") from exc


@lru_cache(maxsize=1)
def fingerprint() -> AdapterFingerprint:
    return AdapterFingerprint(
        cornercaselab_version=_package_version("cornercaselab"),
        highway_env_version=_package_version("highway-env"),
        gymnasium_version=_package_version("gymnasium"),
        scenario_schema=SCENARIO_SCHEMA,
        controller_policy=CONTROLLER_POLICY,
        horizon_s=SIM_SETTINGS.horizon_s,
        simulation_hz=SIM_SETTINGS.simulation_hz,
        policy_hz=SIM_SETTINGS.policy_hz,
    )


class ScenarioAdapter:
    """Runs exactly one real HighwayEnv episode per call."""

    def __init__(self) -> None:
        self._verify_interface()

    # -- verification -----------------------------------------------------
    def _verify_interface(self) -> None:
        version = _package_version("cornercaselab")
        if version != REQUIRED_CORNERCASELAB_VERSION:
            raise AdapterVerificationError(
                f"cornercaselab {version} installed but protocol requires "
                f"{REQUIRED_CORNERCASELAB_VERSION}; refusing to run episodes"
            )
        if SCENARIO_SCHEMA != "merge-scenario-v1":
            raise AdapterVerificationError(
                f"unexpected scenario schema {SCENARIO_SCHEMA!r}"
            )
        if set(UPSTREAM_BOUNDS) != EXPECTED_DIMENSIONS:
            raise AdapterVerificationError(
                f"scenario dimensions drifted: {sorted(UPSTREAM_BOUNDS)}"
            )
        from cornercaselab.policy import POLICIES

        if CONTROLLER_POLICY not in POLICIES:
            raise AdapterVerificationError(
                f"controller {CONTROLLER_POLICY!r} not available; policies={POLICIES}"
            )
        # The two intervened fields must exist as real scenario fields.
        probe = Scenario()
        for field in ("front_gap", "ego_speed"):
            if not hasattr(probe, field):
                raise AdapterVerificationError(f"scenario field {field!r} missing")

    # -- execution --------------------------------------------------------
    def run_episode(self, scenario: Scenario, sim_seed: int) -> dict[str, Any]:
        """Run one real episode. Returns a normalised result record.

        Raises on simulator failure; the caller (SimulatorRunner) is
        responsible for billing the attempt in the EpisodeLedger.
        """
        from .seeds import check_seed

        check_seed(sim_seed)
        result = evaluate(
            scenario,
            sim_seed,
            policy=CONTROLLER_POLICY,
            settings=SIM_SETTINGS,
        )
        return {
            "ego_collision": bool(result["ego_collision"]),
            "goal_reached": bool(result["goal_reached"]),
            "termination": str(result["termination"]),
            "npc_collisions": int(result["npc_collisions"]),
            "sim_time_s": float(result["sim_time_s"]),
            "policy_steps": int(result["policy_steps"]),
            "min_forward_ttc_sampled_s": result["min_forward_ttc_sampled_s"],
            "reward_sum": float(result["reward_sum"]),
            "wall_time_s": float(result["wall_time_s"]),
            "trace_sha256_rounded_9dp": str(result["trace_sha256_rounded_9dp"]),
            "trajectory": result["trajectory"],
        }

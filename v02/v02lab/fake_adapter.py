"""Synthetic test double for the V02 pipeline (NEVER a real episode).

``FakeAdapterV02`` mimics the *shape* of an episode result (per-step forward
candidate/closing, a termination class, a collision flag and a deterministic trace
hash) so the pure state model, reporting and statistics interfaces can be tested
end to end offline. It does not import or run any simulator and consumes zero
simulation budget (``is_test_double = True``).

The "dynamics" are a deliberately simple deterministic toy, not a model of road
risk; tests assert *structural* properties (categories present, determinism,
paired sharing), never physical accuracy.
"""
from __future__ import annotations

import hashlib
import random
from typing import Any, Callable

from .conditions import CONDITIONS

DEFAULT_HORIZON_STEPS = 60
DEFAULT_DT_S = 0.2
# above this initial front gap we pretend there is no forward candidate at all
NO_CANDIDATE_GAP_M = 60.0


class FakeAdapterV02:
    is_test_double = True

    def __init__(self, *, fail: Callable[[dict, int], bool] | None = None,
                 error_type: type[Exception] = RuntimeError,
                 horizon_steps: int = DEFAULT_HORIZON_STEPS) -> None:
        self.calls: list[tuple[dict[str, Any], int]] = []
        self.fail = fail
        self.error_type = error_type
        self.horizon_steps = horizon_steps

    def run_episode(self, scenario: dict[str, Any], sim_seed: int,
                    perturbation: dict[str, float] | None = None) -> dict[str, Any]:
        self.calls.append((scenario, sim_seed))
        if self.fail is not None and self.fail(scenario, sim_seed):
            raise self.error_type("injected failure")

        pert = perturbation or {}
        gap = float(scenario["front_gap"])
        v_ego = float(scenario["ego_speed"])
        v_lead = float(scenario.get("front_speed", v_ego - 3.0)) + float(
            pert.get("lead_speed", 0.0))
        rng = random.Random(sim_seed)
        # deterministic, tiny nuisance jitter so repetitions differ structurally
        v_lead += rng.uniform(-0.25, 0.25)

        steps: list[tuple[bool, float, float]] = []
        collision = 0
        termination = "horizon"
        for _ in range(self.horizon_steps):
            has_candidate = gap <= NO_CANDIDATE_GAP_M
            closing = (v_ego - v_lead) if has_candidate else None
            steps.append((has_candidate, gap, closing if closing is not None else 0.0))
            v_ego = max(0.0, v_ego - 0.2)
            gap += (v_ego - v_lead) * DEFAULT_DT_S
            if has_candidate and gap <= 0.0:
                collision = 1
                termination = "collision"
                break
        trace = hashlib.sha256(
            f"{scenario.get('uid', '')}|{sim_seed}|{v_lead}".encode()).hexdigest()
        return {
            "steps": steps,                      # list[(has_candidate, gap, closing)]
            "exit_status": "completed",
            "termination": termination,
            "ego_collision": collision,
            "trace_sha256": trace,
        }


def synthetic_scenario(*, front_gap: float, ego_speed: float, front_speed: float | None = None,
                       uid: str = "synth") -> dict[str, Any]:
    return {"uid": uid, "front_gap": front_gap, "ego_speed": ego_speed,
            "front_speed": front_speed if front_speed is not None else ego_speed - 3.0}


def synthetic_quartet_records(adapter: FakeAdapterV02, scenario: dict[str, Any], *,
                              sim_seed: int, anchor_id: str, repetition: int, gap_m: float,
                              speed_mps: float) -> list[dict[str, Any]]:
    """Run the four conditions (paired, shared seed) and return raw step traces."""
    from .conditions import apply_condition

    out = []
    for c in CONDITIONS:
        cond_scn = apply_condition(scenario, c, gap_m, speed_mps)
        cond_scn["uid"] = f"{scenario.get('uid', 'synth')}|{c}"
        out.append(adapter.run_episode(cond_scn, sim_seed, perturbation=None))
    return out

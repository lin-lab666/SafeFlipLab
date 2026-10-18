"""Test doubles. These NEVER stand in for real smoke/pilot episodes: they
exist only for unit tests that must not consume simulation budget."""
from __future__ import annotations

import hashlib
from typing import Any, Callable

from cornercaselab.domain import Scenario

#: Deterministic fake collision rule over the conditioned scenario. Chosen so
#: unit tests see a mix of all-zero, reverse (Y00=0,Y11=1) and rescue
#: (Y00=1,Y11=0) quartets.
FAKE_GAP_THRESHOLD = 30.0
FAKE_EGO_THRESHOLD = 21.5


def fake_collision(scenario: Scenario) -> bool:
    return bool(scenario.front_gap <= FAKE_GAP_THRESHOLD or scenario.ego_speed <= FAKE_EGO_THRESHOLD)


def fake_result(scenario: Scenario, sim_seed: int) -> dict[str, Any]:
    payload = f"{scenario.uid}|{sim_seed}".encode()
    trace_hash = hashlib.sha256(payload).hexdigest()
    return {
        "ego_collision": fake_collision(scenario),
        "goal_reached": not fake_collision(scenario),
        "termination": "collision" if fake_collision(scenario) else "goal",
        "npc_collisions": 0,
        "sim_time_s": 12.5,
        "policy_steps": 62,
        "min_forward_ttc_sampled_s": 1.25,
        "reward_sum": -3.5,
        "wall_time_s": 0.01,
        "trace_sha256_rounded_9dp": trace_hash,
        "trajectory": [{"time_s": 0.0, "action": None,
                        "vehicles": [{"x": 0.0, "y": 0.0, "speed": scenario.ego_speed,
                                      "heading": 0.0, "crashed": False}]}],
    }


class FakeAdapter:
    """Drop-in replacement for ScenarioAdapter in unit tests.

    ``is_test_double = True`` is a cooperation marker read by the formal safety
    guard in ``safefliplab.experiments``: the guard refuses to drive anything
    that is *not* a test double unless an explicit human GO is supplied, so the
    full formal scheduler can be integration-tested offline without ever being
    able to start a real simulator episode by accident.
    """

    is_test_double = True

    def __init__(self, *, fail: Callable[[Scenario, int], bool] | None = None,
                 error_type: type[Exception] = RuntimeError) -> None:
        self.calls: list[tuple[Scenario, int]] = []
        self.fail = fail
        self.error_type = error_type

    def run_episode(self, scenario: Scenario, sim_seed: int) -> dict[str, Any]:
        self.calls.append((scenario, sim_seed))
        if self.fail is not None and self.fail(scenario, sim_seed):
            raise self.error_type("injected failure")
        return fake_result(scenario, sim_seed)

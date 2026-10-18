#!/usr/bin/env python3
"""Offline, synthetic demo of the four-condition quartet pipeline.

WHAT THIS IS
  A pure-Python walkthrough of the study's design shape: one legal anchor, the
  frozen interventions (front_gap +2.0 m, ego_speed -1.0 m/s), the four
  conditions (00/10/01/11), an anchor-shared perturbation, and a *toy* closing
  model that stands in for the simulator.

WHAT THIS IS NOT
  It does not import the simulator, launches **zero** episodes, writes **no**
  files, and prints **synthetic output only**. The numbers below are not
  experimental results and must not be cited as evidence for or against any
  intervention. The real (frozen, exploratory, INCONCLUSIVE) results live in
  ``reports/`` and ``v02/reports/``; see ``DATA_AVAILABILITY.md`` for the
  limits.

Run:
    python examples/offline_demo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running straight from a checkout without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cornercaselab.domain import Scenario  # noqa: E402

from safefliplab.domain import (  # noqa: E402
    GAP_INTERVENTION_M,
    SPEED_INTERVENTION_MPS,
    quartet_scenarios,
)
from safefliplab.seeds import CONDITIONS  # noqa: E402

BANNER = "SYNTHETIC OUTPUT - NOT EXPERIMENTAL RESULTS"

#: Deliberately arbitrary, deterministic "friction" shared by the four
#: conditions of one anchor. Its only purpose is to make the demo look like the
#: real design (anchor-shared perturbation), not to model anything.
SHARED_PERTURBATION_S = -0.80


def toy_min_ttc(scenario: Scenario) -> float:
    """Closing-time toy: gap / closing speed (+ shared perturbation).

    This is a pedagogical stand-in, **not** the study's endpoint. The study's
    endpoint is recomputed from full trajectories (1D, 5 Hz, constant speed,
    longitudinal only) and is itself only a proxy - not a collision
    probability.
    """
    closing = max(0.10, scenario.ego_speed - scenario.front_speed)
    return scenario.front_gap / closing + SHARED_PERTURBATION_S


def main() -> int:
    anchor = Scenario(
        ego_speed=27.0,
        front_gap=45.0,
        front_speed=25.0,
        ramp_x=110.0,
        ramp_speed=20.0,
        ramp_target_speed=30.0,
    )
    scenarios = quartet_scenarios(anchor)
    ttc = {cond: toy_min_ttc(scenarios[cond]) for cond in CONDITIONS}

    print("=" * 72)
    print(BANNER)
    print("=" * 72)
    print(f"anchor: ego_speed={anchor.ego_speed} m/s, front_gap={anchor.front_gap} m, "
          f"front_speed={anchor.front_speed} m/s")
    print(f"design: gap +{GAP_INTERVENTION_M} m, speed -{SPEED_INTERVENTION_MPS} m/s; "
          f"shared perturbation {SHARED_PERTURBATION_S:+.2f} s")
    print("-" * 72)
    for cond in CONDITIONS:
        label = {
            "00": "control        ",
            "10": "gap only       ",
            "01": "speed only     ",
            "11": "both           ",
        }[cond]
        print(f"condition {cond}  {label}  toy min-TTC = {ttc[cond]:7.2f} s")
    print("-" * 72)
    print(f"delta gap   (10-00) = {ttc['10'] - ttc['00']:+.2f} s")
    print(f"delta speed (01-00) = {ttc['01'] - ttc['00']:+.2f} s")
    print(f"delta both  (11-00) = {ttc['11'] - ttc['00']:+.2f} s")
    print(f"I_lin (11-10-01+00) = "
          f"{ttc['11'] - ttc['10'] - ttc['01'] + ttc['00']:+.2f} s")
    print("-" * 72)
    print("These numbers come from a toy formula, not from a simulator run.")
    print("Their sign and size were chosen to make the printout easy to read;")
    print("they say nothing about the real study (which reports INCONCLUSIVE).")
    print(f"{BANNER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

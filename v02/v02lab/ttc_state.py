"""TTC state model — three separated layers (proposal section 3.4).

**Layer 1** per-step state (``StepTTCState``): at each 5 Hz policy step decide
whether a forward candidate exists, and whether it is closing.

**Layer 2** episode aggregation (``EpisodeTTCCategory``): summarise one episode's
per-step states into exactly one of FINITE / CENSORED / NO_CANDIDATE / MISSING,
recording exposure and per-state counts.

**Layer 3** termination (``TerminationClass``): *why* the episode ended, kept
orthogonal to Layer 2 (a TECHNICAL_FAILURE forces Layer 2 = MISSING).

Also: quartet **pair missingness** (``PairStatus``) and the ``I_log`` **domain**
handling (``ILogStatus``) for TTC = 0 / +inf (censored) / missing.

Standards: standard library only; ``Literal``-style enums; no research default is
fabricated — ``tau_cap`` must be supplied explicitly.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from .conditions import CONDITIONS
from .schema import UnsetParameterError

# Upstream-mirrored metric constants (from cornercaselab 0.3.0 metrics), NOT
# research decisions. Kept here so the state model matches upstream semantics.
LATERAL_OVERLAP_M = 2.0
VEHICLE_LENGTH_M = 5.0


class StepTTCState(Enum):
    NORMAL_CLOSING = "NORMAL_CLOSING"   # candidate present, closing > 0 -> finite TTC
    NO_CLOSING = "NO_CLOSING"           # candidate present, closing <= 0 -> +inf
    NO_CANDIDATE = "NO_CANDIDATE"       # no forward lateral-overlapping candidate -> None


class EpisodeTTCCategory(Enum):
    FINITE = "FINITE"                   # >= 1 finite closing step
    CENSORED = "CENSORED"               # no finite step, >= 1 non-closing step
    NO_CANDIDATE = "NO_CANDIDATE"       # every step had no candidate (prior-safe)
    MISSING = "MISSING"                 # technical failure / no valid step


class TerminationClass(Enum):
    HORIZON_REACHED = "HORIZON_REACHED"
    TERMINAL_EVENT = "TERMINAL_EVENT"   # collision / offroad / goal — informative
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"  # error / interrupted


class PairStatus(Enum):
    OK = "OK"
    PAIR_MISSING = "PAIR_MISSING"
    CENSORING_AFFECTED = "CENSORING_AFFECTED"


class ILogStatus(Enum):
    DEFINED = "DEFINED"
    ZERO_TTC = "ZERO_TTC"
    CENSORED_INFINITY = "CENSORED_INFINITY"
    MISSING = "MISSING"


def step_ttc_state(*, has_candidate: bool, gap: float | None,
                   closing: float | None) -> tuple[StepTTCState, float | None]:
    """Classify one policy step. ``None != safe`` and ``None != 0.0``."""
    if not has_candidate:
        return StepTTCState.NO_CANDIDATE, None
    if closing is None:
        raise ValueError("closing must be provided when a candidate exists")
    if closing <= 0:
        return StepTTCState.NO_CLOSING, None
    if gap is None:
        raise ValueError("gap must be provided when closing > 0")
    if gap <= 0:
        return StepTTCState.NORMAL_CLOSING, 0.0
    return StepTTCState.NORMAL_CLOSING, float(gap) / float(closing)


@dataclass(frozen=True)
class EpisodeTTC:
    value: float | None
    category: EpisodeTTCCategory
    censored: bool
    n_steps_observed: int
    n_normal: int
    n_no_closing: int
    n_no_candidate: int
    termination: TerminationClass
    no_candidate_policy: str

    @property
    def is_missing(self) -> bool:
        return self.category is EpisodeTTCCategory.MISSING


def aggregate_episode(steps: Sequence[tuple[StepTTCState, float | None]], *,
                      termination: TerminationClass, tau_cap: float | None,
                      no_candidate_policy: str) -> EpisodeTTC:
    """Layer 2: summarise per-step Layer 1 states into one episode category."""
    if tau_cap is None:
        raise UnsetParameterError("tau_cap is UNSET; refusing to fabricate a censoring ceiling")
    if no_candidate_policy not in ("assign_cap", "exclude"):
        raise ValueError(f"no_candidate_policy must be assign_cap/exclude, got {no_candidate_policy!r}")

    n_normal = n_no_closing = n_no_candidate = 0
    min_val: float | None = None
    for state, value in steps:
        if state is StepTTCState.NORMAL_CLOSING:
            n_normal += 1
            if value is None:
                raise ValueError("NORMAL_CLOSING step must carry a finite value")
            min_val = value if min_val is None else min(min_val, value)
        elif state is StepTTCState.NO_CLOSING:
            n_no_closing += 1
        elif state is StepTTCState.NO_CANDIDATE:
            n_no_candidate += 1
        else:  # pragma: no cover - exhaustive enum
            raise ValueError(f"unknown step state {state!r}")
    n = len(steps)

    if termination is TerminationClass.TECHNICAL_FAILURE or n == 0:
        return EpisodeTTC(None, EpisodeTTCCategory.MISSING, False, n, n_normal,
                          n_no_closing, n_no_candidate, termination, no_candidate_policy)

    if n_normal > 0:
        return EpisodeTTC(min_val, EpisodeTTCCategory.FINITE,
                          censored=(n_no_closing + n_no_candidate) > 0,
                          n_steps_observed=n, n_normal=n_normal,
                          n_no_closing=n_no_closing, n_no_candidate=n_no_candidate,
                          termination=termination, no_candidate_policy=no_candidate_policy)
    if n_no_closing > 0:
        return EpisodeTTC(tau_cap, EpisodeTTCCategory.CENSORED, True, n, n_normal,
                          n_no_closing, n_no_candidate, termination, no_candidate_policy)
    # every observed step had no candidate -> prior-safe category
    value = tau_cap if no_candidate_policy == "assign_cap" else None
    return EpisodeTTC(value, EpisodeTTCCategory.NO_CANDIDATE, True, n, n_normal,
                      n_no_closing, n_no_candidate, termination, no_candidate_policy)


def termination_from_exit(exit_status: str, termination: str = "") -> TerminationClass:
    """Map (exit_status, termination label) to a TerminationClass."""
    if exit_status in ("error", "interrupted"):
        return TerminationClass.TECHNICAL_FAILURE
    if exit_status == "completed" and termination in ("collision", "offroad", "goal"):
        return TerminationClass.TERMINAL_EVENT
    return TerminationClass.HORIZON_REACHED


def quartet_pair_status(episodes: Mapping[str, EpisodeTTC]) -> PairStatus:
    """Pair missingness of one quartet (all four conditions required)."""
    for c in CONDITIONS:
        ep = episodes.get(c)
        if ep is None or ep.category is EpisodeTTCCategory.MISSING:
            return PairStatus.PAIR_MISSING
    for c in CONDITIONS:
        if episodes[c].category in (EpisodeTTCCategory.CENSORED, EpisodeTTCCategory.NO_CANDIDATE):
            return PairStatus.CENSORING_AFFECTED
    return PairStatus.OK


@dataclass(frozen=True)
class ILogResult:
    status: ILogStatus
    value: float | None          # pure I_log (None when not DEFINED)
    floored_value: float | None  # only when a floor was supplied AND status == ZERO_TTC
    floor: float | None
    reason: str


def _numeric(entry: Any) -> tuple[float | None, bool]:
    """Return (value, censored) from an EpisodeTTC or a plain number."""
    if isinstance(entry, EpisodeTTC):
        if entry.category is EpisodeTTCCategory.MISSING:
            return None, False
        censored = entry.category in (EpisodeTTCCategory.CENSORED, EpisodeTTCCategory.NO_CANDIDATE)
        return entry.value, censored
    if entry is None:
        return None, False
    return float(entry), False


def log_interaction(values: Mapping[str, Any], *, floor: float | None = None) -> ILogResult:
    """``I_log = log M11 - log M10 - log M01 + log M00`` with honest domain handling.

    Undefined (reason code) when any comparison quantity is missing, censored
    (+inf) or non-positive (TTC = 0). Priority: MISSING > CENSORED_INFINITY >
    ZERO_TTC > DEFINED. A floored value is produced only for ZERO_TTC **and only
    when an explicit floor is supplied** — never as a silent default.
    """
    nums: dict[str, float | None] = {}
    censored_any = False
    for c in CONDITIONS:
        v, cens = _numeric(values.get(c))
        nums[c] = v
        censored_any = censored_any or cens
    if any(nums[c] is None for c in CONDITIONS):
        return ILogResult(ILogStatus.MISSING, None, None, floor,
                          "at least one condition is missing")
    if censored_any:
        return ILogResult(ILogStatus.CENSORED_INFINITY, None, None, floor,
                          "at least one condition is right-censored (+inf)")
    vals = {c: float(nums[c]) for c in CONDITIONS}  # type: ignore[arg-type]
    if any(vals[c] <= 0.0 for c in CONDITIONS):
        floored = None
        if floor is not None and floor > 0:
            floored = (math.log(max(vals["11"], floor)) - math.log(max(vals["10"], floor))
                       - math.log(max(vals["01"], floor)) + math.log(max(vals["00"], floor)))
        return ILogResult(ILogStatus.ZERO_TTC, None, floored, floor,
                          "at least one condition has TTC <= 0 (log undefined)")
    i_log = (math.log(vals["11"]) - math.log(vals["10"])
             - math.log(vals["01"]) + math.log(vals["00"]))
    return ILogResult(ILogStatus.DEFINED, i_log, None, floor, "defined")

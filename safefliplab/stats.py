"""Paired quartet statistics.

All quantities are computed from *real* recorded Y values only. A quartet
contributes only when all four conditions completed; incomplete quartets are
excluded from quartet-level statistics but their episodes remain billed.

Primary metrics (per quartet, then averaged over quartets):

* ``delta_both   = mean(Y11 - Y00)``
* ``delta_gap    = mean(Y10 - Y00)``
* ``delta_speed  = mean(Y01 - Y00)``
* ``interaction  = mean(Y11 - Y10 - Y01 + Y00)``  (risk-difference scale)

Secondary counts:

* ``reverse_pairs = count(Y00=0, Y11=1)``
* ``rescue_pairs  = count(Y00=1, Y11=0)``

A single reverse pair is never called a "stable reversal".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .seeds import CONDITIONS


@dataclass(frozen=True)
class QuartetMetrics:
    delta_both: float
    delta_gap: float
    delta_speed: float
    interaction: float
    reverse: int
    rescue: int


def quartet_metrics(y: Mapping[str, int]) -> QuartetMetrics:
    """Metrics of one complete quartet. ``y`` must contain all four Y values."""
    missing = [c for c in CONDITIONS if c not in y]
    if missing:
        raise ValueError(f"incomplete quartet, missing conditions {missing}")
    for c in CONDITIONS:
        if y[c] not in (0, 1):
            raise ValueError(f"Y[{c}] must be 0 or 1, got {y[c]!r}")
    y00, y10, y01, y11 = (int(y[c]) for c in CONDITIONS)
    return QuartetMetrics(
        delta_both=float(y11 - y00),
        delta_gap=float(y10 - y00),
        delta_speed=float(y01 - y00),
        interaction=float(y11 - y10 - y01 + y00),
        reverse=1 if (y00 == 0 and y11 == 1) else 0,
        rescue=1 if (y00 == 1 and y11 == 0) else 0,
    )


@dataclass(frozen=True)
class AggregateMetrics:
    n_quartets: int
    mean_delta_both: float | None
    mean_delta_gap: float | None
    mean_delta_speed: float | None
    mean_interaction: float | None
    reverse_pairs: int
    rescue_pairs: int
    collision_rate: dict[str, float | None]  # per condition, over complete quartets


def aggregate(quartets: Sequence[Mapping[str, int]]) -> AggregateMetrics:
    """Aggregate over complete quartets (each a full Y00/Y10/Y01/Y11 mapping)."""
    complete = []
    for q in quartets:
        if all(c in q for c in CONDITIONS):
            complete.append(q)
    n = len(complete)
    if n == 0:
        return AggregateMetrics(
            n_quartets=0,
            mean_delta_both=None,
            mean_delta_gap=None,
            mean_delta_speed=None,
            mean_interaction=None,
            reverse_pairs=0,
            rescue_pairs=0,
            collision_rate={c: None for c in CONDITIONS},
        )
    per = [quartet_metrics(q) for q in complete]
    return AggregateMetrics(
        n_quartets=n,
        mean_delta_both=sum(m.delta_both for m in per) / n,
        mean_delta_gap=sum(m.delta_gap for m in per) / n,
        mean_delta_speed=sum(m.delta_speed for m in per) / n,
        mean_interaction=sum(m.interaction for m in per) / n,
        reverse_pairs=sum(m.reverse for m in per),
        rescue_pairs=sum(m.rescue for m in per),
        collision_rate={
            c: sum(int(q[c]) for q in complete) / n for c in CONDITIONS
        },
    )


def paired_delta_series(quartets: Sequence[Mapping[str, int]], condition: str) -> list[float]:
    """Per-quartet Y(condition) - Y(00); only complete quartets."""
    if condition not in ("10", "01", "11"):
        raise ValueError(f"condition must be 10/01/11, got {condition!r}")
    out = []
    for q in quartets:
        if all(c in q for c in CONDITIONS):
            out.append(float(q[condition] - q["00"]))
    return out


def summarise_conditions(quartets: Iterable[Mapping[str, int]]) -> dict[str, float | None]:
    """Collision rate per condition over complete quartets."""
    return aggregate(list(quartets)).collision_rate

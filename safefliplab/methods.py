"""The two budgeted discovery methods and the independent held-out audit.

Formal design (frozen, docs/PROTOCOL_V01.md): per ``method x master_seed``
exactly 800 episode slots = 400 discovery + 400 audit.

``WideExplore``
    discovery: 100 distinct anchors x 1 quartet (400 episodes);
    nominate top-5 by discovery ``delta_both`` desc, tie-break
    (first_seen, anchor_id); audit: 5 nominees x 20 fresh-seed quartets.

``VerifyFirst``
    discovery stage 1: first 40 anchors x 1 quartet (160 episodes);
    freeze 20 anchors by ``delta_both`` desc, then the other two
    single-factor deltas, then (first_seen, anchor_id); each of the 20 gets
    3 fresh repetition quartets (240 episodes); discovery = 400;
    nominate top-5 from all 40 discovered anchors by the frozen rule
    (mean delta_both desc, valid quartets desc, first_seen, anchor_id);
    audit: 5 nominees x 20 fresh-seed quartets.

Audit isolation: nomination happens before any audit episode is launched;
audit quartets use fresh seeds (stream tag ``audit``) and can never feed
back into nomination.

This module contains the pure planning/scoring logic only; it never touches
the simulator. Execution lives in ``safefliplab.experiments``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .seeds import CONDITIONS

METHOD_WIDE = "WideExplore"
METHOD_VERIFY = "VerifyFirst"
METHODS = (METHOD_WIDE, METHOD_VERIFY)

# Frozen formal sizes (per method x master seed).
FORMAL_BUDGET = 800
FORMAL_DISCOVERY_BUDGET = 400
FORMAL_AUDIT_BUDGET = 400
WIDE_DISCOVERY_ANCHORS = 100
WIDE_NOMINEES = 5
VERIFY_STAGE1_ANCHORS = 40
VERIFY_SELECTED = 20
VERIFY_EXTRA_QUARTETS = 3
AUDIT_QUARTETS_PER_NOMINEE = 20

# Pilot scaling (PROPOSED, frozen in configs/dev_v01.json): same structure,
# smaller counts, exact 240-episode total for both methods.
PILOT_BUDGET_PER_METHOD = 120
PILOT_WIDE_DISCOVERY_ANCHORS = 15
PILOT_WIDE_NOMINEES = 3
PILOT_AUDIT_QUARTETS = 5
PILOT_VERIFY_STAGE1_ANCHORS = 6
PILOT_VERIFY_SELECTED = 3


class MethodError(RuntimeError):
    pass


@dataclass
class AnchorRecord:
    """Discovery observations for one anchor."""

    anchor_id: str
    index: int  # first_seen order in the shared stream
    quartets: list[dict[str, int]] = field(default_factory=list)

    @property
    def valid_n(self) -> int:
        return len(self.quartets)

    def mean_delta(self, condition: str) -> float:
        from .stats import paired_delta_series

        series = paired_delta_series(self.quartets, condition)
        if not series:
            raise MethodError(f"anchor {self.anchor_id} has no complete quartet")
        return sum(series) / len(series)

    def to_dict(self) -> dict[str, Any]:
        from .stats import aggregate

        agg = aggregate(self.quartets)
        return {
            "anchor_id": self.anchor_id,
            "index": self.index,
            "valid_n": self.valid_n,
            "quartets": [dict(q) for q in self.quartets],
            "mean_delta_both": agg.mean_delta_both,
            "mean_delta_gap": agg.mean_delta_gap,
            "mean_delta_speed": agg.mean_delta_speed,
            "mean_interaction": agg.mean_interaction,
            "reverse_pairs": agg.reverse_pairs,
            "rescue_pairs": agg.rescue_pairs,
        }


def _require_complete(q: Mapping[str, int], where: str) -> None:
    missing = [c for c in CONDITIONS if c not in q]
    if missing:
        raise MethodError(f"{where}: incomplete quartet, missing {missing}")
    for c in CONDITIONS:
        if q[c] not in (0, 1):
            raise MethodError(f"{where}: Y[{c}] must be 0/1, got {q[c]!r}")


def add_quartet(record: AnchorRecord, y: Mapping[str, int]) -> None:
    _require_complete(y, f"anchor {record.anchor_id}")
    record.quartets.append({c: int(y[c]) for c in CONDITIONS})


# -- frozen sort keys ------------------------------------------------------
def wide_nomination_key(record: AnchorRecord) -> tuple:
    """WideExplore: delta_both desc, then first_seen, then anchor_id."""
    return (-record.mean_delta("11"), record.index, record.anchor_id)


def verify_select_key(record: AnchorRecord) -> tuple:
    """VerifyFirst stage-1 selection: delta_both, then the other two
    single-factor deltas (PROPOSED order: gap, speed), then first_seen,
    anchor_id — all descending for the risk deltas."""
    return (
        -record.mean_delta("11"),
        -record.mean_delta("10"),
        -record.mean_delta("01"),
        record.index,
        record.anchor_id,
    )


def verify_final_key(record: AnchorRecord) -> tuple:
    """VerifyFirst final nomination (PROPOSED frozen order): mean delta_both
    desc, valid quartets desc, first_seen, anchor_id."""
    return (-record.mean_delta("11"), -record.valid_n, record.index, record.anchor_id)


def select_top(records: Sequence[AnchorRecord], key, k: int) -> list[AnchorRecord]:
    """Deterministic top-k with the frozen tie-break key."""
    eligible = [r for r in records if r.valid_n > 0]
    ordered = sorted(eligible, key=key)
    if k > len(ordered):
        raise MethodError(f"cannot nominate {k} from {len(ordered)} eligible anchors")
    return ordered[:k]


# -- plan construction (pure) ----------------------------------------------
@dataclass(frozen=True)
class QuartetJob:
    method: str
    anchor_index: int
    repetition: int
    stream: str  # discovery | audit
    purpose: str  # wide_discovery | verify_stage1 | verify_stage2 | audit


def wide_discovery_jobs(n_anchors: int) -> list[QuartetJob]:
    return [
        QuartetJob(METHOD_WIDE, i, 0, "discovery", "wide_discovery")
        for i in range(n_anchors)
    ]


def verify_stage1_jobs(n_anchors: int) -> list[QuartetJob]:
    return [
        QuartetJob(METHOD_VERIFY, i, 0, "discovery", "verify_stage1")
        for i in range(n_anchors)
    ]


def verify_stage2_jobs(selected_indices: Sequence[int], extra: int) -> list[QuartetJob]:
    jobs = []
    for i in selected_indices:
        for rep in range(1, extra + 1):
            jobs.append(QuartetJob(METHOD_VERIFY, i, rep, "discovery", "verify_stage2"))
    return jobs


def audit_jobs(method: str, nominee_indices: Sequence[int], quartets: int) -> list[QuartetJob]:
    return [
        QuartetJob(method, i, rep, "audit", "audit")
        for i in nominee_indices
        for rep in range(quartets)
    ]


def budget_check(name: str, planned_jobs: Sequence[QuartetJob], cap: int) -> None:
    episodes = 4 * len(planned_jobs)
    if episodes > cap:
        raise MethodError(f"{name}: plan needs {episodes} episodes, cap is {cap}")
    if episodes != cap:
        raise MethodError(
            f"{name}: plan must use the budget exactly ({episodes} != {cap}); "
            "partial plans are not allowed for a completed phase"
        )


def validate_formal_plans() -> dict[str, int]:
    """Sanity check that the frozen formal plans close exactly at 800/800."""
    wide = wide_discovery_jobs(WIDE_DISCOVERY_ANCHORS)
    budget_check("WideExplore discovery", wide, FORMAL_DISCOVERY_BUDGET)
    verify1 = verify_stage1_jobs(VERIFY_STAGE1_ANCHORS)
    budget_check("VerifyFirst stage1", verify1, 160)
    verify2 = verify_stage2_jobs(list(range(VERIFY_SELECTED)), VERIFY_EXTRA_QUARTETS)
    budget_check("VerifyFirst stage2", verify2, 240)
    audit = audit_jobs(METHOD_WIDE, list(range(WIDE_NOMINEES)), AUDIT_QUARTETS_PER_NOMINEE)
    budget_check("WideExplore audit", audit, FORMAL_AUDIT_BUDGET)
    audit_v = audit_jobs(METHOD_VERIFY, list(range(WIDE_NOMINEES)), AUDIT_QUARTETS_PER_NOMINEE)
    budget_check("VerifyFirst audit", audit_v, FORMAL_AUDIT_BUDGET)
    total = 4 * (len(wide) + len(verify1) + len(verify2) + len(audit) + len(audit_v))
    if total != 2 * FORMAL_BUDGET:
        raise MethodError(f"formal total {total} != {2 * FORMAL_BUDGET}")
    return {
        "WideExplore": 4 * (len(wide) + len(audit)),
        "VerifyFirst": 4 * (len(verify1) + len(verify2) + len(audit_v)),
    }

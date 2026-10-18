"""V02 nomination rules for the auxiliary method comparison.

Both methods nominate from the **same** discovery quartets; only the allocation
rule differs. The objective is reversal-seeking: a good nomination is an anchor
where the joint intervention *reduces* the safety margin (``delta_both < 0``),
so the ranking prefers the most negative ``delta_both``.

Rules (frozen in ``configs/v02_frozen_v1.json`` semantics; recorded in
``docs/AUTONOMOUS_DECISIONS.md`` D34):

* **WideExplore** — one quartet per anchor over a broad stream, then rank by the
  single-quartet ``delta_both`` (ascending), tie-break ``(first_seen, anchor_id)``.
* **VerifyFirst** — uses every repetition it verified, ranks by the anchor-level
  mean ``delta_both`` (ascending), then by the number of usable quartets
  (descending, i.e. it prefers anchors it actually re-verified), then
  ``(first_seen, anchor_id)``.

An anchor with **no usable quartet** is never scored and never nominated — it is
not given a virtual zero.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

METHOD_WIDE = "WideExplore"
METHOD_VERIFY = "VerifyFirst"
METHODS = (METHOD_WIDE, METHOD_VERIFY)


def usable_delta_both(quartets: Sequence[Mapping[str, Any]]) -> tuple[float | None, int]:
    """(mean delta_both over usable quartets, number of usable quartets)."""
    vals = [float(q["delta_both"]) for q in quartets
            if q.get("usable") and q.get("delta_both") is not None]
    if not vals:
        return None, 0
    return sum(vals) / len(vals), len(vals)


def wide_key(quartets: Sequence[Mapping[str, Any]]) -> tuple | None:
    mean, n = usable_delta_both(quartets)
    if n == 0 or mean is None:
        return None
    anchor_index = int(quartets[0]["anchor_index"])
    return (mean, anchor_index, str(quartets[0]["anchor_id"]))


def verify_key(quartets: Sequence[Mapping[str, Any]]) -> tuple | None:
    mean, n = usable_delta_both(quartets)
    if n == 0 or mean is None:
        return None
    anchor_index = int(quartets[0]["anchor_index"])
    return (mean, -n, anchor_index, str(quartets[0]["anchor_id"]))


def nomination_key(quartets: Sequence[Mapping[str, Any]]) -> tuple | None:
    """Default key used by :func:`select_top` (VerifyFirst semantics)."""
    return verify_key(quartets)


def select_top(pool: Mapping[int, Sequence[Mapping[str, Any]]],
               key_fn: Callable[[Sequence[Mapping[str, Any]]], tuple | None],
               k: int) -> list[int]:
    """Top-``k`` anchor indices; anchors without a usable quartet are excluded."""
    scored = []
    for ai, quartets in pool.items():
        key = key_fn(quartets)
        if key is None:
            continue
        scored.append((key, int(ai)))
    scored.sort(key=lambda t: t[0])
    return [ai for _, ai in scored[:k]]


def precision_at_k(audit_quartets: Sequence[Mapping[str, Any]], *, delta_eq_s: float
                   ) -> dict[str, Any]:
    """Auxiliary nomination-quality indicator Q1 on the independent audit.

    ``R_a = 1{anchor-level audit mean delta_both < -delta_eq}``; precision@k is the
    share of nominees that reverse. Anchors whose audit quartet is unusable are
    reported separately and are NOT silently counted as non-reversing.
    """
    if not audit_quartets:
        return {"k": 0, "n_reversal": 0, "precision_at_k": None,
                "n_unusable": 0, "per_anchor": []}
    per: list[dict[str, Any]] = []
    usable = 0
    reversals = 0
    for q in audit_quartets:
        if not q.get("usable") or q.get("delta_both") is None:
            per.append({"anchor_id": q["anchor_id"], "usable": False,
                        "delta_both": None, "reversal": None})
            continue
        usable += 1
        rev = float(q["delta_both"]) < -float(delta_eq_s)
        reversals += int(rev)
        per.append({"anchor_id": q["anchor_id"], "usable": True,
                    "delta_both": float(q["delta_both"]), "reversal": bool(rev)})
    return {"k": usable, "n_nominated": len(audit_quartets), "n_reversal": reversals,
            "precision_at_k": (reversals / usable) if usable else None,
            "n_unusable": len(audit_quartets) - usable, "per_anchor": per}

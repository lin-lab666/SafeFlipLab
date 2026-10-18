"""Frozen formal research protocol + config drift validation.

The formal study design (budgets, method plans, controller policy, simulator
cadence) is frozen in ``configs/formal_v01.json``. That file is a *research
artifact*: an accidental edit (a changed budget, a reordered seed, a tweaked
simulator cadence) must never slip into a real 12,800-episode run unnoticed.

This module:

* declares the frozen design as code (``FROZEN_DESIGN``);
* derives a stable ``protocol_fingerprint`` over that design;
* validates a formal config against the frozen design, collecting *every*
  problem at once — seed count, seed uniqueness, frozen seed values and order,
  frozen budget / plan / simulator values, and the protocol fingerprint.

It performs no simulation and never imports the simulator.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping

from .seeds import (
    FORMAL_MASTER_SEED_COUNT,
    PROTOCOL_ID,
    canonical_json,
    formal_master_seeds,
)

__all__ = [
    "PROTOCOL_ID",
    "FROZEN_DESIGN",
    "FROZEN_RULES",
    "FormalConfigError",
    "frozen_protocol_fingerprint",
    "formal_config_fingerprint",
    "validate_formal_config",
    "validate_method_rules",
]

FROZEN_CONTROLLER_POLICY = "boundary"

# -- frozen research rules -------------------------------------------------
# The human-readable rule strings frozen in configs/formal_v01.json. They are
# part of FROZEN_DESIGN, so *any* edit to a rule description in the config is a
# frozen-design drift (and is refused). ``validate_method_rules`` additionally
# cross-checks these declared rules against the actual sort-key functions in
# ``safefliplab.methods`` — so changing either the description OR the
# implementation without the other is caught. (D4/D5/D6 remain PROPOSED: these
# strings record the current proposed rules; they are not a hidden approval.)
WIDE_NOMINATION_RULE = "discovery delta_both desc, tie-break (first_seen, anchor_id)"
VERIFY_SELECTION_RULE = ("delta_both desc, then delta_gap desc, then delta_speed desc, "
                         "then (first_seen, anchor_id); frozen after stage 1")
VERIFY_NOMINATION_POOL = "all stage-1 discovered anchors"
VERIFY_NOMINATION_RULE = ("PROPOSED: mean delta_both desc, valid quartets desc, "
                          "(first_seen, anchor_id); requires human sign-off before formal")

#: Structured form of the frozen rules: an ordered list of (field, direction).
#: This is the machine-checkable counterpart of the descriptions above and is
#: compared against ``safefliplab.methods``' key functions by
#: :func:`validate_method_rules`.
FROZEN_RULES: dict[str, dict[str, Any]] = {
    "wide_nomination": {
        "description": WIDE_NOMINATION_RULE,
        "methods_key": "wide_nomination_key",
        "key": [
            ("mean_delta_both", "desc"),
            ("first_seen", "asc"),
            ("anchor_id", "asc"),
        ],
    },
    "verify_selection": {
        "description": VERIFY_SELECTION_RULE,
        "methods_key": "verify_select_key",
        "key": [
            ("mean_delta_both", "desc"),
            ("mean_delta_gap", "desc"),
            ("mean_delta_speed", "desc"),
            ("first_seen", "asc"),
            ("anchor_id", "asc"),
        ],
    },
    "verify_final_nomination": {
        "description": VERIFY_NOMINATION_RULE,
        "methods_key": "verify_final_key",
        "key": [
            ("mean_delta_both", "desc"),
            ("valid_quartets", "desc"),
            ("first_seen", "asc"),
            ("anchor_id", "asc"),
        ],
    },
}

#: The rule names whose descriptions are frozen into the config sections.
_CONFIG_RULE_FIELDS = {
    "wide_explore": ("nomination_rule", WIDE_NOMINATION_RULE),
    "verify_first": ("selection_rule", VERIFY_SELECTION_RULE),
}

#: The frozen design, mirroring configs/formal_v01.json exactly. Any divergence
#: in a config is a protocol drift and is refused by ``validate_formal_config``.
FROZEN_DESIGN: dict[str, Any] = {
    "protocol": PROTOCOL_ID,
    "controller_policy": FROZEN_CONTROLLER_POLICY,
    "simulator": {"horizon_s": 25.0, "simulation_hz": 15, "policy_hz": 5},
    "budget": {
        "episodes_per_method_seed": 800,
        "discovery_episodes": 400,
        "audit_episodes": 400,
        "methods": 2,
        "master_seeds": 8,
        "total_episodes": 12800,
    },
    "wide_explore": {
        "discovery_anchors": 100,
        "discovery_quartets_per_anchor": 1,
        "nominees": 5,
        "nomination_rule": WIDE_NOMINATION_RULE,
        "audit_quartets_per_nominee": 20,
    },
    "verify_first": {
        "stage1_anchors": 40,
        "stage1_quartets_per_anchor": 1,
        "selected": 20,
        "selection_rule": VERIFY_SELECTION_RULE,
        "extra_quartets_per_selected": 3,
        "nominees": 5,
        "nomination_pool": VERIFY_NOMINATION_POOL,
        "nomination_rule": VERIFY_NOMINATION_RULE,
        "audit_quartets_per_nominee": 20,
    },
}

_WIDE_KEYS = tuple(FROZEN_DESIGN["wide_explore"])
_VERIFY_KEYS = tuple(FROZEN_DESIGN["verify_first"])


class FormalConfigError(ValueError):
    """Raised when a formal config deviates from the frozen research design."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = list(issues)
        super().__init__("formal config rejected: " + "; ".join(self.issues))


def _subset(value: Any, keys: tuple[str, ...]) -> Any:
    if not isinstance(value, Mapping):
        return value
    return {k: value.get(k) for k in keys}


def _design_payload(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The design-defining subset of a config (same shape as ``FROZEN_DESIGN``)."""
    return {
        "protocol": cfg.get("protocol"),
        "controller_policy": cfg.get("controller_policy"),
        "simulator": cfg.get("simulator"),
        "budget": cfg.get("budget"),
        "wide_explore": _subset(cfg.get("wide_explore"), _WIDE_KEYS),
        "verify_first": _subset(cfg.get("verify_first"), _VERIFY_KEYS),
    }


def frozen_protocol_fingerprint() -> str:
    """SHA-256 over the frozen design (dict keys canonicalised, so stable)."""
    return hashlib.sha256(canonical_json(FROZEN_DESIGN).encode("utf-8")).hexdigest()


def formal_config_fingerprint(cfg: Mapping[str, Any]) -> str:
    """SHA-256 over a config's design fields (same shape as the frozen one)."""
    return hashlib.sha256(canonical_json(_design_payload(cfg)).encode("utf-8")).hexdigest()


def _reference_rule_key(spec: list[tuple[str, str]], record: Any) -> tuple:
    """Compute the sort key a declared rule implies, from an AnchorRecord."""
    parts: list[Any] = []
    for field, direction in spec:
        if field == "mean_delta_both":
            value: Any = record.mean_delta("11")
        elif field == "mean_delta_gap":
            value = record.mean_delta("10")
        elif field == "mean_delta_speed":
            value = record.mean_delta("01")
        elif field == "first_seen":
            value = record.index
        elif field == "anchor_id":
            value = record.anchor_id
        elif field == "valid_quartets":
            value = record.valid_n
        else:  # pragma: no cover - guarded by the frozen spec
            raise ValueError(f"unknown rule field {field!r}")
        parts.append(-value if direction == "desc" else value)
    return tuple(parts)


def _rule_battery() -> list[Any]:
    """Synthetic AnchorRecords exercising every rule component / tie-break.

    Built without touching the simulator. Distinct delta components, indices and
    anchor ids make any swapped/relabelled key component change the tuple, so a
    description/implementation drift is detected by simple equality.
    """
    from .methods import AnchorRecord, add_quartet

    def rec(aid: str, index: int, quartets: list[dict[str, int]]):
        r = AnchorRecord(anchor_id=aid, index=index)
        for y in quartets:
            add_quartet(r, y)
        return r

    q_high = {"00": 0, "10": 0, "01": 0, "11": 1}
    q_gap = {"00": 0, "10": 1, "01": 0, "11": 0}
    q_speed = {"00": 0, "10": 0, "01": 1, "11": 0}
    q_low = {"00": 1, "10": 0, "01": 0, "11": 0}
    q_both = {"00": 0, "10": 1, "01": 1, "11": 1}
    return [
        rec("anchor-0000", 0, [q_high]),
        rec("anchor-0001", 1, [q_both, q_low]),
        rec("anchor-0002", 2, [q_speed]),
        rec("anchor-0003", 3, [q_low]),
        rec("anchor-0005", 2, [q_high, q_high]),   # same index as 0002, different aid
        rec("anchor-0009", 5, [q_gap]),
    ]


def validate_method_rules() -> list[str]:
    """Cross-check the declared rules against ``safefliplab.methods``.

    Returns a list of issue strings (empty when consistent). This is what makes
    "edit the rule description only" (or "edit the sort key only") fail loudly:
    the declared spec and the actual key function must produce identical keys on
    a battery of records. Pure and simulator-free.
    """
    from . import methods

    issues: list[str] = []
    battery = _rule_battery()
    for rule_name, rule in FROZEN_RULES.items():
        fn_name = rule["methods_key"]
        fn = getattr(methods, fn_name, None)
        if fn is None:
            issues.append(f"rule {rule_name!r}: methods.{fn_name} is missing")
            continue
        for record in battery:
            try:
                actual = fn(record)
            except Exception as exc:  # pragma: no cover - defensive
                issues.append(f"rule {rule_name!r}: methods.{fn_name} raised {exc!r}")
                break
            expected = _reference_rule_key(rule["key"], record)
            if actual != expected:
                issues.append(
                    f"rule {rule_name!r} drift: methods.{fn_name} gives {actual!r} but the "
                    f"declared rule implies {expected!r}")
                break
    return issues


def validate_formal_config(cfg: Mapping[str, Any], *, strict_design: bool = True,
                           expected_master_seed_count: int | None = None) -> dict[str, Any]:
    """Validate a formal config against the frozen research design.

    Always enforced (even in non-strict / scaled-test mode):

    * ``formal_master_seeds`` is a list of plain ints;
    * its length equals ``expected_master_seed_count`` (default: the frozen 8);
    * the seeds are **unique**.

    Additionally enforced when ``strict_design`` is True (the real run path):

    * ``protocol`` == ``SafeFlipLab-v01`` and ``controller_policy`` == ``boundary``;
    * simulator cadence, budget block and method plan sizes equal the frozen values;
    * the seed list equals the frozen SHA-256 derivation **in the frozen order**;
    * if the config declares ``protocol_fingerprint`` it must match the frozen one.

    Returns ``{"valid", "strict", "fingerprint", "seeds"}``; raises
    :class:`FormalConfigError` listing every problem otherwise.
    """
    issues: list[str] = []
    count = (expected_master_seed_count if expected_master_seed_count is not None
             else FORMAL_MASTER_SEED_COUNT)

    seeds = cfg.get("formal_master_seeds")
    if not isinstance(seeds, list):
        issues.append("formal_master_seeds must be a list")
        seeds = []
    else:
        if len(seeds) != count:
            issues.append(f"expected {count} formal master seeds, got {len(seeds)}")
        if any(isinstance(s, bool) or not isinstance(s, int) for s in seeds):
            issues.append("formal_master_seeds must be plain integers")
        if len(set(seeds)) != len(seeds):
            issues.append("formal_master_seeds must be unique")

    if strict_design:
        if cfg.get("protocol") != PROTOCOL_ID:
            issues.append(f"protocol must be {PROTOCOL_ID!r}, got {cfg.get('protocol')!r}")
        payload = _design_payload(cfg)
        for section, frozen in FROZEN_DESIGN.items():
            if payload.get(section) != frozen:
                issues.append(f"frozen design drift in {section!r}")
        if isinstance(seeds, list) and seeds != formal_master_seeds():
            issues.append(
                "formal_master_seeds must equal the frozen SHA-256 derivation "
                "(exact values and order)")
        declared_fp = cfg.get("protocol_fingerprint")
        if declared_fp is not None and declared_fp != frozen_protocol_fingerprint():
            issues.append("declared protocol_fingerprint does not match the frozen design")

    # Always enforced (strict and non-strict): the declared research rules must
    # match the actual implementation in safefliplab.methods. This is what makes
    # an "edited description but unchanged code" (or the reverse) fail loudly.
    issues.extend(validate_method_rules())

    if issues:
        raise FormalConfigError(issues)
    return {
        "valid": True,
        "strict": strict_design,
        "fingerprint": formal_config_fingerprint(cfg),
        "seeds": list(seeds),
    }

"""Config schema validation that forces every research parameter to be explicit.

Design rule (V02 proposal §7.2 / §8.3.1): a research parameter must never be
silently defaulted. Every parameter node therefore carries an explicit
``status`` in ``{PROPOSED, FROZEN, UNSET}`` and a ``value``:

* ``UNSET``  -> ``value`` MUST be ``null`` (the parameter is not decided yet);
* ``PROPOSED`` / ``FROZEN`` -> ``value`` MUST be present and type-correct.

Taking the value of an UNSET (or non-FROZEN, when frozen is required) parameter
raises :class:`UnsetParameterError` instead of returning a fabricated default.

Standard library only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STATUS_VALUES = ("PROPOSED", "FROZEN", "UNSET")
_TYPE_CHECKS = {
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "string": lambda v: isinstance(v, str),
    "bool": lambda v: isinstance(v, bool),
    "list": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


class SchemaError(ValueError):
    """Raised when a config violates the schema (structural)."""


class UnsetParameterError(RuntimeError):
    """Raised when an UNSET (or not-yet-FROZEN) parameter is taken."""


def load_json(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _validate_parameter(name: str, spec: dict[str, Any], node: Any) -> list[str]:
    problems: list[str] = []
    if not isinstance(node, dict):
        return [f"parameter {name!r}: node must be an object with status/value"]
    if "status" not in node:
        problems.append(f"parameter {name!r}: missing explicit 'status' (no arbitrary defaults allowed)")
        return problems
    status = node["status"]
    if status not in STATUS_VALUES:
        problems.append(f"parameter {name!r}: status {status!r} not in {STATUS_VALUES}")
        return problems
    if "value" not in node:
        problems.append(f"parameter {name!r}: missing 'value' key")
        return problems
    value = node["value"]
    if status == "UNSET":
        if value is not None:
            problems.append(f"parameter {name!r}: status UNSET requires value=null, got {value!r}")
        return problems
    # PROPOSED / FROZEN -> value required and type-checked
    if value is None:
        problems.append(f"parameter {name!r}: status {status} requires a non-null value")
        return problems
    decl = spec.get("type", "object")
    check = _TYPE_CHECKS.get(decl)
    if check is None:
        problems.append(f"parameter {name!r}: unknown schema type {decl!r}")
    elif not check(value):
        problems.append(f"parameter {name!r}: value {value!r} is not of declared type {decl!r}")
    if "allowed" in spec and value not in spec["allowed"]:
        problems.append(f"parameter {name!r}: value {value!r} not in allowed {spec['allowed']!r}")
    return problems


def validate_config(config: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Return a list of violations (empty list == valid). Strict on extras."""
    problems: list[str] = []
    params_spec = schema.get("parameters")
    if not isinstance(params_spec, dict):
        return ["schema: missing 'parameters' object"]
    node_params = config.get("parameters")
    if not isinstance(node_params, dict):
        return ["config: missing 'parameters' object"]
    for name, spec in params_spec.items():
        if name not in node_params:
            problems.append(f"parameter {name!r}: missing from config (schema requires it)")
            continue
        problems.extend(_validate_parameter(name, spec, node_params[name]))
    for name in node_params:
        if name not in params_spec:
            problems.append(f"parameter {name!r}: present in config but absent from schema "
                            "(strict mode refuses undeclared parameters)")
    return problems


def require_valid(config: dict[str, Any], schema: dict[str, Any]) -> None:
    problems = validate_config(config, schema)
    if problems:
        raise SchemaError("; ".join(problems))


def get_node(config: dict[str, Any], name: str) -> dict[str, Any]:
    node = config.get("parameters", {}).get(name)
    if node is None:
        raise SchemaError(f"parameter {name!r} is not declared in the config")
    return node


def resolve(config: dict[str, Any], name: str) -> Any:
    """Return the value of a parameter regardless of status (raises if UNSET)."""
    node = get_node(config, name)
    if node.get("status") == "UNSET":
        raise UnsetParameterError(
            f"parameter {name!r} is UNSET; refusing to fabricate a default. "
            f"note={node.get('note', '')!r}")
    if node.get("value") is None:
        raise UnsetParameterError(f"parameter {name!r} has no value; refusing to default")
    return node["value"]


def require_frozen(config: dict[str, Any], name: str) -> Any:
    """Return a parameter value only if it is FROZEN."""
    node = get_node(config, name)
    status = node.get("status")
    if status != "FROZEN":
        raise UnsetParameterError(
            f"parameter {name!r} is {status!r}, not FROZEN; frozen value required. "
            f"note={node.get('note', '')!r}")
    return node["value"]


def status_of(config: dict[str, Any], name: str) -> str:
    return get_node(config, name).get("status", "MISSING")


def assert_no_silent_defaults(config: dict[str, Any]) -> None:
    """Cheap self-check: every declared parameter must carry an explicit status."""
    for name, node in config.get("parameters", {}).items():
        if not isinstance(node, dict) or "status" not in node:
            raise SchemaError(f"parameter {name!r} lacks an explicit status")
        if node["status"] not in STATUS_VALUES:
            raise SchemaError(f"parameter {name!r} has invalid status {node['status']!r}")

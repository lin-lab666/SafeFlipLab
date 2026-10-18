"""Deterministic SHA-256 seed derivation for SafeFlipLab.

All seeds, anchor indices and identifiers are derived with SHA-256 over a
canonical JSON payload. Python's built-in ``hash()`` is never used because it
is salted per process (PYTHONHASHSEED) and would break reproducibility.

Conventions
-----------
* ``master_seed``: an integer in [0, 2**32). ``dev_seed = 20261011`` is used
  for smoke/pilot only and is never valid formal evidence.
* Formal master seeds are derived once, offline, from the protocol label
  ``SafeFlipLab-v01-formal-{i}`` (i = 0..7) and frozen in
  ``configs/formal_v01.json`` (see docs/PROTOCOL_V01.md).
* ``sim_seed`` labels never include the quartet condition code: the four
  conditions of one anchor-repetition must share a single paired sim_seed.
  Labels DO include the stream tag (``discovery`` vs ``audit``) so audit
  episodes can never reuse a discovery seed.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

PROTOCOL_ID = "SafeFlipLab-v01"
DEV_SEED = 20261011
FORMAL_MASTER_SEED_COUNT = 8
# Formal budget: 2 methods x 8 master seeds x 800 episodes = 12,800.
FORMAL_EPISODES_PER_METHOD_SEED = 800
FORMAL_TOTAL_EPISODES = 2 * FORMAL_MASTER_SEED_COUNT * FORMAL_EPISODES_PER_METHOD_SEED

# Quartet condition codes (fixed order everywhere: reports, CSV, tests).
CONDITIONS = ("00", "10", "01", "11")

# Stream tags: discovery quartets and audit quartets must never share seeds.
STREAM_DISCOVERY = "discovery"
STREAM_AUDIT = "audit"


def canonical_json(value: Any) -> str:
    """Stable JSON serialisation (sorted keys, no whitespace, no NaN)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def check_seed(seed: Any) -> int:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(f"seed must be an int, got {type(seed).__name__}")
    if not 0 <= seed < 2**32:
        raise ValueError(f"seed must be in [0, 2**32), got {seed}")
    return seed


def _sha256_int(payload: str, nbytes: int = 4) -> int:
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:nbytes], "big")


def derive_seed(master_seed: int, *labels: Any) -> int:
    """Derive a 32-bit seed from a master seed and explicit labels."""
    check_seed(master_seed)
    payload = canonical_json([PROTOCOL_ID, "seed", master_seed, *labels])
    return _sha256_int(payload)


def formal_master_seeds() -> list[int]:
    """The 8 frozen formal master seeds (SHA-256 derived, never result-picked)."""
    return [
        _sha256_int(canonical_json([PROTOCOL_ID, "formal-master", i]))
        for i in range(FORMAL_MASTER_SEED_COUNT)
    ]


def anchor_id(index: int) -> str:
    """Stable, method-independent anchor identifier from its stream index."""
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ValueError(f"anchor index must be a non-negative int, got {index!r}")
    return f"anchor-{index:04d}"


def anchor_stream_seed(master_seed: int) -> int:
    """Seed of the shared legal-anchor sampling stream for a master seed."""
    return derive_seed(master_seed, "anchor-stream", "v01")


def sim_seed_for(master_seed: int, method: str, stream: str, anchor: str, repetition: int) -> int:
    """Paired sim_seed for one anchor-repetition (shared by all 4 conditions).

    ``stream`` must be ``discovery`` or ``audit``; including it guarantees
    audit episodes never reuse discovery randomness.
    """
    if stream not in (STREAM_DISCOVERY, STREAM_AUDIT):
        raise ValueError(f"stream must be {STREAM_DISCOVERY!r} or {STREAM_AUDIT!r}, got {stream!r}")
    if not isinstance(repetition, int) or isinstance(repetition, bool) or repetition < 0:
        raise ValueError(f"repetition must be a non-negative int, got {repetition!r}")
    return derive_seed(master_seed, "sim", method, stream, anchor, repetition)


def run_id(phase: str, method: str, master_seed: int, utc_iso: str) -> str:
    """Human-readable run id: phase_method_seed_YYYYmmddTHHMMSSZ_shorthash."""
    stamp = utc_iso.replace("-", "").replace(":", "").replace(".", "")
    short = format(
        _sha256_int(canonical_json([phase, method, master_seed, utc_iso]), 4), "08x"
    )
    return f"{phase}_{method}_{master_seed}_{stamp}_{short}"

"""Anchor-level estimation, cluster bootstrap intervals and GATED tests.

Implements proposal section 8:

* the estimation unit is the **anchor** (cluster); intervals come from an
  anchor-level cluster bootstrap whose validity only needs "anchor is the
  sampling unit" — it does **not** assume the four condition labels are
  exchangeable;
* confirmatory tests (sign-flip / max-T) are **gated**: they return ``PENDING``
  unless an explicit ``SamplingAssumption`` with ``basis in {A,B,C}``,
  ``status == "FROZEN"`` and a non-empty ``justification_ref`` is supplied. No
  p-value is produced while the assumption is unproven (section 8.3).

No research value is defaulted: ``B`` (resamples), ``alpha`` and ``seed`` must be
passed explicitly.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping, Sequence

CONTRASTS = ("delta_gap", "delta_speed", "delta_both", "i_lin")
_NEEDS = {
    "delta_gap": ("10", "00"),
    "delta_speed": ("01", "00"),
    "delta_both": ("11", "00"),
    "i_lin": ("11", "10", "01", "00"),
}


@dataclass(frozen=True)
class SamplingAssumption:
    unit: str
    basis: str          # UNPROVEN | A | B | C
    justification_ref: str | None
    status: str         # PROPOSED | FROZEN

    def is_confirmatory_eligible(self) -> bool:
        return (self.unit == "anchor" and self.basis in ("A", "B", "C")
                and self.status == "FROZEN" and bool(self.justification_ref))


def unproven_assumption() -> SamplingAssumption:
    return SamplingAssumption(unit="anchor", basis="UNPROVEN", justification_ref=None,
                              status="PROPOSED")


@dataclass(frozen=True)
class Estimate:
    contrast: str
    point: float | None
    ci_low: float | None
    ci_high: float | None
    n_anchors: int
    assumption: SamplingAssumption
    note: str


@dataclass(frozen=True)
class ConfirmatoryTest:
    status: str                 # OK | PENDING
    method: str
    p_value: float | None
    reason: str
    assumption: SamplingAssumption


def _finite(values: Sequence[float | None]) -> list[float]:
    return [float(v) for v in values if v is not None]


def anchor_contrast(per_repetition: Sequence[Mapping[str, float | None]],
                    contrast: str) -> float | None:
    """Anchor-level paired contrast: pair within repetition, then mean over reps.

    A repetition contributes only if every required condition is present
    (finite). Missing repetitions are dropped; if none remains, returns ``None``.
    """
    if contrast not in CONTRASTS:
        raise ValueError(f"unknown contrast {contrast!r}")
    need = _NEEDS[contrast]
    diffs: list[float] = []
    for rep in per_repetition:
        vals = [rep.get(c) for c in need]
        if any(v is None for v in vals):
            continue
        v = {c: float(rep[c]) for c in need}  # type: ignore[arg-type]
        if contrast == "delta_gap":
            d = v["10"] - v["00"]
        elif contrast == "delta_speed":
            d = v["01"] - v["00"]
        elif contrast == "delta_both":
            d = v["11"] - v["00"]
        else:  # i_lin
            d = v["11"] - v["10"] - v["01"] + v["00"]
        diffs.append(d)
    if not diffs:
        return None
    return sum(diffs) / len(diffs)


def anchor_contrasts(per_repetition: Sequence[Mapping[str, float | None]]) -> dict[str, float | None]:
    return {c: anchor_contrast(per_repetition, c) for c in CONTRASTS}


def _percentile(sorted_vals: Sequence[float], p: float) -> float:
    if not sorted_vals:
        raise ValueError("empty")
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    pos = (len(sorted_vals) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return float(sorted_vals[lo]) * (1 - frac) + float(sorted_vals[hi]) * frac


def cluster_bootstrap_ci(values: Sequence[float | None], *, b_resamples: int, alpha: float,
                         seed: int) -> tuple[float | None, float | None]:
    """Anchor-level cluster bootstrap percentile interval (deterministic)."""
    vals = _finite(values)
    if len(vals) < 2:
        return None, None
    rng = random.Random(seed)
    n = len(vals)
    means: list[float] = []
    for _ in range(b_resamples):
        s = 0.0
        for _ in range(n):
            s += vals[rng.randrange(n)]
        means.append(s / n)
    means.sort()
    return _percentile(means, alpha / 2.0), _percentile(means, 1.0 - alpha / 2.0)


def estimate(contrast: str, anchor_values: Sequence[float | None], *, b_resamples: int,
             alpha: float, seed: int, assumption: SamplingAssumption | None = None) -> Estimate:
    assumption = assumption or unproven_assumption()
    vals = _finite(anchor_values)
    point = sum(vals) / len(vals) if vals else None
    lo, hi = cluster_bootstrap_ci(anchor_values, b_resamples=b_resamples, alpha=alpha, seed=seed)
    if len(vals) < 2:
        note = "fewer than 2 usable anchors: interval not estimable"
    elif len(set(vals)) == 1:
        note = "zero variance across anchors: interval degenerate (not a sampling interval)"
    else:
        note = f"anchor-level cluster bootstrap; sampling basis={assumption.basis}"
    return Estimate(contrast, point, lo, hi, len(vals), assumption, note)


def sign_flip_test(values: Sequence[float | None], *, b_resamples: int, seed: int,
                   assumption: SamplingAssumption | None) -> ConfirmatoryTest:
    """Two-sided anchor-level sign-flip test — GATED (proposal section 8.3)."""
    assumption = assumption or unproven_assumption()
    vals = _finite(values)
    if not assumption.is_confirmatory_eligible():
        return ConfirmatoryTest(
            "PENDING", "sign_flip", None,
            f"sampling assumption not eligible (basis={assumption.basis}, status={assumption.status}, "
            f"justification_ref={assumption.justification_ref!r}); no p-value produced",
            assumption)
    if len(vals) < 2:
        return ConfirmatoryTest("PENDING", "sign_flip", None, "fewer than 2 anchors", assumption)
    obs = abs(sum(vals) / len(vals))
    rng = random.Random(seed)
    n = len(vals)
    ge = 0
    for _ in range(b_resamples):
        s = 0.0
        for v in vals:
            s += v if rng.random() < 0.5 else -v
        if abs(s / n) >= obs - 1e-12:
            ge += 1
    p = (ge + 1) / (b_resamples + 1)
    return ConfirmatoryTest("OK", "sign_flip", p, f"basis={assumption.basis}", assumption)


def max_t_test(anchor_values_by_contrast: Mapping[str, Sequence[float | None]], *,
               b_resamples: int, seed: int, assumption: SamplingAssumption | None) -> ConfirmatoryTest:
    """FWER-controlling max-|T| sign-flip test over the pre-registered family — GATED."""
    assumption = assumption or unproven_assumption()
    if not assumption.is_confirmatory_eligible():
        return ConfirmatoryTest(
            "PENDING", "max_t", None,
            f"sampling assumption not eligible (basis={assumption.basis}); no p-value produced",
            assumption)
    fam = {k: _finite(v) for k, v in anchor_values_by_contrast.items()}
    fam = {k: v for k, v in fam.items() if len(v) >= 2}
    if not fam:
        return ConfirmatoryTest("PENDING", "max_t", None, "no contrast with >=2 anchors", assumption)
    obs_max = max(abs(sum(v) / len(v)) for v in fam.values())
    rng = random.Random(seed)
    ge = 0
    for _ in range(b_resamples):
        cur = 0.0
        for v in fam.values():
            n = len(v)
            s = 0.0
            for x in v:
                s += x if rng.random() < 0.5 else -x
            cur = max(cur, abs(s / n))
        if cur >= obs_max - 1e-12:
            ge += 1
    p = (ge + 1) / (b_resamples + 1)
    return ConfirmatoryTest("OK", "max_t", p, f"basis={assumption.basis}", assumption)


def confirmatory_status(assumption: SamplingAssumption | None) -> str:
    assumption = assumption or unproven_assumption()
    return "ELIGIBLE" if assumption.is_confirmatory_eligible() else "PENDING"

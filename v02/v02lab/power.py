"""Anchor-level sample-size derivation for a future formal V02 run.

This implements the §7.3 program of the V02 proposal: given an anchor-level
variance estimate from the pilot, a pre-registered minimum detectable effect
(MDE), a two-sided alpha, a target power and a multiplicity rule, compute how many
**anchors** (not episodes) a formal run would need.

Scope and honesty:

* this module only *derives* a number. It launches nothing, and the derived number
  is **not** an authorisation to run anything;
* the variance input comes from 18 pilot anchors, so every derived number carries
  substantial uncertainty and must be re-derived once a larger variance estimate
  exists;
* no p-value is produced by this project; the alpha used here is a *design* input
  for sizing, not a licence to run confirmatory tests (those remain gated, see
  ``stats_anchor``).

Standard library only; no research parameter is defaulted — ``mde``, ``alpha``,
``power`` and the multiplicity rule must be supplied explicitly.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

#: 97.5th percentile of the standard normal (two-sided alpha = 0.05).
Z_975 = 1.959963984540054


def normal_quantile(p: float) -> float:
    """Inverse standard-normal CDF (Acklam's rational approximation)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q, r = p - 0.5, (p - 0.5) ** 2
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def adjusted_alpha(alpha: float, family_size: int, rule: str) -> float:
    """Per-contrast alpha under a multiplicity rule.

    ``bonferroni`` divides alpha by the family size. ``holm_worst_case`` uses the
    same worst-case divisor (Holm's first step), which is the conservative sizing
    choice; Holm is uniformly more powerful than Bonferroni for the later steps.
    A max-T randomisation rule is *not* used for sizing here because its critical
    value depends on an exchangeability assumption this project has not
    established (see AUTONOMOUS_DECISIONS D35); sizing must not presuppose it.
    """
    if family_size < 1:
        raise ValueError("family_size must be >= 1")
    if rule == "bonferroni":
        return alpha / family_size
    if rule == "holm_worst_case":
        return alpha / family_size
    if rule == "none":
        return alpha
    raise ValueError(f"unknown multiplicity rule {rule!r}")


@dataclass(frozen=True)
class SampleSize:
    contrast: str
    sd_anchors: float
    mde: float
    alpha_used: float
    power: float
    n_anchors: int
    n_episodes: int
    achieved_halfwidth_at_n: float | None
    note: str


def required_anchors(*, sd: float, mde: float, alpha: float, power: float) -> int:
    """Anchors needed for a paired anchor-level z-test (normal approximation).

    ``n = (z_{1-alpha/2} + z_{power})^2 * sd^2 / mde^2``, rounded up, minimum 2.
    """
    if sd <= 0:
        raise ValueError("sd must be positive")
    if mde <= 0:
        raise ValueError("mde must be positive (a one-sided MDE is not allowed here)")
    if not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError("alpha and power must be in (0, 1)")
    z_a = normal_quantile(1 - alpha / 2)
    z_p = normal_quantile(power)
    n = ((z_a + z_p) ** 2) * (sd ** 2) / (mde ** 2)
    return max(2, math.ceil(n))


def plan(*, contrast_sd: Mapping[str, float], mde: float, alpha: float, power: float,
         rule: str, repetitions: int, methods: int, seeds: int) -> dict:
    """Full sizing plan. Episodes = anchors x repetitions x 4 conditions x methods x seeds."""
    if repetitions < 1 or methods < 1 or seeds < 1:
        raise ValueError("repetitions/methods/seeds must be >= 1")
    a = adjusted_alpha(alpha, len(contrast_sd), rule)
    sizes = {}
    for c, sd in contrast_sd.items():
        n = required_anchors(sd=float(sd), mde=mde, alpha=a, power=power)
        half = (normal_quantile(1 - a / 2) + normal_quantile(power)) * float(sd) / math.sqrt(n)
        sizes[c] = SampleSize(
            contrast=c, sd_anchors=float(sd), mde=mde, alpha_used=a, power=power,
            n_anchors=n, n_episodes=n * repetitions * 4 * methods * seeds,
            achieved_halfwidth_at_n=half,
            note="normal approximation; sd estimated from the 18-anchor pilot (uncertain)")
    n_req = max(s.n_anchors for s in sizes.values())
    return {
        "mde_s": mde, "alpha": alpha, "alpha_per_contrast": a, "power": power,
        "multiplicity_rule": rule, "family_size": len(contrast_sd),
        "repetitions": repetitions, "methods": methods, "seeds": seeds,
        "per_contrast": {c: s.__dict__ for c, s in sizes.items()},
        "required_anchors": n_req,
        "required_episodes": n_req * repetitions * 4 * methods * seeds,
        "note": "derivation only; grants no authorisation to run anything",
    }


def mde_at_n(*, sd: float, n: int, alpha: float, power: float) -> float:
    """Smallest detectable effect with ``n`` anchors (inverse of the sizing rule)."""
    if n < 2:
        raise ValueError("n must be >= 2")
    z_a = normal_quantile(1 - alpha / 2)
    z_p = normal_quantile(power)
    return (z_a + z_p) * sd / math.sqrt(n)


def anchor_sd(series: Sequence[float | None]) -> float | None:
    """Sample standard deviation of a contrast series (ddof=1)."""
    vals = [float(v) for v in series if v is not None]
    if len(vals) < 2:
        return None
    m = sum(vals) / len(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))

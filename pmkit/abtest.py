"""A/B test planning and readout for conversion-style (yes/no) metrics.

Standard library only. Everything here is the textbook two-proportion machinery,
written to be readable and explained in docs/how-it-works.md. It does NOT handle:
continuous metrics (revenue per user), sequential testing ("peeking"), more than two
arms, or multiple-comparison corrections. The CLI says so where it matters.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

_N = NormalDist()


def _z(p: float) -> float:
    return _N.inv_cdf(p)


def _check_prob(name: str, value: float) -> None:
    if not 0 < value < 1:
        raise ValueError(f"{name} must be strictly between 0 and 1 (got {value})")


# ---------------------------------------------------------------- planning


def sample_size_per_arm(baseline: float, mde_abs: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Visitors needed in EACH arm to detect an absolute change of `mde_abs` from `baseline`.

    Two-sided test, equal allocation. Uses the standard normal-approximation formula for
    comparing two proportions: the null-hypothesis variance (pooled rate) for the
    significance threshold and the alternative-hypothesis variance for power.
    Rounded up, because you cannot recruit a fraction of a visitor.
    """
    _check_prob("baseline", baseline)
    _check_prob("alpha", alpha)
    _check_prob("power", power)
    if mde_abs == 0:
        raise ValueError("mde_abs must be non-zero")
    p1 = baseline + mde_abs
    if not 0 < p1 < 1:
        raise ValueError(f"baseline + mde_abs = {p1:.4f} is outside (0, 1); choose a smaller effect")
    za, zb = _z(1 - alpha / 2), _z(power)
    pbar = (baseline + p1) / 2
    numerator = (za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(baseline * (1 - baseline) + p1 * (1 - p1))) ** 2
    return math.ceil(numerator / mde_abs**2)


def minimum_detectable_effect(baseline: float, n_per_arm: int, alpha: float = 0.05, power: float = 0.80) -> float:
    """Smallest absolute INCREASE over `baseline` the test could reliably detect with `n_per_arm`.

    Solved numerically from sample_size_per_arm (bisection), so the two functions always
    agree. Returns an absolute change (0.03 = 3 percentage points). Only the upward
    direction is solved; the downward effect is close to it but not identical, which is
    an inherent asymmetry of proportions near 0 or 1.
    """
    _check_prob("baseline", baseline)
    if n_per_arm < 2:
        raise ValueError("n_per_arm must be at least 2")
    hi = (1 - baseline) - 1e-9  # largest possible upward change
    if sample_size_per_arm(baseline, hi, alpha, power) > n_per_arm:
        return float("inf")  # even the largest possible change could not be detected
    lo = 1e-9
    for _ in range(100):
        mid = (lo + hi) / 2
        if sample_size_per_arm(baseline, mid, alpha, power) > n_per_arm:
            lo = mid
        else:
            hi = mid
    return hi


def days_needed(n_per_arm: int, daily_visitors: float, arms: int = 2) -> int:
    """Calendar days to collect `n_per_arm` in every arm given total daily traffic split evenly."""
    if daily_visitors <= 0:
        raise ValueError("daily_visitors must be positive")
    return math.ceil(n_per_arm * arms / daily_visitors)

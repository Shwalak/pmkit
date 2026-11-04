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


# ---------------------------------------------------------------- readout


@dataclass(frozen=True)
class Arm:
    conversions: int
    visitors: int

    def __post_init__(self) -> None:
        if self.visitors <= 0:
            raise ValueError("visitors must be positive")
        if not 0 <= self.conversions <= self.visitors:
            raise ValueError(f"conversions ({self.conversions}) must be between 0 and visitors ({self.visitors})")

    @property
    def rate(self) -> float:
        return self.conversions / self.visitors


def wilson_interval(conversions: int, visitors: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval for one proportion. Behaves well near 0 and 1, unlike mean +/- 1.96 se."""
    z = _z(1 - alpha / 2)
    p = conversions / visitors
    denom = 1 + z * z / visitors
    center = (p + z * z / (2 * visitors)) / denom
    half = z * math.sqrt(p * (1 - p) / visitors + z * z / (4 * visitors**2)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def newcombe_difference_ci(control: Arm, treatment: Arm, alpha: float = 0.05) -> tuple[float, float]:
    """Confidence interval for (treatment rate - control rate), Newcombe's hybrid score method.

    Built from the two Wilson intervals, so it stays sensible with small counts and rates near
    0 or 1, where the common "difference +/- 1.96 se" interval can spill outside [-1, 1].
    """
    lc, uc = wilson_interval(control.conversions, control.visitors, alpha)
    lt, ut = wilson_interval(treatment.conversions, treatment.visitors, alpha)
    pc, pt = control.rate, treatment.rate
    d = pt - pc
    lower = d - math.sqrt((pt - lt) ** 2 + (uc - pc) ** 2)
    upper = d + math.sqrt((ut - pt) ** 2 + (pc - lc) ** 2)
    return lower, upper


def two_proportion_z(control: Arm, treatment: Arm) -> tuple[float, float]:
    """Pooled two-proportion z-test. Returns (z, two-sided p-value)."""
    pooled = (control.conversions + treatment.conversions) / (control.visitors + treatment.visitors)
    se = math.sqrt(pooled * (1 - pooled) * (1 / control.visitors + 1 / treatment.visitors))
    if se == 0:  # both arms at 0% or both at 100%: no difference to test
        return 0.0, 1.0
    z = (treatment.rate - control.rate) / se
    return z, 2 * (1 - _N.cdf(abs(z)))


def sample_ratio_mismatch(control_visitors: int, treatment_visitors: int, treatment_share: float = 0.5) -> tuple[float, float]:
    """Chi-square test (1 degree of freedom) that visitors were split as planned. Returns (chi2, p).

    A tiny p-value means the assignment mechanism is broken (bots, redirects, logging loss,
    a bad rollout), and then NO downstream result can be trusted, however significant it looks.
    """
    _check_prob("treatment_share", treatment_share)
    total = control_visitors + treatment_visitors
    exp_t, exp_c = total * treatment_share, total * (1 - treatment_share)
    chi2 = (treatment_visitors - exp_t) ** 2 / exp_t + (control_visitors - exp_c) ** 2 / exp_c
    return chi2, 2 * (1 - _N.cdf(math.sqrt(chi2)))


SRM_THRESHOLD = 0.001  # the conventional, deliberately strict cut-off for SRM alarms

SIGNIFICANT_POSITIVE = "SIGNIFICANT_POSITIVE"
SIGNIFICANT_NEGATIVE = "SIGNIFICANT_NEGATIVE"
BORDERLINE = "BORDERLINE"
INCONCLUSIVE = "INCONCLUSIVE"
DO_NOT_TRUST = "DO_NOT_TRUST"


@dataclass
class Readout:
    control: Arm
    treatment: Arm
    alpha: float
    difference: float                 # treatment - control, absolute
    relative_lift: float | None       # difference / control rate; None when control rate is 0
    z: float
    p_value: float
    ci_low: float
    ci_high: float
    srm_chi2: float
    srm_p: float
    detectable_effect: float          # smallest upward change reliably (80% power) detectable with this much data
    verdict: str
    summary: str
    warnings: list[str]


def _pp(x: float) -> str:
    return f"{x * 100:+.2f} pp"


def readout(control: Arm, treatment: Arm, alpha: float = 0.05, treatment_share: float = 0.5, power: float = 0.80) -> Readout:
    """Statistical reading of a finished two-arm test on a yes/no metric.

    The order of checks is deliberate: a sample ratio mismatch overrides everything else,
    because significance on broken data is meaningless.
    """
    _check_prob("alpha", alpha)
    d = treatment.rate - control.rate
    rel = None if control.rate == 0 else d / control.rate
    z, p = two_proportion_z(control, treatment)
    lo, hi = newcombe_difference_ci(control, treatment, alpha)
    chi2, srm_p = sample_ratio_mismatch(control.visitors, treatment.visitors, treatment_share)
    n_min = min(control.visitors, treatment.visitors)
    baseline = min(max(control.rate, 1e-6), 1 - 1e-6)
    mde = minimum_detectable_effect(baseline, n_min, alpha, power) if n_min >= 2 else float("inf")

    warnings: list[str] = []
    for name, arm in (("control", control), ("treatment", treatment)):
        if arm.conversions < 10 or arm.visitors - arm.conversions < 10:
            warnings.append(
                f"The {name} arm has fewer than 10 conversions or non-conversions; the normal approximation "
                "behind these p-values is unreliable. Treat the result as rough."
            )
    level = f"{(1 - alpha) * 100:g}% CI"

    if srm_p < SRM_THRESHOLD:
        verdict = DO_NOT_TRUST
        summary = (
            f"Do not trust this result. The split of visitors between arms looks wrong "
            f"(sample ratio mismatch, p = {srm_p:.2g}). Find out why before reading anything else."
        )
    elif p < alpha and (lo > 0 or hi < 0):
        verdict = SIGNIFICANT_POSITIVE if d > 0 else SIGNIFICANT_NEGATIVE
        word = "better than" if d > 0 else "worse than"
        summary = f"Treatment is statistically {word} control: {_pp(d)} ({level}: {_pp(lo)} to {_pp(hi)}, p = {p:.3g})."
    elif p < alpha:
        verdict = BORDERLINE
        summary = (
            f"Borderline. The p-value ({p:.3g}) says the difference is significant but the {level} "
            f"({_pp(lo)} to {_pp(hi)}) still includes zero. Treat as inconclusive and gather more data."
        )
    else:
        verdict = INCONCLUSIVE
        reach = "an effect this large is impossible to detect with this much data" if math.isinf(mde) else (
            f"with this much data the test could only reliably detect a change of about {mde * 100:.2f} pp or more"
        )
        summary = (
            f"No statistically significant difference ({_pp(d)}, {level}: {_pp(lo)} to {_pp(hi)}, p = {p:.3g}). "
            f"That is not evidence of no effect: {reach}."
        )
    return Readout(control, treatment, alpha, d, rel, z, p, lo, hi, chi2, srm_p, mde, verdict, summary, warnings)

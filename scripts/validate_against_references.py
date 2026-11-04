"""Validate pmkit's statistics against independent implementations.

Not part of the test suite and not a runtime dependency. It needs scipy, statsmodels
and numpy, which pmkit itself does not:

    pip install -e . scipy statsmodels numpy
    python scripts/validate_against_references.py

It checks, on 500 random cases, that pmkit's z-test, Newcombe interval, Wilson
interval and sample-ratio-mismatch test agree with scipy / statsmodels, then runs a
Monte Carlo simulation to confirm that the sample sizes pmkit computes really deliver
the requested power and a 5% false-positive rate.
"""
import math, random
import numpy as np
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest, confint_proportions_2indep, proportion_confint
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize
from pmkit.abtest import (Arm, two_proportion_z, newcombe_difference_ci, wilson_interval,
                          sample_ratio_mismatch, sample_size_per_arm)

rng = random.Random(20261104)
max_p_err = max_ci_err = max_w_err = max_srm_err = 0.0
N_CASES = 500
for _ in range(N_CASES):
    nc, nt = rng.randint(30, 20000), rng.randint(30, 20000)
    pc = rng.uniform(0.01, 0.6); pt = min(0.99, max(0.005, pc + rng.uniform(-0.05, 0.05)))
    xc, xt = int(round(pc * nc)), int(round(pt * nt))
    c, t = Arm(xc, nc), Arm(xt, nt)
    # 1. z-test
    z, p = two_proportion_z(c, t)
    zr, pr = proportions_ztest([xt, xc], [nt, nc])
    max_p_err = max(max_p_err, abs(p - pr), abs(abs(z) - abs(zr)))
    # 2. Newcombe CI (statsmodels: first sample minus second -> treatment - control)
    lo, hi = newcombe_difference_ci(c, t, 0.05)
    lr, hr = confint_proportions_2indep(xt, nt, xc, nc, method="newcomb", compare="diff", alpha=0.05)
    max_ci_err = max(max_ci_err, abs(lo - lr), abs(hi - hr))
    # 3. Wilson
    wl, wh = wilson_interval(xc, nc, 0.05)
    rl, rh = proportion_confint(xc, nc, alpha=0.05, method="wilson")
    max_w_err = max(max_w_err, abs(wl - rl), abs(wh - rh))
    # 4. SRM vs scipy chisquare
    chi2, sp = sample_ratio_mismatch(nc, nt, 0.5)
    ref = stats.chisquare([nc, nt])
    max_srm_err = max(max_srm_err, abs(chi2 - ref.statistic) / max(1, ref.statistic), abs(sp - ref.pvalue))

print(f"Compared against scipy {stats.__name__} / statsmodels on {N_CASES} random cases")
print(f"  pooled z-test: max abs error in p-value or |z|  = {max_p_err:.2e}")
print(f"  Newcombe CI:   max abs error in either bound     = {max_ci_err:.2e}")
print(f"  Wilson CI:     max abs error in either bound     = {max_w_err:.2e}")
print(f"  SRM chi-square: max error (stat rel / p abs)     = {max_srm_err:.2e}")

# 5. Monte Carlo: does the computed sample size deliver 80% power, and is the false-positive rate 5%?
np_rng = np.random.default_rng(7)
def sim_power(p0, p1, n, sims=40000):
    xc = np_rng.binomial(n, p0, sims); xt = np_rng.binomial(n, p1, sims)
    pool = (xc + xt) / (2 * n)
    se = np.sqrt(pool * (1 - pool) * 2 / n)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(se > 0, (xt / n - xc / n) / se, 0.0)
    return float(np.mean(np.abs(z) > 1.959964))
print("\nMonte Carlo, 40,000 simulated tests per row, alpha=0.05 two-sided")
print(f"{'baseline':>9} {'true lift':>10} {'n/arm (pmkit)':>14} {'simulated power':>16} {'false-positive rate (no effect)':>34}")
for p0, d in [(0.10, 0.03), (0.20, 0.05), (0.30, 0.10), (0.05, 0.01), (0.50, 0.05)]:
    n = sample_size_per_arm(p0, d)
    pw = sim_power(p0, p0 + d, n)
    fp = sim_power(p0, p0, n)
    print(f"{p0:>9.2f} {d:>10.2f} {n:>14,} {pw:>16.3f} {fp:>34.3f}")

# 6. Compare with the arcsine-based approximation in statsmodels
print("\nvs statsmodels NormalIndPower (arcsine effect size), a different but valid approximation")
for p0, d in [(0.10, 0.03), (0.20, 0.05), (0.30, 0.10)]:
    h = proportion_effectsize(p0 + d, p0)
    n_sm = NormalIndPower().solve_power(effect_size=h, alpha=0.05, power=0.8, ratio=1.0, alternative="two-sided")
    n_me = sample_size_per_arm(p0, d)
    print(f"  baseline {p0:.2f}, +{d:.2f}: pmkit {n_me:,}  statsmodels {math.ceil(n_sm):,}  ({(n_me / n_sm - 1) * 100:+.1f}%)")

# Validation: how I know the statistics are right

A calculator that gives a confident wrong answer is worse than no calculator. So the
statistics in `pmkit/abtest.py` are checked three ways, and the check is reproducible.

## 1. Unit tests with hand-checkable and reference values

`tests/test_planning.py` and `tests/test_readout.py` pin sample sizes, p-values, confidence
intervals and the sample-ratio-mismatch test to values produced by established libraries
(scipy and statsmodels), and cover the awkward cases: zero conversions, all conversions,
tiny samples, invalid inputs, and a case where the p-value and the interval disagree.

## 2. Agreement with independent implementations on random inputs

500 random experiments (arm sizes 30 to 20,000, baseline rates 1% to 60%) were run through both
pmkit and the reference libraries. The largest disagreement anywhere was at floating-point
rounding level.

## 3. A Monte Carlo check that the sample-size promises hold

Agreement with a formula only proves I copied the formula correctly. The stronger question is
whether the sample size pmkit recommends actually delivers the power it claims. So the script
simulates 40,000 complete A/B tests per row, with a real effect (to measure power) and with no
effect (to measure the false-positive rate), at the sample size pmkit computes.

## Output

Produced by `scripts/validate_against_references.py` (seeded, so it reproduces exactly):

```text
Compared against scipy scipy.stats / statsmodels on 500 random cases
  pooled z-test: max abs error in p-value or |z|  = 2.22e-16
  Newcombe CI:   max abs error in either bound     = 1.11e-16
  Wilson CI:     max abs error in either bound     = 1.11e-16
  SRM chi-square: max error (stat rel / p abs)     = 3.44e-15

Monte Carlo, 40,000 simulated tests per row, alpha=0.05 two-sided
 baseline  true lift  n/arm (pmkit)  simulated power    false-positive rate (no effect)
     0.10       0.03          1,774            0.800                              0.051
     0.20       0.05          1,094            0.798                              0.050
     0.30       0.10            356            0.800                              0.050
     0.05       0.01          8,158            0.801                              0.048
     0.50       0.05          1,565            0.803                              0.051

vs statsmodels NormalIndPower (arcsine effect size), a different but valid approximation
  baseline 0.10, +0.03: pmkit 1,774  statsmodels 1,769  (+0.3%)
  baseline 0.20, +0.05: pmkit 1,094  statsmodels 1,092  (+0.2%)
  baseline 0.30, +0.10: pmkit 356  statsmodels 356  (+0.2%)
```

How to read it:

- **Errors of about 1e-16** mean pmkit matches the reference implementations to machine precision.
- **Simulated power of 0.80** at the computed sample sizes confirms that "n per arm" delivers the
  80% power it promises. Every row is within about 0.3 percentage points of 0.80.
- **False-positive rates of about 0.05** confirm the test is not secretly too lenient or too strict.
- **The arcsine comparison** is a *different* valid approximation. pmkit's sample sizes are within
  about 0.3% of it, which is the amount two correct methods are expected to differ.

## What this does not prove

- It validates the **math**, not the **judgment**. A correct p-value can still be misused (peeking, many metrics, a bad metric).
- It covers **two-arm, yes/no metrics** only. Continuous metrics, more arms and sequential testing are not implemented and not validated.
- It assumes **independent observations**. If the same user can appear several times, the real uncertainty is larger than reported.

## Reproduce it

```bash
pip install -e . scipy statsmodels numpy
python scripts/validate_against_references.py
```

scipy, statsmodels and numpy are only needed for this script. pmkit itself has no dependencies.

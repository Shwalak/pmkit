import pytest

from pmkit.abtest import (
    BORDERLINE,
    DO_NOT_TRUST,
    INCONCLUSIVE,
    SIGNIFICANT_NEGATIVE,
    SIGNIFICANT_POSITIVE,
    Arm,
    newcombe_difference_ci,
    readout,
    sample_ratio_mismatch,
    two_proportion_z,
    wilson_interval,
)

# Reference values below were produced by statsmodels / scipy (see docs/validation.md);
# pmkit agrees with them to about 1e-16 on 500 random cases.


def test_arm_validation():
    for bad in ((-1, 10), (11, 10), (0, 0), (5, -3)):
        with pytest.raises(ValueError):
            Arm(*bad)


def test_pooled_z_test_matches_reference():
    z, p = two_proportion_z(Arm(200, 1000), Arm(240, 1000))
    assert z == pytest.approx(2.1592, abs=1e-4)
    assert p == pytest.approx(0.030841, abs=1e-5)


def test_wilson_matches_reference():
    assert wilson_interval(200, 1000) == pytest.approx((0.176377, 0.225919), abs=1e-6)
    assert wilson_interval(0, 50) == pytest.approx((0.0, 0.071348), abs=1e-6)     # zero conversions: lower bound stays 0
    assert wilson_interval(50, 50) == pytest.approx((0.928652, 1.0), abs=1e-6)    # all conversions: upper bound stays 1
    assert wilson_interval(3, 40) == pytest.approx((0.025836, 0.198642), abs=1e-6)


def test_newcombe_ci_matches_reference_and_stays_in_bounds():
    lo, hi = newcombe_difference_ci(Arm(200, 1000), Arm(240, 1000))
    assert (lo, hi) == pytest.approx((0.00368, 0.07620), abs=1e-4)
    lo, hi = newcombe_difference_ci(Arm(0, 30), Arm(30, 30))    # extreme case: the naive interval can leave [-1, 1]
    assert -1 <= lo <= hi <= 1


def test_srm_matches_reference():
    chi2, p = sample_ratio_mismatch(5000, 5400)
    assert chi2 == pytest.approx(15.3846, abs=1e-3)
    assert p == pytest.approx(8.77e-5, rel=1e-2)
    assert sample_ratio_mismatch(5000, 5200)[1] == pytest.approx(0.0477, abs=1e-3)   # mild imbalance: not an alarm
    assert sample_ratio_mismatch(100, 100)[1] == pytest.approx(1.0)


def test_srm_respects_planned_split():
    # A deliberate 90/10 split: 9000 vs 1000 is exactly on plan.
    assert sample_ratio_mismatch(9000, 1000, treatment_share=0.1)[1] == pytest.approx(1.0)


def test_significant_positive():
    r = readout(Arm(200, 1000), Arm(240, 1000))
    assert r.verdict == SIGNIFICANT_POSITIVE
    assert r.difference == pytest.approx(0.04) and r.relative_lift == pytest.approx(0.2)
    assert "better than" in r.summary and "+4.00 pp" in r.summary


def test_significant_negative():
    r = readout(Arm(240, 1000), Arm(200, 1000))
    assert r.verdict == SIGNIFICANT_NEGATIVE and "worse than" in r.summary


def test_inconclusive_explains_what_the_test_could_detect():
    r = readout(Arm(200, 1000), Arm(205, 1000))
    assert r.verdict == INCONCLUSIVE
    assert "not evidence of no effect" in r.summary
    assert r.detectable_effect == pytest.approx(0.0524, abs=1e-3)


def test_borderline_when_p_value_and_interval_disagree():
    # p = 0.0447 < 0.05 but the Newcombe interval's lower bound is slightly below zero.
    r = readout(Arm(3, 100), Arm(10, 100))
    assert r.p_value < 0.05 and r.ci_low <= 0
    assert r.verdict == BORDERLINE and "Treat as inconclusive" in r.summary


def test_sample_ratio_mismatch_overrides_a_significant_result():
    r = readout(Arm(500, 5000), Arm(700, 5400))   # large "win", but the split is broken
    assert r.p_value < 0.001
    assert r.verdict == DO_NOT_TRUST and "Do not trust" in r.summary


def test_small_counts_produce_a_warning():
    r = readout(Arm(2, 40), Arm(6, 40))
    assert any("fewer than 10" in w for w in r.warnings)
    assert not readout(Arm(200, 1000), Arm(240, 1000)).warnings


def test_zero_conversions_everywhere_is_handled():
    r = readout(Arm(0, 500), Arm(0, 500))
    assert r.p_value == 1.0 and r.verdict == INCONCLUSIVE and r.relative_lift is None


def test_alpha_changes_the_conclusion():
    r05 = readout(Arm(200, 1000), Arm(240, 1000), alpha=0.05)
    r01 = readout(Arm(200, 1000), Arm(240, 1000), alpha=0.01)
    assert r05.verdict == SIGNIFICANT_POSITIVE and r01.verdict == INCONCLUSIVE
    assert "99% CI" in r01.summary

import math

import pytest

from pmkit.abtest import days_needed, minimum_detectable_effect, sample_size_per_arm


def test_known_sample_sizes():
    # Values from the formula in abtest.py; independently re-derived and simulated in docs/validation.md
    assert sample_size_per_arm(0.10, 0.03) == 1774
    assert sample_size_per_arm(0.20, 0.05) == 1094
    assert sample_size_per_arm(0.30, 0.10) == 356


def test_bigger_effect_needs_fewer_visitors():
    assert sample_size_per_arm(0.2, 0.10) < sample_size_per_arm(0.2, 0.05) < sample_size_per_arm(0.2, 0.02)


def test_higher_power_and_stricter_alpha_need_more():
    base = sample_size_per_arm(0.2, 0.05)
    assert sample_size_per_arm(0.2, 0.05, power=0.9) > base
    assert sample_size_per_arm(0.2, 0.05, alpha=0.01) > base


def test_direction_of_effect_is_handled():
    assert sample_size_per_arm(0.20, -0.05) > 0  # a drop is detectable too


def test_invalid_inputs_are_rejected():
    for bad in (dict(baseline=0, mde_abs=0.01), dict(baseline=1, mde_abs=0.01), dict(baseline=0.5, mde_abs=0),
                dict(baseline=0.95, mde_abs=0.10)):
        with pytest.raises(ValueError):
            sample_size_per_arm(**bad)
    with pytest.raises(ValueError):
        sample_size_per_arm(0.2, 0.05, alpha=1.5)


def test_mde_is_the_inverse_of_sample_size():
    n = sample_size_per_arm(0.20, 0.05)
    # The MDE for exactly that n should be (within rounding) the 5pp we started from.
    assert minimum_detectable_effect(0.20, n) == pytest.approx(0.05, abs=1e-4)


def test_mde_shrinks_as_sample_grows():
    assert minimum_detectable_effect(0.1, 10_000) < minimum_detectable_effect(0.1, 1_000)


def test_mde_infinite_when_nothing_could_be_detected():
    assert math.isinf(minimum_detectable_effect(0.5, 3))


def test_days_needed():
    assert days_needed(1000, 500) == 4          # 2 arms x 1000 / 500 per day
    assert days_needed(1001, 500) == 5          # rounds up
    with pytest.raises(ValueError):
        days_needed(100, 0)

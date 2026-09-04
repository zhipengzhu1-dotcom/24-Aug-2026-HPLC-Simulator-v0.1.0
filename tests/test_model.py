"""Data-model unit boundaries (SPEC §4): %B <-> phi, and the one S_e <-> S conversion."""

import math

import pytest

from hplcsim.model import (
    ln_k0_from_log10_k0,
    log10_k0_from_ln_k0,
    percent_b_from_phi,
    phi_from_percent_b,
    s_base10_from_s_e,
    s_e_from_s_base10,
)


def test_percent_b_converts_to_fraction() -> None:
    assert phi_from_percent_b(5.0) == pytest.approx(0.05)
    assert phi_from_percent_b(95.0) == pytest.approx(0.95)


def test_phi_converts_back_to_percent_b() -> None:
    assert percent_b_from_phi(0.05) == pytest.approx(5.0)


def test_a_typed_percent_b_comes_back_exactly() -> None:
    """The display boundary is integer-exact for what was typed: 55, not 55.00000000000001."""
    for typed in (5.0, 15.0, 55.0, 95.0, 12.5):
        assert percent_b_from_phi(phi_from_percent_b(typed)) == typed


def test_s_base10_is_natural_log_s_over_ln10() -> None:
    # S = 4 means one decade of k per 0.25 phi -> S_e = 4 * ln 10
    assert s_e_from_s_base10(4.0) == pytest.approx(4.0 * math.log(10))
    assert s_base10_from_s_e(4.0 * math.log(10)) == pytest.approx(4.0)


def test_log10_k0_converts_through_the_same_boundary() -> None:
    assert ln_k0_from_log10_k0(2.0) == pytest.approx(math.log(100.0))
    assert log10_k0_from_ln_k0(math.log(100.0)) == pytest.approx(2.0)

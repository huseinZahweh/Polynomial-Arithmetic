"""Step 1 smoke tests for Milestone 3 skeleton, exceptions, and _reference layer."""
from __future__ import annotations

import pytest

import gf2m_m3
from gf2m_m3 import (
    GF2mInverseError,
    NotInvertibleError,
    ZeroElementHasNoInverseError,
)
from gf2m_m3._reference import (
    FIELD_REGISTRY,
    bin_to_int,
    deg,
    format_poly_representations,
    get_field_spec,
    get_m_poly_int,
    gf2m_multiply,
    hamming_weight,
    hex_to_int,
    int_to_algebraic,
    int_to_bin,
    int_to_hex,
    is_supported_degree,
    list_supported_degrees,
    mod_reduce,
)


def test_package_imports_and_exports() -> None:
    """Verify top-level package imports and exception exports."""
    assert hasattr(gf2m_m3, "ZeroElementHasNoInverseError")
    assert hasattr(gf2m_m3, "NotInvertibleError")
    assert hasattr(gf2m_m3, "GF2mInverseError")
    assert issubclass(ZeroElementHasNoInverseError, GF2mInverseError)
    assert issubclass(NotInvertibleError, GF2mInverseError)
    assert issubclass(GF2mInverseError, ValueError)


def test_exception_attributes_and_messages() -> None:
    """Verify custom exceptions preserve gcd and trace attributes."""
    step0 = [{"step": 0, "Q": None, "A1": 1, "A2": 0, "A3": 0x11B, "B1": 0, "B2": 1, "B3": 0}]
    err_zero = ZeroElementHasNoInverseError(gcd=0x11B, trace=step0)
    assert err_zero.gcd == 0x11B
    assert err_zero.trace == step0
    assert "B3(x) = 0" in str(err_zero)
    assert "11B" in str(err_zero)

    reducible_trace = [{"step": 0}, {"step": 1, "B3": 0, "A3": 0b101}]
    err_not_inv = NotInvertibleError(gcd=0b101, trace=reducible_trace)
    assert err_not_inv.gcd == 0b101
    assert err_not_inv.trace == reducible_trace
    assert "gcd" in str(err_not_inv).lower()


@pytest.mark.parametrize(
    ("m_degree", "expected_taps"),
    [
        (2, (2, 1, 0)),
        (3, (3, 2, 0)),
        (4, (4, 3, 0)),
        (5, (5, 2, 0)),
        (6, (6, 1, 0)),
        (7, (7, 1, 0)),
        (8, (8, 4, 3, 1, 0)),
        (163, (163, 7, 6, 3, 0)),
        (233, (233, 74, 0)),
        (239, (239, 158, 0)),
        (283, (283, 12, 7, 5, 0)),
        (409, (409, 87, 0)),
        (571, (571, 10, 5, 2, 0)),
    ],
)
def test_all_13_field_polynomials(m_degree: int, expected_taps: tuple[int, ...]) -> None:
    """Verify all 13 Plan 01 field polynomials (including m=3 [3,2,0] and m=4 [4,3,0])."""
    assert is_supported_degree(m_degree)
    spec = get_field_spec(m_degree)
    expected_int = sum(1 << k for k in expected_taps)

    assert spec.m_degree == m_degree
    assert spec.taps == expected_taps
    assert spec.m_poly_int == expected_int
    assert get_m_poly_int(m_degree) == expected_int
    assert deg(spec.m_poly_int) == m_degree
    assert (spec.m_poly_int >> m_degree) == 1


def test_field_registry_completeness() -> None:
    """Verify exactly 13 fields exist (7 textbook + 6 cryptographic)."""
    degrees = list_supported_degrees()
    assert degrees == [2, 3, 4, 5, 6, 7, 8, 163, 233, 239, 283, 409, 571]
    assert len(FIELD_REGISTRY) == 13
    assert list_supported_degrees(include_textbook=False) == [163, 233, 239, 283, 409, 571]

    with pytest.raises(ValueError, match="Unsupported field degree"):
        get_field_spec(128)


def test_deg_and_formatting_helpers() -> None:
    """Verify deg, hamming_weight, uppercase hex padding, binary padding, and algebraic format."""
    assert deg(0) == -1
    assert deg(1) == 0
    assert deg(0b10) == 1
    assert deg(0x11B) == 8
    assert hamming_weight(0x11B) == 5

    # Uppercase hex + zero-padding to ceil(m/4) digits
    assert int_to_hex(0x0A, m_degree=8) == "0A"
    assert int_to_hex(0x8A, m_degree=8) == "8A"
    assert int_to_hex(0x11B, m_degree=8) == "11B"  # does not truncate > m bits
    assert len(int_to_hex(1, m_degree=163)) == 41
    assert int_to_hex(1, m_degree=163).endswith("1")

    assert int_to_bin(0x05, m_degree=8) == "00000101"
    assert bin_to_int("0b 0101 0111") == 0x57
    assert hex_to_int("{8A}") == 0x8A

    assert int_to_algebraic(0) == "0"
    assert int_to_algebraic(1) == "1"
    assert int_to_algebraic(0x83) == "x^7 + x + 1"
    assert int_to_algebraic(0x11B) == "x^8 + x^4 + x^3 + x + 1"

    rep = format_poly_representations(0x0A, m_degree=8)
    assert rep == {
        "int": 0x0A,
        "hex": "0A",
        "bin": "00001010",
        "algebraic": "x^3 + x",
        "degree": 3,
    }


def test_negative_integer_rejection() -> None:
    """Verify negative integers are cleanly rejected with ValueError."""
    with pytest.raises(ValueError, match="non-negative"):
        deg(-1)
    with pytest.raises(ValueError, match="non-negative"):
        int_to_hex(-5, m_degree=8)
    with pytest.raises(ValueError, match="non-negative"):
        int_to_bin(-5, m_degree=8)
    with pytest.raises(ValueError, match="non-negative"):
        int_to_algebraic(-5)
    with pytest.raises(ValueError, match="non-negative"):
        mod_reduce(-1, 0x11B, 8)
    with pytest.raises(ValueError, match="non-negative"):
        gf2m_multiply(-1, 0x02, 0x11B, 8)
    with pytest.raises(ValueError, match="non-negative"):
        gf2m_multiply(0x02, -1, 0x11B, 8)


def test_reference_mod_reduce_and_multiply_smoke() -> None:
    """Verify reference mod_reduce and Shift-and-XOR gf2m_multiply against Stallings Ch. 4 & 5."""
    m_poly = get_m_poly_int(8)  # 0x11B

    r_int, mod_trace = mod_reduce(0x11B, m_poly, 8)
    assert r_int == 0
    assert mod_trace["was_reduced"] is True
    assert len(mod_trace["steps"]) == 1

    # Stallings Ch. 4: {57} * {83} mod {11B} = {C1}
    prod1, trace1 = gf2m_multiply(0x57, 0x83, m_poly, 8)
    assert prod1 == 0xC1
    assert trace1["trace_type"] == "shift_and_xor"

    # Stallings Ch. 5 AES: {02} * {87} mod {11B} = {15}
    prod2, trace2 = gf2m_multiply(0x02, 0x87, m_poly, 8)
    assert prod2 == 0x15
    assert trace2["summary"]["reduction_count"] == 1

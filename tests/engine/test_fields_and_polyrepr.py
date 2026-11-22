"""Unit tests for the 13-field registry, multi-base converters, and domain exceptions."""
from __future__ import annotations

import pytest

import backend.engine as engine
from backend.engine import (
    BIN_TO_INT,
    DEFAULT_DEGREE,
    DEG,
    ElementRepr,
    GF2mInverseError,
    HAMMING_WEIGHT,
    HEX_TO_INT,
    INT_TO_ALGEBRAIC,
    INT_TO_BIN,
    INT_TO_HEX,
    MOD_REDUCE,
    NotInvertibleError,
    ZeroElementHasNoInverseError,
    format_poly_representations,
    get_field,
    get_m_poly_int,
    is_supported,
    list_fields,
    list_supported_degrees,
    multiply,
    multiply_traced,
    parse_value,
)

EXPECTED_TAPS = {
    2: (2, 1, 0),
    3: (3, 2, 0),
    4: (4, 3, 0),
    5: (5, 2, 0),
    6: (6, 1, 0),
    7: (7, 1, 0),
    8: (8, 4, 3, 1, 0),
    163: (163, 7, 6, 3, 0),
    233: (233, 74, 0),
    239: (239, 158, 0),
    283: (283, 12, 7, 5, 0),
    409: (409, 87, 0),
    571: (571, 10, 5, 2, 0),
}


def test_package_imports_and_exception_hierarchy() -> None:
    """Verify top-level engine exports and GF(2^m) exception hierarchy."""
    assert hasattr(engine, "ZeroElementHasNoInverseError")
    assert hasattr(engine, "NotInvertibleError")
    assert hasattr(engine, "GF2mInverseError")
    assert issubclass(ZeroElementHasNoInverseError, GF2mInverseError)
    assert issubclass(NotInvertibleError, GF2mInverseError)
    assert issubclass(GF2mInverseError, ValueError)


def test_exception_attributes_and_messages() -> None:
    """Verify custom inverse exceptions preserve gcd and trace attributes."""
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


@pytest.mark.parametrize("degree,taps", EXPECTED_TAPS.items())
def test_field_taps(degree: int, taps: tuple[int, ...]) -> None:
    """Verify all 13 configured field polynomials, taps, bitmasks, and categories."""
    assert is_supported(degree)
    field = get_field(degree)
    expected_int = sum(2**term for term in taps)
    assert field.m == degree
    assert field.taps == taps
    assert tuple(reversed(field.reduction_poly_terms)) == taps
    assert field.mod_poly == expected_int
    assert get_m_poly_int(degree) == expected_int
    assert DEG(field.mod_poly) == degree
    assert (field.mod_poly >> degree) == 1
    assert field.category == ("textbook" if degree < 163 else "nist")
    assert field.name == f"GF(2^{degree})"


def test_registry_filters_and_default() -> None:
    assert DEFAULT_DEGREE == 163
    assert [field.m for field in list_fields()] == list(EXPECTED_TAPS)
    assert list_supported_degrees() == [2, 3, 4, 5, 6, 7, 8, 163, 233, 239, 283, 409, 571]
    assert [field.m for field in list_fields(include_textbook=False)] == [163, 233, 239, 283, 409, 571]
    assert list_supported_degrees(include_textbook=False) == [163, 233, 239, 283, 409, 571]


@pytest.mark.parametrize("degree", [0, 1, 9, 128, 164, True, 8.0, "8"])
def test_unsupported_degrees(degree) -> None:
    assert not is_supported(degree)
    with pytest.raises(ValueError, match="unsupported field degree"):
        get_field(degree)


@pytest.mark.parametrize("m", [8, 163, 571])
def test_round_trip_and_minimum_width(m: int) -> None:
    for value in (0, 1, 2**(m - 1) | 0x3F, 2**m - 1):
        binary = INT_TO_BIN(value, m)
        hexadecimal = INT_TO_HEX(value, m)
        assert len(binary) == m
        assert len(hexadecimal) == (m + 3) // 4
        assert hexadecimal == hexadecimal.upper()
        assert BIN_TO_INT(binary) == HEX_TO_INT(hexadecimal) == value

    modulus = get_field(m).mod_poly
    assert BIN_TO_INT(INT_TO_BIN(modulus, m)) == HEX_TO_INT(INT_TO_HEX(modulus, m)) == modulus


def test_notation_and_metrics() -> None:
    assert BIN_TO_INT(" 0B0101 0111\t") == HEX_TO_INT(" {0X 5 7} ") == 0x57
    assert BIN_TO_INT("0b 0101 0111") == 0x57
    assert HEX_TO_INT("{8A}") == 0x8A
    assert DEG(0) == -1
    assert DEG(1) == 0
    assert DEG(0b10) == 1
    assert DEG(0x11B) == 8
    assert HAMMING_WEIGHT(0) == 0
    assert HAMMING_WEIGHT(0x11B) == 5

    assert INT_TO_HEX(0x0A, 8) == "0A"
    assert INT_TO_HEX(0x8A, 8) == "8A"
    assert INT_TO_HEX(0x11B, 8) == "11B"
    assert len(INT_TO_HEX(1, 163)) == 41
    assert INT_TO_HEX(1, 163).endswith("1")
    assert INT_TO_BIN(0x05, 8) == "00000101"

    assert INT_TO_ALGEBRAIC(0) == "0"
    assert INT_TO_ALGEBRAIC(1) == "1"
    assert INT_TO_ALGEBRAIC(0x57) == "x^6 + x^4 + x^2 + x + 1"
    assert INT_TO_ALGEBRAIC(0x83) == "x^7 + x + 1"
    assert INT_TO_ALGEBRAIC(0x11B) == "x^8 + x^4 + x^3 + x + 1"
    assert INT_TO_ALGEBRAIC((1 << 162) | 2) == "x^162 + x"

    assert format_poly_representations(0x0A, m_degree=8) == {
        "int": 0x0A,
        "hex": "0A",
        "bin": "00001010",
        "algebraic": "x^3 + x",
        "degree": 3,
    }
    assert ElementRepr.from_int(0xD4, 8).dict() == {
        "hex": "d4",
        "bin": "11010100",
        "poly": "x^7 + x^6 + x^4 + x^2",
        "degree": 7,
        "bit_length": 8,
        "hamming_weight": 4,
    }
    assert parse_value("{0b1010}", "bin") == 10
    with pytest.raises(ValueError):
        parse_value("1 010", "bin")


@pytest.mark.parametrize(
    "text,base,expected",
    [
        ("{57}", "hex", 0x57),
        (" {0x83} ", "hex", 0x83),
        ("{0b1011}", "bin", 0b1011),
    ],
)
def test_parse_value_accepts_braces(text: str, base: str, expected: int) -> None:
    assert parse_value(text, base) == expected


@pytest.mark.parametrize(
    "text,base",
    [
        ("-5", "hex"),
        ("+5", "hex"),
        ("-101", "bin"),
        ("+101", "bin"),
        ("5 7", "hex"),
        ("5_7", "hex"),
        ("10_10", "bin"),
        ("ZZ", "hex"),
        ("102", "bin"),
        ("0x", "hex"),
        ("0b", "bin"),
        ("{}", "hex"),
    ],
)
def test_parse_value_rejects_signed_and_malformed(text: str, base: str) -> None:
    with pytest.raises(ValueError):
        parse_value(text, base)


@pytest.mark.parametrize(
    "parse,text",
    [
        (BIN_TO_INT, "102"),
        (BIN_TO_INT, "0b"),
        (BIN_TO_INT, "-10"),
        (BIN_TO_INT, "1_01"),
        (HEX_TO_INT, "0x"),
        (HEX_TO_INT, "+5A"),
        (HEX_TO_INT, "{5a"),
        (HEX_TO_INT, "{  }"),
        (HEX_TO_INT, "ＦＦ"),
        (HEX_TO_INT, 123),
    ],
)
def test_malformed_operands(parse, text) -> None:
    with pytest.raises(ValueError):
        parse(text)


@pytest.mark.parametrize("format_value", [DEG, HAMMING_WEIGHT, INT_TO_ALGEBRAIC])
def test_invalid_bitmasks(format_value) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        format_value(-1)
    with pytest.raises(TypeError):
        format_value(True)


def test_negative_integer_rejection_across_engine() -> None:
    """Verify negative integers raise ValueError across formatting, reduction, and multiply."""
    with pytest.raises(ValueError, match="non-negative"):
        INT_TO_HEX(-5, 8)
    with pytest.raises(ValueError, match="non-negative"):
        INT_TO_BIN(-5, 8)
    with pytest.raises(ValueError, match="non-negative"):
        MOD_REDUCE(-1, 0x11B, 8)
    with pytest.raises(ValueError, match="non-negative"):
        multiply(-1, 0x02, 0x11B, 8)
    with pytest.raises(ValueError, match="non-negative"):
        multiply(0x02, -1, 0x11B, 8)
    with pytest.raises(ValueError, match="non-negative"):
        multiply_traced(-1, 0x02, 0x11B, 8)


def test_stallings_ch4_and_ch5_mod_reduce_and_multiply_smoke() -> None:
    """Smoke-test MOD_REDUCE and Shift-and-XOR multiply against Stallings Ch. 4 & 5."""
    m_poly = get_m_poly_int(8)  # 0x11B

    r_int, mod_trace = MOD_REDUCE(0x11B, m_poly, 8)
    assert r_int == 0
    assert mod_trace["was_reduced"] is True
    assert len(mod_trace["steps"]) == 1

    # Stallings Ch. 4: {57} * {83} mod {11B} = {C1}
    prod1, trace1 = multiply_traced(0x57, 0x83, m_poly, 8)
    assert prod1 == 0xC1
    assert trace1.algorithm == "shift-and-xor"

    # Stallings Ch. 5 AES: {02} * {87} mod {11B} = {15}
    prod2, trace2 = multiply_traced(0x02, 0x87, m_poly, 8)
    assert prod2 == 0x15
    assert trace2.reductions == 1

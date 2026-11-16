"""Verify the course's field definitions and lossless display conversions."""

import pytest

from gf2m_m1 import (
    BIN_TO_INT,
    DEFAULT_DEGREE,
    DEG,
    HAMMING_WEIGHT,
    HEX_TO_INT,
    INT_TO_ALGEBRAIC,
    INT_TO_BIN,
    INT_TO_HEX,
    get_field,
    is_supported,
    list_fields,
)
from gf2m_m1.polyrepr import ElementRepr, parse_value

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


@pytest.mark.parametrize("degree,taps", EXPECTED_TAPS.items())
def test_field_taps(degree, taps):
    field = get_field(degree)
    assert field.m == degree
    assert tuple(reversed(field.reduction_poly_terms)) == taps
    assert field.mod_poly == sum(2**term for term in taps)
    assert field.category == ("textbook" if degree < 163 else "nist")
    assert field.name == f"GF(2^{degree})"


def test_registry_filters_and_default():
    assert DEFAULT_DEGREE == 163
    assert [field.m for field in list_fields()] == list(EXPECTED_TAPS)
    assert [field.m for field in list_fields(include_textbook=False)] == [163, 233, 239, 283, 409, 571]


@pytest.mark.parametrize("degree", [0, 1, 9, 164, True, 8.0, "8"])
def test_unsupported_degrees(degree):
    assert not is_supported(degree)
    with pytest.raises(ValueError, match="unsupported field degree"):
        get_field(degree)


@pytest.mark.parametrize("m", [8, 163, 571])
def test_round_trip_and_minimum_width(m):
    for value in (0, 1, 2**(m - 1) | 0x3F, 2**m - 1):
        binary = INT_TO_BIN(value, m)
        hexadecimal = INT_TO_HEX(value, m)
        assert len(binary) == m
        assert len(hexadecimal) == (m + 3) // 4
        assert hexadecimal == hexadecimal.upper()
        assert BIN_TO_INT(binary) == HEX_TO_INT(hexadecimal) == value

    modulus = get_field(m).mod_poly
    assert BIN_TO_INT(INT_TO_BIN(modulus, m)) == HEX_TO_INT(INT_TO_HEX(modulus, m)) == modulus


def test_notation_and_metrics():
    assert BIN_TO_INT(" 0B0101 0111\t") == HEX_TO_INT(" {0X 5 7} ") == 0x57
    assert DEG(0) == -1
    assert HAMMING_WEIGHT(0) == 0
    assert INT_TO_ALGEBRAIC(0) == "0"
    assert INT_TO_ALGEBRAIC(0x57) == "x^6 + x^4 + x^2 + x + 1"
    assert INT_TO_ALGEBRAIC((1 << 162) | 2) == "x^162 + x"
    assert ElementRepr.from_int(0xD4, 8).dict() == {
        "hex": "d4", "bin": "11010100", "poly": "x^7 + x^6 + x^4 + x^2",
        "degree": 7, "bit_length": 8, "hamming_weight": 4,
    }
    assert parse_value("{0b1010}", "bin") == 10
    with pytest.raises(ValueError):
        parse_value("1 010", "bin")


@pytest.mark.parametrize("parse,text", [
    (BIN_TO_INT, "102"), (BIN_TO_INT, "0b"), (BIN_TO_INT, "-10"),
    (BIN_TO_INT, "1_01"), (HEX_TO_INT, "0x"), (HEX_TO_INT, "+5A"),
    (HEX_TO_INT, "{5a"), (HEX_TO_INT, "{  }"), (HEX_TO_INT, "ＦＦ"),
    (HEX_TO_INT, 123),
])
def test_malformed_operands(parse, text):
    with pytest.raises(ValueError):
        parse(text)


@pytest.mark.parametrize("format_value", [DEG, HAMMING_WEIGHT, INT_TO_ALGEBRAIC])
def test_invalid_bitmasks(format_value):
    with pytest.raises(ValueError):
        format_value(-1)
    with pytest.raises(TypeError):
        format_value(True)

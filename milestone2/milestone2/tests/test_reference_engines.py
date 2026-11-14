"""Reference M1/M3 engines used by the backend — correctness checks."""
import random

import pytest

from gf2m import multiply as M
from gf2m._reference import additive, inverse_division as invdiv
from gf2m._reference.fields import get_field, list_fields

ALL_M = [f.m for f in list_fields()]


# --- additive / modulo -------------------------------------------------------
def test_add_is_xor():
    assert additive.add(0b1010, 0b0110, 0, 4) == 0b1100
    assert additive.subtract(0b1010, 0b0110, 0, 4) == 0b1100  # same in char 2


@pytest.mark.parametrize("m", ALL_M)
def test_modulo_reduces_degree(m):
    f = get_field(m)
    rng = random.Random(7 + m)
    for _ in range(20):
        big = rng.getrandbits(2 * m)
        r = additive.modulo(big, f.mod_poly, f.m)
        assert r.bit_length() - 1 < f.m
        # reducing an already-reduced element is a no-op
        assert additive.modulo(r, f.mod_poly, f.m) == r


# --- inverse / division across all fields ------------------------------------
@pytest.mark.parametrize("m", ALL_M)
def test_inverse_identity(m):
    f = get_field(m)
    rng = random.Random(99 + m)
    for _ in range(20):
        a = rng.getrandbits(m) or 1
        inv = invdiv.inverse(a, f.mod_poly, f.m)
        assert M.multiply(a, inv, f.mod_poly, f.m) == 1


def test_inverse_of_one():
    f = get_field(163)
    assert invdiv.inverse(1, f.mod_poly, f.m) == 1


def test_inverse_of_zero_raises():
    f = get_field(163)
    with pytest.raises(invdiv.NoInverseError):
        invdiv.inverse(0, f.mod_poly, f.m)


@pytest.mark.parametrize("m", ALL_M)
def test_division_identity(m):
    f = get_field(m)
    rng = random.Random(123 + m)
    for _ in range(15):
        a = rng.getrandbits(m)
        b = rng.getrandbits(m) or 1
        q = invdiv.divide(a, b, f.mod_poly, f.m)
        # q * b == a (reduced)
        assert M.multiply(q, b, f.mod_poly, f.m) == additive.modulo(a, f.mod_poly, f.m)


def test_divide_by_zero_raises():
    f = get_field(8)
    with pytest.raises(invdiv.NoInverseError):
        invdiv.divide(0x53, 0, f.mod_poly, f.m)


def test_inverse_trace_present():
    f = get_field(8)
    _, trace = invdiv.inverse(0x53, f.mod_poly, f.m, with_trace=True)
    assert trace["algorithm"] == "extended-euclidean"
    assert trace["summary"]["iterations"] >= 1

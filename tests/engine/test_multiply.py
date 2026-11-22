"""Unit tests for the Shift-and-XOR multiplication engine and Table 1 & 2 traces."""
from __future__ import annotations

import random

import pytest

from backend.engine import polyrepr
from backend.engine.fields import get_field, list_fields
from backend.engine.multiply import carryless_mul, multiply, multiply_traced, reduce_mod

ALL_M = [field.m for field in list_fields()]


def brute_force(a: int, b: int, mod_poly: int, m: int) -> int:
    """Independent reference: full carry-free product followed by modulo reduction."""
    return reduce_mod(carryless_mul(a, b), mod_poly, m)


def test_known_small_case() -> None:
    f = get_field(3)  # 0b1101 (x^3 + x^2 + 1)
    assert multiply(0b101, 0b011, f.mod_poly, f.m) == 0b010


def test_known_chapter4_vector() -> None:
    f = get_field(8)  # 0x11B
    assert multiply(0b01010111, 0b10000011, f.mod_poly, f.m) == 0b11000001
    traced_res, trace = multiply_traced(0x57, 0x83, f.mod_poly, f.m)
    assert traced_res == 0xC1
    assert trace.steps[-1].accumulator_hex == "c1"


def test_known_aes_case() -> None:
    f = get_field(8)
    assert multiply(0x53, 0xCA, f.mod_poly, f.m) == 0x01
    assert multiply(0x02, 0x87, f.mod_poly, f.m) == 0x15
    traced_res, _ = multiply_traced(0x02, 0x87, f.mod_poly, f.m)
    assert traced_res == 0x15


@pytest.mark.parametrize("m", ALL_M)
def test_matches_brute_force(m: int) -> None:
    f = get_field(m)
    rng = random.Random(1000 + m)
    for _ in range(40):
        a = rng.getrandbits(m)
        b = rng.getrandbits(m)
        expected = brute_force(a, b, f.mod_poly, f.m)
        assert multiply(a, b, f.mod_poly, f.m) == expected


@pytest.mark.parametrize("m", ALL_M)
def test_traced_matches_fast(m: int) -> None:
    f = get_field(m)
    rng = random.Random(2000 + m)
    for _ in range(15):
        a = rng.getrandbits(m)
        b = rng.getrandbits(m)
        fast = multiply(a, b, f.mod_poly, f.m)
        traced, _ = multiply_traced(a, b, f.mod_poly, f.m)
        assert fast == traced


@pytest.mark.parametrize("m", [2, 3, 4, 5, 6, 7, 8])
def test_algebra_laws(m: int) -> None:
    f = get_field(m)
    mod, mm = f.mod_poly, f.m
    size = 1 << mm
    rng = random.Random(42 + m)
    for _ in range(30):
        a, b, c = (rng.randrange(size) for _ in range(3))
        assert multiply(a, 1, mod, mm) == a
        assert multiply(a, 0, mod, mm) == 0
        assert multiply(a, b, mod, mm) == multiply(b, a, mod, mm)
        ab_c = multiply(multiply(a, b, mod, mm), c, mod, mm)
        a_bc = multiply(a, multiply(b, c, mod, mm), mod, mm)
        assert ab_c == a_bc
        lhs = multiply(a, b ^ c, mod, mm)
        rhs = multiply(a, b, mod, mm) ^ multiply(a, c, mod, mm)
        assert lhs == rhs


def test_trace_tables_reconstruct_product() -> None:
    f = get_field(8)
    a, b = 0x53, 0xCA
    result, trace = multiply_traced(a, b, f.mod_poly, f.m)
    d = trace.dict()
    assert d["algorithm"] == "shift-and-xor"
    acc = 0
    for step in d["steps"]:
        if step["added"]:
            acc ^= int(step["partial_hex"], 16)
        assert int(step["accumulator_hex"], 16) == acc
    assert acc == result
    assert int(d["steps"][-1]["accumulator_hex"], 16) == result


def test_trace_result_in_field() -> None:
    f = get_field(163)
    a = (1 << 160) | 0b1011
    b = (1 << 100) | (1 << 7) | 1
    result, trace = multiply_traced(a, b, f.mod_poly, f.m)
    assert result.bit_length() - 1 < f.m
    assert trace.partial_products >= 1


def test_unreduced_inputs_are_reduced_internally() -> None:
    f = get_field(8)
    a_unred = (1 << 10) | 0x57
    b_unred = (1 << 9) | 0x83
    a_red = reduce_mod(a_unred, f.mod_poly, f.m)
    b_red = reduce_mod(b_unred, f.mod_poly, f.m)
    expected = multiply(a_red, b_red, f.mod_poly, f.m)
    assert multiply(a_unred, b_unred, f.mod_poly, f.m) == expected
    traced_res, trace = multiply_traced(a_unred, b_unred, f.mod_poly, f.m)
    assert traced_res == expected
    assert traced_res.bit_length() - 1 < f.m
    assert trace.operand_a_hex == polyrepr.to_hex(a_red, f.m)
    assert trace.operand_b_hex == polyrepr.to_hex(b_red, f.m)
    assert multiply(0x57, f.mod_poly, f.mod_poly, f.m) == 0


def test_trace_truncation_preserves_exact_product() -> None:
    f = get_field(571)
    a = (1 << 570) | (1 << 200) | 0xA5
    b = (1 << 571) - 1
    expected = multiply(a, b, f.mod_poly, f.m)
    result, trace = multiply_traced(a, b, f.mod_poly, f.m, max_steps=16)
    assert trace.truncated is True
    assert len(trace.steps) == 16
    assert result == expected

"""Milestone 2 multiplication engine — correctness and trace integrity."""
import random

import pytest

from gf2m import multiply as M, polyrepr
from gf2m._reference.fields import get_field, list_fields

ALL_M = [f.m for f in list_fields()]


def brute_force(a, b, mod_poly, m):
    """Independent reference: full carry-less product, then reduce."""
    return M.reduce_mod(M.carryless_mul(a, b), mod_poly, m)


# --- Known textbook case: GF(2^3), m(x)=x^3+x^2+1 -----------------------------
def test_known_small_case():
    f = get_field(3)  # 0b1101 (x^3 + x^2 + 1)
    # (x^2+1)(x+1) = x^3 + x^2 + x + 1 ≡ x (mod x^3 + x^2 + 1)
    assert M.multiply(0b101, 0b011, f.mod_poly, f.m) == 0b010


def test_known_chapter4_vector():
    f = get_field(8)  # 0b100011011 = 0x11b
    # Stallings Ch. 4: 01010111 * 10000011 mod 100011011 = 11000001 (0x57 * 0x83 = 0xC1)
    assert M.multiply(0b01010111, 0b10000011, f.mod_poly, f.m) == 0b11000001
    traced_res, trace = M.multiply_traced(0x57, 0x83, f.mod_poly, f.m)
    assert traced_res == 0xC1
    assert trace.steps[-1].accumulator_hex == "c1"


def test_known_aes_case():
    f = get_field(8)  # AES field x^8+x^4+x^3+x+1
    # Classic AES example: 0x53 * 0xCA = 0x01
    assert M.multiply(0x53, 0xCA, f.mod_poly, f.m) == 0x01
    # Stallings Ch. 5 AES vector: 0x02 * 0x87 mod 0x11b = 0x15
    assert M.multiply(0x02, 0x87, f.mod_poly, f.m) == 0x15
    traced_res, _ = M.multiply_traced(0x02, 0x87, f.mod_poly, f.m)
    assert traced_res == 0x15


# --- Engine matches the independent brute force across every field -----------
@pytest.mark.parametrize("m", ALL_M)
def test_matches_brute_force(m):
    f = get_field(m)
    rng = random.Random(1000 + m)
    for _ in range(40):
        a = rng.getrandbits(m)
        b = rng.getrandbits(m)
        expected = brute_force(a, b, f.mod_poly, f.m)
        assert M.multiply(a, b, f.mod_poly, f.m) == expected


# --- Traced path agrees with the fast path -----------------------------------
@pytest.mark.parametrize("m", ALL_M)
def test_traced_matches_fast(m):
    f = get_field(m)
    rng = random.Random(2000 + m)
    for _ in range(15):
        a = rng.getrandbits(m)
        b = rng.getrandbits(m)
        fast = M.multiply(a, b, f.mod_poly, f.m)
        traced, _ = M.multiply_traced(a, b, f.mod_poly, f.m)
        assert fast == traced


# --- Field algebra laws (checked on the small fields) ------------------------
@pytest.mark.parametrize("m", [2, 3, 4, 5, 6, 7, 8])
def test_algebra_laws(m):
    f = get_field(m)
    mod, mm = f.mod_poly, f.m
    size = 1 << mm
    rng = random.Random(42 + m)
    for _ in range(30):
        a, b, c = (rng.randrange(size) for _ in range(3))
        # identity and zero
        assert M.multiply(a, 1, mod, mm) == a
        assert M.multiply(a, 0, mod, mm) == 0
        # commutativity
        assert M.multiply(a, b, mod, mm) == M.multiply(b, a, mod, mm)
        # associativity
        ab_c = M.multiply(M.multiply(a, b, mod, mm), c, mod, mm)
        a_bc = M.multiply(a, M.multiply(b, c, mod, mm), mod, mm)
        assert ab_c == a_bc
        # distributivity over XOR addition
        lhs = M.multiply(a, b ^ c, mod, mm)
        rhs = M.multiply(a, b, mod, mm) ^ M.multiply(a, c, mod, mm)
        assert lhs == rhs


# --- Trace structure is well-formed and the tables reconstruct the product ---
def test_trace_tables_reconstruct_product():
    f = get_field(8)
    a, b = 0x53, 0xCA
    result, trace = M.multiply_traced(a, b, f.mod_poly, f.m)
    d = trace.dict()
    assert d["algorithm"] == "shift-and-xor"
    # Table 2 reconstruction: XOR every added partial product -> result.
    acc = 0
    for step in d["steps"]:
        if step["added"]:
            acc ^= int(step["partial_hex"], 16)
        # the recorded accumulator must match our running XOR
        assert int(step["accumulator_hex"], 16) == acc
    assert acc == result
    # final accumulator equals the product
    assert int(d["steps"][-1]["accumulator_hex"], 16) == result


def test_trace_result_in_field():
    f = get_field(163)
    a = (1 << 160) | 0b1011
    b = (1 << 100) | (1 << 7) | 1
    result, trace = M.multiply_traced(a, b, f.mod_poly, f.m)
    assert result.bit_length() - 1 < f.m          # degree < m
    assert trace.partial_products >= 1


def test_unreduced_inputs_are_reduced_internally():
    f = get_field(8)
    a_unred = (1 << 10) | 0x57
    b_unred = (1 << 9) | 0x83
    a_red = M.reduce_mod(a_unred, f.mod_poly, f.m)
    b_red = M.reduce_mod(b_unred, f.mod_poly, f.m)
    expected = M.multiply(a_red, b_red, f.mod_poly, f.m)
    assert M.multiply(a_unred, b_unred, f.mod_poly, f.m) == expected
    traced_res, trace = M.multiply_traced(a_unred, b_unred, f.mod_poly, f.m)
    assert traced_res == expected
    assert traced_res.bit_length() - 1 < f.m
    assert trace.operand_a_hex == polyrepr.to_hex(a_red, f.m)
    assert trace.operand_b_hex == polyrepr.to_hex(b_red, f.m)
    # b == m(x) reduces to 0 -> product is 0
    assert M.multiply(0x57, f.mod_poly, f.mod_poly, f.m) == 0


def test_trace_truncation_preserves_exact_product():
    f = get_field(571)
    a = (1 << 570) | (1 << 200) | 0xA5
    b = (1 << 571) - 1  # dense multiplier
    expected = M.multiply(a, b, f.mod_poly, f.m)
    result, trace = M.multiply_traced(a, b, f.mod_poly, f.m, max_steps=16)
    assert trace.truncated is True
    assert len(trace.steps) == 16
    assert result == expected


@pytest.mark.parametrize(
    "text,base,expected",
    [
        ("{57}", "hex", 0x57),
        (" {0x83} ", "hex", 0x83),
        ("{0b1011}", "bin", 0b1011),
    ],
)
def test_parse_value_accepts_braces(text, base, expected):
    assert polyrepr.parse_value(text, base) == expected


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
def test_parse_value_rejects_signed_and_malformed(text, base):
    with pytest.raises(ValueError):
        polyrepr.parse_value(text, base)

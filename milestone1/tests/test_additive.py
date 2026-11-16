"""Verify arithmetic results and the educational steps that produce them."""

import pytest

from gf2m_m1 import GF2M_ADD_SUB, MOD_REDUCE, get_field, list_fields
from gf2m_m1.additive import add, modulo, subtract, xor_trace

AES_MODULUS = 0x11B


def test_chapter_four_xor_rows():
    result, trace = GF2M_ADD_SUB(0x57, 0x83, AES_MODULUS, 8)
    assert result == add(0x57, 0x83, AES_MODULUS, 8) == subtract(0x57, 0x83, AES_MODULUS, 8) == 0xD4
    assert trace["a_bin"] == "01010111"
    assert trace["b_bin"] == "10000011"
    assert trace["result_bin"] == "11010100"
    assert trace["rows"]["result"] == {
        "bin": "11010100", "hex": "D4", "poly": "x^7 + x^6 + x^4 + x^2",
    }
    assert [column["exp"] for column in trace["columns"]] == list(reversed(range(8)))
    assert all(column["a"] ^ column["b"] == column["xor"] for column in trace["columns"])
    assert "".join(str(column["xor"]) for column in trace["columns"]) == trace["result_bin"]
    assert not trace["f_mod_trace"]["was_reduced"]
    assert not trace["g_mod_trace"]["was_reduced"]
    assert xor_trace(0x57, 0x83, 8)["rows"] == trace["rows"]


def test_aes_reduction_from_chapter_five():
    result, trace = MOD_REDUCE(0x10E, AES_MODULUS, 8)
    assert result == 0x15
    assert trace["steps"] == [{
        "target_degree": 8, "shift": 0, "before": 0x10E, "reducer": 0x11B, "after": 0x15,
    }]


def test_add_sub_traces_reduce_both_operands():
    a_int = (AES_MODULUS << 12) ^ (AES_MODULUS << 2) ^ 0x57
    b_int = (AES_MODULUS << 1) ^ 0x83
    result, trace = GF2M_ADD_SUB(a_int, b_int, AES_MODULUS, 8)
    assert result == 0xD4
    assert trace["f_mod_trace"]["initial_value"] == a_int
    assert [step["shift"] for step in trace["f_mod_trace"]["steps"]] == [12, 2]
    assert trace["g_mod_trace"]["reduced_value"] == 0x83


@pytest.mark.parametrize("m", [f.m for f in list_fields()])
def test_modulus_cancellation_and_self_inverse(m):
    mod_poly = get_field(m).mod_poly
    residue = (1 << (m - 1)) | 1
    value = (mod_poly << 17) ^ (mod_poly << 2) ^ mod_poly ^ residue
    result, trace = MOD_REDUCE(value, mod_poly, m)
    assert result == modulo(value, mod_poly, m) == residue
    assert [step["shift"] for step in trace["steps"]] == [17, 2, 0]
    assert trace["step_count"] == 3
    remainder = value
    for step in trace["steps"]:
        assert step["before"] == remainder
        assert step["target_degree"] == remainder.bit_length() - 1
        assert step["reducer"] == mod_poly << step["shift"]
        remainder ^= step["reducer"]
        assert step["after"] == remainder
    assert remainder == result
    assert GF2M_ADD_SUB(value, value, mod_poly, m)[0] == 0
    assert MOD_REDUCE(mod_poly, mod_poly, m)[0] == 0
    assert MOD_REDUCE(0, mod_poly, m)[1]["steps"] == []


@pytest.mark.parametrize("operand,mod_poly,m,error", [
    (-1, AES_MODULUS, 8, ValueError),
    (True, AES_MODULUS, 8, TypeError),
    (0, 0, 8, ValueError),
    (0, AES_MODULUS, 7, ValueError),
    (0, AES_MODULUS, 0, ValueError),
])
def test_reduction_rejects_invalid_arguments(operand, mod_poly, m, error):
    with pytest.raises(error):
        MOD_REDUCE(operand, mod_poly, m)

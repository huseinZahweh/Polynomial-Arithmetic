"""Regressions for the independent November 2026 source audit."""
import json
import random

import pytest

from backend.engine.explorations import gcm_ghash
from backend.engine.fields import get_field
from backend.engine.parser import parse_operand_file, OperandFileError
from backend.engine.polyrepr import parse_value
from backend.engine.exceptions import NotInvertibleError, ZeroElementHasNoInverseError
from backend.engine.extended_euclid import EXTENDED_EUCLID_GF2M
from backend.api.services import calculate
from backend.api.schemas import CalculateRequest


def nist_multiply(x, y):
    """Independent SP 800-38D Algorithm 1; no project arithmetic calls."""
    z, v = 0, y
    for i in range(128):
        if (x >> (127 - i)) & 1:
            z ^= v
        v = (v >> 1) ^ ((0xE1 << 120) if v & 1 else 0)
    return z


@pytest.mark.parametrize("h,blocks,expected", [
    ("80000000000000000000000000000000", ["1"], "00000000000000000000000000000001"),
    ("66E94BD4EF8A2C3B884CFA59CA342B2E", ["0388DACE60B6A392F328C2B971B2FE78"], "5E2EC746917062882C85B0685353DEB7"),
    ("66E94BD4EF8A2C3B884CFA59CA342B2E", ["0388DACE60B6A392F328C2B971B2FE78", "00000000000000000000000000000080"], "F38CBB1AD69223DCC3457AE5B6B0F885"),
])
def test_ghash_external_answers(h, blocks, expected):
    assert gcm_ghash(h, blocks)["tag_hex"] == expected


def test_ghash_random_against_nist_algorithm():
    rng = random.Random(380026)
    for count in range(1, 9):
        h = rng.getrandbits(128)
        blocks = [rng.getrandbits(128) for _ in range(count)]
        expected = 0
        for block in blocks:
            expected = nist_multiply(expected ^ block, h)
        result = gcm_ghash(f"{h:032X}", [f"{b:032X}" for b in blocks])
        assert int(result["tag_hex"], 16) == expected


@pytest.mark.parametrize("base,text", [("hex", "8" + "0" * 1023), ("bin", "1" + "0" * 4095), ("algebraic", "x^4095")])
def test_upload_accepts_exact_bit_boundary(base, text):
    pair = parse_operand_file(json.dumps({"a": text, "base": base}), "ok.json")[0]
    assert parse_value(pair["a"], pair["base"]) == 1 << 4095


@pytest.mark.parametrize("base,text", [("hex", "1" + "0" * 1024), ("bin", "1" + "0" * 4096), ("algebraic", "x^4096")])
def test_upload_rejects_over_bit_boundary(base, text):
    with pytest.raises(OperandFileError) as error:
        parse_operand_file(json.dumps({"a": text, "base": base}), "bad.json")
    assert (error.value.pair, error.value.field) == (1, "a")


def test_algebraic_batch_preserves_meaning():
    pair = parse_operand_file("base: algebraic\nA: x + x + 1\nB: x^7 + 1", "test.txt")[0]
    assert parse_value(pair["a"], pair["base"]) == 1
    assert parse_value(pair["b"], pair["base"]) == 129
    with pytest.raises(OperandFileError):
        parse_operand_file('base: algebraic\nA: x^1 2', 'bad.txt')


@pytest.mark.parametrize("m", [163, 233, 239, 283, 409, 571])
def test_untraced_inverse_matches_teaching_path(m):
    p = get_field(m).mod_poly
    for a in [1, 2, 0x123456789ABCDEF, p ^ 2]:
        expected, trace = EXTENDED_EUCLID_GF2M(p, m, a)
        result, empty = EXTENDED_EUCLID_GF2M(p, m, a, trace=False)
        assert result == expected
        assert empty == {}
        assert trace["termination"]["status"] == "invertible"


@pytest.mark.parametrize("a,p,m,error,gcd", [(0, 0x11B, 8, ZeroElementHasNoInverseError, 0x11B), (0x11B, 0x11B, 8, ZeroElementHasNoInverseError, 0x11B), (3, 5, 2, NotInvertibleError, 3)])
def test_untraced_inverse_preserves_domain_errors(a, p, m, error, gcd):
    with pytest.raises(error) as caught:
        EXTENDED_EUCLID_GF2M(p, m, a, trace=False)
    assert caught.value.gcd == gcd
    assert caught.value.trace is None


@pytest.mark.parametrize("operation", ["inverse", "divide"])
def test_untraced_service_does_not_format_rows(monkeypatch, operation):
    def unexpected(*args, **kwargs):
        raise AssertionError("untraced calculation formatted a teaching row")
    monkeypatch.setattr("backend.engine.extended_euclid._build_table_4_7_row", unexpected)
    result = calculate(CalculateRequest(m=571, operation=operation, a="123456789ABCDEF", b="83", trace=False))
    assert result.verification.passed
    assert result.trace is None

"""Verify random operands, uploads, calculation summaries, and share tokens."""

import json

import pytest

from gf2m_m1 import GENERATE_RANDOM_POLY, list_fields
from gf2m_m1.formatter import make_share_token, parse_share_token, render
from gf2m_m1.parser import OperandFileError, parse_operand_file
from gf2m_m1.polyrepr import ElementRepr, parse_value
from gf2m_m1.randomops import generate_operand


@pytest.mark.parametrize("m", [f.m for f in list_fields()])
def test_random_operands(m):
    seeded_dense = []
    for seed in range(8):
        dense = GENERATE_RANDOM_POLY(m, seed=seed)
        sparse = GENERATE_RANDOM_POLY(m, "sparse", seed=seed)
        assert 0 < dense < 1 << m
        assert 0 < sparse < 1 << m
        assert min(3, m - 1) <= sparse.bit_count() <= min(6, m)
        assert dense == generate_operand(m, "dense", seed)
        assert dense == generate_operand(m, "random", seed)
        assert sparse == generate_operand(m, "sparse", seed)
        seeded_dense.append(dense)
    assert len(set(seeded_dense)) > 1
    for mode in ("dense", "sparse"):
        assert 0 < GENERATE_RANDOM_POLY(m, mode) < 1 << m


@pytest.mark.parametrize("m,mode,seed", [(9, "dense", 1), (8, "other", 1), (8, "dense", True)])
def test_random_validation(m, mode, seed):
    with pytest.raises(ValueError):
        GENERATE_RANDOM_POLY(m, mode, seed=seed)


def test_parse_mixed_base_json_pairs():
    pairs = parse_operand_file(
        '\ufeff{"base":"hex","pairs":[{"a":"a1","b":"0f"},{"a":"0b10 11","base":"binary"}]}',
        "presets.JSON",
    )
    assert pairs == [{"a": "a1", "b": "0f", "base": "hex"}, {"a": "0b1011", "b": "", "base": "bin"}]
    assert parse_value(pairs[1]["a"], pairs[1]["base"]) == 11


def test_single_pair_and_bare_array():
    expected = [{"a": "{0x57}", "b": "83", "base": "hex"}]
    for content in ('{"a":"{0x57}","b":"83"}', '[{"a":"{0x57}","b":"83"}]'):
        assert parse_operand_file(content) == expected


def test_parse_labeled_text_pairs_and_inherited_base():
    content = """base: bin
---
A(x): 0101 0111 # first operand
B(x) = 0b1
===
A: 0001
---
base: hex
A: {5a}
B: ff
"""
    assert parse_operand_file(content, "presets.txt") == [
        {"a": "01010111", "b": "0b1", "base": "bin"},
        {"a": "0001", "b": "", "base": "bin"},
        {"a": "{5a}", "b": "ff", "base": "hex"},
    ]


@pytest.mark.parametrize("content,filename,message", [
    ("", "bad.txt", "empty"),
    ("# comment", "bad.txt", "no operand pairs"),
    ("{not JSON", "bad.json", "invalid JSON"),
    ('{"pairs":9}', "bad.json", "JSON array"),
    ('{"pairs":[]}', "bad.json", "no operand pairs"),
    ("[123]", "bad.json", "operand object"),
    ('{"b":"f"}', "bad.json", "operand string"),
    ('{"a":"1","b":2}', "bad.json", "operand string"),
    ('{"a":"-1"}', "bad.json", "invalid hexadecimal"),
    ('{"a":"1","base":"dec"}', "bad.json", "base must be hex or bin"),
    ("A: ZZ", "bad.txt", "invalid hexadecimal"),
    ("A: 3\nA: 2", "bad.txt", "duplicate label"),
    ("A: 3\nunknown: 2", "bad.txt", "expected an A, B, or base label"),
])
def test_rejects_malformed_file(content, filename, message):
    with pytest.raises(OperandFileError, match=message):
        parse_operand_file(content, filename)


def test_parser_error_locates_bad_operand():
    with pytest.raises(OperandFileError) as error:
        parse_operand_file("base: binary\nA: 1\n---\nA: 11\nB: 22", "bad.txt")
    assert (error.value.pair, error.value.line, error.value.field) == (2, 5, "b")


def test_exports_complete_api_payload():
    calc = {
        "field": {"m": 8, "reduction_poly_hex": "11b", "reduction_poly": "x^8 + x^4 + x^3 + x + 1"},
        "operation": "inverse",
        "operands": {"a": ElementRepr.from_int(0x95, 8).dict(), "b": None},
        "result": ElementRepr.from_int(0x8A, 8).dict(),
        "verification": {"label": "b times inverse equals 1", "passed": True},
        "metrics": {"elapsed_ms": 0.12, "result_bit_length": 8, "result_hamming_weight": 3},
        "trace": {"algorithm": "extended-euclid", "steps": [{"step": 0}]},
        "share_token": make_share_token(8, "inverse", "95", "", "bin"),
    }
    markdown, name, media = render(calc, "md")
    assert (name, media) == ("gf2_8_inverse.md", "text/markdown")
    for fragment in ("Calculation Summary", "10010101", "10001010", "**PASS**",
                     "0.12 ms", "Result Hamming weight: 3", "Educational trace",
                     "extended-euclid", calc["share_token"]):
        assert fragment in markdown
    assert "| B(x) |" not in markdown
    exported_json, name, media = render(calc, "json")
    assert (name, media) == ("gf2_8_inverse.json", "application/json")
    assert json.loads(exported_json) == calc
    with pytest.raises(ValueError, match="unsupported export format"):
        render(calc, "csv")


def test_share_token_compatibility():
    old_token = "76317c387c696e76657273657c39357c7c62696e"
    assert parse_share_token(old_token) == {
        "m": 8, "operation": "inverse", "a": "95", "b": "", "base": "bin",
    }
    assert make_share_token(8, "inverse", "95", "", "bin") == old_token
    with pytest.raises(ValueError, match="invalid calculation share token"):
        parse_share_token("broken")
    with pytest.raises(ValueError, match="unsupported token version"):
        parse_share_token(b"v2|8|inverse|95||bin".hex())

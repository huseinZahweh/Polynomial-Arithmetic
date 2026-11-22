"""Unit tests for random operands, batch uploads, exports, share tokens, and tutorial data."""
from __future__ import annotations

import json

import pytest

from backend.engine import (
    ElementRepr,
    GENERATE_RANDOM_POLY,
    MOD_REDUCE,
    OperandFileError,
    POLY_MUL_NO_MOD,
    generate_operand,
    get_field,
    list_fields,
    load_tutorial,
    make_share_token,
    parse_operand_file,
    parse_share_token,
    parse_value,
    render,
)


@pytest.mark.parametrize("m", [field.m for field in list_fields()])
def test_random_operands(m: int) -> None:
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
def test_random_validation(m, mode, seed) -> None:
    with pytest.raises(ValueError):
        GENERATE_RANDOM_POLY(m, mode, seed=seed)


def test_parse_mixed_base_json_pairs() -> None:
    pairs = parse_operand_file(
        '\ufeff{"base":"hex","pairs":[{"a":"a1","b":"0f"},{"a":"0b10 11","base":"binary"}]}',
        "presets.JSON",
    )
    assert pairs == [{"a": "a1", "b": "0f", "base": "hex"}, {"a": "0b1011", "b": "", "base": "bin"}]
    assert parse_value(pairs[1]["a"], pairs[1]["base"]) == 11


def test_single_pair_and_bare_array() -> None:
    expected = [{"a": "{0x57}", "b": "83", "base": "hex"}]
    for content in ('{"a":"{0x57}","b":"83"}', '[{"a":"{0x57}","b":"83"}]'):
        assert parse_operand_file(content) == expected


def test_parse_labeled_text_pairs_and_inherited_base() -> None:
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


@pytest.mark.parametrize(
    "content,filename,message",
    [
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
    ],
)
def test_rejects_malformed_file(content: str, filename: str, message: str) -> None:
    with pytest.raises(OperandFileError, match=message):
        parse_operand_file(content, filename)


def test_parser_error_locates_bad_operand() -> None:
    with pytest.raises(OperandFileError) as error:
        parse_operand_file("base: binary\nA: 1\n---\nA: 11\nB: 22", "bad.txt")
    assert (error.value.pair, error.value.line, error.value.field) == (2, 5, "b")


def test_exports_complete_api_payload() -> None:
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
    for fragment in (
        "Calculation Summary",
        "10010101",
        "10001010",
        "**PASS**",
        "0.12 ms",
        "Result Hamming weight: 3",
        "Educational trace",
        "extended-euclid",
        calc["share_token"],
    ):
        assert fragment in markdown
    assert "| B(x) |" not in markdown
    exported_json, name, media = render(calc, "json")
    assert (name, media) == ("gf2_8_inverse.json", "application/json")
    assert json.loads(exported_json) == calc
    with pytest.raises(ValueError, match="unsupported export format"):
        render(calc, "csv")


def test_share_token_compatibility() -> None:
    old_token = "76317c387c696e76657273657c39357c7c62696e"
    assert parse_share_token(old_token) == {
        "m": 8,
        "operation": "inverse",
        "a": "95",
        "b": "",
        "base": "bin",
    }
    assert make_share_token(8, "inverse", "95", "", "bin") == old_token
    with pytest.raises(ValueError, match="invalid calculation share token"):
        parse_share_token("broken")
    with pytest.raises(ValueError, match="unsupported token version"):
        parse_share_token(b"v2|8|inverse|95||bin".hex())


def test_tutorial_and_preset_schema(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    tutorial = load_tutorial()
    assert tutorial["version"] == "1.0"
    assert tutorial["title"]
    slides = tutorial["slides"]
    assert [slide["id"] for slide in slides] == [1, 2, 3, 4]
    assert all(slide["title"] and slide["body"] and slide["key_points"] for slide in slides)
    assert any("B3(x) = 1" in text and "B2(x)" in text for text in slides[2]["key_points"])
    assert any("B3(x) = 0" in text and "gcd" in text for text in slides[2]["key_points"])
    assert [preset["id"] for preset in slides[3]["presets"]] == ["ch4-gf256", "ch5-aes-inverse"]


def test_preset_results_match_field_identities() -> None:
    multiply_preset, inverse_preset = load_tutorial()["slides"][3]["presets"]
    modulus = get_field(8).mod_poly
    assert (
        multiply_preset["m"],
        multiply_preset["operation"],
        multiply_preset["a"],
        multiply_preset["b"],
    ) == (8, "multiply", "57", "83")
    a, b, expected = (
        parse_value(multiply_preset[key], multiply_preset["input_base"])
        for key in ("a", "b", "expected_hex")
    )
    assert MOD_REDUCE(POLY_MUL_NO_MOD(a, b), modulus, 8)[0] == expected == 0xC1

    assert (inverse_preset["m"], inverse_preset["operation"], inverse_preset["a"]) == (
        8,
        "inverse",
        "95",
    )
    a, expected = (
        parse_value(inverse_preset[key], inverse_preset["input_base"])
        for key in ("a", "expected_hex")
    )
    assert expected == 0x8A
    assert MOD_REDUCE(POLY_MUL_NO_MOD(a, expected), modulus, 8)[0] == 1

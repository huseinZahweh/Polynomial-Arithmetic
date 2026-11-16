"""Verify the tutorial schema and field identities used by the presets."""

from gf2m_m1 import MOD_REDUCE, get_field
from gf2m_m1.polyrepr import parse_value
from gf2m_m1.tutorial import load_tutorial


def test_tutorial_and_preset_schema(tmp_path, monkeypatch):
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


def _product(a, b):
    """Build an unreduced product for checking the two tutorial examples."""
    result = 0
    for exponent in range(b.bit_length()):
        if b & (1 << exponent):
            result ^= a << exponent
    return result


def test_preset_results_match_field_identities():
    multiply, inverse = load_tutorial()["slides"][3]["presets"]
    modulus = get_field(8).mod_poly
    assert (multiply["m"], multiply["operation"], multiply["a"], multiply["b"]) == (8, "multiply", "57", "83")
    a, b, expected = (parse_value(multiply[key], multiply["input_base"])
                      for key in ("a", "b", "expected_hex"))
    assert MOD_REDUCE(_product(a, b), modulus, 8)[0] == expected == 0xC1

    assert (inverse["m"], inverse["operation"], inverse["a"]) == (8, "inverse", "95")
    a, expected = (parse_value(inverse[key], inverse["input_base"])
                   for key in ("a", "expected_hex"))
    assert expected == 0x8A
    assert MOD_REDUCE(_product(a, expected), modulus, 8)[0] == 1

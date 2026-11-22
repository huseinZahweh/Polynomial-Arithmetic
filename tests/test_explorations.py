"""Check factor witnesses and compare the new labs against independent calculations."""

from fastapi.testclient import TestClient
import pytest

from lab import app
from app.schemas import Base
from explorations import ModulusRequest, SBoxRequest, aes_sbox, explore_modulus
from gf2m.multiply import multiply
from gf2m_m3.poly_ops import DivisionStep, POLY_DIVMOD, POLY_MUL_NO_MOD


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as api:
        yield api


def test_modulus_classification_and_witnesses():
    # For small degrees, trial division is an independent, exhaustive check.
    for degree in range(2, 9):
        for f in range(1 << degree, 1 << (degree + 1)):
            result = explore_modulus(ModulusRequest(polynomial=format(f, "x"), input_base=Base.hex))
            factors = any(POLY_DIVMOD(f, d)[1] == 0 for d in range(2, 1 << (degree // 2 + 1)))
            assert result["irreducible"] == (not factors), hex(f)
            if factors:
                witness = result["witness"]
                a, b = (int(witness[key]["hex"], 16) for key in ("a", "b"))
                assert 1 < a < f and 1 < b < f
                assert POLY_MUL_NO_MOD(a, b) == f
                assert int(witness["remainder"]["hex"], 16) == 0


def test_modulus_endpoint_and_equal_degree_factors(client):
    example = client.post("/api/explorations/modulus", json={"polynomial": "x^8 + 1"}).json()
    assert not example["irreducible"]
    assert example["witness"]["a"]["poly"] == "x + 1"
    # The product of the two irreducible cubics requires splitting a GCD of f itself.
    f = POLY_MUL_NO_MOD(0xB, 0xD)
    split = client.post("/api/explorations/modulus", json={"polynomial": f"{f:X}", "input_base": "hex"}).json()
    assert split["split_with_berlekamp"]
    assert {split["witness"][key]["hex"] for key in ("a", "b")} == {"b", "d"}
    maximum = client.post("/api/explorations/modulus", json={"polynomial": "x^571 + x^10 + x^5 + x^2 + 1"}).json()
    assert maximum["irreducible"]
    assert len(maximum["checks"]) == 285
    for invalid in ("0", "x", "x^572 + 1", "2x^8"):
        assert client.post("/api/explorations/modulus", json={"polynomial": invalid}).status_code == 400


def test_aes_all_bytes_against_inverse_by_exponentiation_and_bit_formula():
    for byte in range(256):
        reference_inverse = 1
        for _ in range(254):
            reference_inverse = multiply(reference_inverse, byte, 0x11B, 8)
        expected = 0x63
        for destination in range(8):
            for offset in (0, 4, 5, 6, 7):
                bit = (reference_inverse >> ((destination + offset) % 8)) & 1
                expected ^= bit << destination
        result = aes_sbox(SBoxRequest(byte=f"{byte:02X}"))
        assert int(result["inverse"]["hex"], 16) == reference_inverse
        assert int(result["output"]["hex"], 16) == expected
        assert result["affine_rows"][-1]["running"] == result["output"]


def test_aes_known_values_and_invalid_byte(client):
    endpoint = "/api/explorations/aes-sbox"
    standard = client.post(endpoint, json={"byte": "01010011", "input_base": "binary"}).json()
    assert standard["inverse"]["hex"] == "ca"
    assert standard["output"]["hex"] == "ed"
    assert standard["inverse_trace"]["table_4_7_rows"][-1]["B3"] == 1
    zero = client.post(endpoint, json={"byte": "00"}).json()
    assert zero["output"]["hex"] == "63"
    assert zero["inverse_trace"] is None
    assert client.post(endpoint, json={"byte": "100"}).status_code == 400


def test_comparison_preserves_exact_results_and_trace(client):
    endpoint = "/api/explorations/compare-multiplication"
    data = client.post(endpoint, json={"m": 8, "a": "57", "b": "83"}).json()
    assert data["agree"]
    assert data["raw_product"]["hex"] == "2b79"
    assert data["quotient"]["hex"] == "28"
    assert data["remainder"]["hex"] == data["shift_result"]["hex"] == "c1"
    assert data["division_steps"][-1]["after_hex"] == "C1"
    data = client.post(endpoint, json={"m": 8, "a": "100", "b": "0"}).json()
    assert data["inputs_reduced"]
    assert data["a"]["hex"] == "1b"
    assert data["remainder"]["hex"] == "00"
    assert not data["division_steps"]
    assert client.post(endpoint, json={"m": 9, "a": "1", "b": "1"}).status_code == 400


def test_long_division_trace_and_benchmark(client):
    rows: list[DivisionStep] = []
    quotient, remainder = POLY_DIVMOD(0x2B79, 0x11B, steps=rows)
    assert (quotient, remainder) == (0x28, 0xC1)
    assert len(rows) == 2
    assert all(row.before ^ row.shifted_divisor == row.after for row in rows)
    timings = client.get("/api/explorations/multiplication-benchmarks").json()
    assert timings["trials"] == 31
    assert [row["m"] for row in timings["rows"]] == [163, 571]
    assert all(row["agree"] and row["shift_xor_us"] > 0 and row["long_division_us"] > 0 for row in timings["rows"])

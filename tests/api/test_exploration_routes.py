"""FastAPI TestClient coverage for the four /api/explorations/* routes."""
from __future__ import annotations

from backend.engine import POLY_MUL_NO_MOD


def test_modulus_endpoint_and_equal_degree_factors(client) -> None:
    example = client.post("/api/explorations/modulus", json={"polynomial": "x^8 + 1"}).json()
    assert not example["irreducible"]
    assert example["witness"]["a"]["poly"] == "x + 1"

    # Product of two irreducible cubics triggers Berlekamp equal-degree splitting.
    f = POLY_MUL_NO_MOD(0xB, 0xD)
    split = client.post(
        "/api/explorations/modulus", json={"polynomial": f"{f:X}", "input_base": "hex"}
    ).json()
    assert split["split_with_berlekamp"]
    assert {split["witness"][key]["hex"] for key in ("a", "b")} == {"b", "d"}

    maximum = client.post(
        "/api/explorations/modulus", json={"polynomial": "x^571 + x^10 + x^5 + x^2 + 1"}
    ).json()
    assert maximum["irreducible"]
    assert len(maximum["checks"]) == 285

    for invalid in ("0", "x", "x^572 + 1", "2x^8"):
        assert client.post("/api/explorations/modulus", json={"polynomial": invalid}).status_code == 400


def test_aes_known_values_and_invalid_byte(client) -> None:
    endpoint = "/api/explorations/aes-sbox"
    standard = client.post(endpoint, json={"byte": "01010011", "input_base": "binary"}).json()
    assert standard["inverse"]["hex"] == "ca"
    assert standard["output"]["hex"] == "ed"
    assert standard["inverse_trace"]["table_4_7_rows"][-1]["B3"] == 1

    zero = client.post(endpoint, json={"byte": "00"}).json()
    assert zero["output"]["hex"] == "63"
    assert zero["inverse_trace"] is None

    assert client.post(endpoint, json={"byte": "100"}).status_code == 400


def test_comparison_preserves_exact_results_and_trace(client) -> None:
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


def test_benchmark_endpoint(client) -> None:
    timings = client.get("/api/explorations/multiplication-benchmarks").json()
    assert timings["trials"] == 31
    assert [row["m"] for row in timings["rows"]] == [163, 571]
    assert all(
        row["agree"] and row["shift_xor_us"] > 0 and row["long_division_us"] > 0
        for row in timings["rows"]
    )

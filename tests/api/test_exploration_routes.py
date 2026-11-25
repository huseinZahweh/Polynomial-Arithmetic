"""FastAPI TestClient coverage for the six /api/explorations/* routes."""
from __future__ import annotations

from backend.engine import POLY_MUL_NO_MOD


def test_modulus_endpoint_and_equal_degree_factors(client) -> None:
    """Verify irreducibility checks, Berlekamp splitting, and 400 validation on /modulus."""
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


def test_xts_tweak_endpoint_and_validation(client) -> None:
    """Verify POST /api/explorations/xts-tweak overflow XOR 0x87 and validation."""
    endpoint = "/api/explorations/xts-tweak"
    resp = client.post(
        endpoint,
        json={"t0_hex": "80000000000000000000000000000001", "steps": 4},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["m"] == 128
    assert len(data["blocks"]) == 5
    assert data["blocks"][1]["overflowed"] is True
    assert data["blocks"][1]["reduced_xor_87"] is True
    assert int(data["blocks"][1]["tweak_hex"], 16) == 0x85
    assert data["blocks"][2]["overflowed"] is False
    assert int(data["blocks"][2]["tweak_hex"], 16) == 0x10A

    assert client.post(endpoint, json={"t0_hex": "1" + "0" * 32, "steps": 2}).status_code == 400
    assert client.post(endpoint, json={"t0_hex": "ZZZZ", "steps": 2}).status_code == 400
    assert client.post("/api/explorations/aes-sbox", json={"byte": "53"}).status_code == 404


def test_binary_ecc_endpoint_gf2_4_and_nist_b163(client) -> None:
    """Verify POST /api/explorations/binary-ecc for GF(2^4), NIST B-163, and error handling."""
    endpoint = "/api/explorations/binary-ecc"
    small = client.post(endpoint, json={"curve": "gf2_4", "n_a": 5, "n_b": 9}).json()
    assert int(small["doubling"]["result"]["x"]["hex"], 16) == 0xA
    assert int(small["doubling"]["result"]["y"]["hex"], 16) == 0xB
    assert small["ecdh"]["shared_secret_matches"] is True

    b163 = client.post(endpoint, json={"curve": "nist_b163", "n_a": 5, "n_b": 9}).json()
    assert b163["curve"]["m"] == 163
    assert b163["curve"]["base_point_g"]["on_curve"] is True
    assert b163["doubling"]["result"]["on_curve"] is True
    assert b163["addition"]["result"]["on_curve"] is True
    assert b163["ecdh"]["shared_secret_matches"] is True
    assert b163["ecdh"]["all_points_on_curve"] is True

    # Off-curve custom point and unknown curve return HTTP 400.
    assert client.post(endpoint, json={"curve": "gf2_4", "p_x": "1", "p_y": "1"}).status_code == 400
    assert client.post(endpoint, json={"curve": "unknown"}).status_code == 400


def test_gcm_ghash_endpoint_and_validation(client) -> None:
    """Verify POST /api/explorations/gcm-ghash HTTP 200 computation and HTTP 400 validation."""
    endpoint = "/api/explorations/gcm-ghash"
    h_hex = "66E94BD4EF8A2C3B884CFA59CA342B2E"
    blocks = [
        "0388DACE60B6A392F328C2B971B2FE78",
        "D9313225F88406E5A55909C5AFF5269A",
        "00000000000000000000000000000080",
    ]
    resp = client.post(endpoint, json={"h_hex": h_hex, "blocks_hex": blocks})
    assert resp.status_code == 200
    data = resp.json()
    assert data["m"] == 128
    assert data["h_hex"] == h_hex
    assert data["block_count"] == 3
    assert len(data["steps"]) == 3
    assert data["steps"][-1]["y_i_hex"] == data["tag_hex"]
    assert len(data["tag_hex"]) == 32

    # Invalid hex, overflow (> 128 bits), empty blocks, and > 8 blocks all return HTTP 400.
    assert client.post(endpoint, json={"h_hex": "NOTHEX", "blocks_hex": blocks[:1]}).status_code == 400
    assert client.post(endpoint, json={"h_hex": "1" + "0" * 32, "blocks_hex": blocks[:1]}).status_code == 400
    assert client.post(endpoint, json={"h_hex": h_hex, "blocks_hex": []}).status_code == 400
    assert client.post(endpoint, json={"h_hex": h_hex, "blocks_hex": blocks[:1] * 9}).status_code == 400
    assert client.post(endpoint, json={"h_hex": h_hex, "blocks_hex": ["-5"]}).status_code == 400


def test_comparison_preserves_exact_results_and_trace(client) -> None:
    """Verify Shift-and-XOR vs. carry-free + long division comparison endpoint."""
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
    """Verify GET /api/explorations/multiplication-benchmarks at 163 and 571 bits."""
    timings = client.get("/api/explorations/multiplication-benchmarks").json()
    assert timings["trials"] == 31
    assert [row["m"] for row in timings["rows"]] == [163, 571]
    assert all(
        row["agree"] and row["shift_xor_us"] > 0 and row["long_division_us"] > 0
        for row in timings["rows"]
    )

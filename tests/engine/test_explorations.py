"""Pure-engine verification for Modulus irreducibility, XTS-AES GF(2^128), Binary ECC, and GCM/GHASH."""
from __future__ import annotations

import pytest

from backend.engine import (
    ECC_CURVES,
    GHASH_MODULUS,
    POLY_DIVMOD,
    POLY_MUL_NO_MOD,
    add,
    compute_xts_tweak,
    ecc_add,
    ecc_double,
    ecc_is_on_curve,
    ecc_scalar_mul,
    explore_binary_ecc,
    explore_modulus,
    gcm_ghash,
    get_field,
    multiply,
)


def test_modulus_classification_and_witnesses() -> None:
    """Exhaustively cross-check irreducibility and factor witnesses for all degrees 2..8."""
    for degree in range(2, 9):
        for f in range(1 << degree, 1 << (degree + 1)):
            result = explore_modulus(f)
            has_factor = any(POLY_DIVMOD(f, d)[1] == 0 for d in range(2, 1 << (degree // 2 + 1)))
            assert result["irreducible"] == (not has_factor), hex(f)
            if has_factor:
                witness = result["witness"]
                a, b = (int(witness[key]["hex"], 16) for key in ("a", "b"))
                assert 1 < a < f and 1 < b < f
                assert POLY_MUL_NO_MOD(a, b) == f
                assert int(witness["remainder"]["hex"], 16) == 0


def test_xts_tweak_overflow_and_non_overflow() -> None:
    """Verify IEEE 1619-2007 GF(2^128) tweak shifts with and without MSB overflow XOR 0x87."""
    # Start with MSB = 1 (0x8000...0001): Step 1 overflows x^128 and XORs 0x87; Step 2 does not overflow.
    t0 = (1 << 127) | 1
    data = compute_xts_tweak(t0, steps=3)
    assert data["m"] == 128
    assert data["reduction_mask_hex"] == "87"
    assert len(data["blocks"]) == 4

    b0, b1, b2, b3 = data["blocks"]
    assert b0["block_index"] == 0 and not b0["overflowed"]
    # (0x8000...0001 << 1) mod (x^128 + x^7 + x^2 + x + 1) = 0x02 XOR 0x87 = 0x85.
    assert b1["msb_before_shift"] == 1
    assert b1["overflowed"] is True and b1["reduced_xor_87"] is True
    assert int(b1["shifted_hex"], 16) == 0x02
    assert int(b1["tweak_hex"], 16) == 0x85

    # Next shift has MSB = 0 -> pure left shift 0x85 << 1 = 0x10A without XOR 0x87.
    assert b2["msb_before_shift"] == 0
    assert b2["overflowed"] is False and b2["reduced_xor_87"] is False
    assert int(b2["tweak_hex"], 16) == 0x10A
    assert int(b3["tweak_hex"], 16) == 0x214

    with pytest.raises(ValueError):
        compute_xts_tweak(1 << 128, steps=2)
    with pytest.raises(ValueError):
        compute_xts_tweak(1, steps=17)


def test_binary_ecc_gf2_4_hand_verified_and_edge_cases() -> None:
    """Verify hand-checked GF(2^4) doubling 2(3, C) = (A, B), point addition, infinity, and ECDH."""
    f4 = get_field(4)
    p = (0x3, 0xC)
    assert ecc_is_on_curve(p, 1, 1, f4.mod_poly, 4)

    p2, _ = ecc_double(p, 1, f4.mod_poly, 4)
    assert p2 == (0xA, 0xB)
    assert ecc_is_on_curve(p2, 1, 1, f4.mod_poly, 4)

    # P + (-P) = O where -P = (x, x XOR y) = (3, F).
    neg_p = (0x3, 0x3 ^ 0xC)
    assert ecc_is_on_curve(neg_p, 1, 1, f4.mod_poly, 4)
    inf, _ = ecc_add(p, neg_p, 1, f4.mod_poly, 4)
    assert inf is None

    # Identity laws: O + P = P and P + O = P; vertical tangent x = 0 doubles to O.
    assert ecc_add(None, p, 1, f4.mod_poly, 4)[0] == p
    assert ecc_add(p, None, 1, f4.mod_poly, 4)[0] == p
    assert ecc_double((0, 1), 1, f4.mod_poly, 4)[0] is None

    # P + P delegates cleanly to 2P.
    assert ecc_add(p, p, 1, f4.mod_poly, 4)[0] == p2

    # Full exploration payload + ECDH shared-secret match.
    res = explore_binary_ecc("gf2_4", n_a=5, n_b=9)
    assert int(res["doubling"]["result"]["x"]["hex"], 16) == 0xA
    assert int(res["doubling"]["result"]["y"]["hex"], 16) == 0xB
    assert res["addition"]["result"]["on_curve"] is True
    assert res["ecdh"]["shared_secret_matches"] is True
    assert res["ecdh"]["all_points_on_curve"] is True


def test_binary_ecc_nist_b163_base_point_doubling_addition_and_ecdh() -> None:
    """Verify official NIST FIPS 186-4 B-163 base point G, 2G, G + 2G, and ECDH shared secret."""
    spec = ECC_CURVES["nist_b163"]
    f163 = get_field(163)
    g = (spec["gx"], spec["gy"])
    assert ecc_is_on_curve(g, spec["a"], spec["b"], f163.mod_poly, 163)

    g2, _ = ecc_double(g, spec["a"], f163.mod_poly, 163)
    assert g2 is not None and ecc_is_on_curve(g2, spec["a"], spec["b"], f163.mod_poly, 163)

    g3, _ = ecc_add(g, g2, spec["a"], f163.mod_poly, 163)
    assert g3 is not None and ecc_is_on_curve(g3, spec["a"], spec["b"], f163.mod_poly, 163)
    assert ecc_scalar_mul(3, g, spec["a"], f163.mod_poly, 163) == g3

    res = explore_binary_ecc("nist_b163", n_a=5, n_b=9)
    assert res["curve"]["m"] == 163
    assert res["curve"]["base_point_g"]["on_curve"] is True
    assert res["doubling"]["result"]["on_curve"] is True
    assert res["addition"]["result"]["on_curve"] is True
    assert res["ecdh"]["shared_secret_matches"] is True
    assert res["ecdh"]["all_points_on_curve"] is True
    assert res["ecdh"]["shared_a"] == res["ecdh"]["shared_b"]


def test_gcm_ghash_identities_edge_cases_and_validation() -> None:
    """Verify GCM/GHASH single-block, multi-block Horner identity, zero edge cases, and input validation."""
    h_hex = "66E94BD4EF8A2C3B884CFA59CA342B2E"
    x1_hex = "0388DACE60B6A392F328C2B971B2FE78"
    x2_hex = "D9313225F88406E5A55909C5AFF5269A"
    h_int = int(h_hex, 16)
    x1_int = int(x1_hex, 16)
    x2_int = int(x2_hex, 16)

    # 1. Single-block identity: Y_1 = X_1 * H mod m(x) using NIST MSB-first bit order.
    def reverse(value: int) -> int:
        return int(f"{value:0128b}"[::-1], 2)

    single = gcm_ghash(h_hex, [x1_hex])
    expected_y1 = reverse(multiply(reverse(x1_int), reverse(h_int), GHASH_MODULUS, 128))
    assert single["block_count"] == 1
    assert single["output_kind"] == "ghash"
    assert single["modulus_poly"] == "x^128 + x^7 + x^2 + x + 1"
    assert int(single["tag_hex"], 16) == expected_y1
    assert len(single["tag_hex"]) == 32
    assert single["steps"][0]["prev_y_hex"] == "0" * 32
    assert single["steps"][0]["xor_input_hex"] == x1_hex
    assert single["steps"][0]["y_i_hex"] == single["tag_hex"]
    assert single["elapsed_ms"] >= 0

    # 2. Multi-block algebraic polynomial identity: Y_2 = (X_1 * H^2) XOR (X_2 * H) mod m(x).
    two_blocks = gcm_ghash(h_hex, [x1_hex, x2_hex])
    h_sq = multiply(reverse(h_int), reverse(h_int), GHASH_MODULUS, 128)
    expected_y2 = reverse(
        add(
            multiply(reverse(x1_int), h_sq, GHASH_MODULUS, 128),
            multiply(reverse(x2_int), reverse(h_int), GHASH_MODULUS, 128),
            GHASH_MODULUS,
            128,
        )
    )
    assert two_blocks["block_count"] == 2
    assert int(two_blocks["tag_hex"], 16) == expected_y2
    assert two_blocks["steps"][1]["prev_y_hex"] == single["tag_hex"]

    # 3. Zero key / zero block edge cases.
    zero_key = gcm_ghash("0", [x1_hex, x2_hex])
    assert int(zero_key["tag_hex"], 16) == 0
    assert zero_key["tag_poly"] == "0"
    zero_blk = gcm_ghash(h_hex, ["0"])
    assert int(zero_blk["tag_hex"], 16) == 0

    # 4. Invalid inputs raise ValueError.
    with pytest.raises(ValueError):
        gcm_ghash("ZZZZ", [x1_hex])
    with pytest.raises(ValueError):
        gcm_ghash("-1", [x1_hex])
    with pytest.raises(ValueError):
        gcm_ghash("1" + "0" * 32, [x1_hex])
    with pytest.raises(ValueError):
        gcm_ghash(h_hex, [])
    with pytest.raises(ValueError):
        gcm_ghash(h_hex, [x1_hex] * 9)
    with pytest.raises(ValueError):
        gcm_ghash(h_hex, ["1" + "0" * 32])

"""Pure-engine verification for Modulus irreducibility, Berlekamp splitting, and AES S-box."""
from __future__ import annotations

from backend.engine import (
    POLY_DIVMOD,
    POLY_MUL_NO_MOD,
    compute_aes_sbox,
    explore_modulus,
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


def test_aes_all_bytes_against_inverse_by_exponentiation_and_bit_formula() -> None:
    """Exhaustively verify all 256 AES S-box outputs against a^254 and FIPS 197 bit math."""
    for byte in range(256):
        reference_inverse = 1
        for _ in range(254):
            reference_inverse = multiply(reference_inverse, byte, 0x11B, 8)
        expected = 0x63
        for destination in range(8):
            for offset in (0, 4, 5, 6, 7):
                bit = (reference_inverse >> ((destination + offset) % 8)) & 1
                expected ^= bit << destination
        result = compute_aes_sbox(byte)
        assert int(result["inverse"]["hex"], 16) == reference_inverse
        assert int(result["output"]["hex"], 16) == expected
        assert result["affine_rows"][-1]["running"] == result["output"]

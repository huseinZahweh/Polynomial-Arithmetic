"""Unit tests for EXTENDED_EUCLID_GF2M and Stallings Table 4.7 traces."""
from __future__ import annotations

import random

import pytest

from backend.engine import (
    EXTENDED_EUCLID_GF2M,
    GF2mInverseError,
    NotInvertibleError,
    ZeroElementHasNoInverseError,
    get_field,
    get_m_poly_int,
    list_supported_degrees,
    multiply,
)


class TestExtendedEuclidTextbook:
    """Verify exact textbook examples from Stallings Chapters 4 and 5."""

    def test_stallings_ch4_table_4_7_exact_trace(self) -> None:
        """Reproduce Table 4.7: {83}^(-1) mod {11B} = {80} in 3 division steps."""
        m_poly = get_m_poly_int(8)
        b_int = 0x83

        b_inv_int, trace = EXTENDED_EUCLID_GF2M(m_poly, 8, b_int)

        assert b_inv_int == 0x80
        assert trace["trace_type"] == "extended_euclid_table_4_7"
        assert trace["initial_reduction"]["was_reduced"] is False
        assert trace["termination"]["status"] == "invertible"
        assert trace["termination"]["b3_final"] == 1
        assert trace["termination"]["gcd_int"] == 1
        assert trace["termination"]["inverse_int"] == 0x80
        assert trace["termination"]["iterations"] == 3
        assert trace["termination"]["total_rows"] == 4

        rows = trace["table_4_7_rows"]
        assert len(rows) == 4

        expected_rows = [
            (0, None, 0x01, 0x00, 0x11B, 0x00, 0x01, 0x83),
            (1, 0x02, 0x00, 0x01, 0x83, 0x01, 0x02, 0x1D),
            (2, 0x0D, 0x01, 0x02, 0x1D, 0x0D, 0x1B, 0x02),
            (3, 0x0E, 0x0D, 0x1B, 0x02, 0x47, 0x80, 0x01),
        ]
        for row, (step, q_exp, a1, a2, a3, b1, b2, b3) in zip(rows, expected_rows):
            assert row["step"] == step
            assert row["Q"] == q_exp
            assert row["A1"] == a1
            assert row["A2"] == a2
            assert row["A3"] == a3
            assert row["B1"] == b1
            assert row["B2"] == b2
            assert row["B3"] == b3

        assert rows[0]["cells"]["Q"] == {
            "int": None,
            "hex": "-",
            "bin": "-",
            "algebraic": "-",
            "degree": None,
        }
        assert rows[3]["cells"]["B2"]["hex"] == "80"
        assert rows[3]["cells"]["B2"]["bin"] == "10000000"
        assert rows[3]["cells"]["B2"]["algebraic"] == "x^7"

    def test_stallings_ch5_aes_sbox_inverse(self) -> None:
        """Reproduce AES S-Box inversion: {95}^(-1) mod {11B} = {8A}."""
        m_poly = get_m_poly_int(8)
        b_inv_int, trace = EXTENDED_EUCLID_GF2M(m_poly, 8, 0x95)

        assert b_inv_int == 0x8A
        assert trace["termination"]["status"] == "invertible"
        assert trace["termination"]["iterations"] == 3
        assert trace["table_4_7_rows"][-1]["cells"]["B2"]["algebraic"] == "x^7 + x^3 + x"
        assert multiply(0x95, b_inv_int, m_poly, 8) == 1

    def test_inverse_trace_present_for_aes_byte(self) -> None:
        f = get_field(8)
        inv, trace = EXTENDED_EUCLID_GF2M(f.mod_poly, f.m, 0x53)
        assert inv == 0xCA
        assert trace["trace_type"] == "extended_euclid_table_4_7"
        assert trace["termination"]["iterations"] >= 1


class TestExtendedEuclidEdgeCases:
    """Verify edge cases, initial reduction, and both B3 == 0 error paths."""

    def test_zero_element_raises_with_step0_trace(self) -> None:
        m_poly = get_m_poly_int(8)
        with pytest.raises(ZeroElementHasNoInverseError) as exc_info:
            EXTENDED_EUCLID_GF2M(m_poly, 8, 0)

        err = exc_info.value
        assert err.gcd == m_poly
        assert err.trace is not None
        assert err.trace["termination"]["status"] == "zero_element"
        assert err.trace["termination"]["b3_final"] == 0
        assert err.trace["termination"]["gcd_int"] == m_poly
        assert err.trace["termination"]["iterations"] == 0
        assert len(err.trace["table_4_7_rows"]) == 1
        assert err.trace["table_4_7_rows"][0]["step"] == 0
        assert err.trace["table_4_7_rows"][0]["Q"] is None
        assert err.trace["table_4_7_rows"][0]["A3"] == m_poly
        assert err.trace["table_4_7_rows"][0]["B3"] == 0

    def test_inverse_of_one_and_zero_in_primary_field(self) -> None:
        f = get_field(163)
        inv, _ = EXTENDED_EUCLID_GF2M(f.mod_poly, f.m, 1)
        assert inv == 1
        with pytest.raises(GF2mInverseError):
            EXTENDED_EUCLID_GF2M(f.mod_poly, f.m, 0)

    def test_modulus_equivalent_to_zero_raises_zero_inverse_error(self) -> None:
        m_poly = get_m_poly_int(8)
        with pytest.raises(ZeroElementHasNoInverseError) as exc_info:
            EXTENDED_EUCLID_GF2M(m_poly, 8, m_poly)

        err = exc_info.value
        assert err.gcd == m_poly
        assert err.trace["initial_reduction"]["was_reduced"] is True
        assert err.trace["b_reduced_int"] == 0
        assert len(err.trace["table_4_7_rows"]) == 1

        multiple_of_m = (m_poly << 2) ^ m_poly
        with pytest.raises(ZeroElementHasNoInverseError) as exc_info_mult:
            EXTENDED_EUCLID_GF2M(m_poly, 8, multiple_of_m)
        assert exc_info_mult.value.gcd == m_poly
        assert exc_info_mult.value.trace["initial_reduction"]["was_reduced"] is True

    def test_identity_one_terminates_at_step_0(self) -> None:
        m_poly = get_m_poly_int(8)
        b_inv_int, trace = EXTENDED_EUCLID_GF2M(m_poly, 8, 1)

        assert b_inv_int == 1
        assert trace["termination"]["status"] == "invertible"
        assert trace["termination"]["iterations"] == 0
        assert trace["termination"]["total_rows"] == 1
        assert len(trace["table_4_7_rows"]) == 1
        assert trace["table_4_7_rows"][0]["B2"] == 1
        assert trace["table_4_7_rows"][0]["B3"] == 1

    def test_unreduced_input_auto_reduced_with_note(self) -> None:
        m_poly = get_m_poly_int(8)
        b_unreduced = (m_poly << 1) ^ 0x83

        b_inv_int, trace = EXTENDED_EUCLID_GF2M(m_poly, 8, b_unreduced)

        assert b_inv_int == 0x80
        assert trace["b_input_int"] == b_unreduced
        assert trace["b_reduced_int"] == 0x83
        assert trace["initial_reduction"]["was_reduced"] is True
        assert "reduced modulo m(x)" in trace["initial_reduction"]["note"]
        assert trace["termination"]["iterations"] == 3

    def test_reducible_modulus_single_step_not_invertible(self) -> None:
        reducible_m = 0b11011
        b_int = 0b101

        with pytest.raises(NotInvertibleError) as exc_info:
            EXTENDED_EUCLID_GF2M(reducible_m, 4, b_int)

        err = exc_info.value
        assert err.gcd == 0b101
        assert err.trace is not None
        assert err.trace["termination"]["status"] == "not_invertible"
        assert err.trace["termination"]["b3_final"] == 0
        assert err.trace["termination"]["gcd_int"] == 0b101
        assert err.trace["termination"]["iterations"] == 1
        rows = err.trace["table_4_7_rows"]
        assert len(rows) == 2
        assert rows[-1]["B3"] == 0
        assert rows[-1]["A3"] == 0b101

    def test_reducible_modulus_multistep_not_invertible(self) -> None:
        reducible_m = 0b110001
        b_int = 0b1001

        with pytest.raises(NotInvertibleError) as exc_info:
            EXTENDED_EUCLID_GF2M(reducible_m, 5, b_int)

        err = exc_info.value
        assert err.gcd == 0b111
        assert err.trace["termination"]["iterations"] == 2
        assert err.trace["table_4_7_rows"][-1]["B3"] == 0
        assert err.trace["table_4_7_rows"][-1]["A3"] == 0b111

    def test_negative_and_invalid_inputs_raise(self) -> None:
        m_poly = get_m_poly_int(8)
        with pytest.raises(ValueError, match="non-negative"):
            EXTENDED_EUCLID_GF2M(m_poly, 8, -1)
        with pytest.raises(ValueError, match="non-negative"):
            EXTENDED_EUCLID_GF2M(-m_poly, 8, 5)
        with pytest.raises(ValueError, match="degree"):
            EXTENDED_EUCLID_GF2M(m_poly, 7, 5)
        with pytest.raises(TypeError):
            EXTENDED_EUCLID_GF2M(m_poly, 8, True)  # type: ignore[arg-type]

    @pytest.mark.parametrize("m", list_supported_degrees())
    def test_inverse_identity_all_fields(self, m: int) -> None:
        field = get_field(m)
        rng = random.Random(99 + m)
        for _ in range(20):
            a = rng.getrandbits(m) or 1
            inv, _ = EXTENDED_EUCLID_GF2M(field.mod_poly, field.m, a)
            assert multiply(a, inv, field.mod_poly, field.m) == 1

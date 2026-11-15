"""Step 4 unit tests for GF2M_DIVIDE, VERIFY_INVERSE, and VERIFY_DIVISION."""
from __future__ import annotations

import pytest

from gf2m_m3 import (
    EXTENDED_EUCLID_GF2M,
    GF2M_DIVIDE,
    NotInvertibleError,
    VERIFY_DIVISION,
    VERIFY_INVERSE,
    ZeroElementHasNoInverseError,
)
from gf2m_m3._reference import get_m_poly_int, gf2m_multiply


class TestGf2mDivide:
    """Unit tests for two-stage field division GF2M_DIVIDE."""

    def test_textbook_ch4_and_ch5_division_identities(self) -> None:
        m_poly = get_m_poly_int(8)  # 0x11B

        # Stallings Ch. 4: {57} * {83} = {C1} => {C1} / {83} = {57}
        q1, trace1 = GF2M_DIVIDE(0xC1, 0x83, m_poly, 8)
        assert q1 == 0x57
        assert trace1["inverse_of_b_int"] == 0x80
        assert trace1["inverse_of_b"]["hex"] == "80"
        assert VERIFY_DIVISION(0xC1, 0x83, q1, m_poly, 8)["verified"] is True

        # Stallings Ch. 5 AES: {02} * {87} = {15} => {15} / {02} = {87}
        q2, _ = GF2M_DIVIDE(0x15, 0x02, m_poly, 8)
        assert q2 == 0x87
        assert VERIFY_DIVISION(0x15, 0x02, q2, m_poly, 8)["verified"] is True

        # AES S-Box check: 1 / {95} = {8A}
        q3, _ = GF2M_DIVIDE(1, 0x95, m_poly, 8)
        assert q3 == 0x8A

    def test_algebraic_identities_and_zero_numerator(self) -> None:
        m_poly = get_m_poly_int(8)

        # 0 / b = 0 for any non-zero b
        q_zero, _ = GF2M_DIVIDE(0, 0x83, m_poly, 8)
        assert q_zero == 0
        assert VERIFY_DIVISION(0, 0x83, q_zero, m_poly, 8)["verified"] is True

        # a / 1 = a mod m(x)
        q_unit, _ = GF2M_DIVIDE(0x57, 1, m_poly, 8)
        assert q_unit == 0x57

        # a / a = 1
        q_self, _ = GF2M_DIVIDE(0x95, 0x95, m_poly, 8)
        assert q_self == 1

        # (a * b) / b == a
        prod, _ = gf2m_multiply(0x57, 0x95, m_poly, 8)
        recovered, _ = GF2M_DIVIDE(prod, 0x95, m_poly, 8)
        assert recovered == 0x57

    def test_two_stage_trace_completeness(self) -> None:
        m_poly = get_m_poly_int(8)
        q_int, trace = GF2M_DIVIDE(0xC1, 0x83, m_poly, 8)

        assert q_int == 0x57
        assert trace["trace_type"] == "gf2m_division_two_stage"
        assert trace["m_degree"] == 8
        assert trace["m_poly_int"] == m_poly
        assert trace["a_input_int"] == 0xC1
        assert trace["b_input_int"] == 0x83
        assert trace["a_reduced_int"] == 0xC1
        assert trace["b_reduced_int"] == 0x83
        assert trace["initial_reduction"]["a_was_reduced"] is False
        assert trace["initial_reduction"]["b_was_reduced"] is False
        assert trace["quotient_int"] == 0x57
        assert trace["quotient_formatted"]["hex"] == "57"
        assert trace["inverse_of_b"]["int"] == 0x80
        assert trace["inverse_of_b"]["hex"] == "80"

        # Stage 1: Table 4.7 trace
        stage1 = trace["stage_1_inverse"]
        assert stage1["trace_type"] == "extended_euclid_table_4_7"
        assert stage1["termination"]["iterations"] == 3
        assert len(stage1["table_4_7_rows"]) == 4

        # Stage 2: Shift-and-XOR multiplication trace
        stage2 = trace["stage_2_multiply"]
        assert stage2["trace_type"] == "shift_and_xor"
        assert len(stage2["shift_steps"]) > 0
        assert len(stage2["selected_terms"]) > 0

    def test_unreduced_a_and_b_auto_reduced(self) -> None:
        m_poly = get_m_poly_int(8)
        a_unreduced = (m_poly << 2) ^ 0xC1
        b_unreduced = (m_poly << 1) ^ 0x83

        q_int, trace = GF2M_DIVIDE(a_unreduced, b_unreduced, m_poly, 8)

        assert q_int == 0x57
        assert trace["a_reduced_int"] == 0xC1
        assert trace["b_reduced_int"] == 0x83
        assert trace["initial_reduction"]["a_was_reduced"] is True
        assert trace["initial_reduction"]["b_was_reduced"] is True
        assert trace["stage_1_inverse"]["initial_reduction"]["was_reduced"] is True
        assert VERIFY_DIVISION(a_unreduced, b_unreduced, q_int, m_poly, 8)["verified"] is True

    def test_zero_and_modulus_divisors_raise_with_trace(self) -> None:
        m_poly = get_m_poly_int(8)

        for divisor in (0, m_poly, (m_poly << 1) ^ m_poly):
            with pytest.raises(ZeroElementHasNoInverseError) as exc_info:
                GF2M_DIVIDE(0x57, divisor, m_poly, 8)
            assert exc_info.value.gcd == m_poly
            assert exc_info.value.trace is not None
            assert len(exc_info.value.trace["table_4_7_rows"]) == 1

        # 0 / 0 must also fail (cannot divide by zero even when numerator is 0)
        with pytest.raises(ZeroElementHasNoInverseError):
            GF2M_DIVIDE(0, 0, m_poly, 8)

    def test_reducible_modulus_propagates_not_invertible_error(self) -> None:
        reducible_m = 0b11011  # (x^2 + 1)(x^2 + x + 1)
        with pytest.raises(NotInvertibleError) as exc_info:
            GF2M_DIVIDE(0b11, 0b101, reducible_m, 4)
        assert exc_info.value.gcd == 0b101
        assert exc_info.value.trace["termination"]["status"] == "not_invertible"

    def test_negative_and_invalid_inputs_rejected(self) -> None:
        m_poly = get_m_poly_int(8)
        with pytest.raises(ValueError, match="non-negative"):
            GF2M_DIVIDE(-1, 0x83, m_poly, 8)
        with pytest.raises(ValueError, match="non-negative"):
            GF2M_DIVIDE(0x57, -1, m_poly, 8)
        with pytest.raises(TypeError):
            GF2M_DIVIDE(True, 0x83, m_poly, 8)  # type: ignore[arg-type]


class TestLiveSelfVerifiers:
    """Unit tests for VERIFY_INVERSE and VERIFY_DIVISION (true & corrupted cases)."""

    def test_verify_inverse_true_and_false_cases(self) -> None:
        m_poly = get_m_poly_int(8)

        # True case: Ch. 4 Table 4.7
        b_inv, _ = EXTENDED_EUCLID_GF2M(m_poly, 8, 0x83)
        res_ok = VERIFY_INVERSE(0x83, b_inv, m_poly, 8)
        assert res_ok["verified"] is True
        assert res_ok["passed"] is True
        assert res_ok["check_result"] == 1
        assert res_ok["expected_result"] == 1
        assert res_ok["is_reduced_element"] is True
        assert "1" in res_ok["label"]

        # True case: unreduced b_int with reduced valid inverse
        res_unred = VERIFY_INVERSE((m_poly << 1) ^ 0x95, 0x8A, m_poly, 8)
        assert res_unred["verified"] is True

        # Corrupted false case 1: bit flip in inverse
        res_bad = VERIFY_INVERSE(0x83, b_inv ^ 0x01, m_poly, 8)
        assert res_bad["verified"] is False
        assert res_bad["passed"] is False
        assert res_bad["check_result"] != 1

        # Corrupted false case 2: zero inverse candidate
        res_zero = VERIFY_INVERSE(0x83, 0, m_poly, 8)
        assert res_zero["verified"] is False
        assert res_zero["check_result"] == 0

        # Corrupted false case 3: unreduced candidate (congruent mod m(x), deg >= m)
        res_unreduced_inv = VERIFY_INVERSE(0x83, b_inv ^ m_poly, m_poly, 8)
        assert res_unreduced_inv["verified"] is False
        assert res_unreduced_inv["is_reduced_element"] is False

    def test_verify_division_true_and_false_cases(self) -> None:
        m_poly = get_m_poly_int(8)
        q_int, _ = GF2M_DIVIDE(0xC1, 0x83, m_poly, 8)

        res_ok = VERIFY_DIVISION(0xC1, 0x83, q_int, m_poly, 8)
        assert res_ok["verified"] is True
        assert res_ok["passed"] is True
        assert res_ok["check_result"] == 0xC1
        assert res_ok["expected_result"] == 0xC1
        assert res_ok["nonzero_divisor"] is True
        assert res_ok["is_reduced_element"] is True

        # Corrupted false case 1: wrong quotient
        res_bad = VERIFY_DIVISION(0xC1, 0x83, q_int ^ 0x01, m_poly, 8)
        assert res_bad["verified"] is False
        assert res_bad["passed"] is False
        assert res_bad["check_result"] != 0xC1

        # Corrupted false case 2: unreduced quotient
        res_unreduced_q = VERIFY_DIVISION(0xC1, 0x83, q_int ^ m_poly, m_poly, 8)
        assert res_unreduced_q["verified"] is False
        assert res_unreduced_q["is_reduced_element"] is False

        # Corrupted false case 3: zero divisor (even when numerator is 0)
        res_zero_div = VERIFY_DIVISION(0, 0, 0, m_poly, 8)
        assert res_zero_div["verified"] is False
        assert res_zero_div["nonzero_divisor"] is False

        # Corrupted false case 4: modulus-equivalent divisor
        res_mod_div = VERIFY_DIVISION(0, m_poly, 0, m_poly, 8)
        assert res_mod_div["verified"] is False
        assert res_mod_div["nonzero_divisor"] is False

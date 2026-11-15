"""Step 2 unit tests for POLY_MUL_NO_MOD and POLY_DIVMOD over GF(2)[x]."""
from __future__ import annotations

import random

import pytest

from gf2m_m3 import POLY_DIVMOD, POLY_MUL_NO_MOD
from gf2m_m3._reference import deg, get_m_poly_int, list_supported_degrees


class TestPolyMulNoMod:
    """Unit tests for carry-free polynomial multiplication POLY_MUL_NO_MOD."""

    def test_zero_and_identity_operands(self) -> None:
        assert POLY_MUL_NO_MOD(0, 0) == 0
        assert POLY_MUL_NO_MOD(0, 0x11B) == 0
        assert POLY_MUL_NO_MOD(0x11B, 0) == 0
        assert POLY_MUL_NO_MOD(1, 0x83) == 0x83
        assert POLY_MUL_NO_MOD(0x83, 1) == 0x83

    def test_carry_free_gf2_cancellation(self) -> None:
        # (x + 1) * (x + 1) = x^2 + 2x + 1 == x^2 + 1 over GF(2)
        assert POLY_MUL_NO_MOD(0b11, 0b11) == 0b101
        # (x^2 + x + 1) * (x + 1) = x^3 + 1
        assert POLY_MUL_NO_MOD(0b111, 0b11) == 0b1001
        # Unreduced AES textbook product: (x^6+x^4+x^2+x+1)*(x^7+x+1)
        # Verify degree addition law deg(a*b) == deg(a) + deg(b)
        prod = POLY_MUL_NO_MOD(0x57, 0x83)
        assert deg(prod) == deg(0x57) + deg(0x83)

    def test_commutativity_and_distributivity(self) -> None:
        rng = random.Random(20261115)
        for _ in range(50):
            a_int = rng.getrandbits(64)
            b_int = rng.getrandbits(64)
            c_int = rng.getrandbits(64)
            assert POLY_MUL_NO_MOD(a_int, b_int) == POLY_MUL_NO_MOD(b_int, a_int)
            assert POLY_MUL_NO_MOD(a_int, b_int ^ c_int) == (
                POLY_MUL_NO_MOD(a_int, b_int) ^ POLY_MUL_NO_MOD(a_int, c_int)
            )

    def test_invalid_inputs_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            POLY_MUL_NO_MOD(-1, 5)
        with pytest.raises(ValueError, match="non-negative"):
            POLY_MUL_NO_MOD(5, -3)
        with pytest.raises(TypeError):
            POLY_MUL_NO_MOD(True, 5)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            POLY_MUL_NO_MOD(5, "3")  # type: ignore[arg-type]


class TestPolyDivMod:
    """Unit tests for polynomial Euclidean long division POLY_DIVMOD."""

    def test_zero_dividend_and_unit_divisor(self) -> None:
        assert POLY_DIVMOD(0, 1) == (0, 0)
        assert POLY_DIVMOD(0, 0x11B) == (0, 0)
        assert POLY_DIVMOD(0x83, 1) == (0x83, 0)
        assert POLY_DIVMOD(0x12345, 1) == (0x12345, 0)

    def test_deg_a_less_than_deg_b(self) -> None:
        assert POLY_DIVMOD(0x57, 0x83) == (0, 0x57)
        assert POLY_DIVMOD(1, 2) == (0, 1)
        assert POLY_DIVMOD(0x7F, 0x11B) == (0, 0x7F)

    def test_deg_a_equal_deg_b(self) -> None:
        # Equal polynomials divide cleanly to (1, 0)
        assert POLY_DIVMOD(0x83, 0x83) == (1, 0)
        # Same degree, distinct polynomials -> quotient 1, remainder a ^ b
        q_int, r_int = POLY_DIVMOD(0x83, 0x95)
        assert q_int == 1
        assert r_int == (0x83 ^ 0x95)
        assert deg(r_int) < deg(0x95)

    def test_exact_divisibility_zero_remainder(self) -> None:
        # (x^4 + x^3 + 1) * (x^3 + x + 1)
        factor_1 = 0b11001
        factor_2 = 0b1011
        product = POLY_MUL_NO_MOD(factor_1, factor_2)
        assert POLY_DIVMOD(product, factor_1) == (factor_2, 0)
        assert POLY_DIVMOD(product, factor_2) == (factor_1, 0)

    def test_stallings_table_4_7_first_division_step(self) -> None:
        # Step 1 of Table 4.7: (x^8 + x^4 + x^3 + x + 1) / (x^7 + x + 1)
        # Q(x) = x (0x02), R(x) = x^4 + x^3 + x^2 + 1 (0x1D)
        q_int, r_int = POLY_DIVMOD(0x11B, 0x83)
        assert q_int == 0x02
        assert r_int == 0x1D
        assert POLY_MUL_NO_MOD(q_int, 0x83) ^ r_int == 0x11B

    def test_error_cases(self) -> None:
        with pytest.raises(ZeroDivisionError):
            POLY_DIVMOD(0x83, 0)
        with pytest.raises(ZeroDivisionError):
            POLY_DIVMOD(0, 0)
        with pytest.raises(ValueError, match="non-negative"):
            POLY_DIVMOD(-1, 5)
        with pytest.raises(ValueError, match="non-negative"):
            POLY_DIVMOD(5, -1)
        with pytest.raises(TypeError):
            POLY_DIVMOD(5, False)  # type: ignore[arg-type]

    @pytest.mark.parametrize("m_degree", list_supported_degrees())
    def test_round_trip_identity_across_all_fields(self, m_degree: int) -> None:
        """Verify POLY_MUL_NO_MOD(q, b) ^ r == a and deg(r) < deg(b) for m=2..571."""
        rng = random.Random(455000 + m_degree)
        m_poly_int = get_m_poly_int(m_degree)

        for _ in range(15):
            # Generate operands up to degree ~2*m to exercise multi-step division
            a_int = rng.getrandbits(min(2 * m_degree, 1200))
            b_int = rng.getrandbits(m_degree) | 1  # guaranteed non-zero

            q_int, r_int = POLY_DIVMOD(a_int, b_int)
            assert POLY_MUL_NO_MOD(q_int, b_int) ^ r_int == a_int
            assert r_int == 0 or deg(r_int) < deg(b_int)

            # Also test dividing an unreduced product by m_poly_int
            q_mod, r_mod = POLY_DIVMOD(a_int, m_poly_int)
            assert POLY_MUL_NO_MOD(q_mod, m_poly_int) ^ r_mod == a_int
            assert r_mod == 0 or deg(r_mod) < m_degree

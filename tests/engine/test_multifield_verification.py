"""Multi-field automated verification suite for GF(2^m) inverse, division, and benchmarks."""
from __future__ import annotations

import random

import pytest

from backend.engine import (
    DEG,
    EXTENDED_EUCLID_GF2M,
    GF2M_DIVIDE,
    POLY_MUL_NO_MOD,
    VERIFY_DIVISION,
    VERIFY_INVERSE,
    get_m_poly_int,
    list_supported_degrees,
)


def _sample_sparse_nonzero(rng: random.Random, m_degree: int) -> int:
    """Sample a nonzero sparse polynomial with 3..6 set bits below degree m."""
    count = min(m_degree, rng.randint(3, 6))
    positions = rng.sample(range(m_degree), k=count)
    value = 0
    for pos in positions:
        value |= 1 << pos
    return value


def _sample_dense_nonzero(rng: random.Random, m_degree: int) -> int:
    """Sample a uniformly random nonzero m-bit polynomial in [1, 2^m - 1]."""
    return rng.randrange(1, 1 << m_degree)


class TestExhaustiveGF256:
    """Exhaustive verification over all 255 nonzero bytes in GF(2^8)."""

    def test_all_255_nonzero_elements_in_gf2_8_have_unique_inverses(self) -> None:
        m_degree = 8
        m_poly_int = get_m_poly_int(m_degree)
        inverses: set[int] = set()

        for b_int in range(1, 256):
            b_inv_int, trace = EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_int)

            assert 1 <= b_inv_int < 256
            assert DEG(b_inv_int) < m_degree
            assert trace["termination"]["status"] == "invertible"

            inv_check = VERIFY_INVERSE(b_int, b_inv_int, m_poly_int, m_degree)
            assert inv_check["verified"] is True

            double_inv, _ = EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_inv_int)
            assert double_inv == b_int
            inverses.add(b_inv_int)

        assert len(inverses) == 255

    def test_gf2_8_division_pairs_across_all_255_divisors(self) -> None:
        m_degree = 8
        m_poly_int = get_m_poly_int(m_degree)
        rng = random.Random(202608)

        for b_int in range(1, 256):
            a_int = rng.randrange(0, 256)
            q_int, div_trace = GF2M_DIVIDE(a_int, b_int, m_poly_int, m_degree)

            assert 0 <= q_int < 256
            assert DEG(q_int) < m_degree
            assert div_trace["quotient_int"] == q_int

            div_check = VERIFY_DIVISION(a_int, b_int, q_int, m_poly_int, m_degree)
            assert div_check["verified"] is True


class TestSmallTextbookFields:
    """Exhaustive verification across all small textbook fields 2 <= m <= 7."""

    @pytest.mark.parametrize("m_degree", [2, 3, 4, 5, 6, 7])
    def test_exhaustive_inverses_and_divisions_small_fields(self, m_degree: int) -> None:
        m_poly_int = get_m_poly_int(m_degree)
        field_size = 1 << m_degree
        rng = random.Random(1000 + m_degree)
        inverses: set[int] = set()

        for b_int in range(1, field_size):
            b_inv_int, _ = EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_int)
            assert 1 <= b_inv_int < field_size
            assert DEG(b_inv_int) < m_degree
            assert VERIFY_INVERSE(b_int, b_inv_int, m_poly_int, m_degree)["verified"] is True

            double_inv, _ = EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_inv_int)
            assert double_inv == b_int
            inverses.add(b_inv_int)

            a_int = rng.randrange(0, field_size)
            q_int, _ = GF2M_DIVIDE(a_int, b_int, m_poly_int, m_degree)
            assert DEG(q_int) < m_degree
            assert VERIFY_DIVISION(a_int, b_int, q_int, m_poly_int, m_degree)["verified"] is True

        assert len(inverses) == field_size - 1


class TestCryptographicFields:
    """Seeded sparse, dense, and unreduced verification for m in {163..571}."""

    @pytest.mark.parametrize("m_degree", list_supported_degrees(include_textbook=False))
    @pytest.mark.parametrize("mode", ["sparse", "dense"])
    def test_cryptographic_fields_inverse_and_division(
        self,
        m_degree: int,
        mode: str,
    ) -> None:
        m_poly_int = get_m_poly_int(m_degree)
        seed = (455632 + m_degree) if mode == "dense" else (990000 + m_degree)
        rng = random.Random(seed)
        sampler = _sample_sparse_nonzero if mode == "sparse" else _sample_dense_nonzero

        for _ in range(4):
            a_int = sampler(rng, m_degree)
            b_int = sampler(rng, m_degree)

            b_inv_int, inv_trace = EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_int)
            assert 1 <= b_inv_int < (1 << m_degree)
            assert DEG(b_inv_int) < m_degree
            assert inv_trace["termination"]["status"] == "invertible"
            assert VERIFY_INVERSE(b_int, b_inv_int, m_poly_int, m_degree)["verified"] is True

            double_inv, _ = EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_inv_int)
            assert double_inv == b_int

            q_int, div_trace = GF2M_DIVIDE(a_int, b_int, m_poly_int, m_degree)
            assert 0 <= q_int < (1 << m_degree)
            assert DEG(q_int) < m_degree
            assert div_trace["inverse_of_b_int"] == b_inv_int
            assert VERIFY_DIVISION(a_int, b_int, q_int, m_poly_int, m_degree)["verified"] is True

    @pytest.mark.parametrize("m_degree", list_supported_degrees(include_textbook=False))
    def test_unreduced_operands_in_cryptographic_fields(self, m_degree: int) -> None:
        """Verify deg >= m operands auto-reduce cleanly and preserve identities."""
        m_poly_int = get_m_poly_int(m_degree)
        rng = random.Random(777000 + m_degree)

        a_base = _sample_dense_nonzero(rng, m_degree)
        b_base = _sample_dense_nonzero(rng, m_degree)
        noise_a = rng.randrange(1, 1 << 16)
        noise_b = rng.randrange(1, 1 << 16)
        a_unreduced = a_base ^ POLY_MUL_NO_MOD(m_poly_int, noise_a)
        b_unreduced = b_base ^ POLY_MUL_NO_MOD(m_poly_int, noise_b)

        b_inv_int, inv_trace = EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_unreduced)
        assert inv_trace["initial_reduction"]["was_reduced"] is True
        assert inv_trace["b_reduced_int"] == b_base
        assert VERIFY_INVERSE(b_unreduced, b_inv_int, m_poly_int, m_degree)["verified"] is True

        q_int, div_trace = GF2M_DIVIDE(a_unreduced, b_unreduced, m_poly_int, m_degree)
        assert div_trace["initial_reduction"]["a_was_reduced"] is True
        assert div_trace["initial_reduction"]["b_was_reduced"] is True
        assert VERIFY_DIVISION(a_unreduced, b_unreduced, q_int, m_poly_int, m_degree)["verified"] is True


def test_benchmark_runner_smoke() -> None:
    """Verify benchmarks.benchmark_gf2m executes and emits valid Markdown rows."""
    from benchmarks.benchmark_gf2m import format_markdown_table, run_benchmarks

    rows = run_benchmarks(degrees=(8, 163), trials=2, seed=455632)
    assert len(rows) == 4
    table = format_markdown_table(rows)
    assert "$GF(2^{8})$" in table
    assert "$GF(2^{163})$" in table
    assert "Sparse" in table
    assert "Dense" in table

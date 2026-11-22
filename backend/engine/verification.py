"""Live algebraic self-verification helpers for GF(2^m) inverse and division.

Original Author
---------------
Husein Zahweh — Milestone 3 (Extended Euclid Inverse, Field Division & Verification).

Mathematical Context & Course References
----------------------------------------
Produces structured runtime proof objects so the API and web workbench can
independently check every inversion and division result via the fast-path
Shift-and-XOR multiplier:

* **Inverse identity:** ``b(x) * b(x)^(-1) mod m(x) == 1`` with ``deg(b^-1) < m``.
* **Division identity:** ``(a(x) / b(x)) * b(x) mod m(x) == a(x) mod m(x)`` with
  ``b(x) mod m(x) != 0`` and ``deg(q) < m``.

References William Stallings, *Cryptography and Network Security*, **Chapter 4**
(Finite Fields), **Chapter 5** (AES S-Box), **Chapter 6** (XTS-AES over
``GF(2^128)``), and **Chapter 10** (Binary ECC over ``GF(2^163)..GF(2^571)``).
"""
from __future__ import annotations

from typing import Any

from .additive import modulo
from .multiply import multiply
from .polyrepr import (
    format_poly_representations,
    validate_modulus,
    validate_non_negative_poly,
)


def VERIFY_INVERSE(
    b_int: int,
    b_inv_int: int,
    m_poly_int: int,
    m_degree: int,
) -> dict[str, Any]:
    """Verify the finite-field inverse identity ``b(x) * b^-1(x) mod m(x) == 1``.

    Also requires ``b_inv_int`` to be a canonical reduced field element
    (``0 <= b_inv_int < 2^m_degree``) so unreduced congruent polynomials fail.

    Args:
        b_int: Input polynomial bitmask ``b(x)``.
        b_inv_int: Candidate multiplicative inverse ``b(x)^(-1) mod m(x)``.
        m_poly_int: Reduction polynomial bitmask of degree ``m_degree`` (bit ``m`` set).
        m_degree: Extension field degree ``m >= 1``.

    Returns:
        Structured proof dictionary containing ``verified``, ``passed``,
        ``label``, ``equation``, ``check_result``, ``expected_result``,
        ``check_result_formatted``, ``expected_result_formatted``, and
        ``is_reduced_element``.

    Raises:
        TypeError: If any argument is not an ``int`` (or is a ``bool``).
        ValueError: If polynomials are negative or ``deg(m_poly_int) != m_degree``.

    Complexity:
        Time ``O(m^2)`` bit operations for one fast-path Shift-and-XOR product;
        space ``O(m)`` for formatted proof fields.
    """
    validate_non_negative_poly(b_int, name="b_int")
    validate_non_negative_poly(b_inv_int, name="b_inv_int")
    validate_modulus(m_poly_int, m_degree)

    is_reduced = b_inv_int < (1 << m_degree)
    check_result = multiply(b_int, b_inv_int, m_poly_int, m_degree)
    verified = is_reduced and (check_result == 1)

    return {
        "verified": verified,
        "passed": verified,
        "label": "b(x) * b^-1(x) mod m(x) == 1",
        "equation": "b(x) * b^-1(x) mod m(x) == 1",
        "check_result": check_result,
        "expected_result": 1,
        "check_result_formatted": format_poly_representations(check_result, m_degree=m_degree),
        "expected_result_formatted": format_poly_representations(1, m_degree=m_degree),
        "is_reduced_element": is_reduced,
    }


def VERIFY_DIVISION(
    a_int: int,
    b_int: int,
    q_int: int,
    m_poly_int: int,
    m_degree: int,
) -> dict[str, Any]:
    """Verify the field division identity ``(a(x)/b(x)) * b(x) mod m(x) == a(x) mod m(x)``.

    Explicitly verifies ``b_int mod m(x) != 0`` and ``q_int < 2^m_degree`` so
    degenerate zero-divisor products (like ``0 * 0 == 0``) cannot pass falsely.

    Args:
        a_int: Dividend polynomial bitmask ``a(x)``.
        b_int: Divisor polynomial bitmask ``b(x)``.
        q_int: Candidate field quotient ``a(x) / b(x) mod m(x)``.
        m_poly_int: Reduction polynomial bitmask of degree ``m_degree`` (bit ``m`` set).
        m_degree: Extension field degree ``m >= 1``.

    Returns:
        Structured proof dictionary containing ``verified``, ``passed``,
        ``label``, ``equation``, ``check_result``, ``expected_result``,
        ``check_result_formatted``, ``expected_result_formatted``,
        ``is_reduced_element``, and ``nonzero_divisor``.

    Raises:
        TypeError: If any argument is not an ``int`` (or is a ``bool``).
        ValueError: If polynomials are negative or ``deg(m_poly_int) != m_degree``.

    Complexity:
        Time ``O(m^2)`` bit operations for modular reductions and one Shift-and-XOR
        multiplication; space ``O(m)`` for formatted proof fields.
    """
    validate_non_negative_poly(a_int, name="a_int")
    validate_non_negative_poly(b_int, name="b_int")
    validate_non_negative_poly(q_int, name="q_int")
    validate_modulus(m_poly_int, m_degree)

    a_red = modulo(a_int, m_poly_int, m_degree)
    b_red = modulo(b_int, m_poly_int, m_degree)
    nonzero_divisor = b_red != 0
    is_reduced = q_int < (1 << m_degree)
    check_result = multiply(q_int, b_red, m_poly_int, m_degree)
    verified = nonzero_divisor and is_reduced and (check_result == a_red)

    return {
        "verified": verified,
        "passed": verified,
        "label": "(a(x) / b(x)) * b(x) mod m(x) == a(x) mod m(x)",
        "equation": "(a(x) / b(x)) * b(x) mod m(x) == a(x) mod m(x)",
        "check_result": check_result,
        "expected_result": a_red,
        "check_result_formatted": format_poly_representations(check_result, m_degree=m_degree),
        "expected_result_formatted": format_poly_representations(a_red, m_degree=m_degree),
        "is_reduced_element": is_reduced,
        "nonzero_divisor": nonzero_divisor,
    }

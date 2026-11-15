"""Live algebraic self-verification helpers for GF(2^m) inverse and division.

Implements :func:`VERIFY_INVERSE` and :func:`VERIFY_DIVISION` per
``Plan/Milestones/03_extended_euclid_inverse_division_and_verification_suite.md``
Section 3 so the backend/GUI can attach a live mathematical proof badge to
every inversion and division result.

References
----------
* Stallings, *Cryptography and Network Security*, Chapter 4 (Finite Fields),
  Chapter 5 (AES S-Box), Chapter 6 (XTS-AES over GF(2^128)), and Chapter 10
  (Binary ECC over GF(2^163)...GF(2^571)).
"""
from __future__ import annotations

from typing import Any, Dict

from ._reference import (
    format_poly_representations,
    gf2m_multiply,
    mod_reduce,
    validate_modulus,
    validate_non_negative_poly,
)


def VERIFY_INVERSE(
    b_int: int,
    b_inv_int: int,
    m_poly_int: int,
    m_degree: int,
) -> Dict[str, Any]:
    """Verify the finite-field inverse identity ``b(x) * b^-1(x) mod m(x) == 1``.

    Also checks that the candidate inverse ``b_inv_int`` is a properly reduced
    element of GF(2^m) (``0 <= b_inv_int < 2^m_degree``).

    Args:
        b_int: Input polynomial ``b(x)`` (non-negative ``int``).
        b_inv_int: Candidate multiplicative inverse ``b(x)^(-1) mod m(x)``.
        m_poly_int: Irreducible modulus ``m(x)`` of degree ``m_degree``.
        m_degree: Extension field degree ``m >= 1``.

    Returns:
        Structured verification dictionary containing:
        * ``verified`` (``bool``): ``True`` iff ``b_inv_int < 2^m_degree`` and
          ``b(x) * b_inv(x) mod m(x) == 1``.
        * ``passed`` (``bool``): Alias of ``verified`` matching Plan 03 / M2 schema.
        * ``label`` / ``equation`` (``str``): Human-readable identity label.
        * ``check_result`` (``int``): Computed product ``b * b_inv mod m(x)``.
        * ``expected_result`` (``int``): Always ``1``.
        * ``is_reduced_element`` (``bool``): Whether ``deg(b_inv_int) < m_degree``.

    Raises:
        TypeError: If any argument is not an ``int`` (or is a ``bool``).
        ValueError: If any polynomial is negative or ``deg(m_poly_int) != m_degree``.

    Complexity:
        ``O(m^2)`` bit operations for one Shift-and-XOR modular multiplication,
        where ``m = m_degree``.
    """
    validate_non_negative_poly(b_int, name="b_int")
    validate_non_negative_poly(b_inv_int, name="b_inv_int")
    validate_modulus(m_poly_int, m_degree)

    is_reduced = b_inv_int < (1 << m_degree)
    check_result, _ = gf2m_multiply(b_int, b_inv_int, m_poly_int, m_degree)
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
) -> Dict[str, Any]:
    """Verify the field division identity ``(a(x)/b(x)) * b(x) mod m(x) == a(x) mod m(x)``.

    Also requires ``q_int`` to be a reduced field element (``q_int < 2^m_degree``)
    and ``b_int mod m_poly_int != 0`` so degenerate zero-divisor products cannot
    falsely validate.

    Args:
        a_int: Dividend polynomial ``a(x)`` (non-negative ``int``).
        b_int: Divisor polynomial ``b(x)`` (non-negative ``int``).
        q_int: Candidate field quotient ``a(x) / b(x) mod m(x)``.
        m_poly_int: Irreducible modulus ``m(x)`` of degree ``m_degree``.
        m_degree: Extension field degree ``m >= 1``.

    Returns:
        Structured verification dictionary containing ``verified``, ``passed``,
        ``label``, ``equation``, ``check_result``, ``expected_result``,
        ``is_reduced_element``, and ``nonzero_divisor``.

    Raises:
        TypeError: If any argument is not an ``int`` (or is a ``bool``).
        ValueError: If any polynomial is negative or ``deg(m_poly_int) != m_degree``.

    Complexity:
        ``O(m^2)`` bit operations for modular reduction and Shift-and-XOR
        multiplication, where ``m = m_degree``.
    """
    validate_non_negative_poly(a_int, name="a_int")
    validate_non_negative_poly(b_int, name="b_int")
    validate_non_negative_poly(q_int, name="q_int")
    validate_modulus(m_poly_int, m_degree)

    a_red, _ = mod_reduce(a_int, m_poly_int, m_degree)
    b_red, _ = mod_reduce(b_int, m_poly_int, m_degree)
    nonzero_divisor = b_red != 0
    is_reduced = q_int < (1 << m_degree)
    check_result, _ = gf2m_multiply(q_int, b_red, m_poly_int, m_degree)
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

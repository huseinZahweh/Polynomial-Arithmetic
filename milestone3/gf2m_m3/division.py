"""Field division engine over GF(2^m) with two-stage educational trace.

Implements :func:`GF2M_DIVIDE` per
``Plan/Milestones/03_extended_euclid_inverse_division_and_verification_suite.md``
Section 2.4 and ``Plan/README.md``:

.. math::

    \\frac{a(x)}{b(x)} \\bmod m(x) = a(x) \\times \\left(b(x)^{-1} \\bmod m(x)\\right) \\bmod m(x)

References
----------
* Stallings, *Cryptography and Network Security*, Chapter 4 (Finite Fields):
  multiplicative inversion via Extended Euclid and modular multiplication via
  Shift-and-XOR.
* Stallings Chapter 5 (AES over GF(2^8)), Chapter 6 (XTS-AES over GF(2^128)),
  and Chapter 10 (Binary ECC over GF(2^163)...GF(2^571)).
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from ._reference import (
    format_poly_representations,
    gf2m_multiply,
    mod_reduce,
    validate_modulus,
    validate_non_negative_poly,
)
from .extended_euclid import EXTENDED_EUCLID_GF2M


def GF2M_DIVIDE(
    a_int: int,
    b_int: int,
    m_poly_int: int,
    m_degree: int,
) -> Tuple[int, Dict[str, Any]]:
    """Compute field division ``a(x) / b(x) mod m(x)`` in GF(2^m).

    Executes in two documented stages:
    1. **Stage 1 (Inverse):** Invokes
       :func:`~gf2m_m3.extended_euclid.EXTENDED_EUCLID_GF2M` on ``b_int`` to
       obtain ``b_inv_int = b(x)^(-1) mod m(x)`` and its Table 4.7 trace.
       If ``b(x) mod m(x) == 0`` or ``gcd(m(x), b(x)) != 1``,
       :class:`ZeroElementHasNoInverseError` or :class:`NotInvertibleError`
       propagates directly with ``gcd`` and ``trace`` preserved.
    2. **Stage 2 (Multiply):** Invokes Shift-and-XOR ``gf2m_multiply`` on
       ``a_red`` and ``b_inv_int`` modulo ``m_poly_int`` to obtain
       ``quotient_int`` and its Shift-and-XOR multiplication trace.

    Args:
        a_int: Dividend polynomial ``a(x)`` (non-negative ``int``; auto-reduced
            if ``deg(a_int) >= m_degree``).
        b_int: Divisor polynomial ``b(x)`` (non-negative ``int``; auto-reduced
            if ``deg(b_int) >= m_degree``).
        m_poly_int: Reduction polynomial ``m(x)`` of degree ``m_degree`` with
            bit ``m_degree`` set to 1.
        m_degree: Extension field degree ``m >= 1``.

    Returns:
        Tuple ``(quotient_int, trace_dict)`` where ``0 <= quotient_int < 2^m_degree``
        and ``trace_dict`` contains ``trace_type="gf2m_division_two_stage"``,
        ``initial_reduction``, ``inverse_of_b``, ``inverse_of_b_int``,
        ``quotient_int``, ``stage_1_inverse``, and ``stage_2_multiply``.

    Raises:
        TypeError: If any argument is not an ``int`` (or is a ``bool``).
        ValueError: If any polynomial is negative or ``deg(m_poly_int) != m_degree``.
        ZeroElementHasNoInverseError: If ``b_int mod m_poly_int == 0``.
        NotInvertibleError: If ``gcd(m(x), b(x)) != 1`` (reducible ``m(x)``).

    Complexity:
        Let ``m = m_degree``. Combines one Extended Euclid inversion (``O(m^2)``
        bit operations) with one Shift-and-XOR multiplication (``O(m^2)`` bit
        operations), giving total time and trace space complexity ``O(m^2)``.
    """
    validate_non_negative_poly(a_int, name="a_int")
    validate_non_negative_poly(b_int, name="b_int")
    validate_modulus(m_poly_int, m_degree)

    a_red, a_mod_trace = mod_reduce(a_int, m_poly_int, m_degree)
    b_red, b_mod_trace = mod_reduce(b_int, m_poly_int, m_degree)

    # Stage 1: Invert b(x) via Extended Euclid (raises cleanly on zero/reducible gcd).
    b_inv_int, inverse_trace = EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_int)

    # Stage 2: Multiply a_red(x) * b_inv(x) mod m(x) via Shift-and-XOR.
    quotient_int, multiply_trace = gf2m_multiply(a_red, b_inv_int, m_poly_int, m_degree)

    trace_dict: Dict[str, Any] = {
        "trace_type": "gf2m_division_two_stage",
        "m_degree": m_degree,
        "m_poly_int": m_poly_int,
        "m_poly_formatted": format_poly_representations(m_poly_int, m_degree=m_degree),
        "a_input_int": a_int,
        "b_input_int": b_int,
        "a_reduced_int": a_red,
        "b_reduced_int": b_red,
        "initial_reduction": {
            "a_was_reduced": bool(a_mod_trace["was_reduced"]),
            "b_was_reduced": bool(b_mod_trace["was_reduced"]),
            "a_mod_trace": a_mod_trace,
            "b_mod_trace": b_mod_trace,
        },
        "inverse_of_b_int": b_inv_int,
        "inverse_of_b": format_poly_representations(b_inv_int, m_degree=m_degree),
        "quotient_int": quotient_int,
        "quotient_formatted": format_poly_representations(quotient_int, m_degree=m_degree),
        "stage_1_inverse": inverse_trace,
        "stage_2_multiply": multiply_trace,
    }
    return quotient_int, trace_dict

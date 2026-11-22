"""Two-stage field division engine over GF(2^m) with combined educational trace.

Original Author
---------------
Husein Zahweh — Milestone 3 (Extended Euclid Inverse, Field Division & Verification).

Mathematical Context & Course References
----------------------------------------
Computes field division in ``GF(2^m)`` by multiplying the dividend by the
multiplicative inverse of the divisor:

    a(x) / b(x) mod m(x) = a(x) * (b(x)^(-1) mod m(x)) mod m(x)

* **Stallings Chapter 4 (Finite Fields):** Stage 1 inverts ``b(x)`` via Extended
  Euclid (Table 4.7); Stage 2 multiplies ``a(x)`` by ``b(x)^(-1)`` via Shift-and-XOR.
* **Stallings Chapter 5 (AES), Chapter 6 (XTS-AES), & Chapter 10 (Binary ECC):**
  Field division over ``GF(2^8)``, ``GF(2^128)``, and ``GF(2^163)..GF(2^571)``
  (e.g. slope computation ``lambda = (y2 + y1) / (x2 + x1)`` in binary ECC point
  addition).
"""
from __future__ import annotations

from typing import Any

from .additive import MOD_REDUCE
from .extended_euclid import EXTENDED_EUCLID_GF2M
from .multiply import multiply_traced
from .polyrepr import (
    format_poly_representations,
    validate_modulus,
    validate_non_negative_poly,
)


def GF2M_DIVIDE(
    a_int: int,
    b_int: int,
    m_poly_int: int,
    m_degree: int,
) -> tuple[int, dict[str, Any]]:
    """Compute field division ``a(x) / b(x) mod m(x)`` with two-stage trace.

    Executes in two canonical stages:

    1. **Stage 1 — Multiplicative Inverse:** Invokes :func:`EXTENDED_EUCLID_GF2M`
       on ``b_int`` to obtain ``b_inv_int = b(x)^(-1) mod m(x)`` and its Table 4.7
       trace. Non-invertible divisors propagate :class:`ZeroElementHasNoInverseError`
       or :class:`NotInvertibleError` with ``.gcd`` and ``.trace`` preserved.
    2. **Stage 2 — Modular Multiplication:** Invokes :func:`multiply_traced` on
       ``a_red`` and ``b_inv_int`` modulo ``m_poly_int`` to compute the quotient
       and its Shift-and-XOR Tables 1 & 2 trace.

    Args:
        a_int: Dividend polynomial bitmask (auto-reduced if ``deg(a_int) >= m_degree``).
        b_int: Divisor polynomial bitmask (auto-reduced if ``deg(b_int) >= m_degree``).
        m_poly_int: Reduction polynomial bitmask of degree ``m_degree`` (bit ``m`` set).
        m_degree: Field extension degree ``m >= 1``.

    Returns:
        Tuple ``(quotient_int, trace_dict)`` where ``0 <= quotient_int < 2^m_degree``
        and ``trace_dict`` carries ``trace_type="gf2m_division_two_stage"``,
        ``initial_reduction``, ``inverse_of_b_int``, ``inverse_of_b``,
        ``quotient_int``, ``quotient_formatted``, ``stage_1_inverse``, and
        ``stage_2_multiply``.

    Raises:
        TypeError: If any argument is not an ``int`` (or is a ``bool``).
        ValueError: If operands are negative or ``deg(m_poly_int) != m_degree``.
        ZeroElementHasNoInverseError: If ``b_int mod m_poly_int == 0``.
        NotInvertibleError: If ``gcd(m(x), b(x)) != 1`` (reducible ``m(x)``).

    Complexity:
        Let ``m = m_degree``. Combines one ``O(m^2)`` Extended Euclid inversion
        with one ``O(m^2)`` Shift-and-XOR multiplication, giving total time and
        trace space complexity ``O(m^2)``.
    """
    validate_non_negative_poly(a_int, name="a_int")
    validate_non_negative_poly(b_int, name="b_int")
    validate_modulus(m_poly_int, m_degree)

    a_red, a_mod_trace = MOD_REDUCE(a_int, m_poly_int, m_degree)
    b_red, b_mod_trace = MOD_REDUCE(b_int, m_poly_int, m_degree)

    # Stage 1: Invert b(x) via Extended Euclid (raises cleanly on zero/reducible gcd).
    b_inv_int, inverse_trace = EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_int)

    # Stage 2: Multiply a_red(x) * b_inv(x) mod m(x) via canonical Shift-and-XOR.
    quotient_int, multiply_trace_obj = multiply_traced(a_red, b_inv_int, m_poly_int, m_degree)
    multiply_trace = multiply_trace_obj.dict()

    trace_dict: dict[str, Any] = {
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

"""Isolated Milestone 2 reference Shift-and-XOR multiplication engine.

Provides standalone ``gf2m_multiply(f_int, g_int, m_poly_int, m_degree)``
returning ``(result_int, trace_dict)`` per ``Plan/README.md`` and
``Plan/Milestones/02_multiplication_engine_and_backend_api_controller.md``.

Milestone 3 depends on modular multiplication in Stage 2 of field division
(``a(x) / b(x) = a(x) * b(x)^(-1) mod m(x)``) and in live algebraic
self-verification (``VERIFY_INVERSE`` and ``VERIFY_DIVISION``). Keeping this
reference helper isolated under ``_reference/`` allows Milestone 5 integration
to swap in Milestone 2's authoritative ``multiply`` module cleanly.

References
----------
* Stallings, *Cryptography and Network Security*, Chapter 4 (Finite Fields):
  Shift-and-XOR modular multiplication in GF(2^m).
* Stallings Chapter 5 (AES MixColumns over GF(2^8)) and Chapter 6 (XTS-AES
  GF(2^128) multiplication).
* Stallings Chapter 10 (Binary ECC scalar arithmetic over GF(2^163)...GF(2^571)).
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .utilities import (
    deg,
    int_to_algebraic,
    int_to_hex,
    mod_reduce,
    validate_modulus,
    validate_non_negative_poly,
)


def gf2m_multiply(
    f_int: int,
    g_int: int,
    m_poly_int: int,
    m_degree: int,
) -> Tuple[int, Dict[str, Any]]:
    """Compute ``f(x) * g(x) mod m(x)`` via Shift-and-XOR with full trace.

    Implements the exact algorithm from ``Plan/Milestones/02_...md`` Section 2.2:
    1. Reduce both ``f_int`` and ``g_int`` modulo ``m_poly_int``.
    2. Iteratively compute ``a_i(x) = x^i * f_red(x) mod m(x)`` by shifting left
       by 1 bit and XORing with ``m_poly_int & ((1 << m_degree) - 1)`` whenever
       the coefficient of ``x^(m_degree - 1)`` overflows into ``x^m_degree``.
    3. XOR ``a_i(x)`` into the running product whenever bit ``i`` of ``g_red`` is 1.

    Args:
        f_int: First polynomial operand (non-negative ``int``; auto-reduced if
            degree >= ``m_degree``).
        g_int: Second polynomial operand (non-negative ``int``; auto-reduced if
            degree >= ``m_degree``).
        m_poly_int: Irreducible modulus polynomial of degree ``m_degree`` (with
            bit ``m_degree`` set to 1).
        m_degree: Field extension degree ``m >= 1``.

    Returns:
        Tuple ``(product_int, trace_dict)`` where ``0 <= product_int < 2^m_degree``
        and ``trace_dict`` contains ``trace_type="shift_and_xor"``, initial
        modular reduction traces ``f_mod_trace`` and ``g_mod_trace``,
        ``shift_steps``, and ``selected_terms``.

    Raises:
        TypeError: If any input is not an integer.
        ValueError: If any polynomial is negative or ``m_poly_int`` does not
            match ``m_degree``.

    Complexity:
        Let ``m = m_degree``. Performs at most ``m`` shift-and-XOR iterations,
        each executing ``O(m)`` bit operations, for total time ``O(m^2)`` bit
        operations (``O(m)`` word operations on fixed-width integers) and
        ``O(m^2)`` trace storage.
    """
    validate_non_negative_poly(f_int, name="f_int")
    validate_non_negative_poly(g_int, name="g_int")
    validate_modulus(m_poly_int, m_degree)

    a_int, f_mod_trace = mod_reduce(f_int, m_poly_int, m_degree)
    b_int, g_mod_trace = mod_reduce(g_int, m_poly_int, m_degree)

    product_int = 0
    low_m_mask = (1 << m_degree) - 1
    reduction_poly = m_poly_int & low_m_mask

    shift_steps: List[Dict[str, Any]] = []
    selected_terms: List[Dict[str, Any]] = []

    deg_b = deg(b_int)
    current_a = a_int
    for i in range(deg_b + 1):
        bit_i = (b_int >> i) & 1
        if bit_i == 1:
            product_int ^= current_a
            selected_terms.append(
                {
                    "exponent_i": i,
                    "term_value": current_a,
                    "term_hex": int_to_hex(current_a, m_degree=m_degree),
                    "term_algebraic": int_to_algebraic(current_a),
                    "running_xor": product_int,
                    "running_xor_hex": int_to_hex(product_int, m_degree=m_degree),
                    "running_xor_algebraic": int_to_algebraic(product_int),
                }
            )
        if i < deg_b:
            msb_set = (current_a >> (m_degree - 1)) & 1
            a_shifted = (current_a << 1) & low_m_mask
            a_next = a_shifted ^ reduction_poly if msb_set == 1 else a_shifted
            shift_steps.append(
                {
                    "power_next": i + 1,
                    "msb_overflow": msb_set,
                    "after_shift": a_shifted,
                    "after_shift_hex": int_to_hex(a_shifted, m_degree=m_degree),
                    "after_reduction": a_next,
                    "after_reduction_hex": int_to_hex(a_next, m_degree=m_degree),
                    "after_reduction_algebraic": int_to_algebraic(a_next),
                }
            )
            current_a = a_next

    trace_dict: Dict[str, Any] = {
        "trace_type": "shift_and_xor",
        "m_degree": m_degree,
        "m_poly_int": m_poly_int,
        "m_poly_hex": int_to_hex(m_poly_int, m_degree=m_degree),
        "f_reduced": a_int,
        "g_reduced": b_int,
        "f_mod_trace": f_mod_trace,
        "g_mod_trace": g_mod_trace,
        "shift_steps": shift_steps,
        "selected_terms": selected_terms,
        "summary": {
            "reduction_count": sum(1 for step in shift_steps if step["msb_overflow"] == 1),
            "selected_term_count": len(selected_terms),
            "shift_step_count": len(shift_steps),
        },
    }
    return product_int, trace_dict

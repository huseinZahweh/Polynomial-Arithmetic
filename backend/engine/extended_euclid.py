"""Extended Euclidean Algorithm over GF(2)[x] with Stallings Table 4.7 tracing.

Original Author
---------------
Husein Zahweh — Milestone 3 (Extended Euclid Inverse, Field Division & Verification).

Mathematical Context & Course References
----------------------------------------
Implements ``EXTENDED EUCLID(m(x), b(x))`` per William Stallings,
*Cryptography and Network Security*:

* **Chapter 4 (Finite Fields, Table 4.7):** Maintains state triples
  ``(A1, A2, A3)`` and ``(B1, B2, B3)`` satisfying the Bezout invariant
  ``A1*m(x) XOR A2*b_red(x) = A3`` and ``B1*m(x) XOR B2*b_red(x) = B3``:
  1. ``B3(x) == 1``: ``gcd(m(x), b(x)) == 1`` and ``B2(x)`` is the unique
     multiplicative inverse ``b(x)^(-1) mod m(x)`` (e.g. ``{83}^(-1) = {80}``).
  2. ``B3(x) == 0``: No inverse exists and ``A3(x) == gcd(m(x), b(x))``:
     - At Step 0 (``b(x) mod m(x) == 0``): ``A3 = m(x)`` -> raises
       :class:`ZeroElementHasNoInverseError`.
     - Mid-loop (reducible ``m(x)`` sharing a factor with ``b(x)``): raises
       :class:`NotInvertibleError` with ``gcd = A3``.
* **Chapter 5 (AES):** Byte inversion in ``GF(2^8)`` modulo ``0x11B``
  (e.g. ``{95}^(-1) = {8A}`` in 3 Euclidean steps).
* **Chapter 6 (XTS-AES) & Chapter 10 (Binary ECC):** Finite-field inversion used
  in affine point addition/doubling over ``GF(2^163)..GF(2^571)``.
"""
from __future__ import annotations

from typing import Any, Optional

from .additive import MOD_REDUCE
from .exceptions import NotInvertibleError, ZeroElementHasNoInverseError
from .poly_ops import POLY_DIVMOD, POLY_MUL_NO_MOD
from .polyrepr import (
    DEG,
    format_poly_representations,
    validate_modulus,
    validate_non_negative_poly,
)


def _build_table_4_7_row(
    step: int,
    q_val: Optional[int],
    a1: int,
    a2: int,
    a3: int,
    b1: int,
    b2: int,
    b3: int,
    m_degree: int,
) -> dict[str, Any]:
    """Assemble one Stallings Table 4.7 trace row with integer and multi-base cells.

    Preserves raw integer columns (``step``, ``Q``, ``A1..A3``, ``B1..B3``)
    alongside pre-formatted ``cells`` (``hex``, ``bin``, ``algebraic``) so the
    GUI can toggle Table 4.7 cell notation instantaneously.

    Args:
        step: Zero-based row index (Step 0 is initialization with ``q_val=None``).
        q_val: Polynomial quotient ``Q(x)`` for this step, or ``None`` at Step 0.
        a1, a2, a3: Current ``A`` triple bitmasks.
        b1, b2, b3: Current ``B`` triple bitmasks.
        m_degree: Field extension degree used for zero-padding formatted cells.

    Returns:
        Dictionary representing one complete Table 4.7 row.

    Complexity:
        Time ``O(m)``, space ``O(m)`` where ``m = m_degree``.
    """
    if q_val is None:
        q_cell: dict[str, Any] = {
            "int": None,
            "hex": "-",
            "bin": "-",
            "algebraic": "-",
            "degree": None,
        }
    else:
        q_cell = format_poly_representations(q_val, m_degree=m_degree)

    return {
        "step": step,
        "Q": q_val,
        "A1": a1,
        "A2": a2,
        "A3": a3,
        "B1": b1,
        "B2": b2,
        "B3": b3,
        "cells": {
            "Q": q_cell,
            "A1": format_poly_representations(a1, m_degree=m_degree),
            "A2": format_poly_representations(a2, m_degree=m_degree),
            "A3": format_poly_representations(a3, m_degree=m_degree),
            "B1": format_poly_representations(b1, m_degree=m_degree),
            "B2": format_poly_representations(b2, m_degree=m_degree),
            "B3": format_poly_representations(b3, m_degree=m_degree),
        },
    }


def _build_trace_dict(
    *,
    m_poly_int: int,
    m_degree: int,
    b_input_int: int,
    b_reduced_int: int,
    b_mod_trace: dict[str, Any],
    table_4_7_rows: list[dict[str, Any]],
    status: str,
    b3_final: int,
    gcd_int: int,
    inverse_int: Optional[int],
) -> dict[str, Any]:
    """Package initial reduction metadata, termination outcome, and Table 4.7 rows.

    Args:
        m_poly_int: Reduction polynomial bitmask.
        m_degree: Field extension degree ``m``.
        b_input_int: Original input operand ``b(x)`` prior to reduction.
        b_reduced_int: Reduced operand ``b(x) mod m(x)``.
        b_mod_trace: Modulo reduction trace returned by :func:`MOD_REDUCE`.
        table_4_7_rows: Recorded Table 4.7 row dictionaries.
        status: One of ``"invertible"``, ``"zero_element"``, or ``"not_invertible"``.
        b3_final: Final ``B3`` value (``1`` on success, ``0`` when non-invertible).
        gcd_int: Final ``gcd(m(x), b(x))`` (``1`` on success, ``A3`` otherwise).
        inverse_int: Computed inverse bitmask on success, or ``None``.

    Returns:
        Structured trace dictionary with ``trace_type="extended_euclid_table_4_7"``.

    Complexity:
        Time ``O(m)``, space ``O(m)`` (excluding the already-built row list).
    """
    was_reduced = bool(b_mod_trace.get("was_reduced", False))
    if was_reduced:
        reduction_note = (
            f"Input b(x) of degree {DEG(b_input_int)} was reduced modulo m(x) "
            f"to degree {DEG(b_reduced_int)} prior to Step 0."
        )
    else:
        reduction_note = (
            "Input b(x) already satisfied deg(b) < m; no initial reduction required."
        )

    return {
        "trace_type": "extended_euclid_table_4_7",
        "m_degree": m_degree,
        "m_poly_int": m_poly_int,
        "m_poly_formatted": format_poly_representations(m_poly_int, m_degree=m_degree),
        "b_input_int": b_input_int,
        "b_reduced_int": b_reduced_int,
        "initial_reduction": {
            "was_reduced": was_reduced,
            "note": reduction_note,
            "mod_trace": b_mod_trace,
        },
        "termination": {
            "status": status,
            "b3_final": b3_final,
            "gcd_int": gcd_int,
            "gcd_formatted": format_poly_representations(gcd_int, m_degree=m_degree),
            "inverse_int": inverse_int,
            "inverse_formatted": (
                format_poly_representations(inverse_int, m_degree=m_degree)
                if inverse_int is not None
                else None
            ),
            "iterations": max(0, len(table_4_7_rows) - 1),
            "total_rows": len(table_4_7_rows),
        },
        "table_4_7_rows": table_4_7_rows,
    }


def EXTENDED_EUCLID_GF2M(
    m_poly_int: int,
    m_degree: int,
    b_int: int,
) -> tuple[int, dict[str, Any]]:
    """Compute multiplicative inverse ``b(x)^(-1) mod m(x)`` via Extended Euclid.

    Follows Stallings Chapter 4 (Table 4.7):

    1. Reduce ``b_int`` modulo ``m_poly_int`` via :func:`MOD_REDUCE`.
    2. Initialize ``(A1, A2, A3) = (1, 0, m_poly_int)`` and
       ``(B1, B2, B3) = (0, 1, b_red)``, recording Step 0 (``Q = None``).
    3. If ``B3 == 0`` at Step 0, raise :class:`ZeroElementHasNoInverseError`
       carrying ``gcd = A3 = m_poly_int`` and Step 0 in ``.trace``.
    4. While ``B3 != 1``: compute ``(Q, T3) = POLY_DIVMOD(A3, B3)``, update
       ``T1 = A1 XOR (Q * B1)``, ``T2 = A2 XOR (Q * B2)``, shift triples, log
       the row, and raise :class:`NotInvertibleError` with ``gcd = A3`` if
       ``B3 == 0`` (reducible modulus).
    5. When ``B3 == 1``, confirm ``B2 mod m(x)`` and return ``(b_inv_int, trace)``.

    Args:
        m_poly_int: Reduction polynomial bitmask of degree ``m_degree`` (bit ``m`` set).
        m_degree: Extension field degree ``m >= 1``.
        b_int: Non-negative polynomial bitmask to invert (auto-reduced if ``deg >= m``).

    Returns:
        Tuple ``(b_inv_int, trace_dict)`` where ``0 < b_inv_int < 2^m_degree``
        satisfies ``b(x) * b_inv(x) mod m(x) == 1`` and ``trace_dict`` contains
        all Stallings Table 4.7 rows plus initial-reduction and termination metadata.

    Raises:
        TypeError: If any argument is not an ``int`` (or is a ``bool``).
        ValueError: If any polynomial is negative or ``deg(m_poly_int) != m_degree``.
        ZeroElementHasNoInverseError: If ``b_int mod m_poly_int == 0``.
        NotInvertibleError: If ``gcd(m(x), b(x)) != 1`` (reducible ``m(x)``).

    Complexity:
        Let ``m = m_degree``. Each division strictly lowers ``deg(B3)`` by at
        least 1, bounding iterations by ``m`` (average ``~m / 2`` for dense
        inputs). Total arithmetic is ``O(m^2)`` bit operations and Table 4.7
        formatted trace storage is ``O(m^2)``.
    """
    validate_modulus(m_poly_int, m_degree)
    validate_non_negative_poly(b_int, name="b_int")

    b_red, b_mod_trace = MOD_REDUCE(b_int, m_poly_int, m_degree)

    # Step 0 initialization: A represents m(x), B represents b_red(x).
    a1, a2, a3 = 1, 0, m_poly_int
    b1, b2, b3 = 0, 1, b_red

    table_4_7_rows: list[dict[str, Any]] = [
        _build_table_4_7_row(
            step=0,
            q_val=None,
            a1=a1,
            a2=a2,
            a3=a3,
            b1=b1,
            b2=b2,
            b3=b3,
            m_degree=m_degree,
        )
    ]

    # Termination Case 2a: b(x) == 0 (mod m(x)) -> no inverse; gcd(m, 0) = m(x).
    if b3 == 0:
        trace_dict = _build_trace_dict(
            m_poly_int=m_poly_int,
            m_degree=m_degree,
            b_input_int=b_int,
            b_reduced_int=b_red,
            b_mod_trace=b_mod_trace,
            table_4_7_rows=table_4_7_rows,
            status="zero_element",
            b3_final=0,
            gcd_int=a3,
            inverse_int=None,
        )
        raise ZeroElementHasNoInverseError(gcd=a3, trace=trace_dict)

    step_num = 1
    while b3 != 1:
        # Euclidean step: A3 = Q * B3 XOR T3 with deg(T3) < deg(B3).
        q_val, t3 = POLY_DIVMOD(a3, b3)
        # Preserve Bezout invariant using characteristic-2 subtraction (XOR).
        t1 = a1 ^ POLY_MUL_NO_MOD(q_val, b1)
        t2 = a2 ^ POLY_MUL_NO_MOD(q_val, b2)

        a1, a2, a3 = b1, b2, b3
        b1, b2, b3 = t1, t2, t3

        table_4_7_rows.append(
            _build_table_4_7_row(
                step=step_num,
                q_val=q_val,
                a1=a1,
                a2=a2,
                a3=a3,
                b1=b1,
                b2=b2,
                b3=b3,
                m_degree=m_degree,
            )
        )

        # Termination Case 2b: B3 == 0 mid-loop -> reducible modulus sharing gcd A3.
        if b3 == 0:
            trace_dict = _build_trace_dict(
                m_poly_int=m_poly_int,
                m_degree=m_degree,
                b_input_int=b_int,
                b_reduced_int=b_red,
                b_mod_trace=b_mod_trace,
                table_4_7_rows=table_4_7_rows,
                status="not_invertible",
                b3_final=0,
                gcd_int=a3,
                inverse_int=None,
            )
            raise NotInvertibleError(gcd=a3, trace=trace_dict)

        step_num += 1

    # Termination Case 1: B3 == 1 -> B2 is the unique inverse modulo m(x).
    b_inv_int, _ = MOD_REDUCE(b2, m_poly_int, m_degree)
    trace_dict = _build_trace_dict(
        m_poly_int=m_poly_int,
        m_degree=m_degree,
        b_input_int=b_int,
        b_reduced_int=b_red,
        b_mod_trace=b_mod_trace,
        table_4_7_rows=table_4_7_rows,
        status="invertible",
        b3_final=1,
        gcd_int=1,
        inverse_int=b_inv_int,
    )
    return b_inv_int, trace_dict

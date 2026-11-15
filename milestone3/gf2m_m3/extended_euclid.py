"""Extended Euclidean Algorithm over GF(2)[x] with Stallings Table 4.7 tracing.

Implements :func:`EXTENDED_EUCLID_GF2M` per
``Plan/Milestones/03_extended_euclid_inverse_division_and_verification_suite.md``
Section 2.3 and ``Plan/README.md``.

Termination Rules (Stallings Chapter 4)
---------------------------------------
Starting from ``(A1, A2, A3) = (1, 0, m(x))`` and
``(B1, B2, B3) = (0, 1, b(x) mod m(x))``:

1. **B3(x) == 1**: ``gcd(m(x), b(x)) = 1`` and ``B2(x)`` is the unique
   multiplicative inverse ``b(x)^(-1) mod m(x)``.
2. **B3(x) == 0**: No multiplicative inverse exists and ``A3(x) = gcd(m(x), b(x))``:
   * At Step 0 (``b(x) mod m(x) == 0``): ``A3(x) = m(x)`` and
     :class:`ZeroElementHasNoInverseError` is raised.
   * Mid-loop (reducible ``m(x)`` sharing a non-trivial factor with ``b(x)``):
     :class:`NotInvertibleError` is raised with ``gcd = A3(x)``.

References
----------
* Stallings, *Cryptography and Network Security*, Chapter 4 (Finite Fields):
  Algorithm ``EXTENDED EUCLID(m(x), b(x))`` and Table 4.7 worked example
  (``(x^7 + x + 1)^(-1) mod (x^8 + x^4 + x^3 + x + 1) = x^7``).
* Stallings Chapter 5 (AES S-Box byte inversion over GF(2^8),
  ``{95}^(-1) mod {11B} = {8A}``).
* Stallings Chapter 6 (XTS-AES arithmetic over GF(2^128)) and Chapter 10
  (Binary Elliptic Curve Cryptography over GF(2^163)...GF(2^571), where
  affine point addition and doubling require finite-field inversion).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ._reference import (
    deg,
    format_poly_representations,
    mod_reduce,
    validate_modulus,
    validate_non_negative_poly,
)
from .exceptions import NotInvertibleError, ZeroElementHasNoInverseError
from .poly_ops import POLY_DIVMOD, POLY_MUL_NO_MOD


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
) -> Dict[str, Any]:
    """Construct one Table 4.7 trace row with integer and formatted cells.

    Each row preserves the raw Plan 03 integer fields (``step``, ``Q``,
    ``A1``, ``A2``, ``A3``, ``B1``, ``B2``, ``B3``) plus a ``cells`` mapping
    containing pre-formatted ``int``, ``hex``, ``bin``, and ``algebraic``
    notations for Milestone 4's UI notation toggle.
    """
    if q_val is None:
        q_cell: Dict[str, Any] = {
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
    b_mod_trace: Dict[str, Any],
    table_4_7_rows: List[Dict[str, Any]],
    status: str,
    b3_final: int,
    gcd_int: int,
    inverse_int: Optional[int],
) -> Dict[str, Any]:
    """Assemble the complete Table 4.7 trace dictionary."""
    was_reduced = bool(b_mod_trace.get("was_reduced", False))
    if was_reduced:
        reduction_note = (
            f"Input b(x) of degree {deg(b_input_int)} was reduced modulo m(x) "
            f"to degree {deg(b_reduced_int)} prior to Step 0."
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
) -> Tuple[int, Dict[str, Any]]:
    """Compute multiplicative inverse ``b(x)^(-1) mod m(x)`` via Extended Euclid.

    Follows Stallings Chapter 4 (Table 4.7) and ``Plan/Milestones/03_...md``
    Section 2.3:

    1. Reduce ``b_int`` modulo ``m_poly_int`` to obtain ``b_red``.
    2. Initialize ``(A1, A2, A3) = (1, 0, m_poly_int)`` and
       ``(B1, B2, B3) = (0, 1, b_red)``, logging Step 0 with ``Q = None``.
    3. If ``B3 == 0`` at Step 0, raise :class:`ZeroElementHasNoInverseError`
       with ``gcd = A3 = m_poly_int`` and the trace containing Step 0.
    4. Loop while ``B3 != 1``:
       compute ``(Q, T3) = POLY_DIVMOD(A3, B3)``, update
       ``T1 = A1 ^ POLY_MUL_NO_MOD(Q, B1)``, ``T2 = A2 ^ POLY_MUL_NO_MOD(Q, B2)``,
       shift ``(A1, A2, A3) <- (B1, B2, B3)`` and ``(B1, B2, B3) <- (T1, T2, T3)``,
       append the Table 4.7 row, and if ``B3 == 0`` raise
       :class:`NotInvertibleError` with ``gcd = A3``.
    5. When ``B3 == 1``, reduce/confirm ``B2 mod m(x)`` and return
       ``(b_inv_int, trace_dict)``.

    Args:
        m_poly_int: Reduction polynomial ``m(x)`` of degree ``m_degree`` with
            bit ``m_degree`` set to 1.
        m_degree: Extension field degree ``m >= 1``.
        b_int: Non-negative polynomial integer to invert modulo ``m(x)``
            (automatically reduced if ``deg(b_int) >= m_degree``).

    Returns:
        Tuple ``(b_inv_int, trace_dict)`` where ``0 <= b_inv_int < 2^m_degree``
        satisfies ``b(x) * b_inv(x) mod m(x) == 1`` and ``trace_dict`` holds
        the full Stallings Table 4.7 row list plus reduction/termination metadata.

    Raises:
        TypeError: If any argument is not an ``int`` (or is a ``bool``).
        ValueError: If any polynomial is negative or ``deg(m_poly_int) != m_degree``.
        ZeroElementHasNoInverseError: If ``b_int mod m_poly_int == 0``.
        NotInvertibleError: If ``gcd(m(x), b(x)) != 1`` (reducible ``m(x)``).

    Complexity:
        Let ``m = m_degree``. Each division step strictly decreases ``deg(B3)``
        by at least 1, so the loop executes at most ``m`` iterations. Across all
        steps, total polynomial division/multiplication work is ``O(m^2)``
        bit operations (``O(m)`` word-level bit shifts/XORs on fixed-width ``m``)
        and ``O(m^2)`` formatted trace storage.
    """
    validate_modulus(m_poly_int, m_degree)
    validate_non_negative_poly(b_int, name="b_int")

    b_red, b_mod_trace = mod_reduce(b_int, m_poly_int, m_degree)

    a1, a2, a3 = 1, 0, m_poly_int
    b1, b2, b3 = 0, 1, b_red

    table_4_7_rows: List[Dict[str, Any]] = [
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
        q_val, t3 = POLY_DIVMOD(a3, b3)
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

    b_inv_int, _ = mod_reduce(b2, m_poly_int, m_degree)
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

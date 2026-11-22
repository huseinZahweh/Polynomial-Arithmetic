"""GF(2^m) addition, subtraction, and polynomial modulo reduction with step traces.

Original Author
---------------
Hussein Abbas — Milestone 1 (Field Configuration, I/O, Additive/Modulo & Utilities).

Mathematical Context & Course References
----------------------------------------
* **Stallings Chapter 4 (Finite Fields):** Over ``GF(2)``, coefficient addition
  and subtraction are both modulo-2 bitwise XOR (``1 + 1 = 0``, ``-1 = +1``),
  so ``f(x) + g(x) = f(x) - g(x) = f(x) XOR g(x)`` with no carry propagation.
  Modulo reduction repeatedly cancels the highest term ``x^d`` (``d >= m``) by
  XORing with the shifted modulus ``x^(d - m) * m(x)`` until ``deg(r) < m``.
* **Stallings Chapter 5 (AES):** Byte XOR (AddRoundKey) and ``GF(2^8)`` reduction
  modulo ``x^8 + x^4 + x^3 + x + 1`` (``0x11B``).
* **Stallings Chapter 6 (Block Cipher Operation) & Chapter 10 (ECC):** Identical
  characteristic-2 XOR addition and sparse-modulus reduction over ``GF(2^128)``
  (XTS-AES) and ``GF(2^163)..GF(2^571)`` (binary elliptic curves).
"""
from __future__ import annotations

from typing import Any

from .polyrepr import (
    INT_TO_ALGEBRAIC,
    INT_TO_BIN,
    INT_TO_HEX,
    validate_modulus,
    validate_non_negative_poly,
)


def _reduce(
    value_int: int,
    m_poly_int: int,
    m_degree: int,
    steps: list[dict[str, int]] | None = None,
) -> int:
    """Iteratively cancel leading terms of degree ``>= m_degree`` via shifted XOR.

    Args:
        value_int: Non-negative polynomial bitmask to reduce.
        m_poly_int: Reduction polynomial ``m(x)`` of degree ``m_degree`` (bit ``m`` set).
        m_degree: Field extension degree ``m >= 1``.
        steps: Optional list; when provided, appends one dict per cancellation step
            recording ``target_degree``, ``shift``, ``before``, ``reducer``, ``after``.

    Returns:
        Reduced polynomial bitmask ``r`` satisfying ``0 <= r < 2^m_degree``.

    Raises:
        TypeError: If inputs are non-integers or booleans.
        ValueError: If inputs are negative or ``deg(m_poly_int) != m_degree``.

    Complexity:
        Let ``d = deg(value_int)`` and ``m = m_degree``. Executes at most
        ``max(0, d - m + 1)`` iterations, each performing an ``O(d)``-bit shift
        and XOR, for worst-case time ``O((d - m + 1) * d)`` bit operations and
        ``O(1)`` auxiliary space when ``steps is None`` (``O((d - m + 1) * d)``
        with trace collection).
    """
    validate_non_negative_poly(value_int, "value_int")
    validate_modulus(m_poly_int, m_degree)

    remainder = value_int
    # bit_length() > m_degree is equivalent to deg(remainder) >= m_degree.
    while remainder.bit_length() > m_degree:
        target_degree = remainder.bit_length() - 1
        shift = target_degree - m_degree
        # Align m(x)'s leading x^m term with remainder's leading x^d term and cancel via XOR.
        reducer = m_poly_int << shift
        next_remainder = remainder ^ reducer
        if steps is not None:
            steps.append(
                {
                    "target_degree": target_degree,
                    "shift": shift,
                    "before": remainder,
                    "reducer": reducer,
                    "after": next_remainder,
                }
            )
        remainder = next_remainder
    return remainder


def MOD_REDUCE(f_int: int, m_poly_int: int, m_degree: int) -> tuple[int, dict[str, Any]]:
    """Reduce ``f(x) mod m(x)`` and return a structured step-by-step trace.

    Args:
        f_int: Unreduced (or already reduced) non-negative polynomial bitmask.
        m_poly_int: Irreducible modulus bitmask of degree ``m_degree``.
        m_degree: Extension field degree ``m >= 1``.

    Returns:
        Tuple ``(reduced_int, trace_dict)`` where ``trace_dict`` has
        ``trace_type="mod_reduce"``, ``m_degree``, ``m_poly_int``,
        ``initial_value``, ``reduced_value``, ``was_reduced``, ``step_count``,
        and ``steps``.

    Raises:
        TypeError: If arguments are non-integers or booleans.
        ValueError: If ``f_int < 0`` or ``m_poly_int`` does not have degree ``m_degree``.

    Complexity:
        Time ``O(max(1, deg(f) - m + 1) * deg(f))`` bit operations;
        space ``O(max(1, deg(f) - m + 1) * deg(f))`` for trace storage.
    """
    steps: list[dict[str, int]] = []
    result = _reduce(f_int, m_poly_int, m_degree, steps)
    return result, {
        "trace_type": "mod_reduce",
        "m_degree": m_degree,
        "m_poly_int": m_poly_int,
        "initial_value": f_int,
        "reduced_value": result,
        "was_reduced": bool(steps),
        "step_count": len(steps),
        "steps": steps,
    }


def xor_trace(a: int, b: int, m: int) -> dict[str, Any]:
    """Build bit-aligned XOR trace columns and formatted rows for ``a XOR b``.

    Args:
        a: First non-negative polynomial bitmask (typically already reduced).
        b: Second non-negative polynomial bitmask (typically already reduced).
        m: Minimum column width (field degree).

    Returns:
        Dictionary with ``algorithm="bitwise-xor"``, ``a_bin``, ``b_bin``,
        ``result_bin``, MSB-to-LSB ``columns`` (``exp``, ``a``, ``b``, ``xor``),
        and ``rows`` (``bin``, ``hex``, ``poly`` for ``a``, ``b``, ``result``).

    Raises:
        TypeError: If ``a`` or ``b`` is not an ``int`` (or is ``bool``).
        ValueError: If ``a < 0``, ``b < 0``, or ``m < 1``.

    Complexity:
        Time ``O(W)``, space ``O(W)`` where ``W = max(m, bit_length(a), bit_length(b))``.
    """
    validate_non_negative_poly(a, "operand A")
    validate_non_negative_poly(b, "operand B")
    width = max(m, a.bit_length(), b.bit_length())
    columns: list[dict[str, int]] = []
    # Walk from x^(width-1) down to x^0 so columns align left-to-right with MSB-first binary.
    for exponent in range(width - 1, -1, -1):
        bit_a = (a >> exponent) & 1
        bit_b = (b >> exponent) & 1
        columns.append({"exp": exponent, "a": bit_a, "b": bit_b, "xor": bit_a ^ bit_b})

    values = {"a": a, "b": b, "result": a ^ b}
    rows = {
        name: {
            "bin": INT_TO_BIN(value, width),
            "hex": INT_TO_HEX(value, width),
            "poly": INT_TO_ALGEBRAIC(value),
        }
        for name, value in values.items()
    }
    return {
        "algorithm": "bitwise-xor",
        "a_bin": rows["a"]["bin"],
        "b_bin": rows["b"]["bin"],
        "result_bin": rows["result"]["bin"],
        "columns": columns,
        "rows": rows,
    }


def GF2M_ADD_SUB(
    f_int: int,
    g_int: int,
    m_poly_int: int,
    m_degree: int,
) -> tuple[int, dict[str, Any]]:
    """Compute ``f(x) +/- g(x) mod m(x)`` with pre-reduction and bitwise-XOR traces.

    Because ``GF(2^m)`` has characteristic 2, addition and subtraction are both
    ``(f mod m) XOR (g mod m)``; once operands have degree ``< m``, their XOR
    cannot overflow degree ``m - 1``.

    Args:
        f_int: First polynomial operand (auto-reduced if ``deg >= m_degree``).
        g_int: Second polynomial operand (auto-reduced if ``deg >= m_degree``).
        m_poly_int: Irreducible reduction polynomial bitmask of degree ``m_degree``.
        m_degree: Extension field degree ``m >= 1``.

    Returns:
        Tuple ``(result_int, trace_dict)`` combining ``f_mod_trace``,
        ``g_mod_trace``, and the aligned ``bitwise-xor`` trace.

    Raises:
        TypeError: If arguments are non-integers or booleans.
        ValueError: If operands are negative or ``deg(m_poly_int) != m_degree``.

    Complexity:
        Time ``O(m + reduction_work)``, space ``O(m + reduction_trace)``.
    """
    a_reduced, a_trace = MOD_REDUCE(f_int, m_poly_int, m_degree)
    b_reduced, b_trace = MOD_REDUCE(g_int, m_poly_int, m_degree)
    return a_reduced ^ b_reduced, {
        "trace_type": "add_sub",
        "f_mod_trace": a_trace,
        "g_mod_trace": b_trace,
        **xor_trace(a_reduced, b_reduced, m_degree),
    }


def modulo(a: int, mod_poly: int, m: int) -> int:
    """Fast-path modulo reduction ``a(x) mod m(x)`` without trace construction.

    Args:
        a: Non-negative polynomial bitmask.
        mod_poly: Reduction polynomial bitmask of degree ``m``.
        m: Field extension degree ``m >= 1``.

    Returns:
        Reduced polynomial bitmask of degree ``< m``.

    Complexity:
        Time ``O(max(1, deg(a) - m + 1) * deg(a))`` bit operations; space ``O(1)``.
    """
    return _reduce(a, mod_poly, m)


def add(a: int, b: int, mod_poly: int, m: int) -> int:
    """Fast-path field addition ``(a(x) + b(x)) mod m(x)`` without trace construction.

    Args:
        a: First non-negative polynomial bitmask.
        b: Second non-negative polynomial bitmask.
        mod_poly: Reduction polynomial bitmask of degree ``m``.
        m: Field extension degree ``m >= 1``.

    Returns:
        Reduced field sum ``(a mod m) XOR (b mod m)``.

    Complexity:
        Time ``O(m)`` for already-reduced operands; space ``O(1)``.
    """
    return modulo(a, mod_poly, m) ^ modulo(b, mod_poly, m)


# In characteristic 2 (GF(2^m)), subtraction is algebraically identical to addition.
subtract = add

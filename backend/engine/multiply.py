"""Shift-and-XOR modular multiplication engine for GF(2^m) with Table 1 & 2 traces.

Original Author
---------------
Hassan Tarhini — Milestone 2 (Shift-and-XOR Multiplication Engine & Backend API).

Mathematical Context & Course References
----------------------------------------
Computes ``c(x) = a(x) * b(x) mod m(x)`` via the iterative Shift-and-XOR method
from William Stallings, *Cryptography and Network Security*:

* **Chapter 4 (Finite Fields):** Iteratively shifts ``t_i = a(x) * x^i mod m(x)``
  left by 1 bit and XORs with ``m(x)`` whenever the ``x^m`` overflow bit is set,
  accumulating ``t_i`` into the running XOR product whenever bit ``i`` of ``b(x)``
  is ``1``.
* **Chapter 5 (AES):** Byte multiplication in ``GF(2^8)`` modulo ``0x11B``
  (e.g. ``{57} * {83} = {C1}``, ``{02} * {87} = {15}``, ``{53} * {CA} = {01}``).
* **Chapter 6 (Block Cipher Operation):** XTS-AES tweak multiplication by ``alpha = x``
  over ``GF(2^128)``.
* **Chapter 10 (Elliptic Curve Cryptography):** Polynomial-basis multiplication
  over binary curves ``GF(2^163)`` through ``GF(2^571)``.

Educational Trace Mapping
-------------------------
* **Table 1 (Shifts & Reductions):** Records ``t_i = a(x) * x^i mod m(x)`` and
  whether overflow bit ``b_{m-1} == 1`` triggered a reduction ``^ m(x)``.
* **Table 2 (Accumulated Partial Products):** Records each step where bit ``i``
  of ``b(x)`` is ``1`` and tracks the cumulative XOR accumulator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from . import polyrepr
from .additive import modulo
from .poly_ops import POLY_MUL_NO_MOD
from .polyrepr import validate_modulus, validate_non_negative_poly


def reduce_mod(value: int, mod_poly: int, m: int) -> int:
    """Reduce ``value`` modulo ``mod_poly`` so the remainder has degree ``< m``.

    Delegates directly to :func:`backend.engine.additive.modulo`.

    Args:
        value: Non-negative polynomial bitmask.
        mod_poly: Reduction polynomial bitmask of degree ``m`` (bit ``m`` set).
        m: Field extension degree ``m >= 1``.

    Returns:
        Reduced polynomial bitmask in ``[0, 2^m - 1]``.

    Raises:
        TypeError: If arguments are not integers (or are booleans).
        ValueError: If ``value < 0`` or ``deg(mod_poly) != m``.

    Complexity:
        Time ``O(max(1, deg(value) - m + 1) * deg(value))`` bit ops; space ``O(1)``.
    """
    return modulo(value, mod_poly, m)


def carryless_mul(a: int, b: int) -> int:
    """Compute unreduced carry-free product ``a(x) * b(x)`` over ``GF(2)[x]``.

    Delegates to :func:`backend.engine.poly_ops.POLY_MUL_NO_MOD` so the entire
    platform shares one canonical carry-free multiplier.

    Args:
        a: First non-negative polynomial bitmask.
        b: Second non-negative polynomial bitmask.

    Returns:
        Unreduced polynomial bitmask ``a(x) * b(x)``.

    Complexity:
        Time ``O(min(deg(a), deg(b)) * (deg(a) + deg(b)))`` bit ops; space ``O(1)``.
    """
    return POLY_MUL_NO_MOD(a, b)


def multiply(a: int, b: int, mod_poly: int, m: int) -> int:
    """Fast-path Shift-and-XOR product ``a(x) * b(x) mod m(x)`` without trace.

    Used by untraced division, live algebraic verification, and the 163/571-bit
    multiplication benchmarks.

    Args:
        a: Multiplicand polynomial bitmask (auto-reduced if ``deg(a) >= m``).
        b: Multiplier polynomial bitmask (auto-reduced if ``deg(b) >= m``).
        mod_poly: Irreducible modulus bitmask of degree ``m`` (bit ``m`` set).
        m: Field extension degree ``m >= 1``.

    Returns:
        Reduced field product ``c(x)`` satisfying ``0 <= c < 2^m``.

    Raises:
        TypeError: If any argument is not an ``int`` (or is ``bool``).
        ValueError: If operands are negative or ``deg(mod_poly) != m``.

    Complexity:
        Time ``O(m^2)`` bit operations (at most ``deg(b) + 1 <= m`` shifts/XORs
        of ``m``-bit integers after initial reduction); space ``O(1)`` auxiliary
        space (``O(m)``-bit integers).
    """
    validate_non_negative_poly(a, "a")
    validate_non_negative_poly(b, "b")
    validate_modulus(mod_poly, m)

    a = modulo(a, mod_poly, m)
    b = modulo(b, mod_poly, m)
    result = 0
    t = a
    # Bit mask for the x^m overflow position (1 << m).
    top = 1 << m
    while b:
        if b & 1:
            result ^= t
        b >>= 1
        # Only shift/reduce t = x * t mod m(x) if higher bits of b remain.
        if b:
            t <<= 1
            if t & top:
                # Clearing x^m and adding lower terms of m(x) is one XOR with full m(x).
                t ^= mod_poly
    return result


@dataclass
class ShiftStep:
    """One bit-position iteration ``i`` of the Shift-and-XOR multiplication loop.

    Attributes:
        i: Multiplier bit index (power of ``x``).
        multiplier_bit: Bit ``i`` of reduced multiplier ``b(x)`` (``0`` or ``1``).
        partial_hex: Lowercase hex of ``t_i = a(x) * x^i mod m(x)`` (Table 1).
        partial_poly: Algebraic notation of ``t_i`` (Table 1).
        reduced: ``True`` if producing ``t_i`` from ``t_{i-1}`` overflowed ``x^m``
            and required XOR with ``m(x)``.
        added: ``True`` if ``multiplier_bit == 1`` caused ``t_i`` to be XORed into
            the running accumulator (Table 2).
        accumulator_hex: Lowercase hex of running product after step ``i`` (Table 2).
    """

    i: int
    multiplier_bit: int
    partial_hex: str
    partial_poly: str
    reduced: bool
    added: bool
    accumulator_hex: str

    def dict(self) -> dict[str, Any]:
        """Return this step's fields as a plain JSON-serializable dictionary."""
        return self.__dict__


@dataclass
class MultiplyTrace:
    """Structured Shift-and-XOR trace plus summary counters for UI badges.

    Attributes:
        algorithm: Always ``"shift-and-xor"``.
        m: Field extension degree.
        reduction_poly_hex: Lowercase hex of ``m(x)`` at width ``m + 1``.
        operand_a_hex: Lowercase hex of reduced multiplicand ``a(x)``.
        operand_b_hex: Lowercase hex of reduced multiplier ``b(x)``.
        steps: List of :class:`ShiftStep` rows up to ``max_steps``.
        reductions: Total count of overflow reductions performed across all bits.
        partial_products: Total count of set bits of ``b(x)`` XORed into result.
        truncated: ``True`` if ``max_steps`` capped recorded trace rows (the
            returned product is always exact regardless of truncation).
    """

    algorithm: str
    m: int
    reduction_poly_hex: str
    operand_a_hex: str
    operand_b_hex: str
    steps: list[ShiftStep] = field(default_factory=list)
    reductions: int = 0
    partial_products: int = 0
    truncated: bool = False

    def dict(self) -> dict[str, Any]:
        """Serialize the complete trace and summary block for JSON API responses."""
        return {
            "algorithm": self.algorithm,
            "m": self.m,
            "reduction_poly_hex": self.reduction_poly_hex,
            "operand_a_hex": self.operand_a_hex,
            "operand_b_hex": self.operand_b_hex,
            "steps": [step.dict() for step in self.steps],
            "summary": {
                "reductions": self.reductions,
                "partial_products": self.partial_products,
                "truncated": self.truncated,
            },
        }


def multiply_traced(
    a: int,
    b: int,
    mod_poly: int,
    m: int,
    max_steps: Optional[int] = 2048,
) -> tuple[int, MultiplyTrace]:
    """Compute ``a(x) * b(x) mod m(x)`` and record Table 1 & Table 2 trace rows.

    Stops as soon as all remaining high bits of ``b(x)`` are zero, keeping traces
    compact for sparse multipliers even in ``GF(2^571)``. When ``max_steps`` is
    reached on a dense large operand, trace recording stops and ``trace.truncated``
    becomes ``True``, while the arithmetic loop finishes computing the exact product.

    Args:
        a: Multiplicand polynomial bitmask (auto-reduced if ``deg(a) >= m``).
        b: Multiplier polynomial bitmask (auto-reduced if ``deg(b) >= m``).
        mod_poly: Irreducible modulus bitmask of degree ``m`` (bit ``m`` set).
        m: Field extension degree ``m >= 1``.
        max_steps: Maximum number of :class:`ShiftStep` entries to record
            (``None`` for unbounded). Defaults to ``2048``.

    Returns:
        Tuple ``(product_int, MultiplyTrace)`` where ``0 <= product_int < 2^m``.

    Raises:
        TypeError: If integer arguments are invalid types or booleans.
        ValueError: If operands are negative or ``deg(mod_poly) != m``.

    Complexity:
        Time ``O(m^2)`` bit operations for the arithmetic loop; space
        ``O(min(m, max_steps) * m)`` for formatted hex and algebraic trace rows.
    """
    validate_non_negative_poly(a, "a")
    validate_non_negative_poly(b, "b")
    validate_modulus(mod_poly, m)

    a = modulo(a, mod_poly, m)
    b_reduced = modulo(b, mod_poly, m)

    trace = MultiplyTrace(
        algorithm="shift-and-xor",
        m=m,
        reduction_poly_hex=polyrepr.to_hex(mod_poly, m + 1),
        operand_a_hex=polyrepr.to_hex(a, m),
        operand_b_hex=polyrepr.to_hex(b_reduced, m),
    )

    result = 0
    t = a
    t_was_reduced = False
    top = 1 << m
    i = 0
    b_work = b_reduced

    while b_work:
        bit = b_work & 1
        added = bit == 1
        if added:
            result ^= t
            trace.partial_products += 1

        # Guardrail: cap serialized trace rows without affecting mathematical accuracy.
        if max_steps is None or len(trace.steps) < max_steps:
            trace.steps.append(
                ShiftStep(
                    i=i,
                    multiplier_bit=bit,
                    partial_hex=polyrepr.to_hex(t, m),
                    partial_poly=polyrepr.to_poly(t),
                    reduced=t_was_reduced,
                    added=added,
                    accumulator_hex=polyrepr.to_hex(result, m),
                )
            )
        else:
            trace.truncated = True

        b_work >>= 1
        i += 1
        if b_work:
            t <<= 1
            if t & top:
                t ^= mod_poly
                t_was_reduced = True
                trace.reductions += 1
            else:
                t_was_reduced = False

    return result, trace

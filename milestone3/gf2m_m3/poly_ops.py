"""Carry-free polynomial multiplication and Euclidean long division over GF(2).

Implements Milestone 3 Helpers 1 and 2 from
``Plan/Milestones/03_extended_euclid_inverse_division_and_verification_suite.md``:
* :func:`POLY_MUL_NO_MOD` — carry-free polynomial multiplication over Z_2[x]
  without modular reduction.
* :func:`POLY_DIVMOD` — polynomial Euclidean long division over Z_2[x]
  computing unique ``(q_int, r_int)`` with ``A(x) = Q(x)*B(x) XOR R(x)`` and
  ``deg(R) < deg(B)`` (or ``R = 0``).

References
----------
* Stallings, *Cryptography and Network Security*, Chapter 4 (Finite Fields):
  Section 4.3 (Polynomial Arithmetic over Z_2) and Section 4.4 (Extended
  Euclidean Algorithm for polynomials in GF(2)[x]).
* Used inside :func:`EXTENDED_EUCLID_GF2M` to update ``T1, T2, T3`` across all
  supported fields including AES GF(2^8) (Chapter 5), XTS-AES GF(2^128)
  (Chapter 6), and Binary ECC GF(2^163)...GF(2^571) (Chapter 10).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from ._reference import deg, validate_non_negative_poly


def POLY_MUL_NO_MOD(a_int: int, b_int: int) -> int:
    """Compute unreduced carry-free product ``a(x) * b(x)`` over GF(2)[x].

    Implements Stallings Chapter 4 carry-free polynomial multiplication:
    addition of coefficients is bitwise XOR with no carries between bit
    positions and no modular reduction.

    Args:
        a_int: First polynomial operand encoded as a non-negative ``int``.
        b_int: Second polynomial operand encoded as a non-negative ``int``.

    Returns:
        Non-negative ``int`` encoding the unreduced product ``a(x) * b(x)``
        in ``GF(2)[x]``, with ``deg(a * b) == deg(a) + deg(b)`` when both
        operands are non-zero (and ``0`` if either operand is ``0``).

    Raises:
        TypeError: If either operand is not an ``int`` (or is a ``bool``).
        ValueError: If either operand is negative.

    Complexity:
        Let ``da = deg(a_int)`` and ``db = deg(b_int)``. Iterates over the
        shorter bit-length operand in ``min(da, db) + 1`` steps, performing
        ``O(da + db)`` word-level XOR/shift operations per step for a worst-case
        bit complexity of ``O(min(da, db) * (da + db))``.
    """
    validate_non_negative_poly(a_int, name="a_int")
    validate_non_negative_poly(b_int, name="b_int")

    if a_int == 0 or b_int == 0:
        return 0

    # Polynomial multiplication over GF(2)[x] is commutative; looping over
    # the smaller-degree operand minimizes shift-and-XOR iterations.
    if a_int.bit_length() > b_int.bit_length():
        a_int, b_int = b_int, a_int

    p_int = 0
    temp_a = a_int
    temp_b = b_int
    while temp_a > 0:
        if temp_a & 1:
            p_int ^= temp_b
        temp_b <<= 1
        temp_a >>= 1
    return p_int


@dataclass(frozen=True)
class DivisionStep:
    """One shifted-divisor XOR in polynomial long division."""

    shift: int
    before: int
    shifted_divisor: int
    after: int


def POLY_DIVMOD(a_int: int, b_int: int, *, steps: list[DivisionStep] | None = None) -> Tuple[int, int]:
    """Compute polynomial quotient and remainder ``A(x) = Q(x)*B(x) XOR R(x)``.

    Implements Euclidean polynomial long division over GF(2)[x] per Stallings
    Chapter 4 until ``R(x) == 0`` or ``deg(R) < deg(B)``.

    Args:
        a_int: Dividend polynomial ``A(x)`` as a non-negative ``int``.
        b_int: Non-zero divisor polynomial ``B(x)`` as a positive ``int``.
        steps: Optional list that records each leading-term cancellation.

    Returns:
        Tuple ``(q_int, r_int)`` of non-negative ``int`` values satisfying::

            POLY_MUL_NO_MOD(q_int, b_int) ^ r_int == a_int
            r_int == 0 or deg(r_int) < deg(b_int)

    Raises:
        TypeError: If either operand is not an ``int`` (or is a ``bool``).
        ValueError: If either operand is negative.
        ZeroDivisionError: If ``b_int == 0``.

    Complexity:
        Let ``da = deg(a_int)`` and ``db = deg(b_int)``. If ``da < db``, runs
        in ``O(1)``. Otherwise performs at most ``da - db + 1`` shift-and-XOR
        eliminations of ``O(da)`` bits, giving ``O((da - db + 1) * da)`` bit
        operations.
    """
    validate_non_negative_poly(a_int, name="a_int")
    validate_non_negative_poly(b_int, name="b_int")

    if b_int == 0:
        raise ZeroDivisionError("Division by zero polynomial B(x) = 0 is undefined.")

    q_int = 0
    r_int = a_int
    deg_b = deg(b_int)

    while r_int != 0:
        deg_r = r_int.bit_length() - 1
        if deg_r < deg_b:
            break
        shift = deg_r - deg_b
        q_int ^= 1 << shift
        shifted = b_int << shift
        reduced = r_int ^ shifted
        if steps is not None:
            steps.append(DivisionStep(shift, r_int, shifted, reduced))
        r_int = reduced

    return q_int, r_int

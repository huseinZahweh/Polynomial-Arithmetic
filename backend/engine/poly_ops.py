"""Carry-free polynomial multiplication and Euclidean long division over GF(2)[x].

Original Author
---------------
Husein Zahweh — Milestone 3 (Extended Euclid Inverse, Field Division & Verification).
(Optional ``DivisionStep`` step-logging hook added by Ali Zahreddine during integration
to power the Multiplication Comparison lab.)

Mathematical Context & Course References
----------------------------------------
* **Stallings Chapter 4 (Finite Fields):** Unreduced polynomial arithmetic over
  ``Z_2[x]`` (Section 4.3) and Euclidean polynomial division used inside the
  Extended Euclidean Algorithm (Section 4.4 / Table 4.7) to update ``T1, T2, T3``.
* **Stallings Chapter 5 (AES), Chapter 6 (XTS-AES), & Chapter 10 (Binary ECC):**
  Core ring primitives underlying finite-field inversion across ``GF(2^8)``,
  ``GF(2^128)``, and ``GF(2^163)..GF(2^571)``.
"""
from __future__ import annotations

from dataclasses import dataclass

from .polyrepr import DEG, validate_non_negative_poly


def POLY_MUL_NO_MOD(a_int: int, b_int: int) -> int:
    """Compute unreduced carry-free product ``a(x) * b(x)`` over ``GF(2)[x]``.

    Over ``GF(2)``, partial products are summed using bitwise XOR with zero
    carries between adjacent coefficient positions and no modular reduction.

    Args:
        a_int: First polynomial operand as a non-negative integer bitmask.
        b_int: Second polynomial operand as a non-negative integer bitmask.

    Returns:
        Non-negative integer encoding ``a(x) * b(x)`` in ``GF(2)[x]``, satisfying
        ``deg(a * b) == deg(a) + deg(b)`` for nonzero operands (``0`` if either
        operand is ``0``).

    Raises:
        TypeError: If either operand is not an ``int`` (or is a ``bool``).
        ValueError: If either operand is negative.

    Complexity:
        Let ``da = deg(a_int)`` and ``db = deg(b_int)``. Iterates over the
        shorter operand in ``min(da, db) + 1`` steps, giving worst-case bit
        complexity ``O(min(da, db) * (da + db))`` and ``O(da + db)`` output space.
    """
    validate_non_negative_poly(a_int, name="a_int")
    validate_non_negative_poly(b_int, name="b_int")

    if a_int == 0 or b_int == 0:
        return 0

    # Multiplication over GF(2)[x] is commutative; walk the shorter bit-length operand.
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
    """One shifted-divisor XOR cancellation recorded during :func:`POLY_DIVMOD`.

    Attributes:
        shift: Left shift ``deg(R) - deg(B)`` applied to divisor ``B(x)``.
        before: Remainder bitmask before eliminating its leading term.
        shifted_divisor: Bitmask ``B(x) << shift`` aligned with ``before``.
        after: Remainder bitmask ``before XOR shifted_divisor`` after cancellation.
    """

    shift: int
    before: int
    shifted_divisor: int
    after: int


def POLY_DIVMOD(
    a_int: int,
    b_int: int,
    *,
    steps: list[DivisionStep] | None = None,
) -> tuple[int, int]:
    """Compute unique polynomial quotient and remainder ``A(x) = Q(x)*B(x) XOR R(x)``.

    Implements Euclidean polynomial long division over ``GF(2)[x]`` per Stallings
    Chapter 4 until ``R(x) == 0`` or ``deg(R) < deg(B)``.

    Args:
        a_int: Dividend polynomial ``A(x)`` as a non-negative integer bitmask.
        b_int: Nonzero divisor polynomial ``B(x)`` as a positive integer bitmask.
        steps: Optional list; when provided, each leading-term cancellation step
            is appended as a :class:`DivisionStep`.

    Returns:
        Tuple ``(q_int, r_int)`` of non-negative integers satisfying::

            POLY_MUL_NO_MOD(q_int, b_int) ^ r_int == a_int
            r_int == 0 or DEG(r_int) < DEG(b_int)

    Raises:
        TypeError: If either operand is not an ``int`` (or is a ``bool``).
        ValueError: If either operand is negative.
        ZeroDivisionError: If ``b_int == 0``.

    Complexity:
        Let ``da = deg(a_int)`` and ``db = deg(b_int)``. Runs in ``O(1)`` when
        ``da < db``; otherwise performs at most ``da - db + 1`` shift-and-XOR
        cancellations for worst-case time ``O((da - db + 1) * da)`` bit ops and
        ``O(da)`` space (or ``O((da - db + 1) * da)`` when ``steps`` is recorded).
    """
    validate_non_negative_poly(a_int, name="a_int")
    validate_non_negative_poly(b_int, name="b_int")

    if b_int == 0:
        raise ZeroDivisionError("Division by zero polynomial B(x) = 0 is undefined.")

    q_int = 0
    r_int = a_int
    deg_b = DEG(b_int)

    while r_int != 0:
        deg_r = r_int.bit_length() - 1
        if deg_r < deg_b:
            break
        # Align divisor's leading term with remainder's leading term and cancel via XOR.
        shift = deg_r - deg_b
        q_int ^= 1 << shift
        shifted = b_int << shift
        reduced = r_int ^ shifted
        if steps is not None:
            steps.append(DivisionStep(shift, r_int, shifted, reduced))
        r_int = reduced

    return q_int, r_int

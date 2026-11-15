"""Custom exception classes for Milestone 3 GF(2^m) inverse and division.

Mathematical Context
--------------------
Per Stallings, *Cryptography and Network Security*, Chapter 4 (Finite Fields),
the Extended Euclidean Algorithm over GF(2)[x] / <m(x)> terminates in one of
two well-defined states:

1. ``B3(x) = 1``: ``gcd(m(x), b(x)) = 1``, and ``B2(x)`` holds the unique
   multiplicative inverse ``b(x)^(-1) mod m(x)``.
2. ``B3(x) = 0``: No multiplicative inverse exists, and ``A3(x)`` equals
   ``gcd(m(x), b(x))``.
   * If ``b(x) mod m(x) == 0``, termination happens immediately at Step 0 with
     ``A3(x) = m(x)`` -> raises :class:`ZeroElementHasNoInverseError`.
   * If termination occurs mid-loop with ``B3(x) = 0`` (possible only when
     ``m(x)`` is reducible and shares a non-trivial factor with ``b(x)``),
     ``A3(x) = gcd(m(x), b(x))`` -> raises :class:`NotInvertibleError`.

Both exceptions carry ``gcd`` and ``trace`` attributes so educational callers
and the Milestone 2/4/5 API & GUI layers can display the full Table 4.7 trace
and explain *why* the element has no inverse.
"""
from __future__ import annotations

from typing import Any, Optional


class GF2mInverseError(ValueError):
    """Base error raised when an element in GF(2)[x] / <m(x)> has no inverse.

    Attributes:
        gcd: Integer bit-string representation of ``gcd(m(x), b(x))`` captured
            from ``A3(x)`` when Extended Euclid terminates with ``B3(x) = 0``.
        trace: Structured Extended Euclid trace (list of Table 4.7 row dicts or
            trace dictionary) captured up to the termination step.
    """

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        gcd: int = 0,
        trace: Optional[Any] = None,
    ) -> None:
        if message is None:
            message = (
                "Element has no multiplicative inverse modulo m(x); "
                f"gcd(m(x), b(x)) = 0x{gcd:X}."
            )
        super().__init__(message)
        self.gcd: int = gcd
        self.trace: Optional[Any] = trace


class ZeroElementHasNoInverseError(GF2mInverseError):
    """Raised when attempting to invert or divide by 0 (mod m(x)).

    Per Stallings Chapter 4, the additive identity ``0`` has no multiplicative
    inverse in any finite field GF(2^m). When ``b(x) mod m(x) == 0``,
    Extended Euclid terminates at Step 0 with ``B3(x) = 0`` and
    ``A3(x) = gcd(m(x), 0) = m(x)``.

    Attributes:
        gcd: ``m_poly_int`` (equals ``gcd(m(x), 0)``).
        trace: Trace containing Step 0 of Table 4.7.
    """

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        gcd: int = 0,
        trace: Optional[Any] = None,
    ) -> None:
        if message is None:
            message = (
                "Zero element has no multiplicative inverse in GF(2^m): "
                "Extended Euclid terminated at Step 0 with B3(x) = 0 and "
                f"A3(x) = gcd(m(x), 0) = 0x{gcd:X}."
            )
        super().__init__(message, gcd=gcd, trace=trace)


class NotInvertibleError(GF2mInverseError):
    """Raised when gcd(m(x), b(x)) != 1 during Extended Euclid.

    Per Stallings Chapter 4, if ``B3(x)`` reaches ``0`` after one or more
    Euclidean division steps, then ``m(x)`` and ``b(x)`` share a non-trivial
    common divisor ``A3(x) = gcd(m(x), b(x))`` of degree >= 1 (which can only
    happen if the supplied modulus ``m(x)`` is reducible).

    Attributes:
        gcd: Non-trivial common divisor ``A3(x) = gcd(m(x), b(x))``.
        trace: Complete Table 4.7 trace up to the ``B3(x) == 0`` step.
    """

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        gcd: int = 0,
        trace: Optional[Any] = None,
    ) -> None:
        if message is None:
            message = (
                "Polynomial is not invertible modulo m(x): Extended Euclid "
                "terminated with B3(x) = 0 and non-trivial factor "
                f"A3(x) = gcd(m(x), b(x)) = 0x{gcd:X}."
            )
        super().__init__(message, gcd=gcd, trace=trace)

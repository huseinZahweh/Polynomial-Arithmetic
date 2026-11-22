"""Custom domain exceptions for GF(2^m) multiplicative inversion and division.

Original Author
---------------
Husein Zahweh — Milestone 3 (Extended Euclid Inverse, Field Division & Verification).

Mathematical Context & Course References
----------------------------------------
Per William Stallings, *Cryptography and Network Security*, **Chapter 4 (Finite Fields)**,
the Extended Euclidean Algorithm over ``GF(2)[x] / <m(x)>`` terminates in one of two
well-defined states:

1. ``B3(x) == 1``: ``gcd(m(x), b(x)) == 1``, and ``B2(x)`` holds the unique
   multiplicative inverse ``b(x)^(-1) mod m(x)``.
2. ``B3(x) == 0``: No multiplicative inverse exists, and ``A3(x) == gcd(m(x), b(x))``:
   * If ``b(x) mod m(x) == 0``, termination occurs at Step 0 with ``A3(x) = m(x)``,
     raising :class:`ZeroElementHasNoInverseError`.
   * If termination occurs mid-loop (possible only when ``m(x)`` is reducible and
     shares a non-trivial factor with ``b(x)``), ``A3(x) = gcd(m(x), b(x))``,
     raising :class:`NotInvertibleError`.

Both subclasses attach ``.gcd`` and ``.trace`` so the API layer and educational
frontend can render the exact Table 4.7 termination row inside HTTP 400 responses.
"""
from __future__ import annotations

from typing import Any, Optional


class GF2mInverseError(ValueError):
    """Base error raised when an element in ``GF(2)[x] / <m(x)>`` has no inverse.

    Attributes:
        gcd (int): Polynomial bitmask of ``gcd(m(x), b(x))`` captured from
            ``A3(x)`` when Extended Euclid terminates with ``B3(x) == 0``.
        trace (Optional[Any]): Structured Table 4.7 trace dictionary captured up
            to the termination step so callers can explain why no inverse exists.
    """

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        gcd: int = 0,
        trace: Optional[Any] = None,
    ) -> None:
        """Initialize the inverse error with optional educational GCD and trace.

        Args:
            message: Human-readable explanation. Defaults to a message citing ``gcd``.
            gcd: Integer bitmask of ``A3(x) = gcd(m(x), b(x))``.
            trace: Table 4.7 trace dictionary recorded up to termination.
        """
        if message is None:
            message = (
                "Element has no multiplicative inverse modulo m(x); "
                f"gcd(m(x), b(x)) = 0x{gcd:X}."
            )
        super().__init__(message)
        self.gcd: int = gcd
        self.trace: Optional[Any] = trace


class ZeroElementHasNoInverseError(GF2mInverseError):
    """Raised when inverting or dividing by an element congruent to ``0 mod m(x)``.

    Per Stallings Chapter 4, the additive identity ``0`` has no multiplicative
    inverse in any finite field ``GF(2^m)``. When ``b(x) mod m(x) == 0``, Extended
    Euclid terminates immediately at Step 0 with ``B3(x) = 0`` and
    ``A3(x) = gcd(m(x), 0) = m(x)``.

    Attributes:
        gcd (int): ``m_poly_int`` (equals ``gcd(m(x), 0)``).
        trace (Optional[Any]): Trace dictionary containing Step 0 of Table 4.7.
    """

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        gcd: int = 0,
        trace: Optional[Any] = None,
    ) -> None:
        """Initialize a zero-inverse error carrying ``gcd = m(x)`` and Step 0 trace.

        Args:
            message: Optional override message.
            gcd: Reduction polynomial bitmask ``m_poly_int``.
            trace: Table 4.7 trace dictionary containing Step 0.
        """
        if message is None:
            message = (
                "Zero element has no multiplicative inverse in GF(2^m): "
                "Extended Euclid terminated at Step 0 with B3(x) = 0 and "
                f"A3(x) = gcd(m(x), 0) = 0x{gcd:X}."
            )
        super().__init__(message, gcd=gcd, trace=trace)


class NotInvertibleError(GF2mInverseError):
    """Raised when ``gcd(m(x), b(x)) != 1`` mid-loop during Extended Euclid.

    Per Stallings Chapter 4, reaching ``B3(x) == 0`` after one or more division
    iterations proves ``m(x)`` and ``b(x)`` share a non-trivial factor
    ``A3(x) = gcd(m(x), b(x))`` of degree ``>= 1`` (which occurs only when the
    supplied modulus ``m(x)`` is reducible).

    Attributes:
        gcd (int): Non-trivial common divisor ``A3(x) = gcd(m(x), b(x))``.
        trace (Optional[Any]): Complete Table 4.7 trace up to ``B3(x) == 0``.
    """

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        gcd: int = 0,
        trace: Optional[Any] = None,
    ) -> None:
        """Initialize a non-invertible error with the shared factor and trace.

        Args:
            message: Optional override message.
            gcd: Non-trivial common divisor ``A3(x) = gcd(m(x), b(x))``.
            trace: Complete Table 4.7 trace up to the ``B3(x) == 0`` row.
        """
        if message is None:
            message = (
                "Polynomial is not invertible modulo m(x): Extended Euclid "
                "terminated with B3(x) = 0 and non-trivial factor "
                f"A3(x) = gcd(m(x), b(x)) = 0x{gcd:X}."
            )
        super().__init__(message, gcd=gcd, trace=trace)

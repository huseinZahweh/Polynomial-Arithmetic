"""Reference multiplicative inverse + division engine.

INTEGRATION CONTRACT — owned by Milestone 3 on merge.

Inverse is computed with the Extended Euclidean Algorithm over GF(2)[x]/m(x)
(Stallings Table 4.7). Division is a(x)/b(x) = a(x) * b(x)^-1 mod m(x). A basic
Euclid-step trace is returned so /api/calculate is usable now; M3 owns the full
Table 4.7 trace logger that replaces it.
"""
from __future__ import annotations

from typing import List, Tuple

from ..multiply import carryless_mul, multiply, reduce_mod
from .. import polyrepr


class NoInverseError(ValueError):
    """Raised when an element has no multiplicative inverse (e.g. 0)."""


def _poly_divmod(a: int, b: int) -> Tuple[int, int]:
    """Carry-less polynomial division: return (quotient, remainder)."""
    if b == 0:
        raise ZeroDivisionError("division by zero polynomial")
    db = b.bit_length() - 1
    q = 0
    r = a
    while r and r.bit_length() - 1 >= db:
        shift = (r.bit_length() - 1) - db
        q ^= 1 << shift
        r ^= b << shift
    return q, r


def inverse(a: int, mod_poly: int, m: int, with_trace: bool = False):
    """Return a(x)^-1 mod m(x) (and a trace if requested)."""
    a = reduce_mod(a, mod_poly, m)
    if a == 0:
        raise NoInverseError("0 has no multiplicative inverse")

    old_r, r = mod_poly, a
    old_s, s = 0, 1
    steps: List[dict] = []
    while r != 0:
        q, _ = _poly_divmod(old_r, r)
        old_r, r = r, old_r ^ carryless_mul(q, r)
        old_s, s = s, old_s ^ carryless_mul(q, s)
        if with_trace:
            steps.append(
                {
                    "quotient_hex": polyrepr.to_hex(q, m + 1),
                    "remainder_hex": polyrepr.to_hex(old_r, m + 1),
                    "coeff_hex": polyrepr.to_hex(reduce_mod(old_s, mod_poly, m), m),
                }
            )

    if old_r != 1:  # gcd != 1 -> not invertible (cannot happen for irreducible m(x))
        raise NoInverseError("element is not invertible in this field")

    result = reduce_mod(old_s, mod_poly, m)
    if not with_trace:
        return result
    trace = {
        "algorithm": "extended-euclidean",
        "steps": steps,
        "summary": {"iterations": len(steps)},
    }
    return result, trace


def divide(a: int, b: int, mod_poly: int, m: int, with_trace: bool = False):
    """Return a(x) / b(x) mod m(x) = a * b^-1."""
    if with_trace:
        inv, trace = inverse(b, mod_poly, m, with_trace=True)
        result = multiply(a, inv, mod_poly, m)
        trace["inverse_of_b_hex"] = polyrepr.to_hex(inv, m)
        return result, trace
    inv = inverse(b, mod_poly, m)
    return multiply(a, inv, mod_poly, m)

"""Bridge the API to Milestone 3 using Milestone 2's multiplication engine."""

from gf2m.multiply import multiply, multiply_traced
from gf2m_m1.additive import MOD_REDUCE
from gf2m_m3 import (
    EXTENDED_EUCLID_GF2M,
    GF2M_DIVIDE,
    GF2mInverseError as NoInverseError,
    VERIFY_DIVISION,
    VERIFY_INVERSE,
)


def _multiply_traced(a, b, modulus, degree):
    result, trace = multiply_traced(a, b, modulus, degree)
    return result, trace.dict()


def inverse(a, mod_poly, m, with_trace=False):
    """Adapt the API argument order and return the full Extended Euclid trace."""
    result, trace = EXTENDED_EUCLID_GF2M(mod_poly, m, a, reduce_traced=MOD_REDUCE)
    return (result, trace) if with_trace else result


def divide(a, b, mod_poly, m, with_trace=False):
    """Combine the canonical inversion and multiplication engines."""
    if not with_trace:
        return multiply(a, inverse(b, mod_poly, m), mod_poly, m)
    return GF2M_DIVIDE(
        a, b, mod_poly, m, multiply_traced=_multiply_traced, reduce_traced=MOD_REDUCE,
    )


def verify_inverse(a, result, modulus, degree):
    return VERIFY_INVERSE(a, result, modulus, degree, multiply=multiply)


def verify_division(a, b, result, modulus, degree):
    return VERIFY_DIVISION(a, b, result, modulus, degree, multiply=multiply)

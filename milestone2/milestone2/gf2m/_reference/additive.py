"""Reference additive + modulo engine.

INTEGRATION CONTRACT — owned by Milestone 1 on merge.

Addition and subtraction in GF(2^m) are both bitwise XOR (coefficients live in
Z_2). Modulo reduction brings any polynomial down to degree < m. A light trace
is provided so the /api/calculate endpoint can return "Add/Sub XOR rows" data
to the GUI even before M1's richer visualizer lands.
"""
from __future__ import annotations

from ..multiply import reduce_mod
from .. import polyrepr


def add(a: int, b: int, mod_poly: int, m: int) -> int:
    return (a ^ b)


def subtract(a: int, b: int, mod_poly: int, m: int) -> int:
    # Identical to addition in characteristic 2.
    return (a ^ b)


def modulo(a: int, mod_poly: int, m: int) -> int:
    return reduce_mod(a, mod_poly, m)


def xor_trace(a: int, b: int, m: int) -> dict:
    """Column-wise XOR trace for the Add/Sub visualizer."""
    width = max(m, a.bit_length(), b.bit_length())
    columns = []
    for i in range(width - 1, -1, -1):
        ba, bb = (a >> i) & 1, (b >> i) & 1
        columns.append({"exp": i, "a": ba, "b": bb, "xor": ba ^ bb})
    return {
        "algorithm": "bitwise-xor",
        "a_bin": polyrepr.to_bin(a, m),
        "b_bin": polyrepr.to_bin(b, m),
        "result_bin": polyrepr.to_bin(a ^ b, m),
        "columns": columns,
    }

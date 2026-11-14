"""Milestone 2 — Shift-and-XOR multiplication engine for GF(2^m).

OWNER: Milestone 2.

Computes ``c(x) = a(x) * b(x) mod m(x)`` using the classic shift-and-XOR
("shift and add") algorithm taught in EECE 455/632 (Stallings, Ch. 4), and
emits a structured, step-by-step trace that the GUI renders as:

* **Table 1 — shift / reduce:** for each position *i*, the running value
  ``t_i = a(x) * x^i mod m(x)`` and whether producing it required a reduction
  (an XOR with the reduction polynomial because the x^m term appeared).
* **Table 2 — accumulate:** for each set bit of the multiplier ``b``, the
  partial product ``t_i`` is XORed into the accumulator; the running sum after
  the final step is the product.

Conventions
-----------
Elements are Python ``int``s: bit *i* is the coefficient of x^i. The reduction
polynomial ``mod_poly`` is a full integer *including* its x^m term — e.g.
GF(2^3) with m(x) = x^3 + x + 1 is ``0b1011`` (= 11). ``m`` is the field degree.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import polyrepr


# --------------------------------------------------------------------------- #
# Low-level field primitives (kept here so the engine is self-contained)       #
# --------------------------------------------------------------------------- #
def reduce_mod(value: int, mod_poly: int, m: int) -> int:
    """Reduce ``value`` modulo ``m(x)`` so the result has degree < m."""
    while value.bit_length() - 1 >= m:
        shift = (value.bit_length() - 1) - m
        value ^= mod_poly << shift
    return value


def carryless_mul(a: int, b: int) -> int:
    """Carry-less (XOR) polynomial product of ``a`` and ``b``; *no* reduction.

    Used only as an independent cross-check reference inside tests and for the
    fast path's correctness guarantees.
    """
    result = 0
    while b:
        if b & 1:
            result ^= a
        a <<= 1
        b >>= 1
    return result


# --------------------------------------------------------------------------- #
# Fast path (no trace) — used for division, benchmarking, large fields         #
# --------------------------------------------------------------------------- #
def multiply(a: int, b: int, mod_poly: int, m: int) -> int:
    """Return ``a * b mod m(x)`` via shift-and-XOR, without building a trace."""
    a = reduce_mod(a, mod_poly, m)
    b = reduce_mod(b, mod_poly, m)
    result = 0
    t = a
    top = 1 << m
    while b:
        if b & 1:
            result ^= t
        b >>= 1
        if b:  # avoid a final useless shift/reduce
            t <<= 1
            if t & top:
                t ^= mod_poly
    return result


# --------------------------------------------------------------------------- #
# Traced path — drives the GUI's Table 1 & Table 2 visualizers                 #
# --------------------------------------------------------------------------- #
@dataclass
class ShiftStep:
    """One iteration *i* of the shift-and-XOR loop."""

    i: int
    multiplier_bit: int         # bit i of b
    partial_hex: str            # t_i = a * x^i mod m(x)   (Table 1 cell)
    partial_poly: str           # same, algebraic form
    reduced: bool               # was t_i formed via a reduction?   (Table 1 flag)
    added: bool                 # was t_i XORed into the accumulator? (Table 2)
    accumulator_hex: str        # running product after this step    (Table 2 cell)

    def dict(self) -> dict:
        return self.__dict__


@dataclass
class MultiplyTrace:
    """Full structured trace plus a compact summary for badges."""

    algorithm: str
    m: int
    reduction_poly_hex: str
    operand_a_hex: str
    operand_b_hex: str
    steps: List[ShiftStep] = field(default_factory=list)
    reductions: int = 0
    partial_products: int = 0
    truncated: bool = False  # True if max_steps capped the trace

    def dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "m": self.m,
            "reduction_poly_hex": self.reduction_poly_hex,
            "operand_a_hex": self.operand_a_hex,
            "operand_b_hex": self.operand_b_hex,
            "steps": [s.dict() for s in self.steps],
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
) -> Tuple[int, MultiplyTrace]:
    """Return ``(result, trace)`` for ``a * b mod m(x)``.

    The loop stops once the remaining high bits of ``b`` are all zero, so a
    sparse multiplier produces a short trace even in GF(2^571). ``max_steps``
    bounds the number of recorded rows (not correctness): if the field is large
    and ``b`` is dense, recording is stopped early and ``trace.truncated`` is
    set, while the *result* is always computed in full.
    """
    a = reduce_mod(a, mod_poly, m)
    b_reduced = reduce_mod(b, mod_poly, m)

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
    b = b_reduced
    while b:
        bit = b & 1
        added = bit == 1
        if added:
            result ^= t
            trace.partial_products += 1

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

        b >>= 1
        i += 1
        if b:  # advance t = t * x mod m(x) only while more bits remain
            t <<= 1
            if t & top:
                t ^= mod_poly
                t_was_reduced = True
                trace.reductions += 1
            else:
                t_was_reduced = False

    return result, trace

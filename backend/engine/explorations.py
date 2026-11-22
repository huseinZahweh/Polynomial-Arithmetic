"""Pure-Python interactive exploration engines for the Finite Field Lab.

Original Author
---------------
Ali Zahreddine — Milestone 4 & Integration (Bonus Teaching & Exploration Tools).

Purpose & Course References
---------------------------
Provides three pure-math classroom explorations built directly on the canonical
``backend.engine`` primitives (with zero HTTP/web dependencies):

1. **Modulus Explorer (:func:`explore_modulus`):** Tests irreducibility of any
   binary polynomial of degree ``2 <= d <= 571`` via Frobenius GCD checkpoints
   ``gcd(f(x), x^(2^i) + x)`` for ``1 <= i <= floor(d / 2)`` (Stallings **Chapter 4**
   irreducible-polynomial foundation). When ``f(x)`` is a product of distinct
   irreducible factors of equal degree ``i`` so the first nontrivial GCD equals
   ``f(x)`` itself, :func:`_split_square_free` extracts a proper factor witness
   via Berlekamp's ``GF(2)`` kernel (**bonus mathematical extension beyond
   Stallings Chapter 4**).
2. **AES S-Box Walkthrough (:func:`compute_aes_sbox`):** Computes the full
   FIPS 197 §5.1.1 / Stallings **Chapter 5** SubBytes substitution: multiplicative
   inversion in ``GF(2^8)`` modulo ``0x11B`` (mapping ``0x00 -> 0x00``) followed
   by the 4 cyclic left bit-rotations and ``0x63`` affine XOR transformation.
3. **Multiplication Method Comparison & Benchmarks
   (:func:`compare_multiplication`, :func:`benchmark_multiplication`):**
   Compares interleaved Shift-and-XOR reduction (:func:`multiply_traced`,
   Stallings **Chapter 4**) against deferred reduction (carry-free product
   :func:`POLY_MUL_NO_MOD` followed by Euclidean long division :func:`POLY_DIVMOD`),
   plus deterministic 31-trial median benchmarks at ``m = 163`` and ``m = 571``
   (Stallings **Chapter 10** binary ECC field sizes).
"""
from __future__ import annotations

from random import Random
from statistics import median
from time import perf_counter_ns
from typing import Any

from .additive import modulo
from .extended_euclid import EXTENDED_EUCLID_GF2M
from .fields import get_field
from .multiply import multiply, multiply_traced
from .poly_ops import DivisionStep, POLY_DIVMOD, POLY_MUL_NO_MOD
from .polyrepr import ElementRepr, INT_TO_HEX, validate_non_negative_poly


def _repr(value: int, bits: int) -> dict[str, Any]:
    """Format polynomial ``value`` into the standard ``ElementRepr`` dictionary."""
    return ElementRepr.from_int(value, bits).dict()


def _poly_gcd(a: int, b: int) -> int:
    """Compute ``gcd(a(x), b(x))`` over ``GF(2)[x]`` via Euclidean remaindering.

    Args:
        a: First non-negative polynomial bitmask.
        b: Second non-negative polynomial bitmask.

    Returns:
        Greatest common divisor polynomial bitmask over ``GF(2)[x]``.

    Complexity:
        Let ``d = max(deg(a), deg(b))``. Time ``O(d^2)`` bit operations;
        space ``O(d)``.
    """
    while b:
        a, b = b, POLY_DIVMOD(a, b)[1]
    return a


def _split_square_free(polynomial: int) -> int:
    """Extract a nontrivial factor from a square-free equal-degree product over ``GF(2)``.

    **Bonus Mathematical Extension (beyond Stallings Chapter 4):** Constructs
    the Berlekamp matrix ``Q - I`` where ``Q`` maps ``x^j -> x^(2j) mod f(x)``
    over ``GF(2)``, and performs Gaussian elimination over columns to find a
    nonconstant fixed point ``h(x)`` satisfying ``h(x)^2 == h(x) (mod f(x))``.
    Because ``h(x)`` evaluates to ``0`` on some irreducible factors and ``1``
    on the remainder, ``gcd(h(x), f(x))`` yields a proper factor.

    Args:
        polynomial: Reducible square-free polynomial bitmask whose irreducible
            factors all share the same degree.

    Returns:
        Nontrivial proper factor bitmask ``g(x)`` with ``1 < deg(g) < deg(f)``
        (or ``1 <= deg(g) < deg(f)``).

    Raises:
        RuntimeError: If invoked on an irreducible polynomial (violating the
            caller precondition that ``polynomial`` is reducible and square-free).

    Complexity:
        Let ``d = deg(polynomial)``. Performs ``O(d)`` squarings and column
        eliminations of ``d``-bit vectors, giving ``O(d^3)`` bit operations
        (fast in practice via Python word-level integer XOR) and ``O(d^2)`` space.
    """
    # Map leading bit index -> (eliminated column vector, original linear combination).
    pivots: dict[int, tuple[int, int]] = {}
    for power in range(1, polynomial.bit_length() - 1):
        combination = 1 << power
        # Column for basis element x^power is (x^(2*power) mod f) XOR x^power.
        column = POLY_DIVMOD(1 << (2 * power), polynomial)[1] ^ combination
        while column:
            pivot = column.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = (column, combination)
                break
            old_column, old_combination = pivots[pivot]
            column ^= old_column
            combination ^= old_combination
        # A zeroed column means 'combination' lies in ker(Q - I), i.e. h^2 = h mod f.
        if column == 0:
            return _poly_gcd(combination, polynomial)
    raise RuntimeError("A reducible square-free polynomial must have a nonconstant fixed point")


def explore_modulus(polynomial: int) -> dict[str, Any]:
    """Test irreducibility of a binary polynomial of degree ``2..571`` and find factors.

    Uses Rabin's distinct-degree divisibility criterion over ``GF(2)[x]``:
    ``x^(2^i) + x`` is the product of all monic irreducible polynomials whose
    degree divides ``i``. Iteratively squaring ``x`` modulo ``f(x)`` for
    ``i = 1 .. floor(deg(f) / 2)`` detects the smallest irreducible factor degree.

    Args:
        polynomial: Non-negative binary polynomial bitmask of degree ``2..571``.

    Returns:
        Dictionary containing ``modulus``, ``degree``, ``irreducible`` (bool),
        ``checks`` (list of GCD checkpoints), ``witness`` (factorization proof
        showing ``a * b == modulus`` and remainder ``0``, or ``None``), and
        ``split_with_berlekamp`` (bool).

    Raises:
        TypeError: If ``polynomial`` is not an ``int`` (or is ``bool``).
        ValueError: If ``polynomial < 0`` or its degree is outside ``2..571``.

    Complexity:
        Let ``d = deg(polynomial)``. Runs up to ``d // 2`` modular squarings and
        polynomial GCDs (``O(d^3)`` bit operations worst case), plus optional
        ``O(d^3)`` Berlekamp splitting when all factors share the same degree;
        space ``O(d^2)`` for checkpoint formatting.
    """
    validate_non_negative_poly(polynomial, "modulus")
    degree = polynomial.bit_length() - 1
    if not 2 <= degree <= 571:
        raise ValueError("Enter a modulus of degree 2 through 571.")

    checks: list[dict[str, Any]] = []
    factor = 1
    residue = 0b10  # x^(2^0) = x
    split = False
    for i in range(1, degree // 2 + 1):
        # Advance residue from x^(2^(i-1)) to x^(2^i) mod f(x).
        residue = POLY_DIVMOD(POLY_MUL_NO_MOD(residue, residue), polynomial)[1]
        common = _poly_gcd(polynomial, residue ^ 0b10)
        checks.append(
            {
                "i": i,
                "power_remainder_hex": INT_TO_HEX(residue, 1),
                "gcd_hex": INT_TO_HEX(common, 1),
            }
        )
        if common != 1:
            # If the first nontrivial GCD equals f itself, f is square-free and all
            # its irreducible factors have degree i -> split via Berlekamp kernel.
            split = common == polynomial
            factor = _split_square_free(polynomial) if split else common
            break

    witness: dict[str, Any] | None = None
    if factor != 1:
        cofactor, _ = POLY_DIVMOD(polynomial, factor)
        product = POLY_MUL_NO_MOD(factor, cofactor)
        witness = {
            "a": _repr(factor, 1),
            "b": _repr(cofactor, 1),
            "product": _repr(product, 1),
            "remainder": _repr(POLY_DIVMOD(product, polynomial)[1], 1),
        }

    return {
        "modulus": _repr(polynomial, degree + 1),
        "degree": degree,
        "irreducible": witness is None,
        "checks": checks,
        "witness": witness,
        "split_with_berlekamp": split,
    }


def compute_aes_sbox(byte: int) -> dict[str, Any]:
    """Compute the FIPS 197 §5.1.1 / Stallings Ch. 5 AES S-box transformation.

    Stage 1 inverts ``byte`` in ``GF(2^8)`` modulo ``0x11B`` via
    :func:`EXTENDED_EUCLID_GF2M` (mapping ``0x00 -> 0x00`` per the AES zero rule).
    Stage 2 XORs the inverse byte with its 4 cyclic left bit-rotations and the
    affine constant ``0x63`` (``01100011``).

    Args:
        byte: Input byte integer in ``[0, 255]``.

    Returns:
        Dictionary containing ``input``, ``inverse``, ``inverse_trace`` (Table 4.7
        trace or ``None`` for ``byte == 0``), ``affine_rows`` (6 cumulative XOR
        rows), and ``output``.

    Raises:
        TypeError: If ``byte`` is not an ``int`` (or is ``bool``).
        ValueError: If ``byte < 0`` or ``byte > 0xFF``.

    Complexity:
        Constant time ``O(1)`` (fixed 8-bit field width) and ``O(1)`` space.
    """
    validate_non_negative_poly(byte, "byte")
    if byte > 0xFF:
        raise ValueError("Enter one byte, from 00 through FF in hex.")

    field = get_field(8)
    if byte:
        inverted, trace = EXTENDED_EUCLID_GF2M(field.mod_poly, field.m, byte)
    else:
        # FIPS 197 §5.1.1 defines the multiplicative inverse of 0x00 as 0x00.
        inverted, trace = 0, None

    running = 0
    rows: list[dict[str, Any]] = []
    # Equivalent to the 8x8 circulant AES affine matrix multiplication over GF(2).
    for shift in range(5):
        rotated = ((inverted << shift) | (inverted >> (8 - shift))) & 0xFF
        running ^= rotated
        rows.append(
            {
                "label": "Inverse byte" if shift == 0 else f"Rotate left by {shift}",
                "value": _repr(rotated, 8),
                "running": _repr(running, 8),
            }
        )
    running ^= 0x63
    rows.append(
        {
            "label": "AES constant",
            "value": _repr(0x63, 8),
            "running": _repr(running, 8),
        }
    )

    return {
        "input": _repr(byte, 8),
        "inverse": _repr(inverted, 8),
        "inverse_trace": trace,
        "affine_rows": rows,
        "output": _repr(running, 8),
    }


def _multiply_then_divide(a: int, b: int, modulus: int, _degree: int) -> int:
    """Deferred-reduction reference path: full carry-free product then long division."""
    return POLY_DIVMOD(POLY_MUL_NO_MOD(a, b), modulus)[1]


def compare_multiplication(m: int, a: int, b: int) -> dict[str, Any]:
    """Run interleaved Shift-and-XOR and deferred long-division multiplication side-by-side.

    Args:
        m: Supported field extension degree.
        a: Non-negative multiplicand bitmask (auto-reduced into ``GF(2^m)``).
        b: Non-negative multiplier bitmask (auto-reduced into ``GF(2^m)``).

    Returns:
        Dictionary comparing both results (``agree``), reduced operands,
        ``inputs_reduced`` flag, Shift-and-XOR trace, unreduced raw product,
        long-division quotient/remainder, and per-step leading-term cancellations.

    Raises:
        TypeError: If operands are not integers (or are booleans).
        ValueError: If ``m`` is unsupported or operands are negative.

    Complexity:
        Time ``O(m^2)`` bit operations; space ``O(m^2)`` for both traces.
    """
    field = get_field(m)
    validate_non_negative_poly(a, "a")
    validate_non_negative_poly(b, "b")

    reduced_a = modulo(a, field.mod_poly, field.m)
    reduced_b = modulo(b, field.mod_poly, field.m)

    # Method 1: Interleaved Shift-and-XOR reduction (Milestone 2).
    shifted, trace = multiply_traced(reduced_a, reduced_b, field.mod_poly, field.m)

    # Method 2: Deferred carry-free product followed by Euclidean long division (Milestone 3).
    raw = POLY_MUL_NO_MOD(reduced_a, reduced_b)
    steps: list[DivisionStep] = []
    quotient, remainder = POLY_DIVMOD(raw, field.mod_poly, steps=steps)
    divisions = [
        {
            "shift": row.shift,
            "before_hex": INT_TO_HEX(row.before, 1),
            "divisor_hex": INT_TO_HEX(row.shifted_divisor, 1),
            "after_hex": INT_TO_HEX(row.after, 1),
        }
        for row in steps
    ]

    return {
        "m": field.m,
        "modulus_hex": INT_TO_HEX(field.mod_poly, field.m + 1),
        "a": _repr(reduced_a, field.m),
        "b": _repr(reduced_b, field.m),
        "inputs_reduced": a != reduced_a or b != reduced_b,
        "agree": shifted == remainder,
        "shift_result": _repr(shifted, field.m),
        "shift_trace": trace.dict(),
        "raw_product": _repr(raw, 1),
        "quotient": _repr(quotient, 1),
        "remainder": _repr(remainder, field.m),
        "division_steps": divisions,
    }


def benchmark_multiplication(
    seed: int = 455,
    trials: int = 31,
    degrees: tuple[int, ...] = (163, 571),
) -> dict[str, Any]:
    """Benchmark untraced Shift-and-XOR vs. carry-free + long division on full-width operands.

    Alternates execution order on each trial to minimize cache/CPU-frequency bias,
    reporting median microseconds over ``trials`` repetitions on identical seeded
    operands with MSB set (full degree ``m - 1``).

    Args:
        seed: Deterministic PRNG seed (default ``455``).
        trials: Number of timed trials per method per field degree (default ``31``).
        degrees: Field degrees to benchmark (default ``(163, 571)``).

    Returns:
        Dictionary ``{"seed", "trials", "rows"}`` where each row contains
        ``m``, ``agree`` (bool), ``shift_xor_us``, and ``long_division_us``.

    Complexity:
        Time ``O(trials * sum(m^2))`` bit operations; space ``O(trials + max(m))``.
    """
    rng = Random(seed)
    rows: list[dict[str, Any]] = []
    for m in degrees:
        # Force bit (m - 1) to 1 so both operands are full-width degree-(m - 1) elements.
        a = (1 << (m - 1)) | rng.getrandbits(m - 1)
        b = (1 << (m - 1)) | rng.getrandbits(m - 1)
        modulus = get_field(m).mod_poly
        engines = (multiply, _multiply_then_divide)
        results = [engine(a, b, modulus, m) for engine in engines]
        samples: list[list[int]] = [[], []]
        for trial in range(trials):
            for index in (trial % 2, 1 - trial % 2):
                start = perf_counter_ns()
                engines[index](a, b, modulus, m)
                samples[index].append(perf_counter_ns() - start)
        rows.append(
            {
                "m": m,
                "agree": results[0] == results[1],
                "shift_xor_us": median(samples[0]) / 1000,
                "long_division_us": median(samples[1]) / 1000,
            }
        )
    return {"seed": seed, "trials": trials, "rows": rows}

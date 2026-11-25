"""Pure-Python interactive exploration engines for the Finite Field Lab.

Original Author
---------------
Ali Zahreddine — Milestone 4 & Integration (Bonus Teaching & Exploration Tools).

Purpose & Course References
---------------------------
Provides five pure-math classroom explorations and real-world applications built
directly on the canonical ``backend.engine`` primitives (with zero HTTP/web
dependencies):

1. **Modulus Explorer (:func:`explore_modulus`):** Tests irreducibility of any
   binary polynomial of degree ``2 <= d <= 571`` via Frobenius GCD checkpoints
   ``gcd(f(x), x^(2^i) + x)`` for ``1 <= i <= floor(d / 2)`` (Stallings **Chapter 4**
   irreducible-polynomial foundation). When ``f(x)`` is a product of distinct
   irreducible factors of equal degree ``i`` so the first nontrivial GCD equals
   ``f(x)`` itself, :func:`_split_square_free` extracts a proper factor witness
   via Berlekamp's ``GF(2)`` kernel (**bonus mathematical extension beyond
   Stallings Chapter 4**).
2. **XTS-AES Tweak Multiplier (:func:`compute_xts_tweak`):** Implements IEEE 1619-2007 /
   Stallings **Chapter 6** tweak progression ``T_j = T_0 * alpha^j mod m(x)`` over
   ``GF(2^128)`` modulo ``m(x) = x^128 + x^7 + x^2 + x + 1`` (reduction mask ``0x87``).
3. **Binary Elliptic Curve Explorer (:func:`explore_binary_ecc`):** Implements
   non-supersingular binary elliptic curve arithmetic ``E_{2^m}(a, b): y^2 + xy = x^3 + ax^2 + b``
   (Stallings **Chapter 10** & NIST FIPS 186-4 / SECG SEC 2 **B-163** plus a
   ``GF(2^4)`` teaching curve), including curve membership checks, point doubling
   ``2P``, point addition ``P + Q``, and compact double-and-add ECDH shared-secret
   derivation built directly on :mod:`backend.engine`.
4. **GCM / GHASH Authenticator (:func:`gcm_ghash`):** Implements NIST SP 800-38D /
   Stallings **Chapter 12** universal hashing over ``GF(2^128)`` modulo
   ``m(x) = x^128 + x^7 + x^2 + x + 1``, iteratively chaining full 128-bit XOR
   (:func:`add`) and Shift-and-XOR multiplication (:func:`multiply`):
   ``Y_i = (Y_{i-1} XOR X_i) * H mod m(x)``.
5. **Multiplication Method Comparison & Benchmarks
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

from .additive import add, modulo
from .division import GF2M_DIVIDE
from .extended_euclid import EXTENDED_EUCLID_GF2M
from .fields import get_field
from .multiply import multiply, multiply_traced
from .poly_ops import DivisionStep, POLY_DIVMOD, POLY_MUL_NO_MOD
from .polyrepr import (
    ElementRepr,
    INT_TO_ALGEBRAIC,
    INT_TO_HEX,
    parse_value,
    validate_non_negative_poly,
)

# IEEE 1619-2007 / Stallings Ch. 6 (XTS-AES) & NIST SP 800-38D / Stallings Ch. 12 (GCM/GHASH)
# GF(2^128) irreducible reduction constants.
XTS_DEGREE: int = 128
XTS_REDUCTION_MASK: int = 0x87
XTS_MASK_128: int = (1 << 128) - 1
XTS_MODULUS: int = (1 << 128) | XTS_REDUCTION_MASK
GHASH_DEGREE: int = XTS_DEGREE
GHASH_MODULUS: int = XTS_MODULUS

# Canonical Binary Elliptic Curve specifications (Stallings Ch. 10 & NIST FIPS 186-4 / SEC 2).
ECC_CURVES: dict[str, dict[str, Any]] = {
    "gf2_4": {
        "id": "gf2_4",
        "name": "Teaching Curve · GF(2^4)",
        "standard": "Stallings Ch. 10 binary curve pedagogy over GF(2^4)",
        "m": 4,
        "a": 1,
        "b": 1,
        "gx": 0x3,
        "gy": 0xC,
        "equation": "y^2 + xy = x^3 + x^2 + 1",
    },
    "nist_b163": {
        "id": "nist_b163",
        "name": "NIST B-163 · GF(2^163)",
        "standard": "NIST FIPS 186-4 / SECG SEC 2 (sect163r2)",
        "m": 163,
        "a": 1,
        "b": 0x20A601907B8C953CA1481EB10512F78744A3205FD,
        "gx": 0x3F0EBA16286A2D57EA0991168D4994637E8343E36,
        "gy": 0x0D51FBC6C71A0094FA2CDD545B11C5C0C797324F1,
        "equation": "y^2 + xy = x^3 + x^2 + b",
    },
}


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


def compute_xts_tweak(t0: int, steps: int = 6) -> dict[str, Any]:
    """Compute XTS-AES ``GF(2^128)`` tweak progression ``T_j = T_0 * alpha^j mod m(x)``.

    Implements the IEEE 1619-2007 / Stallings **Chapter 6** tweak update rule
    over ``GF(2^128)`` with primitive polynomial ``m(x) = x^128 + x^7 + x^2 + x + 1``
    (reduction mask ``0x87``). Multiplying by ``alpha = x`` shifts left by 1 bit
    and XORs the lower 128 bits with ``0x87`` whenever ``b_127 == 1`` overflows.

    Args:
        t0: Initial 128-bit tweak integer ``T_0`` in ``[0, 2^128 - 1]``.
        steps: Number of sequential ``alpha`` multiplications to trace (``1..16``).

    Returns:
        Dictionary containing field metadata (``m=128``, ``modulus_poly``,
        ``modulus_hex``, ``reduction_mask_hex``) and ``blocks`` for ``j = 0..steps``
        recording ``block_index``, ``tweak_hex``, ``msb_before_shift``,
        ``overflowed``, ``shifted_hex``, and ``reduced_xor_87``.

    Raises:
        TypeError: If ``t0`` or ``steps`` is not an ``int`` (or is ``bool``).
        ValueError: If ``t0 < 0``, ``t0 >= 2^128``, or ``steps`` is outside ``1..16``.

    Complexity:
        Time ``O(steps)`` word-level shifts/XORs; space ``O(steps)``.
    """
    validate_non_negative_poly(t0, "t0")
    if t0.bit_length() > XTS_DEGREE:
        raise ValueError("Initial tweak T0 must fit in 128 bits (at most 32 hex digits).")
    if not isinstance(steps, int) or isinstance(steps, bool) or not 1 <= steps <= 16:
        raise ValueError("Steps must be an integer between 1 and 16.")

    curr = t0
    blocks: list[dict[str, Any]] = [
        {
            "block_index": 0,
            "tweak_hex": INT_TO_HEX(curr, XTS_DEGREE).upper(),
            "msb_before_shift": (curr >> 127) & 1,
            "overflowed": False,
            "shifted_hex": INT_TO_HEX(curr, XTS_DEGREE).upper(),
            "reduced_xor_87": False,
        }
    ]
    for block_index in range(1, steps + 1):
        msb = (curr >> 127) & 1
        shifted = (curr << 1) & XTS_MASK_128
        overflowed = bool(msb)
        next_tweak = shifted ^ XTS_REDUCTION_MASK if overflowed else shifted
        blocks.append(
            {
                "block_index": block_index,
                "tweak_hex": INT_TO_HEX(next_tweak, XTS_DEGREE).upper(),
                "msb_before_shift": msb,
                "overflowed": overflowed,
                "shifted_hex": INT_TO_HEX(shifted, XTS_DEGREE).upper(),
                "reduced_xor_87": overflowed,
            }
        )
        curr = next_tweak

    return {
        "m": XTS_DEGREE,
        "modulus_poly": "x^128 + x^7 + x^2 + x + 1",
        "modulus_hex": INT_TO_HEX(XTS_MODULUS, XTS_DEGREE + 1).upper(),
        "reduction_mask_hex": "87",
        "t0_hex": INT_TO_HEX(t0, XTS_DEGREE).upper(),
        "steps": steps,
        "blocks": blocks,
    }


def ecc_is_on_curve(
    point: tuple[int, int] | None,
    a: int,
    b: int,
    mod_poly: int,
    m: int,
) -> bool:
    """Verify whether affine point ``(x, y)`` (or point at infinity ``None``) lies on ``E_{2^m}(a, b)``.

    Checks ``y^2 XOR (x * y) == x^3 XOR (a * x^2) XOR b (mod m(x))`` using the
    canonical :func:`backend.engine.additive.add` and :func:`backend.engine.multiply.multiply`.

    Args:
        point: Affine tuple ``(x, y)`` in ``GF(2^m)`` or ``None`` for identity ``O``.
        a: Curve coefficient ``a`` in ``GF(2^m)``.
        b: Curve coefficient ``b`` in ``GF(2^m)``.
        mod_poly: Irreducible modulus bitmask of degree ``m``.
        m: Field degree.

    Returns:
        ``True`` if ``point`` satisfies the binary elliptic curve equation.

    Complexity:
        Constant number of ``GF(2^m)`` multiplications and XORs: ``O(m^2)`` bit ops.
    """
    if point is None:
        return True
    x, y = point
    lhs = add(multiply(y, y, mod_poly, m), multiply(x, y, mod_poly, m), mod_poly, m)
    x2 = multiply(x, x, mod_poly, m)
    x3 = multiply(x2, x, mod_poly, m)
    rhs = add(add(x3, multiply(a, x2, mod_poly, m), mod_poly, m), b, mod_poly, m)
    return lhs == rhs


def _ecc_divide(num: int, den: int, mod_poly: int, m: int) -> int:
    """Compute ``num / den`` in ``GF(2^m)`` via canonical ``EXTENDED_EUCLID_GF2M`` + ``multiply``."""
    inv, _ = EXTENDED_EUCLID_GF2M(mod_poly, m, den)
    return multiply(num, inv, mod_poly, m)


def ecc_double(
    point: tuple[int, int] | None,
    a: int,
    mod_poly: int,
    m: int,
) -> tuple[tuple[int, int] | None, dict[str, Any]]:
    """Compute binary elliptic curve point doubling ``2P`` with traced algebraic steps.

    Formulas (Stallings **Chapter 10**, non-supersingular curve ``y^2 + xy = x^3 + ax^2 + b``):
        * If ``P = O`` or ``x_1 = 0``: ``2P = O`` (point at infinity).
        * Otherwise:
          ``lambda = x_1 XOR (y_1 / x_1)``,
          ``x_3 = lambda^2 XOR lambda XOR a``,
          ``y_3 = x_1^2 XOR (lambda XOR 1) * x_3``.

    Args:
        point: Affine tuple ``(x_1, y_1)`` or ``None`` for ``O``.
        a: Curve coefficient ``a``.
        mod_poly: Irreducible modulus bitmask of degree ``m``.
        m: Field degree.

    Returns:
        Tuple ``(result_point, trace_dict)`` with intermediate ``lambda``, ``x3``,
        and ``y3`` representations tagged by finite-field operation.

    Complexity:
        One Extended Euclid inversion plus 3 ``GF(2^m)`` multiplications: ``O(m^2)`` bit ops.
    """
    if point is None:
        return None, {
            "special_case": "Point at infinity O doubled stays O.",
            "steps": [],
        }
    x1, y1 = point
    if x1 == 0:
        return None, {
            "special_case": "x_1 = 0, so tangent is vertical and 2P = O (point at infinity).",
            "steps": [],
        }

    # Reuse canonical GF2M_DIVIDE (Stage 1 EEA + Stage 2 Shift-and-XOR) for y_1 / x_1.
    ratio, _ = GF2M_DIVIDE(y1, x1, mod_poly, m)
    lam = add(x1, ratio, mod_poly, m)
    lam2 = multiply(lam, lam, mod_poly, m)
    x3 = add(add(lam2, lam, mod_poly, m), a, mod_poly, m)
    x1_sq = multiply(x1, x1, mod_poly, m)
    lam_plus_1 = add(lam, 1, mod_poly, m)
    y3 = add(x1_sq, multiply(lam_plus_1, x3, mod_poly, m), mod_poly, m)

    return (x3, y3), {
        "special_case": None,
        "lambda": _repr(lam, m),
        "steps": [
            {
                "symbol": "y_1 / x_1",
                "formula": "y_1 * x_1^-1 mod m(x)",
                "engine_op": "÷ / EEA",
                "value": _repr(ratio, m),
            },
            {
                "symbol": "λ",
                "formula": "x_1 ⊕ (y_1 / x_1)",
                "engine_op": "⊕ XOR",
                "value": _repr(lam, m),
            },
            {
                "symbol": "x_3",
                "formula": "λ^2 ⊕ λ ⊕ a",
                "engine_op": "× Shift-and-XOR & ⊕ XOR",
                "value": _repr(x3, m),
            },
            {
                "symbol": "y_3",
                "formula": "x_1^2 ⊕ (λ ⊕ 1) · x_3",
                "engine_op": "× Shift-and-XOR & ⊕ XOR",
                "value": _repr(y3, m),
            },
        ],
    }


def ecc_add(
    p: tuple[int, int] | None,
    q: tuple[int, int] | None,
    a: int,
    mod_poly: int,
    m: int,
) -> tuple[tuple[int, int] | None, dict[str, Any]]:
    """Compute binary elliptic curve point addition ``P + Q`` with traced algebraic steps.

    Handles all group-law cases cleanly:
        * ``P = O`` returns ``Q``; ``Q = O`` returns ``P``.
        * ``x_1 == x_2`` and ``y_1 == x_2 XOR y_2`` (``P = -Q``) returns ``O``.
        * ``P == Q`` delegates to :func:`ecc_double`.
        * Distinct ``x_1 != x_2``:
          ``lambda = (y_1 XOR y_2) / (x_1 XOR x_2)``,
          ``x_3 = lambda^2 XOR lambda XOR x_1 XOR x_2 XOR a``,
          ``y_3 = lambda * (x_1 XOR x_3) XOR x_3 XOR y_1``.

    Args:
        p: First affine point ``(x_1, y_1)`` or ``None`` for ``O``.
        q: Second affine point ``(x_2, y_2)`` or ``None`` for ``O``.
        a: Curve coefficient ``a``.
        mod_poly: Irreducible modulus bitmask of degree ``m``.
        m: Field degree.

    Returns:
        Tuple ``(result_point, trace_dict)`` with intermediate ``lambda``, ``x3``,
        and ``y3`` values tagged by finite-field operation.

    Complexity:
        One Extended Euclid inversion plus 2 ``GF(2^m)`` multiplications: ``O(m^2)`` bit ops.
    """
    if p is None:
        return q, {"special_case": "P = O (identity), so O + Q = Q.", "steps": []}
    if q is None:
        return p, {"special_case": "Q = O (identity), so P + O = P.", "steps": []}

    x1, y1 = p
    x2, y2 = q
    if x1 == x2:
        if y1 == add(x2, y2, mod_poly, m):
            return None, {
                "special_case": "Q = -P (y_2 = x_1 ⊕ y_1), so P + (-P) = O (point at infinity).",
                "steps": [],
            }
        doubled, trace = ecc_double(p, a, mod_poly, m)
        trace["special_case"] = "P = Q, so P + Q delegates to point doubling 2P."
        return doubled, trace

    dy = add(y1, y2, mod_poly, m)
    dx = add(x1, x2, mod_poly, m)
    lam = _ecc_divide(dy, dx, mod_poly, m)
    lam2 = multiply(lam, lam, mod_poly, m)
    x3 = add(add(add(add(lam2, lam, mod_poly, m), x1, mod_poly, m), x2, mod_poly, m), a, mod_poly, m)
    x1_xor_x3 = add(x1, x3, mod_poly, m)
    y3 = add(add(multiply(lam, x1_xor_x3, mod_poly, m), x3, mod_poly, m), y1, mod_poly, m)

    return (x3, y3), {
        "special_case": None,
        "lambda": _repr(lam, m),
        "steps": [
            {
                "symbol": "λ",
                "formula": "(y_1 ⊕ y_2) / (x_1 ⊕ x_2)",
                "engine_op": "÷ / EEA",
                "value": _repr(lam, m),
            },
            {
                "symbol": "x_3",
                "formula": "λ^2 ⊕ λ ⊕ x_1 ⊕ x_2 ⊕ a",
                "engine_op": "× Shift-and-XOR & ⊕ XOR",
                "value": _repr(x3, m),
            },
            {
                "symbol": "y_3",
                "formula": "λ · (x_1 ⊕ x_3) ⊕ x_3 ⊕ y_1",
                "engine_op": "× Shift-and-XOR & ⊕ XOR",
                "value": _repr(y3, m),
            },
        ],
    }


def ecc_scalar_mul(
    k: int,
    point: tuple[int, int] | None,
    a: int,
    mod_poly: int,
    m: int,
) -> tuple[int, int] | None:
    """Compute scalar multiple ``k * P`` on ``E_{2^m}(a, b)`` via double-and-add.

    Args:
        k: Non-negative integer scalar multiplier.
        point: Base point ``P`` or ``None`` for ``O``.
        a: Curve coefficient ``a``.
        mod_poly: Irreducible modulus bitmask of degree ``m``.
        m: Field degree.

    Returns:
        Resulting affine point ``k * P`` or ``None`` for ``O``.

    Complexity:
        ``O(log(k))`` elliptic curve point doublings/additions (``O(log(k) * m^2)`` bit ops).
    """
    if not isinstance(k, int) or isinstance(k, bool) or k < 0:
        raise ValueError("Scalar multiplier k must be a non-negative integer.")
    result: tuple[int, int] | None = None
    addend = point
    n = k
    while n > 0:
        if n & 1:
            result, _ = ecc_add(result, addend, a, mod_poly, m)
        n >>= 1
        if n > 0:
            addend, _ = ecc_double(addend, a, mod_poly, m)
    return result


def _format_ecc_point(
    point: tuple[int, int] | None,
    a: int,
    b: int,
    mod_poly: int,
    m: int,
) -> dict[str, Any]:
    """Serialize an affine point (or identity ``O``) with curve membership verification."""
    if point is None:
        return {"is_infinity": True, "x": None, "y": None, "on_curve": True}
    x, y = point
    return {
        "is_infinity": False,
        "x": _repr(x, m),
        "y": _repr(y, m),
        "on_curve": ecc_is_on_curve(point, a, b, mod_poly, m),
    }


def explore_binary_ecc(
    curve_id: str = "nist_b163",
    p: tuple[int, int] | None = None,
    q: tuple[int, int] | None = None,
    n_a: int = 5,
    n_b: int = 9,
) -> dict[str, Any]:
    """Run Binary ECC point doubling, point addition, and ECDH key exchange on ``E_{2^m}(a, b)``.

    Supports both the ``GF(2^4)`` teaching curve (``gf2_4``) and official
    **NIST B-163** (``nist_b163``, FIPS 186-4 / SEC 2) using the unified
    ``backend.engine`` field primitives.

    Args:
        curve_id: Curve identifier (``"gf2_4"`` or ``"nist_b163"``).
        p: Optional custom point ``P = (x, y)`` (defaults to curve base point ``G``).
        q: Optional custom point ``Q = (x, y)`` (defaults to ``2G``).
        n_a: Alice's private scalar in ``[2, 25]`` for the ECDH demo (default ``5``).
        n_b: Bob's private scalar in ``[2, 25]`` for the ECDH demo (default ``9``).

    Returns:
        Dictionary with curve metadata, base point ``G``, ``point_p``, ``point_q``,
        traced ``doubling`` (``2P``), traced ``addition`` (``P + Q``), and ``ecdh``
        exchange results confirming ``n_a * (n_b * G) == n_b * (n_a * G)``.

    Raises:
        ValueError: If ``curve_id`` is unknown, ``n_a``/``n_b`` are out of ``[2, 25]``,
            or custom coordinates exceed ``2^m - 1`` or do not lie on the curve.

    Complexity:
        Time ``O((log(n_a) + log(n_b)) * m^2)`` bit operations; space ``O(m)``.
    """
    if curve_id not in ECC_CURVES:
        raise ValueError("Unsupported curve. Choose 'gf2_4' or 'nist_b163'.")
    for label, scalar in (("n_a", n_a), ("n_b", n_b)):
        if not isinstance(scalar, int) or isinstance(scalar, bool) or not 2 <= scalar <= 25:
            raise ValueError(f"{label} must be an integer between 2 and 25.")

    spec = ECC_CURVES[curve_id]
    m: int = spec["m"]
    field = get_field(m)
    mod_poly = field.mod_poly
    a: int = spec["a"]
    b: int = spec["b"]
    g_point = (spec["gx"], spec["gy"])

    if p is None:
        point_p = g_point
    else:
        validate_non_negative_poly(p[0], "P.x")
        validate_non_negative_poly(p[1], "P.y")
        if p[0].bit_length() > m or p[1].bit_length() > m:
            raise ValueError(f"Point P coordinates must fit in GF(2^{m}).")
        if not ecc_is_on_curve(p, a, b, mod_poly, m):
            raise ValueError(f"Point P is not on {spec['name']}.")
        point_p = p

    two_g, _ = ecc_double(g_point, a, mod_poly, m)
    if q is None:
        point_q = two_g
    else:
        validate_non_negative_poly(q[0], "Q.x")
        validate_non_negative_poly(q[1], "Q.y")
        if q[0].bit_length() > m or q[1].bit_length() > m:
            raise ValueError(f"Point Q coordinates must fit in GF(2^{m}).")
        if not ecc_is_on_curve(q, a, b, mod_poly, m):
            raise ValueError(f"Point Q is not on {spec['name']}.")
        point_q = q

    doubled_point, doubling_trace = ecc_double(point_p, a, mod_poly, m)
    added_point, addition_trace = ecc_add(point_p, point_q, a, mod_poly, m)

    pub_a = ecc_scalar_mul(n_a, g_point, a, mod_poly, m)
    pub_b = ecc_scalar_mul(n_b, g_point, a, mod_poly, m)
    shared_a = ecc_scalar_mul(n_a, pub_b, a, mod_poly, m)
    shared_b = ecc_scalar_mul(n_b, pub_a, a, mod_poly, m)

    return {
        "curve": {
            "id": spec["id"],
            "name": spec["name"],
            "standard": spec["standard"],
            "m": m,
            "equation": spec["equation"],
            "modulus_poly": INT_TO_ALGEBRAIC(mod_poly),
            "modulus_hex": INT_TO_HEX(mod_poly, m + 1).upper(),
            "a": _repr(a, m),
            "b": _repr(b, m),
            "base_point_g": _format_ecc_point(g_point, a, b, mod_poly, m),
        },
        "point_p": _format_ecc_point(point_p, a, b, mod_poly, m),
        "point_q": _format_ecc_point(point_q, a, b, mod_poly, m),
        "doubling": {
            "result": _format_ecc_point(doubled_point, a, b, mod_poly, m),
            **doubling_trace,
        },
        "addition": {
            "result": _format_ecc_point(added_point, a, b, mod_poly, m),
            **addition_trace,
        },
        "ecdh": {
            "n_a": n_a,
            "n_b": n_b,
            "public_a": _format_ecc_point(pub_a, a, b, mod_poly, m),
            "public_b": _format_ecc_point(pub_b, a, b, mod_poly, m),
            "shared_a": _format_ecc_point(shared_a, a, b, mod_poly, m),
            "shared_b": _format_ecc_point(shared_b, a, b, mod_poly, m),
            "shared_secret_matches": shared_a == shared_b,
            "all_points_on_curve": all(
                ecc_is_on_curve(pt, a, b, mod_poly, m)
                for pt in (g_point, pub_a, pub_b, shared_a, shared_b)
            ),
        },
    }


def _parse_128bit_hex(raw: str, label: str) -> int:
    """Strictly parse an unsigned 128-bit hexadecimal polynomial string.

    Args:
        raw: Unsigned hexadecimal string (up to 32 hex digits / 128 bits).
        label: Field label included in error messages.

    Returns:
        Non-negative integer in ``[0, 2^128 - 1]``.

    Raises:
        ValueError: If ``raw`` is not a non-empty valid unsigned hex string or
            exceeds 128 bits (``>= 2^128``).
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{label}: enter a non-empty 128-bit hexadecimal value.")
    try:
        value = parse_value(raw, "hex")
    except ValueError as exc:
        raise ValueError(f"{label}: {exc}") from exc
    if value.bit_length() > GHASH_DEGREE:
        raise ValueError(f"{label}: value must fit in 128 bits (at most 32 hex digits).")
    return value


def gcm_ghash(h_hex: str, blocks_hex: list[str]) -> dict[str, Any]:
    """Compute GCM GHASH authentication tag over ``GF(2^128)`` modulo ``x^128 + x^7 + x^2 + x + 1``.

    Implements the NIST SP 800-38D / Stallings **Chapter 12** GHASH polynomial
    authenticator using our canonical :func:`backend.engine.additive.add` (XOR)
    and :func:`backend.engine.multiply.multiply` (Shift-and-XOR) primitives.
    Starting from ``Y_0 = 0``, iterates for ``i = 1 .. k``:

        ``Y_i = (Y_{i-1} XOR X_i) * H mod (x^128 + x^7 + x^2 + x + 1)``

    which evaluates the Horner polynomial
    ``Y_k = (X_1 * H^k) XOR (X_2 * H^(k-1)) XOR ... XOR (X_k * H) mod m(x)``.

    Args:
        h_hex: 128-bit hash subkey ``H`` as an unsigned hexadecimal string.
        blocks_hex: Non-empty sequence of ``1`` to ``8`` 128-bit hexadecimal
            data/ciphertext blocks ``[X_1, ..., X_k]``.

    Returns:
        Dictionary containing ``m=128``, ``modulus_hex``, ``modulus_poly``,
        ``h_hex``, ``block_count``, per-block ``steps`` (each with ``block_index``,
        ``x_i_hex``, ``prev_y_hex``, ``xor_input_hex``, ``y_i_hex``), final
        ``tag_hex``, ``tag_poly``, and ``elapsed_ms``.

    Raises:
        ValueError: If ``h_hex`` or any block is malformed/negative/``>= 2^128``,
            or if ``blocks_hex`` does not contain between ``1`` and ``8`` blocks.

    Complexity:
        Let ``k = len(blocks_hex)`` and ``m = 128``. Runs ``k`` full 128-bit
        Shift-and-XOR multiplications and XORs: ``O(k * m^2)`` bit operations,
        space ``O(k * m)``.
    """
    if not isinstance(blocks_hex, (list, tuple)) or not 1 <= len(blocks_hex) <= 8:
        raise ValueError("Provide between 1 and 8 128-bit hexadecimal blocks.")

    h_val = _parse_128bit_hex(h_hex, "Hash subkey H")
    parsed_blocks = [
        _parse_128bit_hex(raw_block, f"Block X{idx}")
        for idx, raw_block in enumerate(blocks_hex, start=1)
    ]

    start_ns = perf_counter_ns()
    y_prev = 0
    steps: list[dict[str, Any]] = []
    for block_index, x_i in enumerate(parsed_blocks, start=1):
        xor_input = add(y_prev, x_i, GHASH_MODULUS, GHASH_DEGREE)
        y_i = multiply(xor_input, h_val, GHASH_MODULUS, GHASH_DEGREE)
        steps.append(
            {
                "block_index": block_index,
                "x_i_hex": INT_TO_HEX(x_i, GHASH_DEGREE).upper(),
                "prev_y_hex": INT_TO_HEX(y_prev, GHASH_DEGREE).upper(),
                "xor_input_hex": INT_TO_HEX(xor_input, GHASH_DEGREE).upper(),
                "y_i_hex": INT_TO_HEX(y_i, GHASH_DEGREE).upper(),
            }
        )
        y_prev = y_i
    elapsed_ms = (perf_counter_ns() - start_ns) / 1_000_000

    return {
        "m": GHASH_DEGREE,
        "modulus_hex": INT_TO_HEX(GHASH_MODULUS, GHASH_DEGREE + 1).upper(),
        "modulus_poly": "x^128 + x^7 + x^2 + x + 1",
        "h_hex": INT_TO_HEX(h_val, GHASH_DEGREE).upper(),
        "block_count": len(steps),
        "steps": steps,
        "tag_hex": INT_TO_HEX(y_prev, GHASH_DEGREE).upper(),
        "tag_poly": INT_TO_ALGEBRAIC(y_prev),
        "elapsed_ms": round(elapsed_ms, 4),
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

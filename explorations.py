"""Interactive experiments using the lab's polynomial arithmetic engines."""

from random import Random
from statistics import median
from time import perf_counter_ns

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.integrated_inverse import inverse
from app.schemas import Base
from gf2m.multiply import multiply, multiply_traced
from gf2m_m1.additive import modulo
from gf2m_m1.fields import get_field
from gf2m_m1.polyrepr import ElementRepr, INT_TO_HEX, parse_value
from gf2m_m3.poly_ops import DivisionStep, POLY_DIVMOD, POLY_MUL_NO_MOD


router = APIRouter(prefix="/api/explorations", tags=["explorations"])


class ModulusRequest(BaseModel):
    polynomial: str = Field(max_length=10000)
    input_base: Base = Base.algebraic


class SBoxRequest(BaseModel):
    byte: str = Field(max_length=64)
    input_base: Base = Base.hex


class MultiplicationRequest(BaseModel):
    m: int
    a: str = Field(max_length=10000)
    b: str = Field(max_length=10000)
    input_base: Base = Base.hex


def _parse(text: str, base: Base, label: str) -> int:
    try:
        value = parse_value(text, base.value)
        if value.bit_length() > 4096:
            raise ValueError("use at most 4096 bits")
        return value
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{label}: {exc}") from exc


def _repr(value: int, bits: int) -> dict:
    return ElementRepr.from_int(value, bits).dict()


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, POLY_DIVMOD(a, b)[1]
    return a


def _split_square_free(polynomial: int) -> int:
    """Find a factor using a nonconstant fixed point of squaring modulo f.

    This is the Berlekamp kernel over GF(2). Eliminate columns of the
    squaring map minus the identity, keeping their original combinations.
    A nonconstant fixed point is 0 on some factors and 1 on the others.
    """
    pivots = {}
    for power in range(1, polynomial.bit_length() - 1):
        combination = 1 << power
        column = POLY_DIVMOD(1 << (2 * power), polynomial)[1] ^ combination
        while column:
            pivot = column.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = column, combination
                break
            old_column, old_combination = pivots[pivot]
            column ^= old_column
            combination ^= old_combination
        if column == 0:
            return _gcd(combination, polynomial)
    raise RuntimeError("A reducible square-free polynomial must have a nonconstant fixed point")


@router.post("/modulus")
def explore_modulus(req: ModulusRequest) -> dict:
    """Detect factors by checking x^(2^i) + x up to half the degree."""
    polynomial = _parse(req.polynomial, req.input_base, "Modulus")
    degree = polynomial.bit_length() - 1
    if not 2 <= degree <= 571:
        raise HTTPException(status_code=400, detail="Enter a modulus of degree 2 through 571.")

    checks = []
    factor = 1
    residue = 0b10
    split = False
    for i in range(1, degree // 2 + 1):
        residue = POLY_DIVMOD(POLY_MUL_NO_MOD(residue, residue), polynomial)[1]
        common = _gcd(polynomial, residue ^ 0b10)
        checks.append({"i": i, "power_remainder_hex": INT_TO_HEX(residue, 1),
                       "gcd_hex": INT_TO_HEX(common, 1)})
        if common != 1:
            # If the first GCD is f itself, f is square-free and all its
            # irreducible factors have degree i. Split that GCD to get a witness.
            split = common == polynomial
            factor = _split_square_free(polynomial) if split else common
            break

    witness = None
    if factor != 1:
        cofactor, _ = POLY_DIVMOD(polynomial, factor)
        product = POLY_MUL_NO_MOD(factor, cofactor)
        witness = {
            "a": _repr(factor, 1),
            "b": _repr(cofactor, 1),
            "product": _repr(product, 1),
            "remainder": _repr(POLY_DIVMOD(product, polynomial)[1], 1),
        }

    return {"modulus": _repr(polynomial, degree + 1), "degree": degree,
            "irreducible": witness is None, "checks": checks,
            "witness": witness, "split_with_berlekamp": split}


@router.post("/aes-sbox")
def aes_sbox(req: SBoxRequest) -> dict:
    """Apply the FIPS 197 §5.1.1 byte substitution, including the zero case."""
    byte = _parse(req.byte, req.input_base, "AES input")
    if byte > 0xFF:
        raise HTTPException(status_code=400, detail="Enter one byte, from 00 through FF in hex.")

    field = get_field(8)
    inverted, trace = inverse(byte, field.mod_poly, field.m, with_trace=True) if byte else (0, None)
    running = 0
    rows = []
    for shift in range(5):
        rotated = ((inverted << shift) | (inverted >> (8 - shift))) & 0xFF
        running ^= rotated
        rows.append({"label": "Inverse byte" if shift == 0 else f"Rotate left by {shift}",
                     "value": _repr(rotated, 8), "running": _repr(running, 8)})
    running ^= 0x63
    rows.append({"label": "AES constant", "value": _repr(0x63, 8), "running": _repr(running, 8)})

    return {"input": _repr(byte, 8), "inverse": _repr(inverted, 8),
            "inverse_trace": trace, "affine_rows": rows, "output": _repr(running, 8)}


def _multiply_then_divide(a: int, b: int, modulus: int, _degree: int) -> int:
    return POLY_DIVMOD(POLY_MUL_NO_MOD(a, b), modulus)[1]


@router.post("/compare-multiplication")
def compare_multiplication(req: MultiplicationRequest) -> dict:
    """Calculate the same product with interleaved and deferred reduction."""
    try:
        field = get_field(req.m)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    a = _parse(req.a, req.input_base, "Operand A")
    b = _parse(req.b, req.input_base, "Operand B")
    reduced_a = modulo(a, field.mod_poly, field.m)
    reduced_b = modulo(b, field.mod_poly, field.m)
    shifted, trace = multiply_traced(reduced_a, reduced_b, field.mod_poly, field.m)
    raw = POLY_MUL_NO_MOD(reduced_a, reduced_b)
    steps: list[DivisionStep] = []
    quotient, remainder = POLY_DIVMOD(raw, field.mod_poly, steps=steps)
    divisions = [{"shift": row.shift, "before_hex": INT_TO_HEX(row.before, 1),
                  "divisor_hex": INT_TO_HEX(row.shifted_divisor, 1),
                  "after_hex": INT_TO_HEX(row.after, 1)} for row in steps]
    return {
        "m": field.m, "modulus_hex": INT_TO_HEX(field.mod_poly, field.m + 1),
        "a": _repr(reduced_a, field.m), "b": _repr(reduced_b, field.m),
        "inputs_reduced": a != reduced_a or b != reduced_b,
        "agree": shifted == remainder, "shift_result": _repr(shifted, field.m),
        "shift_trace": trace.dict(), "raw_product": _repr(raw, 1),
        "quotient": _repr(quotient, 1), "remainder": _repr(remainder, field.m),
        "division_steps": divisions,
    }


@router.get("/multiplication-benchmarks")
def multiplication_benchmarks() -> dict:
    """Time both untraced arithmetic paths on fixed, full-width operands."""
    seed, trials = 455632, 31
    rng = Random(seed)
    rows = []
    for m in (163, 571):
        a = (1 << (m - 1)) | rng.getrandbits(m - 1)
        b = (1 << (m - 1)) | rng.getrandbits(m - 1)
        modulus = get_field(m).mod_poly
        engines = (multiply, _multiply_then_divide)
        results = [engine(a, b, modulus, m) for engine in engines]
        samples = [[], []]
        for trial in range(trials):
            for index in (trial % 2, 1 - trial % 2):
                start = perf_counter_ns()
                engines[index](a, b, modulus, m)
                samples[index].append(perf_counter_ns() - start)
        rows.append({"m": m, "agree": results[0] == results[1],
                     "shift_xor_us": median(samples[0]) / 1000,
                     "long_division_us": median(samples[1]) / 1000})
    return {"seed": seed, "trials": trials, "rows": rows}

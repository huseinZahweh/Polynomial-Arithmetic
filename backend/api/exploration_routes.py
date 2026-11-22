"""FastAPI router exposing the four interactive teaching exploration endpoints.

Original Author
---------------
Ali Zahreddine — Milestone 4 & Integration (Bonus Teaching & Exploration Tools).

Purpose & Course References
---------------------------
Exposes HTTP validation and JSON serialization over the pure-Python engines in
:mod:`backend.engine.explorations`:

* ``POST /api/explorations/modulus`` — Binary polynomial irreducibility check
  and factor-witness extraction (Stallings **Chapter 4** + Berlekamp kernel extension).
* ``POST /api/explorations/aes-sbox`` — FIPS 197 §5.1.1 / Stallings **Chapter 5**
  AES byte substitution walkthrough (EEA inverse + affine XOR rows).
* ``POST /api/explorations/compare-multiplication`` — Side-by-side comparison of
  Shift-and-XOR vs. carry-free product + long division (Stallings **Chapter 4**).
* ``GET /api/explorations/multiplication-benchmarks`` — Seeded 31-trial median
  timing comparison at ``m = 163`` and ``m = 571`` (Stallings **Chapter 10**).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.engine import explorations as engine
from backend.engine.polyrepr import parse_value
from .schemas import Base

router = APIRouter(prefix="/api/explorations", tags=["explorations"])

_MAX_INPUT_BITS = 4096


class ModulusRequest(BaseModel):
    """Request payload for testing irreducibility of a custom binary polynomial."""

    polynomial: str = Field(max_length=10000)
    input_base: Base = Base.algebraic


class SBoxRequest(BaseModel):
    """Request payload for tracing one byte through the AES S-box."""

    byte: str = Field(max_length=64)
    input_base: Base = Base.hex


class MultiplicationRequest(BaseModel):
    """Request payload for comparing both multiplication methods in ``GF(2^m)``."""

    m: int
    a: str = Field(max_length=10000)
    b: str = Field(max_length=10000)
    input_base: Base = Base.hex


def _parse_input(text: str, base: Base, label: str) -> int:
    """Parse one exploration operand string or raise HTTP 400 with a clear message.

    Args:
        text: Raw operand string from request body.
        base: Requested :class:`~backend.api.schemas.Base`.
        label: Field name prepended to validation error details.

    Returns:
        Non-negative integer bitmask of at most ``4096`` bits.

    Raises:
        HTTPException: Status 400 on malformed syntax or bit width ``> 4096``.
    """
    try:
        value = parse_value(text, base.value)
        if value.bit_length() > _MAX_INPUT_BITS:
            raise ValueError(f"use at most {_MAX_INPUT_BITS} bits")
        return value
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{label}: {exc}") from exc


@router.post("/modulus")
def explore_modulus_route(req: ModulusRequest) -> dict[str, Any]:
    """Test whether a custom binary polynomial of degree ``2..571`` is irreducible.

    Args:
        req: :class:`ModulusRequest` specifying polynomial text and notation.

    Returns:
        Irreducibility verdict, GCD checkpoint rows, and factor witness (if reducible).

    Raises:
        HTTPException: Status 400 if syntax is invalid or degree is outside ``2..571``.
    """
    polynomial = _parse_input(req.polynomial, req.input_base, "Modulus")
    try:
        return engine.explore_modulus(polynomial)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/aes-sbox")
def aes_sbox_route(req: SBoxRequest) -> dict[str, Any]:
    """Trace one byte through ``GF(2^8)`` inversion and the AES affine XOR matrix.

    Args:
        req: :class:`SBoxRequest` carrying a single byte in hex or binary.

    Returns:
        Input, inverse, optional Table 4.7 trace, 6 affine XOR rows, and output byte.

    Raises:
        HTTPException: Status 400 if syntax is invalid or value exceeds ``0xFF``.
    """
    byte = _parse_input(req.byte, req.input_base, "AES input")
    try:
        return engine.compute_aes_sbox(byte)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/compare-multiplication")
def compare_multiplication_route(req: MultiplicationRequest) -> dict[str, Any]:
    """Run Shift-and-XOR and carry-free + long division on the same operands.

    Args:
        req: :class:`MultiplicationRequest` specifying degree ``m``, ``a``, ``b``, and base.

    Returns:
        Side-by-side results, agreement flag, Shift-and-XOR trace, raw product,
        quotient, remainder, and long-division cancellation steps.

    Raises:
        HTTPException: Status 400 if ``m`` is unsupported or operands are malformed.
    """
    a = _parse_input(req.a, req.input_base, "Operand A")
    b = _parse_input(req.b, req.input_base, "Operand B")
    try:
        return engine.compare_multiplication(req.m, a, b)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/multiplication-benchmarks")
def multiplication_benchmarks_route() -> dict[str, Any]:
    """Run the seeded 31-trial untraced benchmark at ``m = 163`` and ``m = 571``.

    Returns:
        Dictionary containing ``seed``, ``trials``, and median microsecond timings
        per method confirming both methods agree on each field.
    """
    return engine.benchmark_multiplication()

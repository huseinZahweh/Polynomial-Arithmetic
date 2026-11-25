"""FastAPI router exposing the six interactive teaching exploration & application endpoints.

Original Authors
----------------
* Ali Zahreddine — Milestone 4 & Integration (Modulus Explorer & Multiplication Comparison).
* Husein Zahweh — Milestone 6 (Applications: XTS-AES GF(2^128), Binary ECC NIST B-163, & GCM/GHASH GF(2^128)).

Purpose & Course References
---------------------------
Exposes HTTP validation and JSON serialization over the pure-Python engines in
:mod:`backend.engine.explorations`:

* ``POST /api/explorations/modulus`` — Binary polynomial irreducibility check
  and factor-witness extraction (Stallings **Chapter 4** + Berlekamp kernel extension).
* ``POST /api/explorations/xts-tweak`` — IEEE 1619-2007 / Stallings **Chapter 6**
  XTS-AES ``GF(2^128)`` tweak progression ``T_j = T_0 * alpha^j mod (x^128 + x^7 + x^2 + x + 1)``.
* ``POST /api/explorations/binary-ecc`` — Stallings **Chapter 10** & NIST FIPS 186-4 /
  SECG SEC 2 binary elliptic curve explorer (``GF(2^4)`` teaching curve & **NIST B-163**):
  point doubling, point addition, and ECDH key exchange.
* ``POST /api/explorations/gcm-ghash`` — NIST SP 800-38D / Stallings **Chapter 12**
  GCM GHASH authenticator ``Y_i = (Y_{i-1} XOR X_i) * H mod (x^128 + x^7 + x^2 + x + 1)``.
* ``POST /api/explorations/compare-multiplication`` — Side-by-side comparison of
  Shift-and-XOR vs. carry-free product + long division (Stallings **Chapter 4**).
* ``GET /api/explorations/multiplication-benchmarks`` — Seeded 31-trial median
  timing comparison at ``m = 163`` and ``m = 571`` (Stallings **Chapter 10**).
"""
from __future__ import annotations

from typing import Any, Optional

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


class XTSTweakRequest(BaseModel):
    """Request payload for stepping an XTS-AES 128-bit tweak modulo ``x^128 + x^7 + x^2 + x + 1``."""

    t0_hex: str = Field(default="50000000000000000000000000000001", max_length=128)
    steps: int = Field(default=6, ge=1, le=16)


class BinaryECCRequest(BaseModel):
    """Request payload for binary elliptic curve doubling, addition, and ECDH on ``E_{2^m}(a, b)``."""

    curve: str = Field(default="nist_b163", max_length=32)
    p_x: Optional[str] = Field(default=None, max_length=256)
    p_y: Optional[str] = Field(default=None, max_length=256)
    q_x: Optional[str] = Field(default=None, max_length=256)
    q_y: Optional[str] = Field(default=None, max_length=256)
    n_a: int = Field(default=5, ge=2, le=25)
    n_b: int = Field(default=9, ge=2, le=25)


class GCMGHashRequest(BaseModel):
    """Request payload for computing a NIST SP 800-38D GCM GHASH tag over ``GF(2^128)``."""

    h_hex: str = Field(default="66E94BD4EF8A2C3B884CFA59CA342B2E", max_length=128)
    blocks_hex: list[str] = Field(
        default_factory=lambda: [
            "0388DACE60B6A392F328C2B971B2FE78",
            "00000000000000000000000000000080",
        ]
    )


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


@router.post("/xts-tweak")
def xts_tweak_route(req: XTSTweakRequest) -> dict[str, Any]:
    """Compute XTS-AES ``GF(2^128)`` tweak progression ``T_j = T_0 * alpha^j mod m(x)``.

    Args:
        req: :class:`XTSTweakRequest` specifying initial 128-bit hex tweak and step count.

    Returns:
        Field metadata and per-block shift/overflow/XOR ``0x87`` trace entries.

    Raises:
        HTTPException: Status 400 if ``t0_hex`` is invalid hex or exceeds 128 bits.
    """
    t0 = _parse_input(req.t0_hex, Base.hex, "Initial tweak T0")
    try:
        return engine.compute_xts_tweak(t0, req.steps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/binary-ecc")
def binary_ecc_route(req: BinaryECCRequest) -> dict[str, Any]:
    """Compute Binary ECC point doubling ``2P``, addition ``P + Q``, and ECDH on ``E_{2^m}(a, b)``.

    Args:
        req: :class:`BinaryECCRequest` naming the curve (``gf2_4`` or ``nist_b163``),
            optional custom points ``P`` and ``Q``, and ECDH private scalars ``n_a``, ``n_b``.

    Returns:
        Curve metadata, verified points, traced ``doubling`` and ``addition`` steps,
        and compact ECDH shared-secret verification.

    Raises:
        HTTPException: Status 400 on unknown curve, malformed coordinates, or off-curve points.
    """
    point_p = None
    if req.p_x is not None or req.p_y is not None:
        if req.p_x is None or req.p_y is None:
            raise HTTPException(status_code=400, detail="Point P requires both p_x and p_y.")
        point_p = (_parse_input(req.p_x, Base.hex, "P.x"), _parse_input(req.p_y, Base.hex, "P.y"))

    point_q = None
    if req.q_x is not None or req.q_y is not None:
        if req.q_x is None or req.q_y is None:
            raise HTTPException(status_code=400, detail="Point Q requires both q_x and q_y.")
        point_q = (_parse_input(req.q_x, Base.hex, "Q.x"), _parse_input(req.q_y, Base.hex, "Q.y"))

    try:
        return engine.explore_binary_ecc(
            curve_id=req.curve,
            p=point_p,
            q=point_q,
            n_a=req.n_a,
            n_b=req.n_b,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/gcm-ghash")
def gcm_ghash_route(req: GCMGHashRequest) -> dict[str, Any]:
    """Compute NIST SP 800-38D / Stallings Ch. 12 GCM GHASH over ``GF(2^128)``.

    Args:
        req: :class:`GCMGHashRequest` specifying 128-bit hash subkey ``h_hex``
            and ``1..8`` 128-bit hexadecimal blocks ``blocks_hex``.

    Returns:
        Field metadata, per-block XOR and Shift-and-XOR multiplication steps,
        final GHASH value in legacy ``tag_hex``/``tag_poly`` fields, ``encoding``,
        ``output_kind="ghash"``, and ``elapsed_ms``. Note that GHASH is not a
        complete GCM authentication tag without AAD/length formatting and ``E_K(J_0)``.

    Raises:
        HTTPException: Status 400 on invalid hex, values ``>= 2^128``, or block
            counts outside ``1..8``.
    """
    try:
        return engine.gcm_ghash(req.h_hex, req.blocks_hex)
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

"""Service layer — operation dispatch and response assembly.

The ``/api/calculate`` controller routes each of the six field operations to
the owning engine (M2 multiply; M1 additive/modulo; M3 inverse/division — all
reached through ``providers``), times it, builds the display representations,
and attaches a self-verification badge where one is meaningful.
"""
from __future__ import annotations

import time
from typing import Optional, Tuple

from gf2m import polyrepr

from . import providers
from .schemas import (
    CalculateRequest,
    CalculateResponse,
    ElementReprModel,
    FieldInfo,
    Metrics,
    Operands,
    Operation,
    Verification,
)


class CalculationError(ValueError):
    """Domain error (bad field, missing operand, no inverse). -> HTTP 400."""


# Operations that require operand B.
_BINARY_OPS = {Operation.add, Operation.subtract, Operation.multiply, Operation.divide}


def field_info(m: int) -> FieldInfo:
    if not providers.fields.is_supported(m):
        raise CalculationError(f"unsupported field degree m={m}")
    f = providers.fields.get_field(m)
    return FieldInfo(
        m=f.m,
        category=f.category,
        name=f.name,
        reduction_poly_hex=polyrepr.to_hex(f.mod_poly, f.m + 1),
        reduction_poly=polyrepr.to_poly(f.mod_poly),
        element_bits=f.m,
    )


def _repr(value: int, m: int) -> ElementReprModel:
    return ElementReprModel(**polyrepr.ElementRepr.from_int(value, m).dict())


def _dispatch(op: Operation, a: int, b: Optional[int], mod_poly: int, m: int, want_trace: bool):
    """Return ``(result, trace_or_None, verification_or_None)``."""
    mul = providers.multiply
    add = providers.additive
    invdiv = providers.invdiv

    if op is Operation.add:
        result = add.add(a, b, mod_poly, m)
        trace = add.xor_trace(a, b, m) if want_trace else None
        return result, trace, None

    if op is Operation.subtract:
        result = add.subtract(a, b, mod_poly, m)
        trace = add.xor_trace(a, b, m) if want_trace else None
        return result, trace, None

    if op is Operation.modulo:
        result = add.modulo(a, mod_poly, m)
        return result, None, None

    if op is Operation.multiply:
        if want_trace:
            result, mtrace = mul.multiply_traced(a, b, mod_poly, m)
            return result, mtrace.dict(), None
        return mul.multiply(a, b, mod_poly, m), None, None

    if op is Operation.inverse:
        if want_trace:
            result, trace = invdiv.inverse(a, mod_poly, m, with_trace=True)
        else:
            result, trace = invdiv.inverse(a, mod_poly, m), None
        check = mul.multiply(a, result, mod_poly, m) == 1
        ver = Verification(label="A(x) * A(x)^-1 mod m(x) = 1", passed=check)
        return result, trace, ver

    if op is Operation.divide:
        if want_trace:
            result, trace = invdiv.divide(a, b, mod_poly, m, with_trace=True)
        else:
            result, trace = invdiv.divide(a, b, mod_poly, m), None
        check = mul.multiply(result, b, mod_poly, m) == add.modulo(a, mod_poly, m)
        ver = Verification(label="(A(x)/B(x)) * B(x) mod m(x) = A(x)", passed=check)
        return result, trace, ver

    raise CalculationError(f"unknown operation: {op}")


def calculate(req: CalculateRequest) -> CalculateResponse:
    info = field_info(req.m)
    f = providers.fields.get_field(req.m)

    # Parse operands.
    try:
        a = polyrepr.parse_value(req.a, req.input_base.value)
    except ValueError as exc:
        raise CalculationError(f"operand A: {exc}")

    b: Optional[int] = None
    if req.operation in _BINARY_OPS:
        if req.b is None or req.b.strip() == "":
            raise CalculationError(f"operation '{req.operation.value}' requires operand B")
        try:
            b = polyrepr.parse_value(req.b, req.input_base.value)
        except ValueError as exc:
            raise CalculationError(f"operand B: {exc}")

    # Reduce displayed operands into the field for a faithful echo.
    a_in = providers.additive.modulo(a, f.mod_poly, f.m)
    b_in = providers.additive.modulo(b, f.mod_poly, f.m) if b is not None else None

    try:
        t0 = time.perf_counter()
        result, trace, verification = _dispatch(
            req.operation, a, b, f.mod_poly, f.m, req.trace
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 4)
    except providers.invdiv.NoInverseError as exc:
        raise CalculationError(str(exc))
    except ZeroDivisionError:
        raise CalculationError("division by zero polynomial")

    share_token = providers.formatter.make_share_token(
        m=req.m,
        operation=req.operation.value,
        a_hex=polyrepr.to_hex(a_in, f.m),
        b_hex=polyrepr.to_hex(b_in, f.m) if b_in is not None else "",
        out_base=req.output_base.value,
    )

    return CalculateResponse(
        operation=req.operation,
        field=info,
        operands=Operands(a=_repr(a_in, f.m), b=_repr(b_in, f.m) if b_in is not None else None),
        result=_repr(result, f.m),
        trace=trace,
        verification=verification,
        metrics=Metrics(
            elapsed_ms=elapsed_ms,
            result_bit_length=result.bit_length(),
            result_hamming_weight=polyrepr.hamming_weight(result),
        ),
        share_token=share_token,
    )

"""Service layer dispatching GF(2^m) calculations, traces, timing, and verification.

Original Authors
----------------
* Hassan Tarhini — Milestone 2 (Core operation dispatch, timing, and response assembly).
* Ali Zahreddine — Milestone 4 & Integration (Direct wiring to unified M1/M2/M3
  engines, initial-reduction traces, and live proof badges).

Purpose & Course References
---------------------------
Bridges HTTP payloads from :mod:`backend.api.main` directly to the pure-Python
engines in :mod:`backend.engine`:

* Addition, subtraction, modulo reduction -> :mod:`backend.engine.additive` (Stallings Ch. 4)
* Shift-and-XOR multiplication -> :mod:`backend.engine.multiply` (Stallings Ch. 4 & 5)
* Extended Euclid inverse & two-stage division -> :mod:`backend.engine.extended_euclid`
  and :mod:`backend.engine.division` (Stallings Ch. 4 Table 4.7, Ch. 5 AES, Ch. 10 ECC)
* Live algebraic proof badges -> :mod:`backend.engine.verification`
"""
from __future__ import annotations

import time
from typing import Any, Optional

from backend.engine import (
    EXTENDED_EUCLID_GF2M,
    GF2M_DIVIDE,
    GF2mInverseError,
    MOD_REDUCE,
    VERIFY_DIVISION,
    VERIFY_INVERSE,
    additive,
    fields,
    formatter,
    polyrepr,
)
from backend.engine.multiply import multiply as gf2m_multiply, multiply_traced
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

# Operations requiring both operand A(x) and operand B(x).
_BINARY_OPS = {Operation.add, Operation.subtract, Operation.multiply, Operation.divide}


class CalculationError(ValueError):
    """Domain validation or non-invertible error mapped to HTTP 400 by the API.

    Attributes:
        gcd: Optional ``gcd(m(x), b(x))`` bitmask preserved from Extended Euclid.
        trace: Optional Table 4.7 trace captured up to ``B3(x) == 0``.
    """

    def __init__(
        self,
        message: str,
        *,
        gcd: Optional[int] = None,
        trace: Optional[Any] = None,
    ) -> None:
        """Create a domain error carrying optional educational GCD and trace data.

        Args:
            message: Clear educational message returned in HTTP 400 ``detail``.
            gcd: Optional integer bitmask of ``gcd(m(x), b(x))``.
            trace: Optional Table 4.7 trace dictionary up to termination.
        """
        super().__init__(message)
        self.gcd = gcd
        self.trace = trace


def build_field_info(field: fields.Field) -> FieldInfo:
    """Convert an engine :class:`~backend.engine.fields.Field` into a :class:`FieldInfo` schema.

    Args:
        field: Configured field registry entry.

    Returns:
        Serialized :class:`FieldInfo` with hex, binary, and algebraic ``m(x)``.
    """
    return FieldInfo(
        m=field.m,
        category=field.category,
        name=field.name,
        reduction_poly_hex=polyrepr.to_hex(field.mod_poly, field.m + 1),
        reduction_poly_bin=polyrepr.to_bin(field.mod_poly, field.m + 1),
        reduction_poly=polyrepr.to_poly(field.mod_poly),
        element_bits=field.m,
    )


def field_info(m: int) -> FieldInfo:
    """Look up field degree ``m`` or raise :class:`CalculationError` (HTTP 400).

    Args:
        m: Candidate extension field degree.

    Returns:
        :class:`FieldInfo` for ``GF(2^m)``.

    Raises:
        CalculationError: If ``m`` is not in the 13-field registry.
    """
    if not fields.is_supported(m):
        raise CalculationError(f"unsupported field degree m={m}")
    return build_field_info(fields.get_field(m))


def element_model(value: int, m: int) -> ElementReprModel:
    """Build an :class:`ElementReprModel` for polynomial ``value`` at bit width ``m``.

    Args:
        value: Non-negative polynomial bitmask.
        m: Minimum display bit width.

    Returns:
        Serialized :class:`ElementReprModel`.
    """
    return ElementReprModel(**polyrepr.ElementRepr.from_int(value, m).dict())


def _reduce(
    value: int,
    field: fields.Field,
    want_trace: bool,
) -> tuple[int, Optional[dict[str, Any]]]:
    """Reduce an operand modulo ``m(x)`` and enrich step rows with lowercase hex.

    Args:
        value: Non-negative input polynomial bitmask.
        field: Active :class:`~backend.engine.fields.Field`.
        want_trace: When ``True``, invokes :func:`MOD_REDUCE` and attaches
            ``before_hex``, ``reducer_hex``, and ``after_hex`` to every step.

    Returns:
        Tuple ``(reduced_int, trace_dict_or_None)``.
    """
    if not want_trace:
        return additive.modulo(value, field.mod_poly, field.m), None
    result, trace = MOD_REDUCE(value, field.mod_poly, field.m)
    for row in trace["steps"]:
        for key in ("before", "reducer", "after"):
            row[f"{key}_hex"] = polyrepr.to_hex(row[key], field.m)
    return result, trace


def _parse_operand(text: str, base: str, name: str) -> int:
    """Parse and size-check one string operand, converting failures to :class:`CalculationError`.

    Args:
        text: Raw operand string from the HTTP request.
        base: Normalized base string (``"hex"``, ``"bin"``, or ``"algebraic"``).
        name: Label (``"A"`` or ``"B"``) used in error messages.

    Returns:
        Non-negative integer bitmask of at most ``4096`` bits.

    Raises:
        CalculationError: On malformed syntax or bit lengths exceeding ``4096``.
    """
    try:
        return polyrepr.validate_input_width(polyrepr.parse_value(text, base))
    except ValueError as exc:
        raise CalculationError(f"operand {name}: {exc}") from exc


def _dispatch(
    op: Operation,
    a: int,
    b: Optional[int],
    mod_poly: int,
    m: int,
    want_trace: bool,
) -> tuple[int, Optional[dict[str, Any]], Optional[Verification]]:
    """Execute the requested finite-field operation and optional self-verification.

    Args:
        op: Canonical :class:`Operation` enum member.
        a: Operand ``A(x)`` bitmask (unreduced for ``inverse``/``divide`` so
            Extended Euclid records its own initial reduction note).
        b: Optional operand ``B(x)`` bitmask (required for binary operations).
        mod_poly: Irreducible modulus bitmask ``m(x)`` with bit ``m`` set.
        m: Extension field degree.
        want_trace: Whether to build and return step-by-step educational traces.

    Returns:
        Tuple ``(result_int, trace_dict_or_None, Verification_or_None)``.

    Raises:
        GF2mInverseError: Propagated when inverting or dividing by ``0 mod m(x)``.
        CalculationError: If ``op`` is unrecognized.
    """
    if op is Operation.add:
        assert b is not None
        result = additive.add(a, b, mod_poly, m)
        trace = additive.xor_trace(a, b, m) if want_trace else None
        return result, trace, None

    if op is Operation.subtract:
        assert b is not None
        result = additive.subtract(a, b, mod_poly, m)
        trace = additive.xor_trace(a, b, m) if want_trace else None
        return result, trace, None

    if op is Operation.modulo:
        result = additive.modulo(a, mod_poly, m)
        return result, None, None

    if op is Operation.multiply:
        assert b is not None
        if want_trace:
            result, mtrace = multiply_traced(a, b, mod_poly, m)
            return result, mtrace.dict(), None
        return gf2m_multiply(a, b, mod_poly, m), None, None

    if op is Operation.inverse:
        result, eea_trace = EXTENDED_EUCLID_GF2M(mod_poly, m, a, trace=want_trace)
        proof = VERIFY_INVERSE(a, result, mod_poly, m)
        ver = Verification(
            label="A(x) * A(x)^-1 mod m(x) = 1",
            passed=bool(proof["passed"]),
            proof=proof,
        )
        return result, (eea_trace if want_trace else None), ver

    if op is Operation.divide:
        assert b is not None
        if want_trace:
            result, div_trace = GF2M_DIVIDE(a, b, mod_poly, m)
        else:
            # Fast path when no trace is requested: skip Shift-and-XOR and EEA row formatting.
            b_inv, _ = EXTENDED_EUCLID_GF2M(mod_poly, m, b, trace=False)
            result, div_trace = gf2m_multiply(a, b_inv, mod_poly, m), None
        proof = VERIFY_DIVISION(a, b, result, mod_poly, m)
        ver = Verification(
            label="(A(x)/B(x)) * B(x) mod m(x) = A(x)",
            passed=bool(proof["passed"]),
            proof=proof,
        )
        return result, div_trace, ver

    raise CalculationError(f"unknown operation: {op}")


def calculate(req: CalculateRequest) -> CalculateResponse:
    """Validate, execute, time, verify, and format one ``POST /api/calculate`` request.

    Args:
        req: Validated :class:`CalculateRequest` payload.

    Returns:
        Complete :class:`CalculateResponse` including multi-base operands/result,
        educational trace, initial reductions, live verification badge, timing
        metrics, and a hex share token.

    Raises:
        CalculationError: Mapped to HTTP 400 on unsupported fields, invalid
            operands, missing operand B, or zero/non-invertible divisors.
    """
    info = field_info(req.m)
    field = fields.get_field(req.m)

    a = _parse_operand(req.a, req.input_base.value, "A")

    b: Optional[int] = None
    if req.operation in _BINARY_OPS:
        if req.b is None or req.b.strip() == "":
            raise CalculationError(f"operation '{req.operation.value}' requires operand B")
        b = _parse_operand(req.b, req.input_base.value, "B")

    # Reduce displayed operands into GF(2^m) so echoed operands, trace bits,
    # and dispatched arithmetic reflect the exact same canonical field elements.
    t0 = time.perf_counter()
    a_in, a_reduction = _reduce(a, field, req.trace)
    b_in, b_reduction = _reduce(b, field, req.trace) if b is not None else (None, None)
    reductions = {
        key: trace
        for key, trace in (("a", a_reduction), ("b", b_reduction))
        if trace and trace["was_reduced"]
    }

    try:
        if req.operation == Operation.modulo:
            result, trace, verification = a_in, a_reduction, None
        else:
            # Pass original inputs to inverse/divide so Table 4.7 logs initial reduction too.
            use_original = req.operation in (Operation.inverse, Operation.divide)
            result, trace, verification = _dispatch(
                req.operation,
                a if use_original else a_in,
                b if use_original else b_in,
                field.mod_poly,
                field.m,
                req.trace,
            )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 4)
    except GF2mInverseError as exc:
        raise CalculationError(
            str(exc),
            gcd=getattr(exc, "gcd", None),
            trace=getattr(exc, "trace", None),
        ) from exc
    except ZeroDivisionError as exc:
        raise CalculationError("division by zero polynomial") from exc

    share_token = formatter.make_share_token(
        m=req.m,
        operation=req.operation.value,
        a_hex=polyrepr.to_hex(a, field.m),
        b_hex=polyrepr.to_hex(b, field.m) if b is not None else "",
        out_base=req.output_base.value,
    )

    return CalculateResponse(
        operation=req.operation,
        field=info,
        operands=Operands(
            a=element_model(a_in, field.m),
            b=element_model(b_in, field.m) if b_in is not None else None,
        ),
        result=element_model(result, field.m),
        trace=trace,
        initial_reduction=reductions or None,
        verification=verification,
        metrics=Metrics(
            elapsed_ms=elapsed_ms,
            result_bit_length=result.bit_length(),
            result_hamming_weight=polyrepr.HAMMING_WEIGHT(result),
        ),
        share_token=share_token,
    )

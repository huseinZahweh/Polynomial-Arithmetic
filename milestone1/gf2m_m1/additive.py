"""XOR addition/subtraction and polynomial reduction (Stallings Ch. 4)."""

from .polyrepr import (
    INT_TO_ALGEBRAIC,
    INT_TO_BIN,
    INT_TO_HEX,
    validate_non_negative_poly,
)


def _reduce(
    value_int: int, m_poly_int: int, m_degree: int, steps: list[dict] | None = None
) -> int:
    """Cancel the highest term at each step, optionally collecting its XOR row."""
    validate_non_negative_poly(value_int, "value_int")
    validate_non_negative_poly(m_poly_int, "m_poly_int")
    if type(m_degree) is not int or m_degree < 1:
        raise ValueError("m_degree must be a positive integer")
    if m_poly_int.bit_length() - 1 != m_degree:
        raise ValueError("m_poly_int must have degree m_degree")

    remainder = value_int
    while remainder.bit_length() > m_degree:
        target_degree = remainder.bit_length() - 1
        shift = target_degree - m_degree
        reducer = m_poly_int << shift
        next_remainder = remainder ^ reducer
        if steps is not None:
            steps.append({
                "target_degree": target_degree,
                "shift": shift,
                "before": remainder,
                "reducer": reducer,
                "after": next_remainder,
            })
        remainder = next_remainder
    return remainder


def MOD_REDUCE(f_int: int, m_poly_int: int, m_degree: int) -> tuple[int, dict]:
    """Return the polynomial remainder and its sequence of shifted-modulus XORs.

    At most max(0, degree(f_int) - m_degree + 1) XORs are required.
    """
    steps: list[dict] = []
    result = _reduce(f_int, m_poly_int, m_degree, steps)
    return result, {
        "trace_type": "mod_reduce",
        "m_degree": m_degree,
        "m_poly_int": m_poly_int,
        "initial_value": f_int,
        "reduced_value": result,
        "was_reduced": bool(steps),
        "step_count": len(steps),
        "steps": steps,
    }


def xor_trace(a: int, b: int, m: int) -> dict:
    """Return aligned XOR columns and representations for the supplied operands."""
    validate_non_negative_poly(a, "operand A")
    validate_non_negative_poly(b, "operand B")
    width = max(m, a.bit_length(), b.bit_length())
    columns = []
    for exponent in range(width - 1, -1, -1):
        bit_a, bit_b = (a >> exponent) & 1, (b >> exponent) & 1
        columns.append({"exp": exponent, "a": bit_a, "b": bit_b, "xor": bit_a ^ bit_b})

    values = {"a": a, "b": b, "result": a ^ b}
    rows = {
        name: {
            "bin": INT_TO_BIN(value, width),
            "hex": INT_TO_HEX(value, width),
            "poly": INT_TO_ALGEBRAIC(value),
        }
        for name, value in values.items()
    }
    return {
        "algorithm": "bitwise-xor",
        "a_bin": rows["a"]["bin"],
        "b_bin": rows["b"]["bin"],
        "result_bin": rows["result"]["bin"],
        "columns": columns,
        "rows": rows,
    }


def GF2M_ADD_SUB(
    f_int: int, g_int: int, m_poly_int: int, m_degree: int
) -> tuple[int, dict]:
    """Reduce both operands, then XOR them and return both reductions and XOR rows."""
    a_reduced, a_trace = MOD_REDUCE(f_int, m_poly_int, m_degree)
    b_reduced, b_trace = MOD_REDUCE(g_int, m_poly_int, m_degree)
    return a_reduced ^ b_reduced, {
        "trace_type": "add_sub",
        "f_mod_trace": a_trace,
        "g_mod_trace": b_trace,
        **xor_trace(a_reduced, b_reduced, m_degree),
    }


def modulo(a: int, mod_poly: int, m: int) -> int:
    """Return the remainder without collecting a trace, as expected by Milestone 2."""
    return _reduce(a, mod_poly, m)


def add(a: int, b: int, mod_poly: int, m: int) -> int:
    """Return the field sum without constructing a trace."""
    return modulo(a, mod_poly, m) ^ modulo(b, mod_poly, m)


subtract = add

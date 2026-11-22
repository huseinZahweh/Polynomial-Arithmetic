"""End-to-end 8-row verification matrix across textbook and all 6 cryptographic fields."""
from __future__ import annotations

import pytest

FIELDS = (163, 233, 239, 283, 409, 571)
BASES = ("hex", "binary")

ROWS = [
    (3, "5", "3"),
    (8, "53", "ca"),
    (163, "a3f1", "1f"),
    (233, "deadbeef", "cafe"),
    (239, "12345", "9abc"),
    (283, "f00d", "0ba1"),
    (409, "abcdef12", "77"),
    (571, "1337c0de", "beef"),
]


def _encode(value: int, base: str) -> str:
    return format(value, "b" if base == "binary" else "x")


def _calculate(client, base: str, m: int, op: str, a: int, b: int | None = None, *, trace: bool = True):
    body = {
        "m": m,
        "operation": op,
        "input_base": base,
        "poly_a": _encode(a, base),
        "trace": trace,
    }
    if b is not None:
        body["poly_b"] = _encode(b, base)
    response = client.post("/api/calculate", json=body)
    assert response.status_code == 200, response.text[:1000]
    return response.json()


def _expected_forms(result: dict, value: int, m: int) -> None:
    assert result["hex"] == format(value, f"0{(m + 3) // 4}x")
    assert result["bin"] == format(value, f"0{m}b")


@pytest.mark.parametrize("base", BASES)
@pytest.mark.parametrize(
    "operation,a,b,expected",
    [
        ("add", 0x57, 0x83, 0xD4),
        ("sub", 0x57, 0x83, 0xD4),
        ("mul", 0x57, 0x83, 0xC1),
        ("mul", 0x02, 0x87, 0x15),
        ("inv", 0x83, None, 0x80),
        ("inv", 0x95, None, 0x8A),
    ],
)
def test_textbook_matrix(client, base: str, operation: str, a: int, b: int | None, expected: int) -> None:
    body = _calculate(client, base, 8, operation, a, b)
    _expected_forms(body["result"], expected, 8)
    if operation == "inv":
        assert body["trace"]["termination"]["iterations"] == 3
        assert len(body["trace"]["table_4_7_rows"]) == 4
        assert body["verification"]["proof"]["passed"]


@pytest.mark.parametrize("base", BASES)
@pytest.mark.parametrize("m", FIELDS)
def test_large_field_matrix(client, base: str, m: int) -> None:
    a = (1 << (m - 1)) | 0x57
    b = (1 << (m - 2)) | 0x83
    for op in ("add", "sub"):
        _expected_forms(_calculate(client, base, m, op, a, a, trace=False)["result"], 0, m)
    inverse = _calculate(client, base, m, "inv", b, trace=False)
    assert inverse["verification"]["passed"]
    inv_value = int(inverse["result"]["hex"], 16)
    identity = _calculate(client, base, m, "mul", b, inv_value, trace=False)
    _expected_forms(identity["result"], 1, m)
    quotient = _calculate(client, base, m, "div", a, b, trace=False)
    assert quotient["verification"]["passed"]
    q_value = int(quotient["result"]["hex"], 16)
    recovered = _calculate(client, base, m, "mul", q_value, b, trace=False)
    _expected_forms(recovered["result"], a, m)


def _calc_hex(client, m: int, op: str, a: str, b: str | None = None):
    payload = {"m": m, "operation": op, "a": a, "input_base": "hex"}
    if b is not None:
        payload["b"] = b
    r = client.post("/api/calculate", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("m,a,b", ROWS)
def test_matrix_row_identities(client, m: int, a: str, b: str) -> None:
    inv = _calc_hex(client, m, "inverse", a)
    assert inv["verification"]["passed"] is True

    div = _calc_hex(client, m, "divide", a, b)
    assert div["verification"]["passed"] is True

    s1 = _calc_hex(client, m, "add", a, b)["result"]["hex"]
    s2 = _calc_hex(client, m, "add", s1, b)["result"]["hex"]
    a_reduced = _calc_hex(client, m, "modulo", a)["result"]["hex"]
    assert s2 == a_reduced

    ab = _calc_hex(client, m, "multiply", a, b)["result"]["hex"]
    ba = _calc_hex(client, m, "multiply", b, a)["result"]["hex"]
    assert ab == ba

    for res_hex in (ab, div["result"]["hex"], inv["result"]["hex"]):
        assert int(res_hex, 16).bit_length() - 1 < m


def test_matrix_covers_all_nist_fields() -> None:
    nist = {163, 233, 239, 283, 409, 571}
    assert nist.issubset({row[0] for row in ROWS})

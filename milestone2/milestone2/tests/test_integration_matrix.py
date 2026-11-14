"""End-to-end verification matrix (anticipates the M5 8-row sign-off).

Drives the public API exactly as the GUI/integration layer will, and checks the
field-algebra identities that must hold for every row. Each row exercises a
different field and operation mix.
"""
import pytest

# (m, a_hex, b_hex) rows spanning textbook + all NIST fields.
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


def _calc(client, m, op, a, b=None):
    payload = {"m": m, "operation": op, "a": a, "input_base": "hex"}
    if b is not None:
        payload["b"] = b
    r = client.post("/api/calculate", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("m,a,b", ROWS)
def test_matrix_row_identities(client, m, a, b):
    # 1. a * a^-1 == 1
    inv = _calc(client, m, "inverse", a)
    assert inv["verification"]["passed"] is True

    # 2. (a / b) * b == a
    div = _calc(client, m, "divide", a, b)
    assert div["verification"]["passed"] is True

    # 3. a + b + b == a  (XOR is its own inverse)
    s1 = _calc(client, m, "add", a, b)["result"]["hex"]
    s2 = _calc(client, m, "add", s1, b)["result"]["hex"]
    a_reduced = _calc(client, m, "modulo", a)["result"]["hex"]
    assert s2 == a_reduced

    # 4. a * b == b * a  (commutativity through the API)
    ab = _calc(client, m, "multiply", a, b)["result"]["hex"]
    ba = _calc(client, m, "multiply", b, a)["result"]["hex"]
    assert ab == ba

    # 5. every result sits inside the field (degree < m)
    for res_hex in (ab, div["result"]["hex"], inv["result"]["hex"]):
        assert int(res_hex, 16).bit_length() - 1 < m


def test_matrix_covers_all_nist_fields(client):
    nist = {163, 233, 239, 283, 409, 571}
    assert nist.issubset({row[0] for row in ROWS})

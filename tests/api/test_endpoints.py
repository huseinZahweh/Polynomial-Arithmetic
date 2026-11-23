"""FastAPI TestClient coverage for all six core endpoints, meta routes, and edge cases."""
from __future__ import annotations

import pytest

from backend.engine import NotInvertibleError, parse_share_token


def _calc(client, **kw):
    return client.post("/api/calculate", json=kw)


# --- Meta routes -------------------------------------------------------------
def test_health_and_root(client) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}
    api_data = client.get("/api").json()
    assert api_data["service"] == "gf2m-api"
    assert api_data["docs"] == "/docs"
    assert api_data["workbench"] == "/workbench/"

    root_redirect = client.get("/", follow_redirects=False)
    assert root_redirect.status_code in (302, 307)
    assert root_redirect.headers["location"] == "/workbench/"
    assert client.get("/").status_code == 200
    assert client.get("/workbench/").status_code == 200


# --- 1. GET /api/fields ------------------------------------------------------
def test_fields_lists_all_standard_fields(client) -> None:
    data = client.get("/api/fields").json()
    ms = {f["m"] for f in data["fields"]}
    assert {163, 233, 239, 283, 409, 571}.issubset(ms)
    assert data["count"] == len(data["fields"]) == 13


def test_fields_can_exclude_textbook(client) -> None:
    data = client.get("/api/fields", params={"include_textbook": False}).json()
    cats = {f["category"] for f in data["fields"]}
    assert cats == {"nist"}


def test_field_reduction_poly_shape(client) -> None:
    data = client.get("/api/fields").json()
    by_m = {f["m"]: f for f in data["fields"]}
    assert "x^163" in by_m[163]["reduction_poly"]
    assert by_m[8]["reduction_poly_bin"] == "100011011"
    assert by_m[3]["reduction_poly_bin"] == "1101"
    assert by_m[4]["reduction_poly_bin"] == "11001"
    for m, field in by_m.items():
        assert len(field["reduction_poly_bin"]) == m + 1


# --- 2. POST /api/calculate --------------------------------------------------
def test_calculate_multiply_small(client) -> None:
    r = _calc(client, m=3, operation="multiply", a="5", b="3", input_base="hex")
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["hex"] == "2"
    assert body["trace"]["algorithm"] == "shift-and-xor"
    assert body["metrics"]["elapsed_ms"] >= 0


def test_calculate_all_six_operations(client) -> None:
    ops = ["add", "subtract", "modulo", "multiply", "inverse", "divide"]
    for op in ops:
        payload = {"m": 163, "operation": op, "a": "a3", "b": "1f", "input_base": "hex"}
        r = _calc(client, **payload)
        assert r.status_code == 200, f"{op} -> {r.text}"
        assert "result" in r.json()


def test_calculate_inverse_verification_passes(client) -> None:
    r = _calc(client, m=233, operation="inverse", a=" abc123", input_base="hex")
    assert r.json()["verification"]["passed"] is True


def test_calculate_divide_verification_passes(client) -> None:
    r = _calc(client, m=283, operation="divide", a="deadbeef", b="1234", input_base="hex")
    assert r.json()["verification"]["passed"] is True


def test_calculate_binary_base_roundtrip(client) -> None:
    r = _calc(client, m=4, operation="add", a="1010", b="0110", input_base="bin")
    assert r.json()["result"]["bin"] == "1100"


def test_calculate_missing_operand_b_is_400(client) -> None:
    r = _calc(client, m=163, operation="multiply", a="2")
    assert r.status_code == 400
    assert "operand B" in r.json()["detail"]


def test_calculate_unsupported_field_is_400(client) -> None:
    r = _calc(client, m=99, operation="add", a="1", b="1")
    assert r.status_code == 400


def test_calculate_inverse_of_zero_is_400(client) -> None:
    r = _calc(client, m=163, operation="inverse", a="0")
    assert r.status_code == 400


def test_calculate_divide_by_zero_is_400(client) -> None:
    r = _calc(client, m=8, operation="divide", a="53", b="0")
    assert r.status_code == 400
    assert "detail" in r.json()


def test_calculate_unreduced_operands_consistent(client) -> None:
    for op in ("add", "subtract"):
        r = _calc(client, m=8, operation=op, a="100", b="01", input_base="hex")
        assert r.status_code == 200
        body = r.json()
        assert body["operands"]["a"]["hex"] == "1b"
        assert body["result"]["hex"] == "1a"
        assert body["result"]["degree"] < 8
        assert body["trace"]["a_bin"] == "00011011"

    r_mul = _calc(client, m=8, operation="multiply", a="1ff", b="102", input_base="hex")
    assert r_mul.status_code == 200
    assert r_mul.json()["result"]["hex"] == _calc(
        client, m=8, operation="multiply", a="e4", b="19", input_base="hex"
    ).json()["result"]["hex"]

    assert _calc(client, m=8, operation="inverse", a="11b").status_code == 400
    assert _calc(client, m=8, operation="divide", a="53", b="11b").status_code == 400
    assert _calc(client, m=8, operation="inverse", a="157").json()["verification"]["passed"] is True
    assert _calc(client, m=8, operation="divide", a="157", b="183").json()["verification"]["passed"] is True


def test_calculate_braces_accepted(client) -> None:
    r = _calc(client, m=8, operation="multiply", a="{57}", b="{83}", input_base="hex")
    assert r.status_code == 200
    assert r.json()["result"]["hex"] == "c1"


@pytest.mark.parametrize(
    "bad_a,base",
    [
        ("-5", "hex"),
        ("+5", "hex"),
        ("ZZ", "hex"),
        ("5 7", "hex"),
        ("0x", "hex"),
        ("102", "bin"),
        ("-101", "bin"),
    ],
)
def test_calculate_invalid_operands_are_400(client, bad_a: str, base: str) -> None:
    r = _calc(client, m=8, operation="add", a=bad_a, b="1", input_base=base)
    assert r.status_code == 400
    assert isinstance(r.json()["detail"], str)


def test_calculate_preserves_structured_gcd_and_trace_on_400(client, monkeypatch) -> None:
    from backend.api import services

    # Live path: zero inverse naturally carries gcd=0x11B and Table 4.7 Step 0 trace.
    live = _calc(client, m=8, operation="inverse", a="0", trace=True)
    assert live.status_code == 400
    live_body = live.json()
    assert live_body["gcd"] == 0x11B
    assert live_body["trace"]["table_4_7_rows"][0]["B3"] == 0

    # Custom NotInvertibleError path: verifies any GF2mInverseError payload passes through.
    def fake_eea(mod_poly, m, a):
        raise NotInvertibleError("not invertible", gcd=mod_poly, trace=[{"step": 0, "B3": 0}])

    monkeypatch.setattr(services, "EXTENDED_EUCLID_GF2M", fake_eea)
    r = _calc(client, m=8, operation="inverse", a="5", trace=True)
    assert r.status_code == 400
    body = r.json()
    assert "not invertible" in body["detail"]
    assert body["gcd"] == 0x11B
    assert body["trace"] == [{"step": 0, "B3": 0}]


def test_required_traces_and_error_shapes(client) -> None:
    mod = _calc(client, m=8, operation="mod", input_base="hex", poly_a="100", trace=True).json()
    assert mod["trace"]["steps"][0]["after_hex"] == "1b"

    div = _calc(
        client, m=8, operation="div", input_base="hex", poly_a="157", poly_b="83", trace=True
    ).json()
    assert div["initial_reduction"]["a"]["was_reduced"]
    assert div["trace"]["stage_2_multiply"]["algorithm"] == "shift-and-xor"
    assert div["verification"]["proof"]["nonzero_divisor"]

    for request in [
        {"operation": "inverse", "a": "0"},
        {"operation": "inverse", "a": "11b"},
        {"operation": "divide", "a": "53", "b": "0"},
        {"operation": "divide", "a": "53", "b": "11b"},
    ]:
        response = client.post("/api/calculate", json={"m": 8, **request})
        assert response.status_code == 400
        trace = response.json()["trace"]
        assert trace["termination"]["gcd_formatted"]["hex"] == "11B"
        assert trace["table_4_7_rows"][0]["B3"] == 0


def test_calculate_share_token_roundtrips(client) -> None:
    r = _calc(client, m=163, operation="multiply", a="2", b="2", output_base="bin")
    token = r.json()["share_token"]
    decoded = parse_share_token(token)
    assert decoded["m"] == 163 and decoded["operation"] == "multiply"
    assert decoded["base"] == "bin"


# --- 3. POST /api/random-polynomials -----------------------------------------
def test_random_in_field_and_reproducible(client) -> None:
    p = {"m": 163, "density": "dense", "seed": 7}
    r1 = client.post("/api/random-polynomials", json=p).json()
    r2 = client.post("/api/random-polynomials", json=p).json()
    assert r1["a"] == r2["a"] and r1["b"] == r2["b"]
    assert r1["a"]["degree"] < 163


def test_random_sparse_is_low_weight(client) -> None:
    r = client.post("/api/random-polynomials", json={"m": 283, "density": "sparse", "seed": 3})
    assert r.json()["a"]["hamming_weight"] <= 32
    generated = client.post("/api/random-polynomials", json={"m": 409, "density": "sparse"}).json()
    assert 3 <= generated["a"]["hamming_weight"] <= 6
    batch = client.post(
        "/api/random-polynomials",
        json={"m": 8, "sparsity": "dense", "count": 3, "output_base": "binary", "seed": 9},
    ).json()
    assert len(batch["polynomials"]) == 3
    assert batch["polynomials"][1] == batch["b"]["bin"]


def test_random_unsupported_field_is_400(client) -> None:
    r = client.post("/api/random-polynomials", json={"m": 99, "density": "random"})
    assert r.status_code == 400
    assert "detail" in r.json()


# --- 4. POST /api/parse-polynomials ------------------------------------------
def test_parse_json(client) -> None:
    content = '{"base":"hex","pairs":[{"a":"a1","b":"0f"},{"a":"2","b":"2"}]}'
    r = client.post("/api/parse-polynomials", json={"content": content, "filename": "p.json"})
    body = r.json()
    assert body["count"] == 2
    assert body["pairs"][0]["a"] == "a1"


def test_parse_txt(client) -> None:
    content = "base: hex\nA: a1\nB: 0f\n---\nA: 2\nB: 2\n"
    r = client.post("/api/parse-polynomials", json={"content": content, "filename": "p.txt"})
    assert r.json()["count"] == 2


@pytest.mark.parametrize(
    "content,filename",
    [
        ("", "p.txt"),
        ("{not json", "p.json"),
        ("{", "broken.json"),
        ("hello", "broken.txt"),
        ('{"x": 1}', "p.json"),
        ('{"pairs": 123}', "p.json"),
        ("[123]", "p.json"),
        ('{"a": 123}', "p.json"),
        ('{"pairs": []}', "p.json"),
    ],
)
def test_parse_bad_content_is_400(client, content: str, filename: str) -> None:
    r = client.post("/api/parse-polynomials", json={"content": content, "filename": filename})
    assert r.status_code == 400
    assert "parse error:" in r.json()["detail"]


# --- 5. POST /api/export-calculation & algebraic input -----------------------
def test_export_md_and_json_and_algebraic_input(client) -> None:
    calc = _calc(client, m=8, operation="multiply", a="53", b="ca", input_base="hex").json()
    md = client.post("/api/export-calculation", json={"calculation": calc, "format": "md"})
    js = client.post("/api/export-calculation", json={"calculation": calc, "format": "json"})
    assert "Calculation Summary" in md.json()["content"]
    assert md.json()["filename"].endswith(".md")
    assert '"operation"' in js.json()["content"]

    alg = client.post(
        "/api/calculate",
        json={"m": 8, "operation": "add", "input_base": "algebraic", "a": "x^8 + x + x", "b": "0"},
    ).json()
    assert alg["result"]["hex"] == "1b"
    for fmt in ("md", "json"):
        response = client.post(
            "/api/export-calculation",
            json={"format": fmt, "calculation": alg, "download": True},
        )
        assert response.status_code == 200
        assert response.headers["content-disposition"].endswith("." + fmt + '"')
        assert "1b" in response.text.lower()


def test_export_download_sets_attachment_header(client) -> None:
    calc = _calc(client, m=8, operation="multiply", a="53", b="ca").json()
    r = client.post(
        "/api/export-calculation",
        json={"calculation": calc, "format": "md", "download": True},
    )
    assert "attachment" in r.headers["content-disposition"]


# --- 6. GET /api/tutorial ----------------------------------------------------
def test_tutorial_has_four_slides(client) -> None:
    data = client.get("/api/tutorial").json()
    assert len(data["slides"]) == 4
    assert data["slides"][0]["title"]

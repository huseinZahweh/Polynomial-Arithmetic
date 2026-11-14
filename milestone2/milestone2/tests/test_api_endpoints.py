"""TestClient coverage for all six endpoints + meta routes."""
import pytest


# --- meta --------------------------------------------------------------------
def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


# --- 1. /api/fields ----------------------------------------------------------
def test_fields_lists_all_standard_fields(client):
    data = client.get("/api/fields").json()
    ms = {f["m"] for f in data["fields"]}
    assert {163, 233, 239, 283, 409, 571}.issubset(ms)
    assert data["count"] == len(data["fields"])


def test_fields_can_exclude_textbook(client):
    data = client.get("/api/fields", params={"include_textbook": False}).json()
    cats = {f["category"] for f in data["fields"]}
    assert cats == {"nist"}


def test_field_reduction_poly_shape(client):
    data = client.get("/api/fields").json()
    f163 = next(f for f in data["fields"] if f["m"] == 163)
    assert "x^163" in f163["reduction_poly"]


# --- 2. /api/calculate -------------------------------------------------------
def _calc(client, **kw):
    return client.post("/api/calculate", json=kw)


def test_calculate_multiply_small(client):
    r = _calc(client, m=3, operation="multiply", a="5", b="3", input_base="hex")
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["hex"] == "4"           # (x^2+1)(x+1)=x^2
    assert body["trace"]["algorithm"] == "shift-and-xor"
    assert body["metrics"]["elapsed_ms"] >= 0


def test_calculate_all_six_operations(client):
    ops = ["add", "subtract", "modulo", "multiply", "inverse", "divide"]
    for op in ops:
        payload = {"m": 163, "operation": op, "a": "a3", "b": "1f", "input_base": "hex"}
        r = _calc(client, **payload)
        assert r.status_code == 200, f"{op} -> {r.text}"
        assert "result" in r.json()


def test_calculate_inverse_verification_passes(client):
    r = _calc(client, m=233, operation="inverse", a=" abc123", input_base="hex")
    body = r.json()
    assert body["verification"]["passed"] is True


def test_calculate_divide_verification_passes(client):
    r = _calc(client, m=283, operation="divide", a="deadbeef", b="1234", input_base="hex")
    assert r.json()["verification"]["passed"] is True


def test_calculate_binary_base_roundtrip(client):
    r = _calc(client, m=4, operation="add", a="1010", b="0110", input_base="bin")
    assert r.json()["result"]["bin"] == "1100"


def test_calculate_missing_operand_b_is_400(client):
    r = _calc(client, m=163, operation="multiply", a="2")
    assert r.status_code == 400
    assert "operand B" in r.json()["detail"]


def test_calculate_unsupported_field_is_400(client):
    r = _calc(client, m=99, operation="add", a="1", b="1")
    assert r.status_code == 400


def test_calculate_inverse_of_zero_is_400(client):
    r = _calc(client, m=163, operation="inverse", a="0")
    assert r.status_code == 400


def test_calculate_share_token_roundtrips(client):
    from gf2m._reference.formatter import parse_share_token

    r = _calc(client, m=163, operation="multiply", a="2", b="2", output_base="bin")
    token = r.json()["share_token"]
    decoded = parse_share_token(token)
    assert decoded["m"] == 163 and decoded["operation"] == "multiply"
    assert decoded["base"] == "bin"


# --- 3. /api/random-polynomials ---------------------------------------------
def test_random_in_field_and_reproducible(client):
    p = {"m": 163, "density": "dense", "seed": 7}
    r1 = client.post("/api/random-polynomials", json=p).json()
    r2 = client.post("/api/random-polynomials", json=p).json()
    assert r1["a"] == r2["a"] and r1["b"] == r2["b"]     # seeded -> deterministic
    assert r1["a"]["degree"] < 163


def test_random_sparse_is_low_weight(client):
    r = client.post("/api/random-polynomials", json={"m": 283, "density": "sparse", "seed": 3})
    assert r.json()["a"]["hamming_weight"] <= 32


# --- 4. /api/parse-polynomials ----------------------------------------------
def test_parse_json(client):
    content = '{"base":"hex","pairs":[{"a":"a1","b":"0f"},{"a":"2","b":"2"}]}'
    r = client.post("/api/parse-polynomials", json={"content": content, "filename": "p.json"})
    body = r.json()
    assert body["count"] == 2
    assert body["pairs"][0]["a"] == "a1"


def test_parse_txt(client):
    content = "base: hex\nA: a1\nB: 0f\n---\nA: 2\nB: 2\n"
    r = client.post("/api/parse-polynomials", json={"content": content, "filename": "p.txt"})
    assert r.json()["count"] == 2


def test_parse_bad_content_is_400(client):
    r = client.post("/api/parse-polynomials", json={"content": "", "filename": "p.txt"})
    assert r.status_code == 400


# --- 5. /api/export-calculation ---------------------------------------------
def test_export_md_and_json(client):
    calc = _calc(client, m=8, operation="multiply", a="53", b="ca", input_base="hex").json()
    md = client.post("/api/export-calculation", json={"calculation": calc, "format": "md"})
    js = client.post("/api/export-calculation", json={"calculation": calc, "format": "json"})
    assert "Calculation Summary" in md.json()["content"]
    assert md.json()["filename"].endswith(".md")
    assert '"operation"' in js.json()["content"]


def test_export_download_sets_attachment_header(client):
    calc = _calc(client, m=8, operation="multiply", a="53", b="ca").json()
    r = client.post(
        "/api/export-calculation",
        json={"calculation": calc, "format": "md", "download": True},
    )
    assert "attachment" in r.headers["content-disposition"]


# --- 6. /api/tutorial --------------------------------------------------------
def test_tutorial_has_four_slides(client):
    data = client.get("/api/tutorial").json()
    assert len(data["slides"]) == 4
    assert data["slides"][0]["title"]

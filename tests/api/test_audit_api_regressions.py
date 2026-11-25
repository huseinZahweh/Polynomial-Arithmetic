"""Exercise the fixed contracts through actual local HTTP endpoints."""
import json
import pytest


def test_upload_and_calculation_share_width_rejection(client):
    operand = "1" + "0" * 1024
    parsed = client.post("/api/parse-polynomials", json={"filename": "bad.json", "content": json.dumps({"a": operand, "b": "1"})})
    calc = client.post("/api/calculate", json={"m": 163, "operation": "add", "a": operand, "b": "1", "trace": False})
    assert parsed.status_code == calc.status_code == 400
    assert "4096" in parsed.json()["detail"]
    assert "pair 1" in parsed.json()["detail"]


@pytest.mark.parametrize("filename,content", [
    ("pair.txt", "base: algebraic\nA: x + 1\nB: x"),
    ("pair.json", '{"base":"algebraic","pairs":[{"a":"x + 1","b":"x"}]}'),
])
def test_algebraic_upload_to_calculate(client, filename, content):
    r = client.post("/api/parse-polynomials", json={"filename": filename, "content": content, "default_base": "algebraic"})
    assert r.status_code == 200
    pair = r.json()["pairs"][0]
    r = client.post("/api/calculate", json={"m": 163, "operation": "add", "a": pair["a"], "b": pair["b"], "input_base": pair["base"]})
    assert r.status_code == 200
    assert int(r.json()["result"]["hex"], 16) == 1


def test_ghash_endpoint_standard_identity(client):
    r = client.post("/api/explorations/gcm-ghash", json={"h_hex": "80000000000000000000000000000000", "blocks_hex": ["1"]})
    assert r.status_code == 200
    assert r.json()["tag_hex"] == "00000000000000000000000000000001"
    assert r.json()["output_kind"] == "ghash"

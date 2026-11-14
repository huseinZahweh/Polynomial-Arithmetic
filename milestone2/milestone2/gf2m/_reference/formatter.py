"""Reference summary formatter + shareable-link codec.

INTEGRATION CONTRACT — owned by Milestone 1 on merge.

Turns a completed calculation (the dict produced by the API's calculate
service) into a downloadable Markdown or JSON summary, and encodes/decodes the
compact Hexadecimal share token that lets a scenario reload exactly — including
the chosen display base — from a URL.
"""
from __future__ import annotations

import json
from typing import Dict, Tuple

_TOKEN_VERSION = "v1"


def make_share_token(m: int, operation: str, a_hex: str, b_hex: str, out_base: str) -> str:
    """Encode scenario state as a single lowercase-hex string."""
    payload = f"{_TOKEN_VERSION}|{m}|{operation}|{a_hex}|{b_hex}|{out_base}"
    return payload.encode("utf-8").hex()


def parse_share_token(token: str) -> Dict[str, str]:
    """Inverse of ``make_share_token``."""
    try:
        payload = bytes.fromhex(token.strip()).decode("utf-8")
        version, m, operation, a_hex, b_hex, out_base = payload.split("|")
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"invalid share token: {exc}")
    if version != _TOKEN_VERSION:
        raise ValueError(f"unsupported token version: {version}")
    return {
        "m": int(m),
        "operation": operation,
        "a": a_hex,
        "b": b_hex,
        "base": out_base,
    }


def to_json(calc: dict) -> str:
    return json.dumps(calc, indent=2, ensure_ascii=False)


def to_markdown(calc: dict) -> str:
    field = calc.get("field", {})
    ops = calc.get("operands", {})
    res = calc.get("result", {})
    a = ops.get("a") or {}
    b = ops.get("b") or {}
    lines = [
        f"# GF(2^{field.get('m')}) Calculation Summary",
        "",
        f"- **Operation:** `{calc.get('operation')}`",
        f"- **Field:** GF(2^{field.get('m')})  ·  reduction `{field.get('reduction_poly_hex')}`",
        "",
        "## Operands",
        "",
        "| | Hex | Polynomial |",
        "| :-- | :-- | :-- |",
        f"| A(x) | `{a.get('hex', '-')}` | ${a.get('poly', '-')}$ |",
    ]
    if ops.get("b") is not None:
        lines.append(f"| B(x) | `{b.get('hex', '-')}` | ${b.get('poly', '-')}$ |")
    lines += [
        "",
        "## Result",
        "",
        f"- **Hex:** `{res.get('hex')}`",
        f"- **Binary:** `{res.get('bin')}`",
        f"- **Polynomial:** ${res.get('poly')}$",
        f"- **Degree:** {res.get('degree')}  ·  **Hamming weight:** {res.get('hamming_weight')}",
    ]
    verification = calc.get("verification")
    if verification:
        mark = "PASS" if verification.get("passed") else "FAIL"
        lines += ["", "## Verification", "", f"- {verification.get('label')} — **{mark}**"]
    metrics = calc.get("metrics", {})
    if metrics:
        lines += [
            "",
            "## Metrics",
            "",
            f"- Elapsed: {metrics.get('elapsed_ms')} ms",
            f"- Result bit length: {metrics.get('result_bit_length')}",
        ]
    if calc.get("share_token"):
        lines += ["", f"_Share token:_ `{calc['share_token']}`"]
    return "\n".join(lines) + "\n"


def render(calc: dict, fmt: str) -> Tuple[str, str, str]:
    """Return ``(content, suggested_filename, media_type)`` for ``fmt``."""
    op = calc.get("operation", "calc")
    m = calc.get("field", {}).get("m", "x")
    if fmt == "md":
        return to_markdown(calc), f"gf2_{m}_{op}.md", "text/markdown"
    if fmt == "json":
        return to_json(calc), f"gf2_{m}_{op}.json", "application/json"
    raise ValueError(f"unsupported export format: {fmt!r}")

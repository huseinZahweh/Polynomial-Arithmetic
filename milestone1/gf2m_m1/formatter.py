"""Format Milestone 2 calculation payloads and preserve v1 share tokens."""

import json
import re
from textwrap import indent


def make_share_token(m: int, operation: str, a_hex: str, b_hex: str, out_base: str) -> str:
    """Encode the API's versioned calculation fields as lowercase hex."""
    return f"v1|{m}|{operation}|{a_hex}|{b_hex}|{out_base}".encode("utf-8").hex()


def parse_share_token(token: str) -> dict[str, int | str]:
    """Decode an existing v1 token, including its integer field degree."""
    try:
        version, m, operation, a_hex, b_hex, base = bytes.fromhex(token).decode("utf-8").split("|")
        degree = int(m)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid calculation share token") from exc
    if version != "v1":
        raise ValueError(f"unsupported token version: {version!r}")
    return {"m": degree, "operation": operation, "a": a_hex, "b": b_hex, "base": base}


def to_json(calc: dict) -> str:
    """Serialize the complete calculation payload with indented JSON."""
    return json.dumps(calc, indent=2, ensure_ascii=False)


def to_markdown(calc: dict) -> str:
    """Render field, operand, result, verification, metrics, and trace sections."""
    field = calc.get("field") or {}
    operands = calc.get("operands") or {}
    result = calc.get("result") or {}
    m = field.get("m", "?")
    lines = [
        f"# GF(2^{m}) Calculation Summary",
        "",
        f"- **Operation:** `{calc.get('operation', 'calculation')}`",
        f"- **Modulus (hex):** `{field.get('reduction_poly_hex', '-')}`",
        f"- **Modulus (polynomial):** {field.get('reduction_poly', '-')}",
        "",
        "## Operands",
        "",
        "| Operand | Hex | Binary | Polynomial |",
        "| --- | --- | --- | --- |",
    ]
    for key, label in (("a", "A(x)"), ("b", "B(x)")):
        value = operands.get(key)
        if value is not None:
            lines.append(f"| {label} | `{value['hex']}` | `{value['bin']}` | {value['poly']} |")
    lines += [
        "",
        "## Result",
        "",
        f"- **Hex:** `{result.get('hex', '-')}`",
        f"- **Binary:** `{result.get('bin', '-')}`",
        f"- **Polynomial:** {result.get('poly', '-')}",
        f"- **Degree:** {result.get('degree', '-')}",
        f"- **Hamming weight:** {result.get('hamming_weight', '-')}",
    ]
    verification = calc.get("verification")
    if verification is not None:
        status = "PASS" if verification["passed"] else "FAIL"
        lines += ["", "## Verification", "", f"- {verification['label']} — **{status}**"]
    metrics = calc.get("metrics")
    if metrics:
        lines += [
            "", "## Metrics", "",
            f"- Elapsed time: {metrics['elapsed_ms']} ms",
            f"- Result bit length: {metrics['result_bit_length']}",
            f"- Result Hamming weight: {metrics['result_hamming_weight']}",
        ]
    if calc.get("initial_reduction") and calc.get("operation") != "modulo":
        lines += ["", "## Initial operand reduction", "",
                  indent(to_json(calc["initial_reduction"]), "    ")]
    if calc.get("trace") is not None:
        lines += ["", "## Educational trace", "", indent(to_json(calc["trace"]), "    ")]
    if calc.get("share_token"):
        lines += ["", f"_Share token:_ `{calc['share_token']}`"]
    return "\n".join(lines) + "\n"


def render(calc: dict, fmt: str) -> tuple[str, str, str]:
    """Return formatted content, a safe attachment filename, and media type."""
    degree = str((calc.get("field") or {}).get("m", "x"))
    operation = str(calc.get("operation", "calc"))
    if not re.fullmatch(r"[0-9]+", degree):
        degree = "x"
    if not re.fullmatch(r"[a-z]+", operation):
        operation = "calc"
    stem = f"gf2_{degree}_{operation}"
    if fmt == "md":
        return to_markdown(calc), f"{stem}.md", "text/markdown"
    if fmt == "json":
        return to_json(calc), f"{stem}.json", "application/json"
    raise ValueError(f"unsupported export format: {fmt!r}")

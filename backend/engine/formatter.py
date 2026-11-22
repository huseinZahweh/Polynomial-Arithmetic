"""Calculation summary exporter (.md / .json) and versioned hex share-token codec.

Original Author
---------------
Hussein Abbas — Milestone 1 (Field Configuration, I/O, Additive/Modulo & Utilities).
(Initial-reduction Markdown export section added by Ali Zahreddine during integration.)

Purpose & Course References
---------------------------
Formats completed ``GF(2^m)`` calculation payloads (field metadata, operands,
result, algebraic verification proof, runtime metrics, and step-by-step traces)
into downloadable Markdown or JSON reports, and encodes/decodes compact
hexadecimal ``v1`` share tokens preserving field degree, operation, operands,
and selected display base.
"""
from __future__ import annotations

import json
import re
from textwrap import indent
from typing import Any


def make_share_token(
    m: int,
    operation: str,
    a_hex: str,
    b_hex: str,
    out_base: str,
) -> str:
    """Encode calculation state into a compact lowercase hex ``v1`` share token.

    Encodes ``"v1|{m}|{operation}|{a_hex}|{b_hex}|{out_base}"`` as UTF-8 hex so
    even 571-bit operands stay URL-safe and restore exact display notation.

    Args:
        m: Field extension degree.
        operation: Operation name (e.g. ``"multiply"``, ``"inverse"``).
        a_hex: Operand ``A(x)`` in hexadecimal.
        b_hex: Operand ``B(x)`` in hexadecimal (empty string for unary ops).
        out_base: Selected display base (``"hex"``, ``"bin"``, or ``"algebraic"``).

    Returns:
        Lowercase hexadecimal share-token string.

    Complexity:
        Time ``O(L)``, space ``O(L)`` in payload string length ``L``.
    """
    return f"v1|{m}|{operation}|{a_hex}|{b_hex}|{out_base}".encode("utf-8").hex()


def parse_share_token(token: str) -> dict[str, int | str]:
    """Decode a ``v1`` hexadecimal share token back into calculation parameters.

    Args:
        token: Lowercase or uppercase hex string produced by :func:`make_share_token`.

    Returns:
        Dictionary ``{"m": int, "operation": str, "a": str, "b": str, "base": str}``.

    Raises:
        ValueError: If ``token`` is not valid hex/UTF-8, lacks 6 pipe-separated
            fields, has a non-integer degree, or uses an unsupported version.

    Complexity:
        Time ``O(L)``, space ``O(L)`` where ``L = len(token)``.
    """
    try:
        version, m, operation, a_hex, b_hex, base = bytes.fromhex(token).decode("utf-8").split("|")
        degree = int(m)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid calculation share token") from exc
    if version != "v1":
        raise ValueError(f"unsupported token version: {version!r}")
    return {"m": degree, "operation": operation, "a": a_hex, "b": b_hex, "base": base}


def to_json(calc: dict[str, Any]) -> str:
    """Serialize a calculation payload as 2-space indented UTF-8 JSON.

    Args:
        calc: Calculation response dictionary.

    Returns:
        Formatted JSON string.

    Complexity:
        Time ``O(S)``, space ``O(S)`` in serialized payload size ``S``.
    """
    return json.dumps(calc, indent=2, ensure_ascii=False)


def to_markdown(calc: dict[str, Any]) -> str:
    """Render a structured Markdown report for a completed ``GF(2^m)`` calculation.

    Includes field metadata, an operand table (omitting ``B(x)`` on unary ops),
    result notations and metrics, live verification pass/fail status, optional
    initial reduction trace, full educational trace, and the share token.

    Args:
        calc: Calculation response dictionary (as returned by ``POST /api/calculate``).

    Returns:
        GitHub-Flavored Markdown report ending with a trailing newline.

    Complexity:
        Time ``O(S)``, space ``O(S)`` in serialized payload size ``S``.
    """
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
            "",
            "## Metrics",
            "",
            f"- Elapsed time: {metrics['elapsed_ms']} ms",
            f"- Result bit length: {metrics['result_bit_length']}",
            f"- Result Hamming weight: {metrics['result_hamming_weight']}",
        ]
    if calc.get("initial_reduction") and calc.get("operation") != "modulo":
        lines += [
            "",
            "## Initial operand reduction",
            "",
            indent(to_json(calc["initial_reduction"]), "    "),
        ]
    if calc.get("trace") is not None:
        lines += ["", "## Educational trace", "", indent(to_json(calc["trace"]), "    ")]
    if calc.get("share_token"):
        lines += ["", f"_Share token:_ `{calc['share_token']}`"]
    return "\n".join(lines) + "\n"


def render(calc: dict[str, Any], fmt: str) -> tuple[str, str, str]:
    """Render a calculation summary along with a sanitized attachment filename and MIME type.

    Sanitizes ``field.m`` and ``operation`` strictly against alphanumeric regexes
    so downloaded ``Content-Disposition`` filenames cannot contain header injections.

    Args:
        calc: Calculation response dictionary.
        fmt: Target export format — ``"md"`` or ``"json"``.

    Returns:
        Tuple ``(content, filename, media_type)``.

    Raises:
        ValueError: If ``fmt`` is neither ``"md"`` nor ``"json"``.

    Complexity:
        Time ``O(S)``, space ``O(S)`` in serialized payload size ``S``.
    """
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

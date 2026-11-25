"""Batch polynomial operand file parser (.txt and .json) with location diagnostics.

Original Author
---------------
Hussein Abbas — Milestone 1 (Field Configuration, I/O, Additive/Modulo & Utilities).

Purpose & Course References
---------------------------
Parses classroom batch operand files uploaded via ``POST /api/parse-polynomials``
into validated ``{"a", "b", "base"}`` records for Binary, Hexadecimal and Algebraic inputs
(Stallings **Chapter 4** polynomial bit-strings and **Chapter 5** braced hex byte
notation such as ``{57}``). Supports:

* **JSON:** A single pair object ``{"a": ..., "b": ...}``, a bare JSON array of
  pair objects, or a wrapper object ``{"base": "hex", "pairs": [...]}``.
* **Plain Text:** Labeled ``A:`` / ``A(x):`` / ``B:`` / ``B(x):`` / ``base:``
  lines (using ``:`` or ``=``) separated by ``---`` or ``===``, with ``#`` comments.
"""
from __future__ import annotations

import json

from .polyrepr import ALGEBRAIC_TO_INT, BIN_TO_INT, HEX_TO_INT, validate_input_width


class OperandFileError(ValueError):
    """Structured parse error locating the offending pair, line, and operand field.

    Attributes:
        pair: 1-based pair index where validation failed, if known.
        line: 1-based line number in the uploaded text/JSON file, if known.
        field: Field name (``"a"``, ``"b"``, or ``"base"``) that failed, if known.
    """

    def __init__(
        self,
        message: str,
        *,
        pair: int | None = None,
        line: int | None = None,
        field: str | None = None,
    ) -> None:
        """Build a readable diagnostic message prefixed with available location metadata.

        Args:
            message: Explanation of the syntax or validation failure.
            pair: Optional 1-based operand-pair number.
            line: Optional 1-based source line number.
            field: Optional field key (``"a"``, ``"b"``, ``"base"``).
        """
        self.pair = pair
        self.line = line
        self.field = field
        location: list[str] = []
        if pair is not None:
            location.append(f"pair {pair}")
        if line is not None:
            location.append(f"line {line}")
        if field is not None:
            location.append(field)
        super().__init__(f"{', '.join(location)}: {message}" if location else message)


def _normalize_base(
    base: str,
    *,
    pair: int | None = None,
    line: int | None = None,
) -> str:
    """Normalize batch base labels to ``"hex"``, ``"bin"``, or ``"algebraic"``.

    Args:
        base: Candidate base string (``"hex"``, ``"bin"``, ``"binary"``, or ``"algebraic"``).
        pair: Optional 1-based pair index for error reporting.
        line: Optional 1-based source line number for error reporting.

    Returns:
        Normalized string ``"hex"``, ``"bin"``, or ``"algebraic"``.

    Raises:
        OperandFileError: If ``base`` is not a recognized string.
    """
    if isinstance(base, str):
        normalized = base.strip().lower()
        if normalized == "hex":
            return normalized
        if normalized in ("bin", "binary"):
            return "bin"
        if normalized == "algebraic":
            return normalized
    raise OperandFileError("base must be hex or bin or algebraic", pair=pair, line=line, field="base")


def _validate_pair(
    item: dict,
    fallback_base: str,
    pair: int,
    lines: dict[str, int] | None = None,
) -> dict[str, str]:
    """Validate one operand pair and strip internal grouping spaces for API compatibility.

    Operand ``a`` is always required; operand ``b`` may be omitted or empty for
    unary operations (modulo reduction and multiplicative inverse).

    Args:
        item: Raw mapping containing ``"a"``, optional ``"b"``, and optional ``"base"``.
        fallback_base: Inherited base when ``item`` omits ``"base"``.
        pair: 1-based pair index.
        lines: Optional map from field name to 1-based source line number.

    Returns:
        Normalized record ``{"a": str, "b": str, "base": "hex" | "bin"}``.

    Raises:
        OperandFileError: If ``item`` is not a dict or contains invalid digits.
    """
    if not isinstance(item, dict):
        raise OperandFileError("expected an operand object", pair=pair)
    lines = lines or {}
    base = _normalize_base(item.get("base", fallback_base), pair=pair, line=lines.get("base"))
    parse = {"hex": HEX_TO_INT, "bin": BIN_TO_INT, "algebraic": ALGEBRAIC_TO_INT}[base]
    result = {"base": base}
    for field in ("a", "b"):
        value = item.get(field, "")
        if not isinstance(value, str) or (field == "a" and not value.strip()):
            raise OperandFileError(
                "expected an operand string",
                pair=pair,
                line=lines.get(field),
                field=field,
            )
        if value.strip():
            try:
                validate_input_width(parse(value))
            except ValueError as exc:
                raise OperandFileError(
                    str(exc),
                    pair=pair,
                    line=lines.get(field),
                    field=field,
                ) from exc
        # Collapse grouping whitespace for hex/bin, but preserve algebraic token
        # boundaries so malformed syntax like "x^1 2" is never silently rewritten.
        result[field] = value.strip() if base == "algebraic" else "".join(value.split())
    return result


def _parse_json(content: str, default_base: str) -> list[dict[str, str]]:
    """Parse JSON batch text containing a pair object, pair array, or ``pairs`` wrapper.

    Args:
        content: Raw JSON text.
        default_base: Normalized fallback base (``"hex"`` or ``"bin"``).

    Returns:
        List of validated ``{"a", "b", "base"}`` records.

    Raises:
        OperandFileError: On invalid JSON syntax or schema violations.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise OperandFileError(
            f"invalid JSON at column {exc.colno}: {exc.msg}",
            line=exc.lineno,
        ) from exc

    if isinstance(data, dict) and "pairs" in data:
        default_base = _normalize_base(data.get("base", default_base))
        data = data["pairs"]
        if not isinstance(data, list):
            raise OperandFileError("'pairs' must be a JSON array")
    elif isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise OperandFileError("expected an object or an array of operand pairs")
    return [_validate_pair(item, default_base, i) for i, item in enumerate(data, 1)]


def _parse_text(content: str, default_base: str) -> list[dict[str, str]]:
    """Parse labeled ``A``/``B``/``base`` plain-text blocks separated by ``---`` or ``===``.

    Args:
        content: Raw text file contents.
        default_base: Normalized fallback base (``"hex"`` or ``"bin"``).

    Returns:
        List of validated ``{"a", "b", "base"}`` records.

    Raises:
        OperandFileError: On unrecognized labels, duplicate labels within a block,
            or malformed operand values.
    """
    pairs: list[dict[str, str]] = []
    item: dict[str, str] = {}
    lines: dict[str, int] = {}
    labels = {"a": "a", "a(x)": "a", "b": "b", "b(x)": "b", "base": "base"}
    base = default_base

    for number, raw_line in enumerate(content.splitlines(), 1):
        # Strip inline '#' comments and outer whitespace.
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line in ("---", "==="):
            if item:
                pairs.append(_validate_pair(item, base, len(pairs) + 1, lines))
            item, lines = {}, {}
            continue

        key, separator, value = line.partition(":" if ":" in line else "=")
        field = labels.get(key.strip().lower())
        if not separator or field is None:
            raise OperandFileError("expected an A, B, or base label", line=number)
        if field in lines:
            raise OperandFileError(
                "duplicate label. Separate pairs with ---",
                line=number,
                field=field,
            )
        lines[field] = number
        if field == "base":
            base = _normalize_base(value, line=number)
        else:
            item[field] = value

    if item:
        pairs.append(_validate_pair(item, base, len(pairs) + 1, lines))
    return pairs


def parse_operand_file(
    content: str,
    filename: str = "",
    default_base: str = "hex",
) -> list[dict[str, str]]:
    """Parse uploaded ``.txt`` or ``.json`` content into validated operand pairs.

    Auto-detects JSON from a ``.json`` extension or leading ``{``/``[`` when
    the filename does not end in ``.txt``, and strips UTF-8 BOMs cleanly.

    Args:
        content: Raw UTF-8 text of the uploaded file.
        filename: Original filename used to infer format (optional).
        default_base: Fallback base when omitted in the file (``"hex"`` or ``"bin"``).

    Returns:
        Non-empty list of ``{"a": str, "b": str, "base": "hex" | "bin"}`` dicts.

    Raises:
        OperandFileError: On empty input, malformed syntax, invalid digits, or
            zero parsed pairs.

    Complexity:
        Time ``O(N)``, space ``O(N)`` in the character length ``N = len(content)``.
    """
    if not isinstance(content, str):
        raise OperandFileError("operand file contents must be text")
    content = content.removeprefix("\ufeff")
    if not content.strip():
        raise OperandFileError("empty operand file")
    base = _normalize_base(default_base)
    is_json = filename.lower().endswith(".json") or (
        not filename.lower().endswith(".txt") and content.lstrip().startswith(("{", "["))
    )
    pairs = _parse_json(content, base) if is_json else _parse_text(content, base)
    if not pairs:
        raise OperandFileError("no operand pairs found in file")
    return pairs

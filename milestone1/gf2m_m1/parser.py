"""Parse student-authored TXT or JSON files into validated operand pairs."""

import json

from .polyrepr import BIN_TO_INT, HEX_TO_INT


class OperandFileError(ValueError):
    """An upload error with the applicable pair, line, and operand field."""

    def __init__(
        self,
        message: str,
        *,
        pair: int | None = None,
        line: int | None = None,
        field: str | None = None,
    ) -> None:
        """Attach structured location information to a readable error."""
        self.pair = pair
        self.line = line
        self.field = field
        location = []
        if pair is not None:
            location.append(f"pair {pair}")
        if line is not None:
            location.append(f"line {line}")
        if field is not None:
            location.append(field)
        super().__init__(f"{', '.join(location)}: {message}" if location else message)


def _normalize_base(base: str, *, pair: int | None = None, line: int | None = None) -> str:
    """Normalize the accepted base names to the API's hex and bin values."""
    if isinstance(base, str):
        normalized = base.strip().lower()
        if normalized == "hex":
            return normalized
        if normalized in ("bin", "binary"):
            return "bin"
    raise OperandFileError("base must be hex or bin", pair=pair, line=line, field="base")


def _validate_pair(
    item: dict, fallback_base: str, pair: int, lines: dict[str, int] | None = None
) -> dict[str, str]:
    """Validate one pair and remove grouping spaces for the strict API parser."""
    if not isinstance(item, dict):
        raise OperandFileError("expected an operand object", pair=pair)
    lines = lines or {}
    base = _normalize_base(item.get("base", fallback_base), pair=pair, line=lines.get("base"))
    parse = HEX_TO_INT if base == "hex" else BIN_TO_INT
    result = {"base": base}
    for field in ("a", "b"):
        value = item.get(field, "")
        if not isinstance(value, str) or (field == "a" and not value.strip()):
            raise OperandFileError("expected an operand string", pair=pair,
                                   line=lines.get(field), field=field)
        if value.strip():
            try:
                parse(value)
            except ValueError as exc:
                raise OperandFileError(str(exc), pair=pair, line=lines.get(field),
                                       field=field) from exc
        result[field] = "".join(value.split())
    return result


def _parse_json(content: str, default_base: str) -> list[dict[str, str]]:
    """Load a bare list, a single pair, or an object with a pairs array."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise OperandFileError(f"invalid JSON at column {exc.colno}: {exc.msg}",
                               line=exc.lineno) from exc

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
    """Read labeled A/B blocks separated by --- or ===, with optional comments."""
    pairs = []
    item: dict[str, str] = {}
    lines: dict[str, int] = {}
    labels = {"a": "a", "a(x)": "a", "b": "b", "b(x)": "b", "base": "base"}
    base = default_base

    for number, raw_line in enumerate(content.splitlines(), 1):
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
            raise OperandFileError("duplicate label. Separate pairs with ---",
                                   line=number, field=field)
        lines[field] = number
        if field == "base":
            base = _normalize_base(value, line=number)
        else:
            item[field] = value

    if item:
        pairs.append(_validate_pair(item, base, len(pairs) + 1, lines))
    return pairs


def parse_operand_file(
    content: str, filename: str = "", default_base: str = "hex"
) -> list[dict[str, str]]:
    """Return validated A/B/base records or raise OperandFileError.

    Operand B may be absent for unary operations, as in Milestone 2's
    upload contract. Parsing is linear in the number of input characters.
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

"""Bitmask conversion for polynomial-basis arithmetic (Stallings Ch. 4 and 5)."""

from dataclasses import asdict, dataclass

_BINARY_DIGITS = frozenset("01")
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


def validate_non_negative_poly(value: int, name: str = "polynomial") -> None:
    """Require an integer bitmask greater than or equal to zero."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer bitmask")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def DEG(poly_int: int) -> int:
    """Return the highest set-bit index (O(1)), or -1 for zero."""
    validate_non_negative_poly(poly_int)
    return poly_int.bit_length() - 1


def HAMMING_WEIGHT(poly_int: int) -> int:
    """Count the nonzero coefficients, scanning the integer's machine words."""
    validate_non_negative_poly(poly_int)
    return poly_int.bit_count()


def _parse(text: str, base: str, *, grouped: bool) -> int:
    """Read one bit string or hex string in O(len(text)) time."""
    if not isinstance(text, str):
        raise ValueError("operand must be a string")

    if base in ("bin", "binary"):
        digits, prefix, radix, name = _BINARY_DIGITS, "0b", 2, "binary"
    elif base == "hex":
        digits, prefix, radix, name = _HEX_DIGITS, "0x", 16, "hexadecimal"
    else:
        raise ValueError(f"unsupported base: {base!r}")

    cleaned = text.strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        cleaned = cleaned[1:-1].strip()
    if cleaned[:2].lower() == prefix:
        cleaned = cleaned[2:]
    if grouped:
        cleaned = "".join(cleaned.split())
    if not cleaned or not digits.issuperset(cleaned):
        raise ValueError(f"invalid {name} polynomial operand: {text!r}")
    return int(cleaned, radix)


def BIN_TO_INT(text: str) -> int:
    """Parse binary digits with optional spacing and a 0b prefix."""
    return _parse(text, "bin", grouped=True)


def HEX_TO_INT(text: str) -> int:
    """Parse hex digits with optional spacing, braces, and a 0x prefix."""
    return _parse(text, "hex", grouped=True)


def parse_value(text: str, base: str) -> int:
    """Read a single operand using the current API's strict digit validation."""
    return _parse(text, base, grouped=False)


def _validate_width(m: int) -> None:
    """Require a positive integer display width in bits."""
    if type(m) is not int or m < 1:
        raise ValueError("display width must be a positive integer")


def INT_TO_BIN(poly_int: int, m: int) -> str:
    """Display the bitmask with at least m digits, retaining any overflow bits."""
    validate_non_negative_poly(poly_int)
    _validate_width(m)
    return format(poly_int, f"0{m}b")


def INT_TO_HEX(poly_int: int, m: int) -> str:
    """Display uppercase hex padded to at least ceil(m / 4) digits."""
    validate_non_negative_poly(poly_int)
    _validate_width(m)
    return format(poly_int, f"0{(m + 3) // 4}X")


def INT_TO_ALGEBRAIC(poly_int: int) -> str:
    """Render set bits as descending powers of x, with 0 for the zero polynomial."""
    exponent = DEG(poly_int)
    if exponent < 0:
        return "0"
    terms = []
    for offset, bit in enumerate(format(poly_int, "b")):
        if bit == "0":
            continue
        power = exponent - offset
        if power > 1:
            terms.append(f"x^{power}")
        else:
            terms.append("x" if power == 1 else "1")
    return " + ".join(terms)


def to_hex(value: int, m: int) -> str:
    """Format lowercase hex for the existing Milestone 2 representation."""
    return INT_TO_HEX(value, m).lower()


degree = DEG
hamming_weight = HAMMING_WEIGHT
to_bin = INT_TO_BIN
to_poly = INT_TO_ALGEBRAIC


@dataclass(frozen=True)
class ElementRepr:
    """Display forms and metrics consumed by Milestone 2."""

    hex: str
    bin: str
    poly: str
    degree: int
    bit_length: int
    hamming_weight: int

    @classmethod
    def from_int(cls, value: int, m: int) -> "ElementRepr":
        """Build the representations at the given minimum bit width."""
        return cls(
            hex=to_hex(value, m),
            bin=to_bin(value, m),
            poly=to_poly(value),
            degree=DEG(value),
            bit_length=value.bit_length(),
            hamming_weight=HAMMING_WEIGHT(value),
        )

    def dict(self) -> dict:
        """Return the display fields and metrics as a plain mapping."""
        return asdict(self)

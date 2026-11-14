"""Binary-field element representations and base conversion.

Shared, framework-agnostic helpers for turning GF(2^m) elements (stored as
Python integers, one bit per polynomial coefficient: bit *i* == coefficient of
x^i) into the hexadecimal / binary / algebraic forms the API and GUI display.

Integration note
----------------
Milestone 1 owns the authoritative multi-base converters (``ALGEBRAIC_TO_INT``
and friends). The functions here are a small, self-contained reference so that
Milestone 2 (multiplication engine + backend) runs and is graded standalone.
They are pure functions over ``int`` and can be swapped for M1's converters on
merge without touching the multiplication engine or the API layer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


def degree(value: int) -> int:
    """Polynomial degree of ``value``; the zero polynomial has degree -1."""
    return value.bit_length() - 1


def hamming_weight(value: int) -> int:
    """Number of non-zero coefficients (set bits)."""
    return bin(value).count("1")


def to_hex(value: int, m: int) -> str:
    """Zero-padded, lowercase hex wide enough to hold an m-bit element."""
    nibbles = max(1, (m + 3) // 4)
    return format(value, f"0{nibbles}x")


def to_bin(value: int, m: int) -> str:
    """Zero-padded binary string of exactly ``m`` bits (MSB first)."""
    return format(value, f"0{m}b")


def to_poly(value: int) -> str:
    """Human-readable algebraic form, e.g. ``x^5 + x^2 + 1``."""
    if value == 0:
        return "0"
    terms = []
    for i in range(value.bit_length() - 1, -1, -1):
        if (value >> i) & 1:
            if i == 0:
                terms.append("1")
            elif i == 1:
                terms.append("x")
            else:
                terms.append(f"x^{i}")
    return " + ".join(terms)


def parse_value(text: str, base: str) -> int:
    """Parse a single operand string in ``hex`` or ``bin`` into an int.

    Tolerates surrounding whitespace, embedded spaces, and ``0x`` / ``0b``
    prefixes. Raises ``ValueError`` on an empty or malformed operand.
    """
    cleaned = text.strip().replace(" ", "").replace("_", "")
    if cleaned == "":
        raise ValueError("empty operand")
    if base == "hex":
        if cleaned.lower().startswith("0x"):
            cleaned = cleaned[2:]
        return int(cleaned, 16)
    if base == "bin":
        if cleaned.lower().startswith("0b"):
            cleaned = cleaned[2:]
        return int(cleaned, 2)
    raise ValueError(f"unsupported base: {base!r}")


@dataclass
class ElementRepr:
    """All display forms of one field element, computed once."""

    hex: str
    bin: str
    poly: str
    degree: int
    bit_length: int
    hamming_weight: int

    @classmethod
    def from_int(cls, value: int, m: int) -> "ElementRepr":
        return cls(
            hex=to_hex(value, m),
            bin=to_bin(value, m),
            poly=to_poly(value),
            degree=degree(value),
            bit_length=value.bit_length(),
            hamming_weight=hamming_weight(value),
        )

    def dict(self) -> dict:
        return asdict(self)

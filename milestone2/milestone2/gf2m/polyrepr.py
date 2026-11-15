"""Binary-field element representations and base conversion.

Shared, framework-agnostic helpers for turning GF(2^m) elements (stored as
Python integers, one bit per polynomial coefficient: bit *i* == coefficient of
x^i) into the hexadecimal / binary / algebraic forms the API and GUI display.

Course references
-----------------
* **Stallings Chapter 4 (Finite Fields):** Polynomial-basis bit-string encoding
  over Z_2[x]/m(x).
* **Stallings Chapter 5 (AES):** Byte-level GF(2^8) hex notation (e.g. ``{57}``).
* **Stallings Chapter 6 (Block Cipher Operation):** XTS-AES arithmetic over
  GF(2^128).
* **Stallings Chapter 10 (ECC):** Binary curve elements over GF(2^163) through
  GF(2^571).

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

_HEX_CHARS = frozenset("0123456789abcdefABCDEF")
_BIN_CHARS = frozenset("01")


def degree(value: int) -> int:
    """Polynomial degree of ``value``; the zero polynomial has degree -1.

    Time complexity: O(1) (bit-length inspection on Python ``int``).
    Space complexity: O(1).
    Ref: Stallings Ch. 4 (polynomial degree over GF(2)).
    """
    return value.bit_length() - 1


def hamming_weight(value: int) -> int:
    """Number of non-zero coefficients (set bits).

    Time complexity: O(m) over an m-bit field element.
    Space complexity: O(m) for binary string conversion.
    Ref: Stallings Ch. 4 & Ch. 10 (sparse polynomial weight metrics).
    """
    return bin(value).count("1")


def to_hex(value: int, m: int) -> str:
    """Zero-padded, lowercase hex wide enough to hold an m-bit element.

    Time & space complexity: O(m) (produces ceil(m / 4) hex digits).
    Ref: Stallings Ch. 4 & Ch. 5 (AES byte hex format) and Ch. 10 (ECC).
    """
    nibbles = max(1, (m + 3) // 4)
    return format(value, f"0{nibbles}x")


def to_bin(value: int, m: int) -> str:
    """Zero-padded binary string of exactly ``m`` bits (MSB first).

    Time & space complexity: O(m).
    Ref: Stallings Ch. 4 (m-bit polynomial representation) & Ch. 6 (XTS-AES).
    """
    return format(value, f"0{m}b")


def to_poly(value: int) -> str:
    """Human-readable algebraic form, e.g. ``x^5 + x^2 + 1``.

    Time & space complexity: O(m) bit inspections and term strings.
    Ref: Stallings Ch. 4, Ch. 5, Ch. 6, and Ch. 10 polynomial notation.
    """
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
    """Parse a single non-negative operand string in ``hex`` or ``bin`` into an int.

    Strips outer whitespace and matching outer ``{...}`` braces (Stallings Ch. 5
    notation such as ``{57}``), strips a single optional ``0x``/``0b`` prefix,
    and validates that every remaining character is a strict digit of ``base``
    (rejecting ``-``, ``+``, embedded spaces, and underscores with ``ValueError``).

    Time & space complexity: O(n) in input string length n.
    Ref: Stallings Ch. 4, Ch. 5 (``{byte}`` notation), Ch. 6, and Ch. 10.
    """
    if not isinstance(text, str):
        raise ValueError("operand must be a string")

    cleaned = text.strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        cleaned = cleaned[1:-1].strip()

    if base == "hex":
        if cleaned.startswith(("0x", "0X")):
            cleaned = cleaned[2:]
        if not cleaned or any(ch not in _HEX_CHARS for ch in cleaned):
            raise ValueError(f"invalid hexadecimal polynomial operand: {text!r}")
        value = int(cleaned, 16)
    elif base == "bin":
        if cleaned.startswith(("0b", "0B")):
            cleaned = cleaned[2:]
        if not cleaned or any(ch not in _BIN_CHARS for ch in cleaned):
            raise ValueError(f"invalid binary polynomial operand: {text!r}")
        value = int(cleaned, 2)
    else:
        raise ValueError(f"unsupported base: {base!r}")

    assert value >= 0
    return value


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

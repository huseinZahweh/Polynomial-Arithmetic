"""Unified binary-field polynomial representation, validation, and base conversion.

Original Authors
----------------
* Hussein Abbas — Milestone 1 (Multi-base I/O converters & bitmask metrics).
* Hassan Tarhini — Milestone 2 (Strict API operand parser & ``ElementRepr`` contract).
* Husein Zahweh — Milestone 3 (Modulus validation & Table 4.7 cell formatter).
* Ali Zahreddine — Milestone 4 & Integration (Stretch ``ALGEBRAIC_TO_INT`` parser).

Purpose & Course References
---------------------------
Converts polynomial-basis elements of ``GF(2^m)``—stored internally as non-negative
Python ``int`` bitmasks where bit ``i`` (LSB = 0) equals the coefficient of ``x^i``
in ``Z_2 = {0, 1}``—between Binary, Hexadecimal, and Algebraic notations without
precision loss up to ``m = 571`` (and beyond):

* **Stallings Chapter 4 (Finite Fields):** Polynomial-basis bit-string encoding
  over ``Z_2[x] / <m(x)>``, polynomial degree, and term notation.
* **Stallings Chapter 5 (AES):** Byte-level ``GF(2^8)`` braced hex notation
  such as ``{57}`` and ``{11B}``.
* **Stallings Chapter 6 (Block Cipher Operation):** Binary polynomial encoding
  for XTS-AES tweaks over ``GF(2^128)``.
* **Stallings Chapter 10 (Elliptic Curve Cryptography):** Padded multi-word hex
  and binary encodings for binary curves ``GF(2^163)`` through ``GF(2^571)``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

_BINARY_DIGITS = frozenset("01")
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")

# Maximum operand bit width shared across calculator and batch file uploads.
MAX_INPUT_BITS = 4096
_MAX_ALGEBRAIC_EXPONENT = MAX_INPUT_BITS


def validate_input_width(value: int) -> int:
    """Apply the shared 4096-bit operand limit to calculator and batch inputs.

    Args:
        value: Candidate polynomial bitmask.

    Returns:
        Validated non-negative integer ``value``.

    Raises:
        TypeError: If ``value`` is not an integer bitmask.
        ValueError: If ``value < 0`` or ``value.bit_length() > MAX_INPUT_BITS``.
    """
    validate_non_negative_poly(value)
    if value.bit_length() > MAX_INPUT_BITS:
        raise ValueError(f"polynomials may have at most {MAX_INPUT_BITS} bits")
    return value


def validate_non_negative_poly(value: int, name: str = "polynomial") -> int:
    """Validate that ``value`` is a non-negative Python ``int`` bitmask.

    Rejects booleans explicitly because ``isinstance(True, int)`` is ``True`` in
    Python, preventing accidental coercion of flags into polynomial bitmasks.

    Args:
        value: Candidate polynomial bitmask.
        name: Parameter name included in diagnostic messages.

    Returns:
        The validated non-negative integer ``value``.

    Raises:
        TypeError: If ``value`` is a ``bool`` or not an ``int``.
        ValueError: If ``value < 0``.

    Complexity:
        Time ``O(1)``, space ``O(1)``.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer bitmask")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def validate_modulus(m_poly_int: int, m_degree: int) -> tuple[int, int]:
    """Validate a reduction polynomial ``m(x)`` and its expected degree ``m``.

    Ensures ``m_degree >= 1`` and ``deg(m_poly_int) == m_degree`` so bit
    ``m_degree`` (the leading ``x^m`` term) is explicitly set to ``1``.

    Args:
        m_poly_int: Reduction polynomial bitmask including bit ``m_degree``.
        m_degree: Extension field degree ``m >= 1``.

    Returns:
        Tuple ``(m_poly_int, m_degree)`` after validation.

    Raises:
        TypeError: If ``m_degree`` or ``m_poly_int`` is not an ``int`` (or is ``bool``).
        ValueError: If ``m_degree < 1``, ``m_poly_int < 0``, or
            ``DEG(m_poly_int) != m_degree``.

    Complexity:
        Time ``O(1)``, space ``O(1)``.
    """
    if isinstance(m_degree, bool) or not isinstance(m_degree, int):
        raise TypeError(f"m_degree must be a positive int, got {type(m_degree).__name__}")
    if m_degree < 1:
        raise ValueError("m_degree must be a positive integer")
    validate_non_negative_poly(m_poly_int, name="m_poly_int")
    actual_deg = m_poly_int.bit_length() - 1
    if actual_deg != m_degree:
        raise ValueError(
            f"m_poly_int must have degree equal to m_degree={m_degree}, got degree {actual_deg}"
        )
    return m_poly_int, m_degree


def DEG(poly_int: int) -> int:
    """Return the polynomial degree of ``poly_int`` over ``GF(2)``.

    Args:
        poly_int: Non-negative polynomial bitmask.

    Returns:
        Highest set-bit index ``>= 0`` for nonzero polynomials, or ``-1`` for
        the zero polynomial ``0`` (standard algebraic convention).

    Raises:
        TypeError: If ``poly_int`` is not an ``int`` (or is a ``bool``).
        ValueError: If ``poly_int < 0``.

    Complexity:
        Time ``O(1)`` (CPython ``int.bit_length()``), space ``O(1)``.
    """
    validate_non_negative_poly(poly_int)
    return poly_int.bit_length() - 1


def HAMMING_WEIGHT(poly_int: int) -> int:
    """Count the nonzero polynomial terms (set bits) in ``poly_int``.

    Args:
        poly_int: Non-negative polynomial bitmask.

    Returns:
        Integer count of ``1`` bits in the binary expansion of ``poly_int``.

    Raises:
        TypeError: If ``poly_int`` is not an ``int`` (or is a ``bool``).
        ValueError: If ``poly_int < 0``.

    Complexity:
        Time ``O(m / w)`` where ``w`` is machine word size (``int.bit_count()``),
        space ``O(1)``.
    """
    validate_non_negative_poly(poly_int)
    return poly_int.bit_count()


def _parse(text: str, base: str, *, grouped: bool) -> int:
    """Parse a binary or hexadecimal operand string into a non-negative integer.

    Strips outer whitespace, optional matching Stallings Ch. 5 braces ``{...}``,
    and a single optional ``0b``/``0x`` prefix. Strictly rejects signed ``+/-``
    prefixes, underscores, non-ASCII digits, and empty payloads.

    Args:
        text: Raw operand string supplied by a user or file.
        base: One of ``"bin"``, ``"binary"``, or ``"hex"``.
        grouped: When ``True``, allows internal whitespace digit grouping
            (used by ``BIN_TO_INT`` / ``HEX_TO_INT`` and batch files); when
            ``False``, rejects embedded spaces (strict REST API contract).

    Returns:
        Non-negative integer bitmask.

    Raises:
        ValueError: If ``text`` is not a string, ``base`` is unsupported, or
            any character is not a valid digit in ``base``.

    Complexity:
        Time ``O(n)``, space ``O(n)`` where ``n = len(text)``.
    """
    if not isinstance(text, str):
        raise ValueError("operand must be a string")

    if base in ("bin", "binary"):
        digits, prefix, radix, name = _BINARY_DIGITS, "0b", 2, "binary"
    elif base == "hex":
        digits, prefix, radix, name = _HEX_DIGITS, "0x", 16, "hexadecimal"
    else:
        raise ValueError(f"unsupported base: {base!r}")

    cleaned = text.strip()
    # Support Stallings Ch. 5 braced byte notation such as "{57}" or "{0x11B}".
    if cleaned.startswith("{") and cleaned.endswith("}"):
        cleaned = cleaned[1:-1].strip()
    if cleaned[:2].lower() == prefix:
        cleaned = cleaned[2:]
    if grouped:
        cleaned = "".join(cleaned.split())
    # Strict character check rejects +/- signs, underscores, fullwidth digits, etc.
    if not cleaned or not digits.issuperset(cleaned):
        raise ValueError(f"invalid {name} polynomial operand: {text!r}")
    return int(cleaned, radix)


def BIN_TO_INT(text: str) -> int:
    """Parse a binary polynomial string (optional spaces, braces, ``0b``) into ``int``.

    Args:
        text: Binary string containing ``'0'`` and ``'1'`` digits.

    Returns:
        Non-negative integer bitmask.

    Raises:
        ValueError: On malformed, signed, empty, or non-string input.

    Complexity:
        Time ``O(n)``, space ``O(n)`` for input length ``n``.
    """
    return _parse(text, "bin", grouped=True)


def HEX_TO_INT(text: str) -> int:
    """Parse a hexadecimal polynomial string (optional spaces, ``{...}``, ``0x``) into ``int``.

    Args:
        text: Hexadecimal string containing ``0-9`` and ``A-F``/``a-f``.

    Returns:
        Non-negative integer bitmask.

    Raises:
        ValueError: On malformed, signed, empty, or non-string input.

    Complexity:
        Time ``O(n)``, space ``O(n)`` for input length ``n``.
    """
    return _parse(text, "hex", grouped=True)


def ALGEBRAIC_TO_INT(text: str) -> int:
    """Parse an algebraic sum of binary monomials (e.g. ``x^7 + x + 1``) into ``int``.

    Duplicate terms cancel automatically modulo 2 via XOR (characteristic 2:
    ``x^k + x^k = 0``). Exponents are capped below ``4096`` to guard against
    denial-of-service bit shifts.

    Args:
        text: Sum of monomial terms separated by ``+``, where each term is
            ``0``, ``1``, ``x``, or ``x^k`` (case-insensitive).

    Returns:
        Non-negative integer bitmask of the reduced modulo-2 sum.

    Raises:
        ValueError: If ``text`` is not a string, contains an invalid monomial,
            or uses an exponent ``>= 4096``.

    Complexity:
        Time ``O(n + E_max / w)``, space ``O(n + E_max / w)`` where ``n = len(text)``
        and ``E_max`` is the largest exponent.
    """
    if not isinstance(text, str):
        raise ValueError("operand must be a string")
    value = 0
    for raw_term in text.split("+"):
        term = raw_term.strip().lower()
        if term == "0":
            continue
        if term == "1":
            exponent = 0
        elif term == "x":
            exponent = 1
        else:
            match = re.fullmatch(r"x\s*\^\s*([0-9]{1,4})", term)
            if match is None:
                raise ValueError(f"invalid polynomial term: {term!r}; use x^7 + x + 1")
            exponent = int(match[1])
        if exponent >= _MAX_ALGEBRAIC_EXPONENT:
            raise ValueError(f"polynomial exponents must be below {_MAX_ALGEBRAIC_EXPONENT}")
        # In GF(2), repeating a term cancels it: x^k + x^k = 0.
        value ^= 1 << exponent
    return value


def parse_value(text: str, base: str) -> int:
    """Parse one operand using the strict REST API validation contract.

    Supports ``"hex"``, ``"bin"``, ``"binary"``, and ``"algebraic"``. For
    ``"hex"`` and ``"bin"``/``"binary"``, embedded spaces, underscores, and
    leading signs (``+``/``-``) are rejected while outer braces ``{...}`` and
    a single ``0x``/``0b`` prefix are accepted.

    Args:
        text: Raw operand string from an API request.
        base: Input notation (``"hex"``, ``"bin"``, ``"binary"``, or ``"algebraic"``).

    Returns:
        Non-negative integer bitmask.

    Raises:
        ValueError: If ``text`` or ``base`` is invalid.

    Complexity:
        Time ``O(n)``, space ``O(n)`` in ``len(text)``.
    """
    if base == "algebraic":
        return ALGEBRAIC_TO_INT(text)
    return _parse(text, base, grouped=False)


def _validate_width(m: int) -> None:
    """Ensure minimum display width ``m`` is a strictly positive integer."""
    if type(m) is not int or m < 1:
        raise ValueError("display width must be a positive integer")


def INT_TO_BIN(poly_int: int, m: int) -> str:
    """Format ``poly_int`` as a zero-padded MSB-first binary string of width ``>= m``.

    Values with ``deg(poly_int) >= m`` (such as ``m(x)`` itself) expand naturally
    without truncating high-order bits.

    Args:
        poly_int: Non-negative polynomial bitmask.
        m: Minimum output bit width (positive ``int``).

    Returns:
        Binary string of ``'0'`` and ``'1'`` characters.

    Raises:
        TypeError: If ``poly_int`` is not an ``int`` (or is ``bool``).
        ValueError: If ``poly_int < 0`` or ``m < 1``.

    Complexity:
        Time ``O(max(m, bit_length))``, space ``O(max(m, bit_length))``.
    """
    validate_non_negative_poly(poly_int)
    _validate_width(m)
    return format(poly_int, f"0{m}b")


def INT_TO_HEX(poly_int: int, m: int) -> str:
    """Format ``poly_int`` as uppercase hex padded to at least ``ceil(m / 4)`` digits.

    Unreduced polynomials with ``bit_length > m`` expand naturally without truncation.

    Args:
        poly_int: Non-negative polynomial bitmask.
        m: Minimum element bit width used to compute nibble padding ``(m + 3) // 4``.

    Returns:
        Uppercase hexadecimal string without ``0x`` prefix (e.g. ``"D4"`` for ``m=8``,
        41 hex digits for ``m=163``, 143 hex digits for ``m=571``).

    Raises:
        TypeError: If ``poly_int`` is not an ``int`` (or is ``bool``).
        ValueError: If ``poly_int < 0`` or ``m < 1``.

    Complexity:
        Time ``O(max(m, bit_length))``, space ``O(max(m, bit_length))``.
    """
    validate_non_negative_poly(poly_int)
    _validate_width(m)
    return format(poly_int, f"0{(m + 3) // 4}X")


def INT_TO_ALGEBRAIC(poly_int: int) -> str:
    """Render set bits of ``poly_int`` as descending powers of ``x``.

    Formats ``k > 1`` as ``"x^k"``, ``k == 1`` as ``"x"``, ``k == 0`` as ``"1"``,
    and the zero polynomial as ``"0"``.

    Args:
        poly_int: Non-negative polynomial bitmask.

    Returns:
        Human-readable algebraic string, e.g. ``"x^6 + x^4 + x^2 + x + 1"``.

    Raises:
        TypeError: If ``poly_int`` is not an ``int`` (or is ``bool``).
        ValueError: If ``poly_int < 0``.

    Complexity:
        Time ``O(deg(poly_int))``, space ``O(wt(poly_int))``.
    """
    exponent = DEG(poly_int)
    if exponent < 0:
        return "0"
    terms: list[str] = []
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
    """Format lowercase hex padded to ``ceil(m / 4)`` digits (REST API convention).

    Args:
        value: Non-negative polynomial bitmask.
        m: Minimum bit width.

    Returns:
        Lowercase hexadecimal string without ``0x`` prefix.

    Complexity:
        Time ``O(max(m, bit_length))``, space ``O(max(m, bit_length))``.
    """
    return INT_TO_HEX(value, m).lower()


def format_poly_representations(
    value_int: int,
    m_degree: int,
    *,
    uppercase_hex: bool = True,
) -> dict[str, Any]:
    """Build multi-notation cell dictionary used by Table 4.7 and verification traces.

    Pre-computing all three notations server-side allows the frontend to switch
    Table 4.7 cells between Hex, Binary, and Algebraic without BigInt recomputation.

    Args:
        value_int: Non-negative polynomial bitmask.
        m_degree: Extension field degree used for zero-padding hex and binary strings.
        uppercase_hex: Emit uppercase hex when ``True`` (default), lowercase otherwise.

    Returns:
        Dictionary ``{"int", "hex", "bin", "algebraic", "degree"}``.

    Raises:
        TypeError: If ``value_int`` is not an ``int`` (or is ``bool``).
        ValueError: If ``value_int < 0`` or ``m_degree < 1``.

    Complexity:
        Time ``O(max(m_degree, bit_length))``, space ``O(max(m_degree, bit_length))``.
    """
    validate_non_negative_poly(value_int, name="value_int")
    hex_str = INT_TO_HEX(value_int, m_degree) if uppercase_hex else to_hex(value_int, m_degree)
    return {
        "int": value_int,
        "hex": hex_str,
        "bin": INT_TO_BIN(value_int, m_degree),
        "algebraic": INT_TO_ALGEBRAIC(value_int),
        "degree": DEG(value_int),
    }


# Lowercase aliases preserved for clean cross-module readability and API compatibility.
deg = DEG
degree = DEG
hamming_weight = HAMMING_WEIGHT
to_bin = INT_TO_BIN
to_poly = INT_TO_ALGEBRAIC


@dataclass(frozen=True)
class ElementRepr:
    """All display representations and structural metrics for one ``GF(2^m)`` element.

    Attributes:
        hex: Lowercase zero-padded hexadecimal string.
        bin: Zero-padded MSB-first binary string of width ``>= m``.
        poly: Descending algebraic polynomial string.
        degree: Highest set-bit index (``-1`` for ``0``).
        bit_length: Number of bits required to represent the integer (``0`` for ``0``).
        hamming_weight: Number of nonzero terms (set bits).
    """

    hex: str
    bin: str
    poly: str
    degree: int
    bit_length: int
    hamming_weight: int

    @classmethod
    def from_int(cls, value: int, m: int) -> ElementRepr:
        """Construct an :class:`ElementRepr` from bitmask ``value`` at bit width ``m``.

        Args:
            value: Non-negative polynomial bitmask.
            m: Minimum display bit width.

        Returns:
            Immutable :class:`ElementRepr` instance.

        Complexity:
            Time ``O(max(m, bit_length))``, space ``O(max(m, bit_length))``.
        """
        return cls(
            hex=to_hex(value, m),
            bin=to_bin(value, m),
            poly=to_poly(value),
            degree=DEG(value),
            bit_length=value.bit_length(),
            hamming_weight=HAMMING_WEIGHT(value),
        )

    def dict(self) -> dict[str, Any]:
        """Serialize display representations and metrics into a plain dictionary.

        Returns:
            Dictionary matching the REST API ``ElementReprModel`` schema.
        """
        return asdict(self)

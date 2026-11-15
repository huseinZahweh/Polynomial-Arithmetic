"""Isolated Milestone 1 reference utilities for Milestone 3.

Provides degree calculation, Hamming weight, modulo reduction ``MOD_REDUCE``,
input validation for non-negative polynomial bit-strings, and lossless
Binary / Hexadecimal / Algebraic conversions strictly matching
``Plan/Milestones/01_field_config_io_additive_mod_and_utilities.md`` and
``Plan/README.md``.

Polynomial Representation Contract
----------------------------------
Every polynomial over GF(2) is represented as a non-negative Python ``int``
where bit ``i`` (LSB = 0) holds the coefficient of ``x^i`` in {0, 1}. The
reduction polynomial ``m_poly_int`` of degree ``m_degree`` includes bit
``m_degree`` set to 1 (e.g., AES ``x^8 + x^4 + x^3 + x + 1`` <-> ``0x11B`` = 283).

References
----------
* Stallings, *Cryptography and Network Security*, Chapter 4 (Finite Fields):
  polynomial arithmetic over Z_2 and modular reduction ``f(x) mod m(x)``.
* Stallings Chapter 5 (AES), Chapter 6 (XTS-AES over GF(2^128)), and
  Chapter 10 (Binary ECC over GF(2^163) ... GF(2^571)).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def validate_non_negative_poly(value_int: int, name: str = "polynomial") -> int:
    """Validate that ``value_int`` is a non-negative Python ``int``.

    Args:
        value_int: Candidate polynomial encoded as a bit-string integer.
        name: Descriptive parameter name used in error messages.

    Returns:
        The validated non-negative ``int``.

    Raises:
        TypeError: If ``value_int`` is a ``bool`` or not an ``int``.
        ValueError: If ``value_int`` is negative.

    Complexity:
        O(1).
    """
    if isinstance(value_int, bool) or not isinstance(value_int, int):
        raise TypeError(
            f"{name} must be a non-negative Python int, got {type(value_int).__name__}."
        )
    if value_int < 0:
        raise ValueError(
            f"{name} must be a non-negative integer (got {value_int})."
        )
    return value_int


def validate_modulus(m_poly_int: int, m_degree: int) -> Tuple[int, int]:
    """Validate reduction polynomial ``m_poly_int`` and degree ``m_degree``.

    Ensures ``m_degree >= 1``, ``m_poly_int > 0``, and ``deg(m_poly_int) == m_degree``
    so bit ``m_degree`` is explicitly set to 1 per the shared contract.

    Args:
        m_poly_int: Reduction polynomial integer (including bit ``m_degree``).
        m_degree: Expected degree ``m >= 1`` of the field extension GF(2^m).

    Returns:
        Tuple ``(m_poly_int, m_degree)``.

    Raises:
        TypeError: If arguments are not integers (or are booleans).
        ValueError: If ``m_degree < 1``, ``m_poly_int <= 0``, or
            ``deg(m_poly_int) != m_degree``.

    Complexity:
        O(1).
    """
    if isinstance(m_degree, bool) or not isinstance(m_degree, int):
        raise TypeError(
            f"m_degree must be a positive int, got {type(m_degree).__name__}."
        )
    if m_degree < 1:
        raise ValueError(f"m_degree must be >= 1 (got {m_degree}).")

    validate_non_negative_poly(m_poly_int, name="m_poly_int")
    actual_deg = deg(m_poly_int)
    if actual_deg != m_degree:
        raise ValueError(
            f"m_poly_int must have degree exactly equal to m_degree={m_degree} "
            f"(with bit {m_degree} set to 1), got degree {actual_deg}."
        )
    return m_poly_int, m_degree


def deg(value_int: int) -> int:
    """Return the polynomial degree of ``value_int`` over GF(2).

    Returns ``value_int.bit_length() - 1`` for non-zero polynomials, and ``-1``
    for the zero polynomial ``0``.

    Args:
        value_int: Non-negative integer representing a polynomial in GF(2)[x].

    Returns:
        Integer degree ``>= 0`` for ``value_int > 0``, or ``-1`` if ``value_int == 0``.

    Raises:
        TypeError: If ``value_int`` is not an ``int`` (or is a ``bool``).
        ValueError: If ``value_int < 0``.

    Complexity:
        O(1) (uses CPython's ``int.bit_length()``).
    """
    validate_non_negative_poly(value_int, name="value_int")
    return value_int.bit_length() - 1


def hamming_weight(value_int: int) -> int:
    """Return the number of non-zero polynomial terms (set bits) in ``value_int``.

    Args:
        value_int: Non-negative integer representing a polynomial in GF(2)[x].

    Returns:
        Count of ``1`` bits in the binary expansion of ``value_int``.

    Complexity:
        O(W) bit operations via CPython's ``int.bit_count()``.
    """
    validate_non_negative_poly(value_int, name="value_int")
    return value_int.bit_count()


def mod_reduce(
    value_int: int,
    m_poly_int: int,
    m_degree: int,
) -> Tuple[int, Dict[str, Any]]:
    """Reduce polynomial ``value_int`` modulo ``m_poly_int`` (Stallings Ch. 4).

    Repeatedly eliminates the leading term ``x^d`` whenever ``d = deg(r) >= m_degree``
    by XORing ``r`` with ``m_poly_int << (d - m_degree)`` until ``deg(r) < m_degree``.

    Args:
        value_int: Non-negative polynomial dividend/input to reduce.
        m_poly_int: Reduction polynomial of degree ``m_degree`` (bit ``m_degree`` = 1).
        m_degree: Degree ``m >= 1`` of the modulus polynomial.

    Returns:
        Tuple ``(r_int, trace_dict)`` matching the ``Plan/README.md`` contract:
        * ``r_int``: Reduced polynomial with ``deg(r_int) < m_degree``.
        * ``trace_dict``: Dictionary containing ``trace_type="mod_reduce"``,
          ``initial_value``, ``reduced_value``, ``was_reduced`` (bool),
          ``m_degree``, ``m_poly_int``, and ``steps`` (each step matching Plan 01:
          ``target_degree``, ``shift``, ``before``, ``reducer``, ``after``).

    Raises:
        TypeError: On non-integer inputs.
        ValueError: On negative inputs or invalid modulus degree.

    Complexity:
        Let ``d = deg(value_int)`` and ``m = m_degree``. Performs at most
        ``max(0, d - m + 1)`` XOR shifts of word length ``O(d)``, i.e.,
        ``O((d - m + 1) * d)`` bit operations (``O(1)`` shifts when already reduced).
    """
    validate_non_negative_poly(value_int, name="value_int")
    validate_modulus(m_poly_int, m_degree)

    r_int = value_int
    steps: List[Dict[str, int]] = []

    while r_int.bit_length() - 1 >= m_degree:
        target_degree = r_int.bit_length() - 1
        shift = target_degree - m_degree
        reducer = m_poly_int << shift
        r_next = r_int ^ reducer
        steps.append(
            {
                "target_degree": target_degree,
                "shift": shift,
                "before": r_int,
                "reducer": reducer,
                "after": r_next,
            }
        )
        r_int = r_next

    trace_dict: Dict[str, Any] = {
        "trace_type": "mod_reduce",
        "m_degree": m_degree,
        "m_poly_int": m_poly_int,
        "initial_value": value_int,
        "reduced_value": r_int,
        "was_reduced": len(steps) > 0,
        "step_count": len(steps),
        "steps": steps,
    }
    return r_int, trace_dict


def int_to_bin(
    value_int: int,
    m_degree: Optional[int] = None,
    pad: bool = True,
) -> str:
    """Format a non-negative polynomial integer as a binary bit-string (MSB first).

    Args:
        value_int: Non-negative polynomial integer.
        m_degree: Optional field degree used for zero-padding to ``m_degree`` bits.
        pad: When ``True`` and ``m_degree`` is given, zero-pads output to at
            least ``m_degree`` bits (without truncating polynomials of degree >= m).

    Returns:
        Binary string of ``'0'`` and ``'1'`` characters.

    Complexity:
        O(n) where ``n = max(m_degree, bit_length(value_int))``.
    """
    validate_non_negative_poly(value_int, name="value_int")
    if m_degree is not None:
        if isinstance(m_degree, bool) or not isinstance(m_degree, int) or m_degree < 1:
            raise ValueError(f"m_degree must be a positive int, got {m_degree!r}.")
        if pad:
            width = max(m_degree, value_int.bit_length(), 1)
            return format(value_int, f"0{width}b")
    return format(value_int, "b")


def int_to_hex(
    value_int: int,
    m_degree: Optional[int] = None,
    pad: bool = True,
    uppercase: bool = True,
) -> str:
    """Format a non-negative polynomial integer as a hexadecimal string.

    Per ``Plan/Milestones/01_...md``, field elements are padded to
    ``ceil(m_degree / 4)`` uppercase hexadecimal digits (e.g., 2 digits for
    GF(2^8), 41 digits for GF(2^163), 143 digits for GF(2^571)). Values whose
    degree exceeds ``m_degree`` (such as ``m_poly_int`` itself) expand naturally
    without truncation.

    Args:
        value_int: Non-negative polynomial integer.
        m_degree: Optional field degree for zero-padding to ``ceil(m_degree / 4)``
            hex digits.
        pad: Whether to zero-pad when ``m_degree`` is provided.
        uppercase: Emit uppercase ``'0'-'9', 'A'-'F'`` when ``True`` (default),
            or lowercase when ``False``.

    Returns:
        Hexadecimal string without ``0x`` prefix.

    Complexity:
        O(n) where ``n = max(m_degree, bit_length(value_int))``.
    """
    validate_non_negative_poly(value_int, name="value_int")
    spec = "X" if uppercase else "x"
    if m_degree is not None:
        if isinstance(m_degree, bool) or not isinstance(m_degree, int) or m_degree < 1:
            raise ValueError(f"m_degree must be a positive int, got {m_degree!r}.")
        if pad:
            nibbles = max(1, (m_degree + 3) // 4)
            return format(value_int, f"0{nibbles}{spec}")
    return format(value_int, spec)


def int_to_algebraic(value_int: int) -> str:
    """Format a non-negative polynomial integer in descending algebraic notation.

    Matches Plan 01 specification: scans set bits from ``deg(value_int)`` down
    to ``0`` and joins terms as ``"x^k"`` (``"x"`` for ``k == 1``, ``"1"`` for
    ``k == 0``, and ``"0"`` when ``value_int == 0``).

    Args:
        value_int: Non-negative polynomial integer.

    Returns:
        Human-readable polynomial string, e.g. ``"x^7 + x + 1"``.

    Complexity:
        O(deg(value_int)) bit checks.
    """
    validate_non_negative_poly(value_int, name="value_int")
    if value_int == 0:
        return "0"

    terms: List[str] = []
    for k in range(value_int.bit_length() - 1, -1, -1):
        if (value_int >> k) & 1:
            if k == 0:
                terms.append("1")
            elif k == 1:
                terms.append("x")
            else:
                terms.append(f"x^{k}")
    return " + ".join(terms)


def bin_to_int(text: str) -> int:
    """Parse a binary polynomial string (with optional spaces / ``0b``) into ``int``.

    Complexity:
        O(len(text)).
    """
    if not isinstance(text, str):
        raise TypeError(f"binary input must be str, got {type(text).__name__}.")
    cleaned = text.strip().replace(" ", "").replace("_", "")
    if cleaned.lower().startswith("0b"):
        cleaned = cleaned[2:]
    if not cleaned or any(ch not in ("0", "1") for ch in cleaned):
        raise ValueError(f"Invalid binary polynomial string: {text!r}.")
    return int(cleaned, 2)


def hex_to_int(text: str) -> int:
    """Parse a hexadecimal polynomial string (with optional spaces, ``{...}``, ``0x``) into ``int``.

    Complexity:
        O(len(text)).
    """
    if not isinstance(text, str):
        raise TypeError(f"hexadecimal input must be str, got {type(text).__name__}.")
    cleaned = text.strip().replace(" ", "").replace("_", "")
    if cleaned.startswith("{") and cleaned.endswith("}"):
        cleaned = cleaned[1:-1].strip()
    if cleaned.lower().startswith("0x"):
        cleaned = cleaned[2:]
    if not cleaned or any(ch not in "0123456789abcdefABCDEF" for ch in cleaned):
        raise ValueError(f"Invalid hexadecimal polynomial string: {text!r}.")
    return int(cleaned, 16)


def format_poly_representations(
    value_int: int,
    m_degree: int,
    *,
    uppercase_hex: bool = True,
) -> Dict[str, Any]:
    """Return structured multi-notation representations of a polynomial integer.

    Useful for Table 4.7 trace cells so Milestone 4's UI can toggle smoothly
    between Hex, Binary, and Algebraic notations without recomputing values.

    Args:
        value_int: Non-negative polynomial integer.
        m_degree: Field degree used for zero-padding Hex and Binary strings.
        uppercase_hex: Whether to format Hex in uppercase (default ``True``).

    Returns:
        Dictionary with keys ``"int"``, ``"hex"``, ``"bin"``, ``"algebraic"``,
        and ``"degree"``.

    Complexity:
        O(max(m_degree, bit_length(value_int))).
    """
    validate_non_negative_poly(value_int, name="value_int")
    return {
        "int": value_int,
        "hex": int_to_hex(value_int, m_degree=m_degree, pad=True, uppercase=uppercase_hex),
        "bin": int_to_bin(value_int, m_degree=m_degree, pad=True),
        "algebraic": int_to_algebraic(value_int),
        "degree": deg(value_int),
    }

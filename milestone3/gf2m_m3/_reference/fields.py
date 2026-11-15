"""Isolated Milestone 1 reference field registry for standalone Milestone 3 use.

This module implements the exact irreducible polynomials specified in
``Plan/Milestones/01_field_config_io_additive_mod_and_utilities.md`` so that
Milestone 3 executes and passes verification completely standalone before
Milestone 5 integration swaps these stand-ins for Milestone 1's authoritative
registry.

Supported Fields
----------------
* Small textbook verification fields (2 <= m <= 8):
  * m = 2: [2, 1, 0]            -> x^2 + x + 1
  * m = 3: [3, 2, 0]            -> x^3 + x^2 + 1
  * m = 4: [4, 3, 0]            -> x^4 + x^3 + 1
  * m = 5: [5, 2, 0]            -> x^5 + x^2 + 1
  * m = 6: [6, 1, 0]            -> x^6 + x + 1
  * m = 7: [7, 1, 0]            -> x^7 + x + 1
  * m = 8: [8, 4, 3, 1, 0]      -> x^8 + x^4 + x^3 + x + 1 (AES, Stallings Ch. 4 & 5)
* Standard NIST/SEC cryptographic binary fields (Stallings Ch. 10, Binary ECC):
  * m = 163: [163, 7, 6, 3, 0]  -> x^163 + x^7 + x^6 + x^3 + 1
  * m = 233: [233, 74, 0]       -> x^233 + x^74 + 1
  * m = 239: [239, 158, 0]      -> x^239 + x^158 + 1
  * m = 283: [283, 12, 7, 5, 0] -> x^283 + x^12 + x^7 + x^5 + 1
  * m = 409: [409, 87, 0]       -> x^409 + x^87 + 1
  * m = 571: [571, 10, 5, 2, 0] -> x^571 + x^10 + x^5 + x^2 + 1

Note on Cryptographic Standards
-------------------------------
* GF(2^8) with m(x) = x^8 + x^4 + x^3 + x + 1 (0x11B) is the AES field in
  Stallings Chapter 5.
* Binary elliptic curve cryptography over GF(2^163) through GF(2^571) is
  covered in Stallings Chapter 10 (NIST/SEC recommended B-/K-curves).
* XTS-AES (Stallings Chapter 6) similarly applies GF(2^128) polynomial
  multiplication via x^128 + x^7 + x^2 + x + 1.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


def taps_to_poly_int(taps: Sequence[int]) -> int:
    """Construct the integer bitmask for m(x) = sum_{k in taps} x^k.

    Args:
        taps: Iterable of non-negative exponent positions with coefficient 1.
            Must include the leading degree ``m``.

    Returns:
        Non-negative Python ``int`` with bit ``k`` set for each ``k`` in ``taps``.

    Raises:
        ValueError: If ``taps`` is empty or contains negative exponents.

    Complexity:
        O(len(taps)) bit-shift and OR operations.
    """
    tap_list = list(taps)
    if not tap_list:
        raise ValueError("taps must contain at least one exponent.")
    m_poly_int = 0
    for exponent in tap_list:
        if isinstance(exponent, bool) or not isinstance(exponent, int):
            raise TypeError(f"exponent must be int, got {type(exponent).__name__}.")
        if exponent < 0:
            raise ValueError(f"exponent must be non-negative, got {exponent}.")
        m_poly_int |= 1 << exponent
    return m_poly_int


@dataclass(frozen=True)
class FieldSpec:
    """Immutable metadata for a supported GF(2^m) finite field.

    Attributes:
        m_degree: Extension field degree ``m``.
        taps: Descending tuple of non-zero term exponents, starting with ``m_degree``.
        m_poly_int: Full irreducible polynomial integer including bit ``m_degree``.
        category: ``"textbook"`` for 2 <= m <= 8 or ``"cryptographic"`` for
            m in {163, 233, 239, 283, 409, 571}.
        name: Human-readable field label such as ``"GF(2^8)"``.
        standard_reference: Textbook / cryptographic standard citation.
    """

    m_degree: int
    taps: Tuple[int, ...]
    m_poly_int: int
    category: str
    name: str
    standard_reference: str


# Exact irreducible polynomial tap lists per Plan/Milestones/01_...md.
TEXTBOOK_FIELD_TAPS: Dict[int, Tuple[int, ...]] = {
    2: (2, 1, 0),
    3: (3, 2, 0),
    4: (4, 3, 0),
    5: (5, 2, 0),
    6: (6, 1, 0),
    7: (7, 1, 0),
    8: (8, 4, 3, 1, 0),
}

CRYPTO_FIELD_TAPS: Dict[int, Tuple[int, ...]] = {
    163: (163, 7, 6, 3, 0),
    233: (233, 74, 0),
    239: (239, 158, 0),
    283: (283, 12, 7, 5, 0),
    409: (409, 87, 0),
    571: (571, 10, 5, 2, 0),
}

_STANDARD_NOTES: Dict[int, str] = {
    2: "Small textbook field (Project-2 / Stallings Ch. 4)",
    3: "Small textbook field (Project-2 / Plan 01)",
    4: "Small textbook field (Project-2 / Plan 01)",
    5: "Small textbook field (Project-2 / Stallings Ch. 4)",
    6: "Small textbook field (Project-2 / Stallings Ch. 4)",
    7: "Small textbook field (Project-2 / Stallings Ch. 4)",
    8: "AES field GF(2^8) (Stallings Ch. 4 Table 4.7 & Ch. 5 S-Box)",
    163: "NIST/SEC B-163 / K-163 Binary ECC primary field (Stallings Ch. 10)",
    233: "NIST/SEC B-233 / K-233 Binary ECC field (Stallings Ch. 10)",
    239: "SEC sect239k1 Binary ECC field (Stallings Ch. 10)",
    283: "NIST/SEC B-283 / K-283 Binary ECC field (Stallings Ch. 10)",
    409: "NIST/SEC B-409 / K-409 Binary ECC field (Stallings Ch. 10)",
    571: "NIST/SEC B-571 / K-571 Binary ECC field (Stallings Ch. 10)",
}


def _build_registry() -> Dict[int, FieldSpec]:
    registry: Dict[int, FieldSpec] = {}
    for m_degree, taps in TEXTBOOK_FIELD_TAPS.items():
        registry[m_degree] = FieldSpec(
            m_degree=m_degree,
            taps=taps,
            m_poly_int=taps_to_poly_int(taps),
            category="textbook",
            name=f"GF(2^{m_degree})",
            standard_reference=_STANDARD_NOTES[m_degree],
        )
    for m_degree, taps in CRYPTO_FIELD_TAPS.items():
        registry[m_degree] = FieldSpec(
            m_degree=m_degree,
            taps=taps,
            m_poly_int=taps_to_poly_int(taps),
            category="cryptographic",
            name=f"GF(2^{m_degree})",
            standard_reference=_STANDARD_NOTES[m_degree],
        )
    return dict(sorted(registry.items()))


FIELD_REGISTRY: Dict[int, FieldSpec] = _build_registry()


def is_supported_degree(m_degree: int) -> bool:
    """Return ``True`` if ``m_degree`` is one of the 13 configured GF(2^m) fields.

    Complexity:
        O(1) dictionary lookup.
    """
    return not isinstance(m_degree, bool) and m_degree in FIELD_REGISTRY


def get_field_spec(m_degree: int) -> FieldSpec:
    """Retrieve the :class:`FieldSpec` for field degree ``m_degree``.

    Args:
        m_degree: Degree ``m`` in {2..8, 163, 233, 239, 283, 409, 571}.

    Returns:
        Corresponding immutable :class:`FieldSpec`.

    Raises:
        ValueError: If ``m_degree`` is not in the supported registry.

    Complexity:
        O(1) dictionary lookup.
    """
    if isinstance(m_degree, bool) or not isinstance(m_degree, int):
        raise ValueError(f"Unsupported field degree m={m_degree!r}.")
    if m_degree not in FIELD_REGISTRY:
        supported = ", ".join(str(k) for k in FIELD_REGISTRY)
        raise ValueError(
            f"Unsupported field degree m={m_degree}. Supported degrees: [{supported}]."
        )
    return FIELD_REGISTRY[m_degree]


def get_m_poly_int(m_degree: int) -> int:
    """Return the integer bitmask ``m_poly_int`` for field degree ``m_degree``.

    Complexity:
        O(1) dictionary lookup.
    """
    return get_field_spec(m_degree).m_poly_int


def list_supported_degrees(include_textbook: bool = True) -> List[int]:
    """Return sorted list of supported field degrees.

    Args:
        include_textbook: When ``False``, returns only the 6 NIST/SEC degrees
            ``[163, 233, 239, 283, 409, 571]``.

    Complexity:
        O(k) where k = 13 is the number of configured fields.
    """
    return [
        spec.m_degree
        for spec in FIELD_REGISTRY.values()
        if include_textbook or spec.category == "cryptographic"
    ]

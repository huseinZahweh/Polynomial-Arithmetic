"""Canonical irreducible-polynomial field registry for GF(2^m).

Original Author
---------------
Hussein Abbas — Milestone 1 (Field Configuration, I/O, Additive/Modulo & Utilities).

Purpose & Course References
---------------------------
Configures the 13 binary finite fields supported by EECE 455 Project-3:

* **7 Small Textbook Fields (2 <= m <= 8):** Exact irreducible polynomials from
  the EECE 455 Project-2 handout, including the AES byte field ``GF(2^8)``
  with ``m(x) = x^8 + x^4 + x^3 + x + 1`` (``0x11B``) from Stallings **Chapter 4**
  (Table 4.7) and **Chapter 5** (AES S-Box and MixColumns).
* **6 Standard Cryptographic Fields (m in {163, 233, 239, 283, 409, 571}):**
  Sparse trinomials and pentanomials specified by NIST FIPS 186-4 and SECG SEC 2
  for binary elliptic-curve cryptography ``E_{2^m}(a, b)`` (Stallings **Chapter 10**),
  with ``m = 163`` as the Project-3 primary field. The same polynomial-basis
  bitmask convention also applies to ``GF(2^128)`` in XTS-AES (Stallings **Chapter 6**).

Bitmask Representation
----------------------
Each modulus ``m(x)`` of degree ``m`` is stored as an integer bitmask with bit
``i`` equal to the coefficient of ``x^i`` and bit ``m`` explicitly set to ``1``:

    m_poly = sum(1 << exponent for exponent in taps)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    """Immutable specification for one configured binary finite field ``GF(2^m)``.

    Attributes:
        m: Field extension degree (element bit width).
        mod_poly: Irreducible reduction polynomial bitmask with bit ``m`` set.
        category: Classification label — ``"textbook"`` (``2 <= m <= 8``) or
            ``"nist"`` (standard binary ECC degrees ``163..571``).
        name: Human-readable field label, e.g. ``"GF(2^163)"``.
    """

    m: int
    mod_poly: int
    category: str
    name: str

    @property
    def reduction_poly_terms(self) -> list[int]:
        """Return nonzero modulus exponents in ascending order.

        Returns:
            List of integer exponents ``i`` in ``[0, m]`` whose bit is set in
            :attr:`mod_poly`.

        Complexity:
            Time ``O(m)``, space ``O(wt(m(x)))`` where ``wt`` is Hamming weight.
        """
        return [i for i in range(self.m + 1) if (self.mod_poly >> i) & 1]

    @property
    def taps(self) -> tuple[int, ...]:
        """Return nonzero modulus exponents in descending order (highest term first).

        Returns:
            Tuple of integer exponents from ``m`` down to ``0``.

        Complexity:
            Time ``O(m)``, space ``O(wt(m(x)))``.
        """
        return _FIELD_TAPS[self.m]


# Canonical tap lists (descending exponents):
# - Degrees 2..8: EECE 455 Project-2 handout (degree 8 is AES 0x11B).
# - Degrees 163..571: Standard binary ECC trinomials/pentanomials (NIST / SEC 2).
_FIELD_TAPS: dict[int, tuple[int, ...]] = {
    2: (2, 1, 0),
    3: (3, 2, 0),
    4: (4, 3, 0),
    5: (5, 2, 0),
    6: (6, 1, 0),
    7: (7, 1, 0),
    8: (8, 4, 3, 1, 0),
    163: (163, 7, 6, 3, 0),
    233: (233, 74, 0),
    239: (239, 158, 0),
    283: (283, 12, 7, 5, 0),
    409: (409, 87, 0),
    571: (571, 10, 5, 2, 0),
}

DEFAULT_DEGREE: int = 163

# Pre-computed O(1) lookup table from degree m to immutable Field metadata.
_REGISTRY: dict[int, Field] = {
    m: Field(
        m=m,
        mod_poly=sum(1 << exponent for exponent in taps),
        category="textbook" if m <= 8 else "nist",
        name=f"GF(2^{m})",
    )
    for m, taps in _FIELD_TAPS.items()
}


def is_supported(m: int) -> bool:
    """Check whether integer degree ``m`` exists in the configured field registry.

    Uses exact ``type(m) is int`` so booleans (``True``/``False``) and floats
    (``8.0``) are rejected rather than coerced to integer keys.

    Args:
        m: Candidate extension field degree.

    Returns:
        ``True`` if ``m`` is a supported integer degree, otherwise ``False``.

    Complexity:
        Time ``O(1)``, space ``O(1)``.
    """
    return type(m) is int and m in _REGISTRY


def get_field(m: int) -> Field:
    """Look up the configured :class:`Field` metadata for degree ``m``.

    Args:
        m: Supported extension field degree (``2..8`` or ``163, 233, 239, 283, 409, 571``).

    Returns:
        The immutable :class:`Field` entry for ``GF(2^m)``.

    Raises:
        ValueError: If ``m`` is not a supported integer degree.

    Complexity:
        Time ``O(1)``, space ``O(1)``.
    """
    if not is_supported(m):
        raise ValueError(f"unsupported field degree m={m!r}")
    return _REGISTRY[m]


def get_m_poly_int(m: int) -> int:
    """Return the irreducible reduction polynomial bitmask ``m(x)`` for degree ``m``.

    Args:
        m: Supported extension field degree.

    Returns:
        Integer bitmask of ``m(x)`` with bit ``m`` set to ``1``.

    Raises:
        ValueError: If ``m`` is not a supported field degree.

    Complexity:
        Time ``O(1)``, space ``O(1)``.
    """
    return get_field(m).mod_poly


def list_fields(include_textbook: bool = True) -> list[Field]:
    """List configured fields in ascending degree order.

    Args:
        include_textbook: When ``True`` (default), returns all 13 fields
            (degrees ``2..8`` and ``163..571``). When ``False``, returns only
            the 6 standard cryptographic binary fields.

    Returns:
        Ordered list of :class:`Field` specifications.

    Complexity:
        Time ``O(F)``, space ``O(F)`` where ``F = 13`` is the registry size.
    """
    return [
        field
        for field in _REGISTRY.values()
        if include_textbook or field.category != "textbook"
    ]


def list_supported_degrees(include_textbook: bool = True) -> list[int]:
    """Return all supported field degrees in ascending order.

    Args:
        include_textbook: Whether to include textbook degrees ``2..8``.

    Returns:
        Sorted list of supported integer degrees ``m``.

    Complexity:
        Time ``O(F)``, space ``O(F)`` where ``F = 13``.
    """
    return [field.m for field in list_fields(include_textbook=include_textbook)]

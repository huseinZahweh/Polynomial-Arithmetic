"""Irreducible polynomials for the course's textbook and binary ECC fields."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    """A field degree and its full modulus, including the leading term."""

    m: int
    mod_poly: int
    category: str
    name: str

    @property
    def reduction_poly_terms(self) -> list[int]:
        """Return nonzero modulus exponents in the API's ascending order."""
        return [i for i in range(self.m + 1) if (self.mod_poly >> i) & 1]


# Project-2 handout for degrees 2–8, with the AES modulus at degree 8.
# The larger taps are the binary ECC choices specified by the team.
_FIELD_TAPS = {
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
DEFAULT_DEGREE = 163
_REGISTRY = {
    m: Field(m, sum(1 << exponent for exponent in taps),
             "textbook" if m <= 8 else "nist", f"GF(2^{m})")
    for m, taps in _FIELD_TAPS.items()
}


def is_supported(m: int) -> bool:
    """Check whether the integer field degree is configured in O(1)."""
    return type(m) is int and m in _REGISTRY


def get_field(m: int) -> Field:
    """Return the configured field in O(1), or raise ValueError."""
    if not is_supported(m):
        raise ValueError(f"unsupported field degree m={m!r}")
    return _REGISTRY[m]


def list_fields(include_textbook: bool = True) -> list[Field]:
    """List fields in ascending degree order, optionally omitting degrees 2–8."""
    return [field for field in _REGISTRY.values()
            if include_textbook or field.category != "textbook"]

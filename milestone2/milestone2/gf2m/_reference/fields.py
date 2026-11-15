"""Reference field registry.

INTEGRATION CONTRACT — owned by Milestone 1 on merge.

Provides the modular field registry for the standard cryptographic binary
fields m in {163, 233, 239, 283, 409, 571} plus the small textbook fields
2 <= m <= 8 used for classroom verification. Reduction polynomials for the
large fields are the NIST / SEC recommended irreducible polynomials used by
binary elliptic curves (B-/K- curves), so they line up with the ECC material
in the course.

Each field exposes:
    m           field degree
    mod_poly    reduction polynomial as a full int (includes the x^m term)
    category    "nist" | "textbook"
    name        human label

The API's /api/fields endpoint reads straight from here; swap this module for
M1's registry on merge and the endpoint is unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


def _poly(m: int, *low_exponents: int) -> int:
    """Build m(x) = x^m + sum(x^e) + ... as an int including the x^m bit."""
    value = 1 << m
    for e in low_exponents:
        value |= 1 << e
    return value


@dataclass(frozen=True)
class Field:
    m: int
    mod_poly: int
    category: str
    name: str

    @property
    def reduction_poly_terms(self) -> List[int]:
        return [i for i in range(self.mod_poly.bit_length()) if (self.mod_poly >> i) & 1]


# NIST/SEC reduction polynomials for the standard binary curve fields.
_NIST: Dict[int, int] = {
    163: _poly(163, 7, 6, 3, 0),      # x^163 + x^7 + x^6 + x^3 + 1
    233: _poly(233, 74, 0),           # x^233 + x^74 + 1
    239: _poly(239, 158, 0),          # x^239 + x^158 + 1   (sect239k1)
    283: _poly(283, 12, 7, 5, 0),     # x^283 + x^12 + x^7 + x^5 + 1
    409: _poly(409, 87, 0),           # x^409 + x^87 + 1
    571: _poly(571, 10, 5, 2, 0),     # x^571 + x^10 + x^5 + x^2 + 1
}

# Common irreducible polynomials for the small textbook fields (Project-2).
_TEXTBOOK: Dict[int, int] = {
    2: _poly(2, 1, 0),                # x^2 + x + 1
    3: _poly(3, 2, 0),                # x^3 + x^2 + 1
    4: _poly(4, 3, 0),                # x^4 + x^3 + 1
    5: _poly(5, 2, 0),                # x^5 + x^2 + 1
    6: _poly(6, 1, 0),                # x^6 + x + 1
    7: _poly(7, 1, 0),                # x^7 + x + 1
    8: _poly(8, 4, 3, 1, 0),          # x^8 + x^4 + x^3 + x + 1 (AES)
}

_REGISTRY: Dict[int, Field] = {}
for _m, _p in _NIST.items():
    _REGISTRY[_m] = Field(m=_m, mod_poly=_p, category="nist", name=f"GF(2^{_m})")
for _m, _p in _TEXTBOOK.items():
    _REGISTRY[_m] = Field(m=_m, mod_poly=_p, category="textbook", name=f"GF(2^{_m})")


def is_supported(m: int) -> bool:
    return m in _REGISTRY


def get_field(m: int) -> Field:
    try:
        return _REGISTRY[m]
    except KeyError:
        raise ValueError(f"unsupported field degree m={m}")


def list_fields(include_textbook: bool = True) -> List[Field]:
    fields = [f for f in _REGISTRY.values() if include_textbook or f.category == "nist"]
    return sorted(fields, key=lambda f: f.m)

"""Isolated reference helpers (Milestone 1 & Milestone 2 stand-ins) for M3.

All M1 (field registry, degree, modulo reduction, formatting) and M2
(Shift-and-XOR multiplication) dependencies are encapsulated in this
subpackage so Milestone 3 runs completely standalone today and can swap to
the real M1/M2 implementations cleanly during Milestone 5 integration.
"""
from __future__ import annotations

from .fields import (
    CRYPTO_FIELD_TAPS,
    FIELD_REGISTRY,
    TEXTBOOK_FIELD_TAPS,
    FieldSpec,
    get_field_spec,
    get_m_poly_int,
    is_supported_degree,
    list_supported_degrees,
    taps_to_poly_int,
)
from .multiply import gf2m_multiply
from .utilities import (
    bin_to_int,
    deg,
    format_poly_representations,
    hamming_weight,
    hex_to_int,
    int_to_algebraic,
    int_to_bin,
    int_to_hex,
    mod_reduce,
    validate_modulus,
    validate_non_negative_poly,
)

__all__ = [
    "CRYPTO_FIELD_TAPS",
    "FIELD_REGISTRY",
    "TEXTBOOK_FIELD_TAPS",
    "FieldSpec",
    "bin_to_int",
    "deg",
    "format_poly_representations",
    "get_field_spec",
    "get_m_poly_int",
    "gf2m_multiply",
    "hamming_weight",
    "hex_to_int",
    "int_to_algebraic",
    "int_to_bin",
    "int_to_hex",
    "is_supported_degree",
    "list_supported_degrees",
    "mod_reduce",
    "taps_to_poly_int",
    "validate_modulus",
    "validate_non_negative_poly",
]

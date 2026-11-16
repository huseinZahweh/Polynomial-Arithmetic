"""Public Milestone 1 field, representation, and arithmetic functions."""

from .additive import GF2M_ADD_SUB, MOD_REDUCE
from .fields import DEFAULT_DEGREE, Field, get_field, is_supported, list_fields
from .polyrepr import (
    BIN_TO_INT,
    DEG,
    HAMMING_WEIGHT,
    HEX_TO_INT,
    INT_TO_ALGEBRAIC,
    INT_TO_BIN,
    INT_TO_HEX,
)
from .randomops import GENERATE_RANDOM_POLY

__all__ = [
    "BIN_TO_INT",
    "DEFAULT_DEGREE",
    "DEG",
    "Field",
    "GENERATE_RANDOM_POLY",
    "GF2M_ADD_SUB",
    "HAMMING_WEIGHT",
    "HEX_TO_INT",
    "INT_TO_ALGEBRAIC",
    "INT_TO_BIN",
    "INT_TO_HEX",
    "MOD_REDUCE",
    "get_field",
    "is_supported",
    "list_fields",
]

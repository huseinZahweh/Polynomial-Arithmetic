"""Unified pure-Python GF(2^m) polynomial arithmetic engine public exports.

Re-exports the canonical field registry, multi-base converters, six finite-field
arithmetic engines, live algebraic self-verifiers, structured exceptions,
classroom utilities, and interactive exploration routines without any web
framework dependencies.

Team Attribution
----------------
* **Hussein Abbas (Milestone 1):** ``fields``, ``polyrepr``, ``additive``,
  ``randomops``, ``parser``, ``formatter``, ``tutorial``.
* **Hassan Tarhini (Milestone 2):** ``multiply`` (Shift-and-XOR + Tables 1 & 2).
* **Husein Zahweh (Milestone 3):** ``poly_ops``, ``extended_euclid``,
  ``division``, ``verification``, ``exceptions``.
* **Ali Zahreddine (Milestone 4 & Integration):** ``explorations``,
  ``ALGEBRAIC_TO_INT``, and unified engine wiring.
"""
from __future__ import annotations

from .additive import GF2M_ADD_SUB, MOD_REDUCE, add, modulo, subtract, xor_trace
from .division import GF2M_DIVIDE
from .exceptions import (
    GF2mInverseError,
    NotInvertibleError,
    ZeroElementHasNoInverseError,
)
from .explorations import (
    benchmark_multiplication,
    compare_multiplication,
    compute_aes_sbox,
    explore_modulus,
)
from .extended_euclid import EXTENDED_EUCLID_GF2M
from .fields import (
    DEFAULT_DEGREE,
    Field,
    get_field,
    get_m_poly_int,
    is_supported,
    list_fields,
    list_supported_degrees,
)
from .formatter import make_share_token, parse_share_token, render, to_json, to_markdown
from .multiply import MultiplyTrace, ShiftStep, carryless_mul, multiply, multiply_traced, reduce_mod
from .parser import OperandFileError, parse_operand_file
from .poly_ops import DivisionStep, POLY_DIVMOD, POLY_MUL_NO_MOD
from .polyrepr import (
    ALGEBRAIC_TO_INT,
    BIN_TO_INT,
    DEG,
    ElementRepr,
    HAMMING_WEIGHT,
    HEX_TO_INT,
    INT_TO_ALGEBRAIC,
    INT_TO_BIN,
    INT_TO_HEX,
    format_poly_representations,
    parse_value,
    to_bin,
    to_hex,
    to_poly,
    validate_modulus,
    validate_non_negative_poly,
)
from .randomops import GENERATE_RANDOM_POLY, generate_operand
from .tutorial import load_tutorial
from .verification import VERIFY_DIVISION, VERIFY_INVERSE

__all__ = [
    "ALGEBRAIC_TO_INT",
    "BIN_TO_INT",
    "DEFAULT_DEGREE",
    "DEG",
    "DivisionStep",
    "EXTENDED_EUCLID_GF2M",
    "ElementRepr",
    "Field",
    "GENERATE_RANDOM_POLY",
    "GF2M_ADD_SUB",
    "GF2M_DIVIDE",
    "GF2mInverseError",
    "HAMMING_WEIGHT",
    "HEX_TO_INT",
    "INT_TO_ALGEBRAIC",
    "INT_TO_BIN",
    "INT_TO_HEX",
    "MOD_REDUCE",
    "MultiplyTrace",
    "NotInvertibleError",
    "OperandFileError",
    "POLY_DIVMOD",
    "POLY_MUL_NO_MOD",
    "ShiftStep",
    "VERIFY_DIVISION",
    "VERIFY_INVERSE",
    "ZeroElementHasNoInverseError",
    "add",
    "benchmark_multiplication",
    "carryless_mul",
    "compare_multiplication",
    "compute_aes_sbox",
    "explore_modulus",
    "format_poly_representations",
    "generate_operand",
    "get_field",
    "get_m_poly_int",
    "is_supported",
    "list_fields",
    "list_supported_degrees",
    "load_tutorial",
    "make_share_token",
    "modulo",
    "multiply",
    "multiply_traced",
    "parse_operand_file",
    "parse_share_token",
    "parse_value",
    "reduce_mod",
    "render",
    "subtract",
    "to_bin",
    "to_hex",
    "to_json",
    "to_markdown",
    "to_poly",
    "validate_modulus",
    "validate_non_negative_poly",
    "xor_trace",
]

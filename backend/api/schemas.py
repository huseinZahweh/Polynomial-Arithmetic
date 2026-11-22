"""Pydantic v2 request and response schemas for the GF(2^m) REST API.

Original Authors
----------------
* Hassan Tarhini — Milestone 2 (Core 6-endpoint API contracts).
* Ali Zahreddine — Milestone 4 & Integration (Aliases for Plan/GUI request keys,
  algebraic base support, initial-reduction & proof fields).

Purpose & Course References
---------------------------
Defines explicit, self-documenting JSON schemas powering OpenAPI (``/docs``) and
strict request validation across all 6 core endpoints and the 4 exploration routes
(Stallings **Chapter 4** finite fields, **Chapter 5** AES ``GF(2^8)``, **Chapter 6**
XTS-AES, and **Chapter 10** binary ECC fields ``GF(2^163)..GF(2^571)``).
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, Field


class Operation(str, Enum):
    """Supported ``GF(2^m)`` arithmetic operations (accepts full and short aliases)."""

    add = "add"
    subtract = "subtract"
    modulo = "modulo"
    multiply = "multiply"
    inverse = "inverse"
    divide = "divide"

    @classmethod
    def _missing_(cls, value: Any) -> Optional[Operation]:
        """Resolve short plan aliases (``sub``, ``mod``, ``mul``, ``inv``, ``div``).

        Args:
            value: Raw incoming operation label.

        Returns:
            Canonical :class:`Operation` member, or ``None`` if unrecognized.
        """
        aliases = {
            "sub": cls.subtract,
            "mod": cls.modulo,
            "mul": cls.multiply,
            "inv": cls.inverse,
            "div": cls.divide,
        }
        if isinstance(value, str):
            return aliases.get(value)
        return None


class Base(str, Enum):
    """Supported polynomial input/output notations (maps ``"binary"`` -> ``"bin"``)."""

    hex = "hex"
    bin = "bin"
    algebraic = "algebraic"

    @classmethod
    def _missing_(cls, value: Any) -> Optional[Base]:
        """Accept ``"binary"`` as an alias for :attr:`Base.bin`.

        Args:
            value: Raw incoming base string.

        Returns:
            :attr:`Base.bin` when ``value == "binary"``, otherwise ``None``.
        """
        if value == "binary":
            return cls.bin
        return None


class Density(str, Enum):
    """Operand density selector for ``POST /api/random-polynomials``."""

    sparse = "sparse"
    dense = "dense"
    random = "random"


# --------------------------------------------------------------------------- #
# Shared Value Objects                                                        #
# --------------------------------------------------------------------------- #
class ElementReprModel(BaseModel):
    """Serialized multi-notation representation and metrics of one ``GF(2^m)`` element."""

    hex: str
    bin: str
    poly: str
    degree: int
    bit_length: int
    hamming_weight: int


class FieldInfo(BaseModel):
    """Public metadata for one configured ``GF(2^m)`` field and its modulus ``m(x)``."""

    m: int
    category: str
    name: str
    reduction_poly_hex: str
    reduction_poly_bin: str
    reduction_poly: str
    element_bits: int


# --------------------------------------------------------------------------- #
# 1. GET /api/fields                                                          #
# --------------------------------------------------------------------------- #
class FieldsResponse(BaseModel):
    """Response payload listing all configured binary finite fields."""

    count: int
    fields: List[FieldInfo]


# --------------------------------------------------------------------------- #
# 2. POST /api/calculate                                                      #
# --------------------------------------------------------------------------- #
class CalculateRequest(BaseModel):
    """Request payload for executing one of the six ``GF(2^m)`` operations."""

    m: int = Field(..., description="Field degree, e.g. 163")
    operation: Operation
    a: str = Field(
        ...,
        validation_alias=AliasChoices("a", "poly_a"),
        max_length=65536,
        description="Operand A in the chosen input base",
    )
    b: Optional[str] = Field(
        None,
        validation_alias=AliasChoices("b", "poly_b"),
        max_length=65536,
        description="Operand B (unused for modulo/inverse)",
    )
    input_base: Base = Base.hex
    output_base: Base = Base.hex
    trace: bool = True

    model_config = {
        "json_schema_extra": {
            "example": {
                "m": 163,
                "operation": "multiply",
                "a": "2",
                "b": "2",
                "input_base": "hex",
                "output_base": "hex",
                "trace": True,
            }
        }
    }


class Operands(BaseModel):
    """Reduced input operands echoed back in all three notations."""

    a: ElementReprModel
    b: Optional[ElementReprModel] = None


class Verification(BaseModel):
    """Live algebraic self-verification status and structured proof payload."""

    label: str
    passed: bool
    proof: Optional[Dict[str, Any]] = None


class Metrics(BaseModel):
    """Execution timing and structural complexity metrics for one calculation."""

    elapsed_ms: float
    result_bit_length: int
    result_hamming_weight: int


class CalculateResponse(BaseModel):
    """Complete response payload returned by ``POST /api/calculate``."""

    operation: Operation
    field: FieldInfo
    operands: Operands
    result: ElementReprModel
    trace: Optional[Dict[str, Any]] = None
    initial_reduction: Optional[Dict[str, Any]] = None
    verification: Optional[Verification] = None
    metrics: Metrics
    share_token: str


# --------------------------------------------------------------------------- #
# 3. POST /api/random-polynomials                                             #
# --------------------------------------------------------------------------- #
class RandomRequest(BaseModel):
    """Request payload for sampling sparse or dense nonzero ``GF(2^m)`` operands."""

    m: int
    density: Density = Field(
        Density.random,
        validation_alias=AliasChoices("density", "sparsity"),
    )
    seed: Optional[int] = None
    count: int = Field(2, ge=1, le=100)
    output_base: Base = Base.hex


class RandomResponse(BaseModel):
    """Generated random field elements in both structured and list forms."""

    field: FieldInfo
    density: Density
    seed: Optional[int]
    a: ElementReprModel
    b: Optional[ElementReprModel]
    m: int
    output_base: Base
    polynomials: List[str]


# --------------------------------------------------------------------------- #
# 4. POST /api/parse-polynomials                                              #
# --------------------------------------------------------------------------- #
class ParseRequest(BaseModel):
    """Request payload carrying raw ``.txt`` or ``.json`` operand-batch contents."""

    content: str = Field(..., description="Raw file contents (.txt or .json)")
    filename: str = Field("", description="Original filename; used to infer format")
    default_base: Base = Base.hex


class OperandPair(BaseModel):
    """One validated operand pair extracted from an uploaded batch file."""

    a: str
    b: str
    base: str


class ParseResponse(BaseModel):
    """Validated batch of operand pairs returned by ``POST /api/parse-polynomials``."""

    count: int
    pairs: List[OperandPair]


# --------------------------------------------------------------------------- #
# 5. POST /api/export-calculation                                             #
# --------------------------------------------------------------------------- #
class ExportFormat(str, Enum):
    """Supported export report formats (Markdown or JSON)."""

    md = "md"
    json = "json"


class ExportRequest(BaseModel):
    """Request payload for exporting a completed calculation summary."""

    calculation: Dict[str, Any] = Field(..., description="A CalculateResponse payload")
    format: ExportFormat = ExportFormat.md
    download: bool = False


class ExportResponse(BaseModel):
    """Inline export payload when ``download=False``."""

    filename: str
    media_type: str
    content: str


# --------------------------------------------------------------------------- #
# 6. GET /api/tutorial                                                        #
# --------------------------------------------------------------------------- #
class TutorialResponse(BaseModel):
    """Structured 4-slide educational tutorial and textbook preset catalog."""

    version: str
    title: str
    slides: List[Dict[str, Any]]

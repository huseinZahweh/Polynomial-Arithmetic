"""Pydantic request/response contracts for the Milestone 2 API.

These are the shared data contracts the GUI (M4) and integration (M5) code bind
to. Keeping them explicit and versioned here is what lets the four tracks be
developed in parallel.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Operation(str, Enum):
    add = "add"
    subtract = "subtract"
    modulo = "modulo"
    multiply = "multiply"
    inverse = "inverse"
    divide = "divide"


class Base(str, Enum):
    hex = "hex"
    bin = "bin"


class Density(str, Enum):
    sparse = "sparse"
    dense = "dense"
    random = "random"


# --------------------------------------------------------------------------- #
# Shared value objects                                                         #
# --------------------------------------------------------------------------- #
class ElementReprModel(BaseModel):
    hex: str
    bin: str
    poly: str
    degree: int
    bit_length: int
    hamming_weight: int


class FieldInfo(BaseModel):
    m: int
    category: str
    name: str
    reduction_poly_hex: str
    reduction_poly: str
    element_bits: int


# --------------------------------------------------------------------------- #
# /api/fields                                                                  #
# --------------------------------------------------------------------------- #
class FieldsResponse(BaseModel):
    count: int
    fields: List[FieldInfo]


# --------------------------------------------------------------------------- #
# /api/calculate                                                               #
# --------------------------------------------------------------------------- #
class CalculateRequest(BaseModel):
    m: int = Field(..., description="Field degree, e.g. 163")
    operation: Operation
    a: str = Field(..., description="Operand A in the chosen input base")
    b: Optional[str] = Field(None, description="Operand B (unused for modulo/inverse)")
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
    a: ElementReprModel
    b: Optional[ElementReprModel] = None


class Verification(BaseModel):
    label: str
    passed: bool


class Metrics(BaseModel):
    elapsed_ms: float
    result_bit_length: int
    result_hamming_weight: int


class CalculateResponse(BaseModel):
    operation: Operation
    field: FieldInfo
    operands: Operands
    result: ElementReprModel
    trace: Optional[Dict[str, Any]] = None
    verification: Optional[Verification] = None
    metrics: Metrics
    share_token: str


# --------------------------------------------------------------------------- #
# /api/random-polynomials                                                      #
# --------------------------------------------------------------------------- #
class RandomRequest(BaseModel):
    m: int
    density: Density = Density.random
    seed: Optional[int] = None


class RandomResponse(BaseModel):
    field: FieldInfo
    density: Density
    seed: Optional[int]
    a: ElementReprModel
    b: ElementReprModel


# --------------------------------------------------------------------------- #
# /api/parse-polynomials                                                       #
# --------------------------------------------------------------------------- #
class ParseRequest(BaseModel):
    content: str = Field(..., description="Raw file contents (.txt or .json)")
    filename: str = Field("", description="Original filename; used to infer format")
    default_base: Base = Base.hex


class OperandPair(BaseModel):
    a: str
    b: str
    base: str


class ParseResponse(BaseModel):
    count: int
    pairs: List[OperandPair]


# --------------------------------------------------------------------------- #
# /api/export-calculation                                                      #
# --------------------------------------------------------------------------- #
class ExportFormat(str, Enum):
    md = "md"
    json = "json"


class ExportRequest(BaseModel):
    calculation: Dict[str, Any] = Field(..., description="A CalculateResponse payload")
    format: ExportFormat = ExportFormat.md
    download: bool = False


class ExportResponse(BaseModel):
    filename: str
    media_type: str
    content: str


# --------------------------------------------------------------------------- #
# /api/tutorial                                                                #
# --------------------------------------------------------------------------- #
class TutorialResponse(BaseModel):
    version: str
    title: str
    slides: List[Dict[str, Any]]

"""Milestone 2 — FastAPI backend controller.

OWNER: Milestone 2.

Six endpoints wire the GF(2^m) engines to the GUI:

    GET  /api/fields               list supported fields
    POST /api/calculate            run one of the six field operations
    POST /api/random-polynomials   generate random operands A(x), B(x)
    POST /api/parse-polynomials    parse an uploaded .txt/.json operand file
    POST /api/export-calculation   render a .md/.json calculation summary
    GET  /api/tutorial             serve the guided tutorial slides

All domain logic lives in the engines (reached via ``providers``); this module
only validates input, maps errors to HTTP status codes, and shapes responses.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from gf2m import polyrepr

from . import providers
from .schemas import (
    CalculateRequest,
    CalculateResponse,
    ExportRequest,
    ExportResponse,
    FieldsResponse,
    OperandPair,
    ParseRequest,
    ParseResponse,
    RandomRequest,
    RandomResponse,
    TutorialResponse,
)
from .services import CalculationError, build_field_info, calculate, field_info

app = FastAPI(
    title="GF(2^m) Polynomial Arithmetic API",
    description="EECE 455/632 Project-3 — Milestone 2 backend controller.",
    version="1.0.0",
)

# The GUI (Milestone 4) is served from a different origin during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {"service": "gf2m-api", "version": app.version, "docs": "/docs"}


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


# --------------------------------------------------------------------------- #
# 1. /api/fields                                                               #
# --------------------------------------------------------------------------- #
@app.get("/api/fields", response_model=FieldsResponse, tags=["fields"])
def get_fields(include_textbook: bool = Query(True)) -> FieldsResponse:
    fields = [
        build_field_info(f)
        for f in providers.fields.list_fields(include_textbook=include_textbook)
    ]
    return FieldsResponse(count=len(fields), fields=fields)


# --------------------------------------------------------------------------- #
# 2. /api/calculate                                                            #
# --------------------------------------------------------------------------- #
@app.post("/api/calculate", response_model=CalculateResponse, tags=["calculate"])
def post_calculate(req: CalculateRequest):
    try:
        return calculate(req)
    except CalculationError as exc:
        payload: dict = {"detail": str(exc)}
        if exc.gcd is not None:
            payload["gcd"] = exc.gcd
        if exc.trace is not None:
            payload["trace"] = exc.trace
        return JSONResponse(status_code=400, content=jsonable_encoder(payload))


# --------------------------------------------------------------------------- #
# 3. /api/random-polynomials                                                   #
# --------------------------------------------------------------------------- #
@app.post("/api/random-polynomials", response_model=RandomResponse, tags=["generate"])
def post_random(req: RandomRequest) -> RandomResponse:
    if not providers.fields.is_supported(req.m):
        raise HTTPException(status_code=400, detail=f"unsupported field degree m={req.m}")
    a = providers.randomops.generate_operand(req.m, req.density.value, req.seed)
    b_seed = None if req.seed is None else req.seed + 1
    b = providers.randomops.generate_operand(req.m, req.density.value, b_seed)
    return RandomResponse(
        field=field_info(req.m),
        density=req.density,
        seed=req.seed,
        a=_element(a, req.m),
        b=_element(b, req.m),
    )


# --------------------------------------------------------------------------- #
# 4. /api/parse-polynomials                                                    #
# --------------------------------------------------------------------------- #
@app.post("/api/parse-polynomials", response_model=ParseResponse, tags=["generate"])
def post_parse(req: ParseRequest) -> ParseResponse:
    try:
        pairs = providers.parser.parse_operand_file(
            req.content, req.filename, req.default_base.value
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"parse error: {exc}")
    return ParseResponse(
        count=len(pairs),
        pairs=[OperandPair(**p) for p in pairs],
    )


# --------------------------------------------------------------------------- #
# 5. /api/export-calculation                                                   #
# --------------------------------------------------------------------------- #
@app.post("/api/export-calculation", tags=["export"])
def post_export(req: ExportRequest):
    try:
        content, filename, media_type = providers.formatter.render(
            req.calculation, req.format.value
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"export error: {exc}")

    if req.download:
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return ExportResponse(filename=filename, media_type=media_type, content=content)


# --------------------------------------------------------------------------- #
# 6. /api/tutorial                                                             #
# --------------------------------------------------------------------------- #
@app.get("/api/tutorial", response_model=TutorialResponse, tags=["tutorial"])
def get_tutorial() -> TutorialResponse:
    data = providers.tutorial.load_tutorial()
    return TutorialResponse(
        version=data.get("version", "1.0"),
        title=data.get("title", "Tutorial"),
        slides=data.get("slides", []),
    )


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def _element(value: int, m: int):
    from .schemas import ElementReprModel

    return ElementReprModel(**polyrepr.ElementRepr.from_int(value, m).dict())

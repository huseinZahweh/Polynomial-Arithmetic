"""Unified FastAPI application hosting all 10 API endpoints and the web workbench.

Original Authors
----------------
* Hassan Tarhini — Milestone 2 (Core 6-endpoint FastAPI backend & CORS setup).
* Ali Zahreddine — Milestone 4 & Integration (Exploration router mount and
  ``/workbench/`` static frontend hosting).

Endpoints Served
----------------
Core REST API (6 endpoints):
    GET  /api/fields               List the 13 configured GF(2^m) fields
    POST /api/calculate            Run add, subtract, modulo, multiply, inverse, divide
    POST /api/random-polynomials   Generate sparse or dense random operands
    POST /api/parse-polynomials    Parse uploaded .txt / .json operand pairs
    POST /api/export-calculation   Render downloadable .md or .json summary reports
    GET  /api/tutorial             Serve the 4-slide tutorial and Ch. 4/5 presets

Teaching Explorations (4 endpoints via :mod:`backend.api.exploration_routes`):
    POST /api/explorations/modulus
    POST /api/explorations/aes-sbox
    POST /api/explorations/compare-multiplication
    GET  /api/explorations/multiplication-benchmarks

Static & Meta Routes:
    GET  /                         Service discovery metadata
    GET  /api/health               Liveness probe
    GET  /docs                     Interactive OpenAPI Swagger UI
    GET  /workbench/               Single-view educational Finite Field Lab GUI
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.engine import fields, formatter, parser, randomops, tutorial
from .exploration_routes import router as explorations_router
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
from .services import CalculationError, build_field_info, calculate, element_model, field_info

FRONTEND_DIR: Path = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(
    title="GF(2^m) Polynomial Arithmetic API",
    description="EECE 455/632 Project-3 — Unified Finite Field Lab backend & workbench.",
    version="1.0.0",
)

# Allow cross-origin requests for local classroom demos and decoupled tooling.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    """Return service metadata and links to OpenAPI docs and the web workbench."""
    return {
        "service": "gf2m-api",
        "version": app.version,
        "docs": "/docs",
        "workbench": "/workbench/",
    }


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    """Return a lightweight liveness indicator for automated checks."""
    return {"status": "ok"}


# --------------------------------------------------------------------------- #
# 1. GET /api/fields                                                          #
# --------------------------------------------------------------------------- #
@app.get("/api/fields", response_model=FieldsResponse, tags=["fields"])
def get_fields(include_textbook: bool = Query(True)) -> FieldsResponse:
    """List supported ``GF(2^m)`` fields and their irreducible moduli ``m(x)``.

    Args:
        include_textbook: Include small degrees ``2..8`` when ``True`` (default),
            or restrict to the 6 binary ECC degrees ``163..571`` when ``False``.

    Returns:
        :class:`FieldsResponse` with count and ordered list of :class:`FieldInfo`.
    """
    field_list = [
        build_field_info(field)
        for field in fields.list_fields(include_textbook=include_textbook)
    ]
    return FieldsResponse(count=len(field_list), fields=field_list)


# --------------------------------------------------------------------------- #
# 2. POST /api/calculate                                                      #
# --------------------------------------------------------------------------- #
@app.post("/api/calculate", response_model=CalculateResponse, tags=["calculate"])
def post_calculate(req: CalculateRequest) -> CalculateResponse | JSONResponse:
    """Execute one finite-field operation and return result, trace, verification, and metrics.

    Domain errors (unsupported field, invalid operand syntax, zero inverse /
    division by zero) return HTTP 400 with ``detail`` plus optional ``gcd``
    and ``trace`` payloads so the GUI can display Table 4.7 termination rows.

    Args:
        req: :class:`CalculateRequest` specifying field, operation, and operands.

    Returns:
        :class:`CalculateResponse` (HTTP 200) or structured error :class:`JSONResponse` (HTTP 400).
    """
    try:
        return calculate(req)
    except CalculationError as exc:
        payload: dict[str, object] = {"detail": str(exc)}
        if exc.gcd is not None:
            payload["gcd"] = exc.gcd
        if exc.trace is not None:
            payload["trace"] = exc.trace
        return JSONResponse(status_code=400, content=jsonable_encoder(payload))


# --------------------------------------------------------------------------- #
# 3. POST /api/random-polynomials                                             #
# --------------------------------------------------------------------------- #
@app.post("/api/random-polynomials", response_model=RandomResponse, tags=["generate"])
def post_random(req: RandomRequest) -> RandomResponse:
    """Generate nonzero random ``GF(2^m)`` operands in sparse or dense mode.

    Args:
        req: :class:`RandomRequest` with field degree ``m``, density, count, and optional seed.

    Returns:
        :class:`RandomResponse` containing structured ``a``/``b`` models and a
        formatted ``polynomials`` list in ``req.output_base``.

    Raises:
        HTTPException: Status 400 if ``req.m`` is not a supported field degree.
    """
    if not fields.is_supported(req.m):
        raise HTTPException(status_code=400, detail=f"unsupported field degree m={req.m}")
    values = []
    for index in range(req.count):
        seed = None if req.seed is None else req.seed + index
        value = randomops.generate_operand(req.m, req.density.value, seed)
        values.append(element_model(value, req.m))
    attribute = "poly" if req.output_base.value == "algebraic" else req.output_base.value
    return RandomResponse(
        field=field_info(req.m),
        density=req.density,
        seed=req.seed,
        a=values[0],
        b=values[1] if len(values) > 1 else None,
        m=req.m,
        output_base=req.output_base,
        polynomials=[getattr(value, attribute) for value in values],
    )


# --------------------------------------------------------------------------- #
# 4. POST /api/parse-polynomials                                              #
# --------------------------------------------------------------------------- #
@app.post("/api/parse-polynomials", response_model=ParseResponse, tags=["generate"])
def post_parse(req: ParseRequest) -> ParseResponse:
    """Validate and extract operand pairs from uploaded ``.txt`` or ``.json`` content.

    Args:
        req: :class:`ParseRequest` containing raw text, filename, and fallback base.

    Returns:
        :class:`ParseResponse` with parsed count and validated :class:`OperandPair` list.

    Raises:
        HTTPException: Status 400 prefixed with ``"parse error: "`` on invalid files.
    """
    try:
        pairs = parser.parse_operand_file(
            req.content,
            req.filename,
            req.default_base.value,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"parse error: {exc}") from exc
    return ParseResponse(
        count=len(pairs),
        pairs=[OperandPair(**pair) for pair in pairs],
    )


# --------------------------------------------------------------------------- #
# 5. POST /api/export-calculation                                             #
# --------------------------------------------------------------------------- #
@app.post("/api/export-calculation", response_model=None, tags=["export"])
def post_export(req: ExportRequest) -> Response | ExportResponse:
    """Render a calculation summary in Markdown or JSON (inline or as file download).

    Args:
        req: :class:`ExportRequest` carrying a calculation payload, format, and download flag.

    Returns:
        Attachment :class:`Response` when ``req.download=True``, otherwise :class:`ExportResponse`.

    Raises:
        HTTPException: Status 400 on unsupported export format.
    """
    try:
        content, filename, media_type = formatter.render(
            req.calculation,
            req.format.value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"export error: {exc}") from exc

    if req.download:
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return ExportResponse(filename=filename, media_type=media_type, content=content)


# --------------------------------------------------------------------------- #
# 6. GET /api/tutorial                                                        #
# --------------------------------------------------------------------------- #
@app.get("/api/tutorial", response_model=TutorialResponse, tags=["tutorial"])
def get_tutorial() -> TutorialResponse:
    """Serve the 4-slide educational tutorial and Chapter 4/5 classroom presets.

    Returns:
        :class:`TutorialResponse` loaded from ``data/tutorial_slides.json``.
    """
    data = tutorial.load_tutorial()
    return TutorialResponse(
        version=data.get("version", "1.0"),
        title=data.get("title", "Tutorial"),
        slides=data.get("slides", []),
    )


# Mount the 4 interactive exploration routes and the static web workbench.
app.include_router(explorations_router)
if FRONTEND_DIR.is_dir():
    app.mount("/workbench", StaticFiles(directory=FRONTEND_DIR, html=True), name="workbench")

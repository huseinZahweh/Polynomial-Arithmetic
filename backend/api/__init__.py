"""FastAPI REST API package for the GF(2^m) Polynomial Arithmetic workbench.

Original Authors
----------------
* Hassan Tarhini — Milestone 2 (Core 6-endpoint FastAPI controller, schemas, services).
* Ali Zahreddine — Milestone 4 & Integration (Exploration router, static frontend
  hosting, and unified engine wiring).
"""
from __future__ import annotations

from .main import app

__all__ = ["app"]

"""Root application launcher for the EECE 455 Finite Field Lab.

Original Author
---------------
Ali Zahreddine — Milestone 4 & Integration (Unified Application Launcher).

Usage
-----
Run from the repository root::

    python run.py
    python run.py --host 127.0.0.1 --port 8000 --reload

Or invoke Uvicorn directly::

    uvicorn backend.api.main:app --reload

Opens the web workbench at ``http://127.0.0.1:8000/workbench/`` and the
interactive OpenAPI documentation at ``http://127.0.0.1:8000/docs``.
"""
from __future__ import annotations

import argparse

import uvicorn


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI server options for host, port, and auto-reload.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Parsed :class:`argparse.Namespace` with ``host``, ``port``, and ``reload``.
    """
    parser = argparse.ArgumentParser(
        description="Launch the EECE 455 GF(2^m) Finite Field Lab server."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address for the ASGI server (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="TCP port for the ASGI server (default: 8000).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable Uvicorn auto-reload during local development.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Start the Uvicorn ASGI server serving ``backend.api.main:app``.

    Args:
        argv: Optional CLI argument list.
    """
    args = parse_args(argv)
    uvicorn.run(
        "backend.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

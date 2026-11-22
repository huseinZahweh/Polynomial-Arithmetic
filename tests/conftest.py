"""Shared pytest fixtures for the unified GF(2^m) engine, API, and E2E test suites."""
from __future__ import annotations

from contextlib import closing
import socket
from threading import Thread
import time

from fastapi.testclient import TestClient
import pytest
import uvicorn

from backend.api.main import app


@pytest.fixture(scope="session")
def client():
    """In-process FastAPI TestClient wired to the unified application."""
    with TestClient(app) as api_client:
        yield api_client


@pytest.fixture(scope="session")
def live_url():
    """Run the unified ASGI app on an ephemeral localhost port for Playwright tests."""
    with closing(socket.socket()) as sock:
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        worker = Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        worker.start()
        try:
            for _ in range(250):
                if server.started:
                    break
                time.sleep(0.02)
            assert server.started
            yield f"http://127.0.0.1:{sock.getsockname()[1]}/workbench/"
        finally:
            server.should_exit = True
            worker.join(timeout=5)

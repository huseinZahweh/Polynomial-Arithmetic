#!/usr/bin/env bash
# Start the Milestone 2 API (http://127.0.0.1:8000, docs at /docs).
set -euo pipefail
cd "$(dirname "$0")"
exec uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

"""Load the four classroom slides bundled with Milestone 1."""

import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "tutorial_slides.json"


def load_tutorial() -> dict:
    """Read the tutorial independently of the caller's working directory."""
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))

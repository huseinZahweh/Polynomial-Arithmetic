"""Reference tutorial-slide loader.

INTEGRATION CONTRACT — owned by Milestone 1 on merge (tutorial_slides.json).

Loads the 4-slide guided tutorial from ``data/tutorial_slides.json``. On merge,
point ``DATA_PATH`` at M1's slide file (or replace this module entirely).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "tutorial_slides.json"


@lru_cache(maxsize=1)
def load_tutorial() -> dict:
    with open(DATA_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)

"""Loader for the 4-slide educational tutorial and Chapter 4/5 textbook presets.

Original Author
---------------
Hussein Abbas — Milestone 1 (Field Configuration, I/O, Additive/Modulo & Utilities).

Purpose & Course References
---------------------------
Reads the canonical classroom tutorial JSON from ``data/tutorial_slides.json``
independently of the caller's working directory. Covers Stallings **Chapter 4**
(finite-field polynomial basis, modulo reduction, Shift-and-XOR, Extended Euclid
termination rules ``B3 = 1`` vs ``B3 = 0``) and **Chapter 5** (AES ``{95}^-1``).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Resolve <repo-root>/data/tutorial_slides.json relative to this module.
DATA_PATH: Path = Path(__file__).resolve().parents[2] / "data" / "tutorial_slides.json"


def load_tutorial() -> dict[str, Any]:
    """Load the structured 4-slide tutorial and textbook presets from disk.

    Returns:
        Dictionary containing ``"version"``, ``"title"``, and ``"slides"``
        (with Chapter 4 and Chapter 5 preset metadata embedded on Slide 4).

    Raises:
        FileNotFoundError: If ``data/tutorial_slides.json`` is missing.
        json.JSONDecodeError: If the JSON file is malformed.

    Complexity:
        Time ``O(S)``, space ``O(S)`` in file size ``S`` (a few kilobytes).
    """
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))

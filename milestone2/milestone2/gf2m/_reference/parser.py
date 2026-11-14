"""Reference batch operand-file parser.

INTEGRATION CONTRACT — owned by Milestone 1 on merge.

Parses uploaded ``.txt`` / ``.json`` operand-pair files into a list of
``{"a", "b", "base"}`` records the GUI can load. Tolerant of several common
layouts so students can hand-author test files:

JSON:
    {"base": "hex", "pairs": [{"a": "a1", "b": "0f"}, ...]}
    {"a": "a1", "b": "0f", "base": "hex"}            # single pair
    [{"a": "...", "b": "..."}, ...]                  # bare array

TXT (one pair per non-comment block; '#' starts a comment):
    A: a1
    B: 0f
    ---
    A = 1011        (base inferred per-line is not attempted; use 'base' line)
"""
from __future__ import annotations

import json
from typing import Dict, List


def _coerce_pairs(obj, default_base: str) -> List[Dict[str, str]]:
    pairs: List[Dict[str, str]] = []
    if isinstance(obj, dict) and "pairs" in obj:
        base = obj.get("base", default_base)
        for p in obj["pairs"]:
            pairs.append({"a": str(p["a"]), "b": str(p.get("b", "")), "base": p.get("base", base)})
    elif isinstance(obj, dict):
        base = obj.get("base", default_base)
        pairs.append({"a": str(obj["a"]), "b": str(obj.get("b", "")), "base": base})
    elif isinstance(obj, list):
        for p in obj:
            pairs.append(
                {"a": str(p["a"]), "b": str(p.get("b", "")), "base": p.get("base", default_base)}
            )
    else:
        raise ValueError("unrecognized JSON operand structure")
    return pairs


def parse_operand_file(content: str, filename: str = "", default_base: str = "hex") -> List[Dict[str, str]]:
    content = content.strip()
    if not content:
        raise ValueError("empty operand file")

    is_json = filename.lower().endswith(".json") or content[0] in "[{"
    if is_json:
        return _coerce_pairs(json.loads(content), default_base)

    # Plain-text parse.
    base = default_base
    pairs: List[Dict[str, str]] = []
    current: Dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line in ("---", "==="):
            if current:
                pairs.append({"a": current.get("a", ""), "b": current.get("b", ""), "base": base})
                current = {}
            continue
        if ":" in line or "=" in line:
            sep = ":" if ":" in line else "="
            key, _, val = line.partition(sep)
            key, val = key.strip().lower(), val.strip()
            if key == "base":
                base = val
            elif key in ("a", "a(x)"):
                current["a"] = val
            elif key in ("b", "b(x)"):
                current["b"] = val
    if current:
        pairs.append({"a": current.get("a", ""), "b": current.get("b", ""), "base": base})
    if not pairs:
        raise ValueError("no operand pairs found in file")
    return pairs

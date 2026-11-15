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


def _extract_pair(item, fallback_base: str) -> Dict[str, str]:
    if not isinstance(item, dict):
        raise ValueError("each operand pair must be a JSON object with string fields 'a' and optional 'b'")
    if "a" not in item or not isinstance(item["a"], str) or not item["a"].strip():
        raise ValueError("operand pair must include a non-empty string field 'a'")
    b_val = item.get("b", "")
    if not isinstance(b_val, str):
        raise ValueError("operand field 'b' must be a string when provided")
    base_val = item.get("base", fallback_base)
    if not isinstance(base_val, str) or base_val.strip().lower() not in ("hex", "bin"):
        raise ValueError(f"unsupported operand base {base_val!r}; expected 'hex' or 'bin'")
    return {"a": item["a"].strip(), "b": b_val.strip(), "base": base_val.strip().lower()}


def _coerce_pairs(obj, default_base: str) -> List[Dict[str, str]]:
    pairs: List[Dict[str, str]] = []
    if isinstance(obj, dict) and "pairs" in obj:
        base = obj.get("base", default_base)
        if not isinstance(base, str):
            raise ValueError("'base' must be a string ('hex' or 'bin')")
        raw_pairs = obj["pairs"]
        if not isinstance(raw_pairs, list):
            raise ValueError("'pairs' must be a JSON array of operand objects")
        for p in raw_pairs:
            pairs.append(_extract_pair(p, base))
    elif isinstance(obj, dict):
        base = obj.get("base", default_base)
        if not isinstance(base, str):
            raise ValueError("'base' must be a string ('hex' or 'bin')")
        pairs.append(_extract_pair(obj, base))
    elif isinstance(obj, list):
        for p in obj:
            pairs.append(_extract_pair(p, default_base))
    else:
        raise ValueError("unrecognized JSON operand structure")
    if not pairs:
        raise ValueError("no operand pairs found in JSON payload")
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

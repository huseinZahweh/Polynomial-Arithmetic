"""Reference random operand generator.

INTEGRATION CONTRACT — owned by Milestone 1 on merge.

Generates random GF(2^m) operands for one-click test scenarios. Density modes:
    "sparse" — a handful of set bits (easy to follow by hand)
    "dense"  — roughly half the bits set
    "random" — each bit independent fair coin
An optional seed makes generation reproducible (used by the test suite).
"""
from __future__ import annotations

import random
from typing import Optional, Tuple


def generate_operand(m: int, density: str = "random", seed: Optional[int] = None) -> int:
    rng = random.Random(seed)
    if density == "sparse":
        # between 1 and ~ceil(m/16) terms, always non-zero
        k = rng.randint(1, max(1, (m + 15) // 16))
        bits = rng.sample(range(m), k)
        value = 0
        for bphi in bits:
            value |= 1 << bphi
        return value or 1
    if density == "dense":
        value = 0
        for i in range(m):
            if rng.random() < 0.5:
                value |= 1 << i
        # guarantee the top bit so degree == m-1 and it's non-zero
        return value | (1 << (m - 1))
    if density == "random":
        value = rng.getrandbits(m)
        return value or 1
    raise ValueError(f"unknown density mode: {density!r}")


def generate_pair(
    m: int, density: str = "random", seed: Optional[int] = None
) -> Tuple[int, int]:
    base = random.Random(seed).getrandbits(31) if seed is not None else None
    a = generate_operand(m, density, None if base is None else base)
    b = generate_operand(m, density, None if base is None else base + 1)
    return a, b

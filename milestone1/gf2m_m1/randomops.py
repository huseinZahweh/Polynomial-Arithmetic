"""Generate nonzero field elements for classroom experiments."""

import random
import secrets

from .fields import get_field


def GENERATE_RANDOM_POLY(m: int, sparsity: str = "dense", *, seed: int | None = None) -> int:
    """Sample a nonzero m-bit value or a polynomial with three to six set bits.

    Sparse sampling caps the term range at m for the smallest fields. With
    no seed, both modes draw from the operating system's random source.
    """
    get_field(m)
    if seed is not None and type(seed) is not int:
        raise ValueError("seed must be an integer")
    rng = secrets.SystemRandom() if seed is None else random.Random(seed)

    if sparsity == "dense":
        return rng.randrange(1, 1 << m)
    if sparsity == "sparse":
        term_count = rng.randint(min(3, m - 1), min(6, m))
        return sum(1 << exponent for exponent in rng.sample(range(m), term_count))
    raise ValueError(f"unknown sparsity mode: {sparsity!r}")


def generate_operand(m: int, density: str = "random", seed: int | None = None) -> int:
    """Generate one value using the Milestone 2 density and seed arguments."""
    return GENERATE_RANDOM_POLY(m, "dense" if density == "random" else density, seed=seed)

"""Random nonzero GF(2^m) operand generator for classroom and test workflows.

Original Author
---------------
Hussein Abbas — Milestone 1 (Field Configuration, I/O, Additive/Modulo & Utilities).

Purpose & Course References
---------------------------
Samples nonzero field elements ``a(x) in GF(2^m) \\ {0}`` across all 13 configured
degrees (Stallings **Chapter 4** finite fields, **Chapter 5** AES ``GF(2^8)``, and
**Chapter 10** binary ECC ``GF(2^163)..GF(2^571)``):

* **Dense mode:** Uniformly random ``m``-bit element in ``[1, 2^m - 1]``.
* **Sparse mode:** Selects 3 to 6 distinct bit positions (clamped for small ``m``)
  so students can inspect compact Shift-and-XOR and Extended Euclid traces even
  in ``GF(2^163)`` or ``GF(2^571)``.
"""
from __future__ import annotations

import random
import secrets

from .fields import get_field


def GENERATE_RANDOM_POLY(
    m: int,
    sparsity: str = "dense",
    *,
    seed: int | None = None,
) -> int:
    """Sample a nonzero element in ``GF(2^m)`` in dense or sparse mode.

    Uses ``secrets.SystemRandom()`` (OS CSPRNG) by default when ``seed is None``,
    and a deterministic ``random.Random(seed)`` when a reproducible classroom
    or unit-test vector is requested.

    Args:
        m: Supported field extension degree from :mod:`backend.engine.fields`.
        sparsity: Sampling density — ``"dense"`` (uniform on ``[1, 2^m - 1]``)
            or ``"sparse"`` (3 to 6 set bits, clamped to ``[min(3, m-1), min(6, m)]``).
        seed: Optional integer PRNG seed for deterministic generation.

    Returns:
        Nonzero integer bitmask strictly less than ``2^m``.

    Raises:
        ValueError: If ``m`` is unsupported, ``seed`` is not an exact ``int``
            (rejecting ``bool``), or ``sparsity`` is unrecognized.

    Complexity:
        Dense mode: Time ``O(m)``, space ``O(m)``.
        Sparse mode: Time ``O(m)`` for ``rng.sample(range(m), k)``, space ``O(m)``.
    """
    get_field(m)
    if seed is not None and type(seed) is not int:
        raise ValueError("seed must be an integer")
    rng = secrets.SystemRandom() if seed is None else random.Random(seed)

    if sparsity == "dense":
        return rng.randrange(1, 1 << m)
    if sparsity == "sparse":
        # Clamp term count for tiny fields (e.g. m=2 yields 1..2 terms, m=3 yields 2..3).
        term_count = rng.randint(min(3, m - 1), min(6, m))
        return sum(1 << exponent for exponent in rng.sample(range(m), term_count))
    raise ValueError(f"unknown sparsity mode: {sparsity!r}")


def generate_operand(
    m: int,
    density: str = "random",
    seed: int | None = None,
) -> int:
    """Adapter for the REST API's ``density`` parameter (``random`` -> ``dense``).

    Args:
        m: Supported field extension degree.
        density: One of ``"random"``, ``"dense"``, or ``"sparse"``.
        seed: Optional deterministic integer seed.

    Returns:
        Nonzero integer bitmask in ``[1, 2^m - 1]``.

    Raises:
        ValueError: On unsupported degree, invalid density, or non-integer seed.

    Complexity:
        Same as :func:`GENERATE_RANDOM_POLY` — ``O(m)`` time and space.
    """
    return GENERATE_RANDOM_POLY(m, "dense" if density == "random" else density, seed=seed)

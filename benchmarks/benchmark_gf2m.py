"""Multi-field performance benchmark CLI for GF(2^m) Extended Euclid & Division.

Original Author
---------------
Husein Zahweh — Milestone 3 (Extended Euclid Inverse, Field Division & Verification).

Purpose & Course References
---------------------------
Measures runtime (``elapsed_ms`` via ``time.perf_counter()``) and Extended
Euclidean Algorithm iteration counts (average, min, max) for
:func:`backend.engine.EXTENDED_EUCLID_GF2M` and :func:`backend.engine.GF2M_DIVIDE`
across:

* ``m = 8`` — AES byte field (Stallings **Chapters 4 & 5**).
* ``m in {163, 233, 239, 283, 409, 571}`` — Standard binary ECC fields
  (Stallings **Chapter 10**; identical bit-level arithmetic generalizes to
  ``GF(2^128)`` XTS-AES in **Chapter 6**).

Both **sparse** (3–6 set bits) and **dense** (uniform random ``m``-bit) operands
are timed using deterministic seeded randomness, and every result is verified
outside the timed window via :func:`backend.engine.VERIFY_INVERSE` and
:func:`backend.engine.VERIFY_DIVISION`.

Usage (from repository root)::

    python -m benchmarks.benchmark_gf2m
    python -m benchmarks.benchmark_gf2m --trials 10 --seed 455
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import random
import statistics
import sys
import time
from typing import Sequence

# Ensure the repository root is importable if executed directly as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.engine import (  # noqa: E402
    EXTENDED_EUCLID_GF2M,
    GF2M_DIVIDE,
    VERIFY_DIVISION,
    VERIFY_INVERSE,
    get_m_poly_int,
)

BENCHMARK_DEGREES: tuple[int, ...] = (8, 163, 233, 239, 283, 409, 571)


@dataclass(frozen=True)
class BenchmarkRow:
    """Aggregated timing and iteration statistics for one ``(m_degree, mode)`` cell.

    Attributes:
        m_degree: Extension field degree ``m``.
        mode: Operand density mode (``"sparse"`` or ``"dense"``).
        trials: Number of deterministic trials averaged.
        eea_avg_ms, eea_min_ms, eea_max_ms: Extended Euclid timing stats in ms.
        eea_avg_iters, eea_min_iters, eea_max_iters: EEA division-loop iteration stats.
        div_avg_ms, div_min_ms, div_max_ms: Two-stage division timing stats in ms.
    """

    m_degree: int
    mode: str
    trials: int
    eea_avg_ms: float
    eea_min_ms: float
    eea_max_ms: float
    eea_avg_iters: float
    eea_min_iters: int
    eea_max_iters: int
    div_avg_ms: float
    div_min_ms: float
    div_max_ms: float


def _sample_sparse_nonzero(rng: random.Random, m_degree: int) -> int:
    """Sample a nonzero sparse polynomial with 3..6 set bits below degree ``m``.

    Args:
        rng: Seeded ``random.Random`` generator.
        m_degree: Field extension degree.

    Returns:
        Nonzero integer bitmask in ``[1, 2^m_degree - 1]``.

    Complexity:
        Time ``O(m_degree)``, space ``O(m_degree)``.
    """
    count = min(m_degree, rng.randint(3, 6))
    positions = rng.sample(range(m_degree), k=count)
    value = 0
    for pos in positions:
        value |= 1 << pos
    return value


def _sample_dense_nonzero(rng: random.Random, m_degree: int) -> int:
    """Sample a uniformly random nonzero ``m``-bit polynomial in ``[1, 2^m - 1]``.

    Args:
        rng: Seeded ``random.Random`` generator.
        m_degree: Field extension degree.

    Returns:
        Nonzero integer bitmask strictly below ``2^m_degree``.

    Complexity:
        Time ``O(m_degree)``, space ``O(m_degree)``.
    """
    return rng.randrange(1, 1 << m_degree)


def run_benchmarks(
    degrees: Sequence[int] = BENCHMARK_DEGREES,
    trials: int = 10,
    seed: int = 455,
) -> list[BenchmarkRow]:
    """Run timed Extended Euclid and Field Division benchmarks across degrees.

    Args:
        degrees: Sequence of supported field degrees to benchmark.
        trials: Number of deterministic operand pairs per ``(m_degree, mode)``.
        seed: Base PRNG seed for reproducible benchmark vectors.

    Returns:
        List of :class:`BenchmarkRow` records with timing and iteration stats.

    Raises:
        ValueError: If ``trials < 1`` or any degree in ``degrees`` is unsupported.
        AssertionError: If live self-verification fails on any computed result.

    Complexity:
        Time ``O(trials * sum(m^2 for m in degrees))`` bit operations;
        space ``O(trials + max(degrees)^2)``.
    """
    if trials < 1:
        raise ValueError(f"trials must be >= 1, got {trials}.")

    rows: list[BenchmarkRow] = []

    for m_degree in degrees:
        m_poly_int = get_m_poly_int(m_degree)
        for mode in ("sparse", "dense"):
            mode_seed = seed + m_degree * 10 + (1 if mode == "dense" else 0)
            rng = random.Random(mode_seed)
            sampler = _sample_sparse_nonzero if mode == "sparse" else _sample_dense_nonzero

            eea_times_ms: list[float] = []
            eea_iters: list[int] = []
            div_times_ms: list[float] = []

            for _ in range(trials):
                a_int = sampler(rng, m_degree)
                b_int = sampler(rng, m_degree)

                t0 = time.perf_counter()
                b_inv_int, inv_trace = EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_int)
                t1 = time.perf_counter()

                q_int, _ = GF2M_DIVIDE(a_int, b_int, m_poly_int, m_degree)
                t2 = time.perf_counter()

                # Verify algebraic identities strictly outside the timed intervals.
                if not VERIFY_INVERSE(b_int, b_inv_int, m_poly_int, m_degree)["verified"]:
                    raise AssertionError(
                        f"Inverse verification failed for m={m_degree}, b={b_int}"
                    )
                if not VERIFY_DIVISION(a_int, b_int, q_int, m_poly_int, m_degree)["verified"]:
                    raise AssertionError(
                        f"Division verification failed for m={m_degree}, a={a_int}, b={b_int}"
                    )

                eea_times_ms.append((t1 - t0) * 1000.0)
                eea_iters.append(int(inv_trace["termination"]["iterations"]))
                div_times_ms.append((t2 - t1) * 1000.0)

            rows.append(
                BenchmarkRow(
                    m_degree=m_degree,
                    mode=mode,
                    trials=trials,
                    eea_avg_ms=statistics.mean(eea_times_ms),
                    eea_min_ms=min(eea_times_ms),
                    eea_max_ms=max(eea_times_ms),
                    eea_avg_iters=statistics.mean(eea_iters),
                    eea_min_iters=min(eea_iters),
                    eea_max_iters=max(eea_iters),
                    div_avg_ms=statistics.mean(div_times_ms),
                    div_min_ms=min(div_times_ms),
                    div_max_ms=max(div_times_ms),
                )
            )

    return rows


def format_markdown_table(rows: Sequence[BenchmarkRow]) -> str:
    """Format benchmark rows as a GitHub-Flavored Markdown table.

    Args:
        rows: Sequence of :class:`BenchmarkRow` records.

    Returns:
        Markdown table string with MathJax-formatted ``$GF(2^{m})$`` labels.
    """
    header = (
        "| Field | Mode | Trials | EEA Avg (ms) | EEA Min/Max (ms) | "
        "EEA Iters Avg (Min-Max) | Div Avg (ms) | Div Min/Max (ms) |"
    )
    separator = "| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |"
    lines = [header, separator]
    for row in rows:
        lines.append(
            f"| $GF(2^{{{row.m_degree}}})$ | {row.mode.capitalize()} | {row.trials} | "
            f"{row.eea_avg_ms:.3f} | {row.eea_min_ms:.3f} / {row.eea_max_ms:.3f} | "
            f"{row.eea_avg_iters:.1f} ({row.eea_min_iters}-{row.eea_max_iters}) | "
            f"{row.div_avg_ms:.3f} | {row.div_min_ms:.3f} / {row.div_max_ms:.3f} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for running and printing multi-field GF(2^m) benchmarks.

    Args:
        argv: Optional CLI argument list (defaults to ``sys.argv[1:]``).
    """
    parser = argparse.ArgumentParser(
        description="Benchmark EXTENDED_EUCLID_GF2M and GF2M_DIVIDE across GF(2^m) fields."
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=10,
        help="Number of seeded operand pairs per (field, mode). Default: 10.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=455,
        help="Deterministic PRNG seed. Default: 455.",
    )
    args = parser.parse_args(argv)

    rows = run_benchmarks(trials=args.trials, seed=args.seed)
    print(f"# GF(2^m) Benchmark Results (trials={args.trials}, seed={args.seed})\n")
    print(format_markdown_table(rows))


if __name__ == "__main__":
    main()

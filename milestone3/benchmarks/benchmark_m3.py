"""Performance benchmark suite for Milestone 3 GF(2^m) inverse and division.

Measures runtime (``elapsed_ms`` via ``time.perf_counter()``) and Extended
Euclidean Algorithm iteration statistics (average, min, max) for
:func:`gf2m_m3.EXTENDED_EUCLID_GF2M` and :func:`gf2m_m3.GF2M_DIVIDE` across:

* ``m = 8`` (AES field, Stallings Ch. 4 & 5)
* ``m in {163, 233, 239, 283, 409, 571}`` (NIST/SEC binary ECC fields, Stallings Ch. 10)

Both **sparse** (3–6 non-zero terms) and **dense** (uniform random m-bit)
operands are benchmarked using deterministic seeded randomness, and every
timed output is verified for mathematical correctness via
:func:`gf2m_m3.VERIFY_INVERSE` and :func:`gf2m_m3.VERIFY_DIVISION`.

Usage (from ``milestone3/``)::

    python benchmarks/benchmark_m3.py
    python benchmarks/benchmark_m3.py --trials 10 --seed 455632
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import random
import statistics
import sys
import time
from typing import List, Sequence

# Ensure milestone3/ is on sys.path whether executed directly or as a module.
_MILESTONE3_ROOT = Path(__file__).resolve().parent.parent
if str(_MILESTONE3_ROOT) not in sys.path:
    sys.path.insert(0, str(_MILESTONE3_ROOT))

from gf2m_m3 import (  # noqa: E402
    EXTENDED_EUCLID_GF2M,
    GF2M_DIVIDE,
    VERIFY_DIVISION,
    VERIFY_INVERSE,
)
from gf2m_m3._reference import get_m_poly_int  # noqa: E402


BENCHMARK_DEGREES: tuple[int, ...] = (8, 163, 233, 239, 283, 409, 571)


@dataclass(frozen=True)
class BenchmarkRow:
    """Aggregated timing and iteration stats for one (m_degree, mode) cell."""

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
    """Generate a non-zero sparse polynomial with 3..6 set bits below degree m."""
    count = min(m_degree, rng.randint(3, 6))
    positions = rng.sample(range(m_degree), k=count)
    value = 0
    for pos in positions:
        value |= 1 << pos
    return value


def _sample_dense_nonzero(rng: random.Random, m_degree: int) -> int:
    """Generate a uniformly random non-zero m-bit polynomial in [1, 2^m - 1]."""
    return rng.randrange(1, 1 << m_degree)


def run_benchmarks(
    degrees: Sequence[int] = BENCHMARK_DEGREES,
    trials: int = 10,
    seed: int = 455632,
) -> List[BenchmarkRow]:
    """Run timed Extended Euclid and Field Division benchmarks across degrees.

    Args:
        degrees: Sequence of supported field degrees to benchmark.
        trials: Number of deterministic operand pairs per ``(m_degree, mode)``.
        seed: Base PRNG seed for reproducible benchmark vectors.

    Returns:
        List of :class:`BenchmarkRow` records containing timing and iteration metrics.
    """
    if trials < 1:
        raise ValueError(f"trials must be >= 1, got {trials}.")

    rows: List[BenchmarkRow] = []

    for m_degree in degrees:
        m_poly_int = get_m_poly_int(m_degree)
        for mode in ("sparse", "dense"):
            mode_seed = seed + m_degree * 10 + (1 if mode == "dense" else 0)
            rng = random.Random(mode_seed)
            sampler = _sample_sparse_nonzero if mode == "sparse" else _sample_dense_nonzero

            eea_times_ms: List[float] = []
            eea_iters: List[int] = []
            div_times_ms: List[float] = []

            for _ in range(trials):
                a_int = sampler(rng, m_degree)
                b_int = sampler(rng, m_degree)

                t0 = time.perf_counter()
                b_inv_int, inv_trace = EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_int)
                t1 = time.perf_counter()

                q_int, _ = GF2M_DIVIDE(a_int, b_int, m_poly_int, m_degree)
                t2 = time.perf_counter()

                # Verify correctness outside the timed intervals.
                if not VERIFY_INVERSE(b_int, b_inv_int, m_poly_int, m_degree)["verified"]:
                    raise AssertionError(f"Inverse verification failed for m={m_degree}, b={b_int}")
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
    """Format benchmark results as a GitHub-Flavored Markdown table."""
    header = (
        "| Field | Mode | Trials | EEA Avg (ms) | EEA Min/Max (ms) | "
        "EEA Iters Avg (Min-Max) | Div Avg (ms) | Div Min/Max (ms) |"
    )
    separator = (
        "| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    lines = [header, separator]
    for r in rows:
        lines.append(
            f"| $GF(2^{{{r.m_degree}}})$ | {r.mode.capitalize()} | {r.trials} | "
            f"{r.eea_avg_ms:.3f} | {r.eea_min_ms:.3f} / {r.eea_max_ms:.3f} | "
            f"{r.eea_avg_iters:.1f} ({r.eea_min_iters}-{r.eea_max_iters}) | "
            f"{r.div_avg_ms:.3f} | {r.div_min_ms:.3f} / {r.div_max_ms:.3f} |"
        )
    return "\n".join(lines)


def main() -> None:
    """CLI entry point for Milestone 3 multi-field performance benchmarks."""
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
        default=455632,
        help="Deterministic PRNG seed. Default: 455632.",
    )
    args = parser.parse_args()

    rows = run_benchmarks(trials=args.trials, seed=args.seed)
    print(f"# Milestone 3 Benchmark Results (trials={args.trials}, seed={args.seed})\n")
    print(format_markdown_table(rows))


if __name__ == "__main__":
    main()

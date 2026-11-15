# Milestone 3: Extended Euclid Inverse, Field Division & Verification Suite

**Project:** EECE 455/632 — Project-3: Polynomial Arithmetic in $GF(2^m)$  
**Owner:** Husein Zahweh  
**Scope:** Polynomial Long Division (`POLY_DIVMOD`), Carry-Free Multiplication (`POLY_MUL_NO_MOD`), Extended Euclidean Multiplicative Inverse (`EXTENDED_EUCLID_GF2M`) with Stallings Table 4.7 traces, Two-Stage Field Division (`GF2M_DIVIDE`), Live Algebraic Self-Verifiers (`VERIFY_INVERSE`, `VERIFY_DIVISION`), and Multi-Field `pytest` Verification & Benchmark Suite.

---

## 1. Repository Structure

```text
milestone3/
├── .gitignore
├── MILESTONE3_EXPLAINED.md          # Full technical, mathematical & integration reference
├── README.md                        # Quickstart, API overview, benchmarks & M5 guide
├── pytest.ini                       # Pytest config (pythonpath = ., testpaths = tests)
├── requirements.txt                 # Minimal standalone dependency (pytest>=8.0)
├── benchmarks/
│   ├── __init__.py
│   └── benchmark_m3.py              # Timed multi-field EEA & division benchmark CLI
├── gf2m_m3/
│   ├── __init__.py                  # Public Milestone 3 exports
│   ├── exceptions.py                # GF2mInverseError, ZeroElementHasNoInverseError, NotInvertibleError
│   ├── poly_ops.py                  # POLY_MUL_NO_MOD & POLY_DIVMOD
│   ├── extended_euclid.py           # EXTENDED_EUCLID_GF2M + Table 4.7 trace logger
│   ├── division.py                  # GF2M_DIVIDE (two-stage inverse + multiply)
│   ├── verification.py              # VERIFY_INVERSE & VERIFY_DIVISION
│   └── _reference/                  # Isolated M1/M2 stand-ins (swapped out in Milestone 5)
│       ├── __init__.py
│       ├── fields.py                # 13 Plan-01 fields (2 <= m <= 8 and 163..571)
│       ├── utilities.py             # deg, mod_reduce, formatting & validation helpers
│       └── multiply.py              # Shift-and-XOR gf2m_multiply returning (int, trace_dict)
└── tests/
    ├── __init__.py
    ├── test_step1_smoke.py
    ├── test_step2_poly_ops.py
    ├── test_step3_extended_euclid.py
    ├── test_step4_division_and_verify.py
    └── test_step5_multifield_verification.py
```

---

## 2. Quickstart: Running Tests & Benchmarks

Run all commands from inside `milestone3/`:

```bash
# 1. Install test runner (only pytest is required; arithmetic engine uses Python stdlib)
pip install -r requirements.txt

# 2. Run the full 87-test verification suite (verbose)
python -m pytest -v

# 3. Run the multi-field performance benchmark (m = 8 and m in {163, 233, 239, 283, 409, 571})
python benchmarks/benchmark_m3.py --trials 10 --seed 455632
```

---

## 3. Public API Summary

Every polynomial is passed as a **non-negative Python `int`** where bit $i$ (counting from $0$ as LSB) encodes the coefficient of $x^i$, and $m(x)$ includes bit $m$ set to $1$ (e.g., AES $x^8 + x^4 + x^3 + x + 1 \leftrightarrow \text{0x11B} = 283$). Negative integers raise `ValueError`.

| Symbol | Signature | Return Contract |
| :--- | :--- | :--- |
| `POLY_MUL_NO_MOD` | `(a_int: int, b_int: int) -> int` | Unreduced carry-free product $a(x) \cdot b(x)$ over $GF(2)[x]$ |
| `POLY_DIVMOD` | `(a_int: int, b_int: int) -> Tuple[int, int]` | `(q_int, r_int)` with $A(x) = Q(x)B(x) \oplus R(x)$, $\deg(R) < \deg(B)$ |
| `EXTENDED_EUCLID_GF2M` | `(m_poly_int: int, m_degree: int, b_int: int) -> Tuple[int, Dict[str, Any]]` | `(b_inv_int, trace_dict)` with full Table 4.7 rows & cell formats |
| `GF2M_DIVIDE` | `(a_int: int, b_int: int, m_poly_int: int, m_degree: int) -> Tuple[int, Dict[str, Any]]` | `(quotient_int, trace_dict)` combining Stage 1 (EEA) & Stage 2 (Multiply) |
| `VERIFY_INVERSE` | `(b_int: int, b_inv_int: int, m_poly_int: int, m_degree: int) -> Dict[str, Any]` | Proof object checking $b(x) \cdot b(x)^{-1} \bmod m(x) = 1$ |
| `VERIFY_DIVISION` | `(a_int: int, b_int: int, q_int: int, m_poly_int: int, m_degree: int) -> Dict[str, Any]` | Proof object checking $(a(x)/b(x)) \cdot b(x) \bmod m(x) = a(x) \bmod m(x)$ |

### Custom Exceptions (`gf2m_m3.exceptions`)
* `GF2mInverseError(ValueError)`: Shared base exception carrying `.gcd: int` and `.trace: Optional[Any]`.
* `ZeroElementHasNoInverseError(GF2mInverseError)`: Raised when $b(x) \bmod m(x) = 0$ (Step 0 termination with $B_3 = 0$ and $A_3 = \gcd(m(x), 0) = m(x)$).
* `NotInvertibleError(GF2mInverseError)`: Raised when $B_3 = 0$ mid-loop with non-trivial common factor $A_3 = \gcd(m(x), b(x)) \neq 1$ (reducible $m(x)$).

---

## 4. Benchmark Snapshot (`--trials 10 --seed 455632`)

Measured with `time.perf_counter()` including full Table 4.7 formatted cell logging (`EXTENDED_EUCLID_GF2M`) and Shift-and-XOR tracing (`GF2M_DIVIDE`):

| Field | Mode | Trials | EEA Avg (ms) | EEA Min/Max (ms) | EEA Iters Avg (Min-Max) | Div Avg (ms) | Div Min/Max (ms) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| $GF(2^{8})$ | Sparse | 10 | 0.143 | 0.084 / 0.212 | 4.3 (2-6) | 0.198 | 0.128 / 0.257 |
| $GF(2^{8})$ | Dense | 10 | 0.135 | 0.068 / 0.201 | 3.5 (1-6) | 0.194 | 0.099 / 0.270 |
| $GF(2^{163})$ | Sparse | 10 | 3.716 | 1.319 / 4.973 | 34.7 (14-53) | 9.482 | 7.573 / 12.064 |
| $GF(2^{163})$ | Dense | 10 | 8.449 | 7.376 / 9.703 | 79.1 (70-89) | 17.620 | 16.839 / 19.196 |
| $GF(2^{233})$ | Sparse | 10 | 7.610 | 3.113 / 11.923 | 55.6 (26-83) | 18.567 | 12.953 / 23.807 |
| $GF(2^{233})$ | Dense | 10 | 24.151 | 16.008 / 38.756 | 118.5 (103-126) | 52.327 | 34.235 / 79.920 |
| $GF(2^{239})$ | Sparse | 10 | 17.645 | 1.650 / 36.203 | 68.8 (15-115) | 36.780 | 10.183 / 61.270 |
| $GF(2^{239})$ | Dense | 10 | 16.478 | 14.587 / 17.393 | 114.2 (104-119) | 35.549 | 33.013 / 38.440 |
| $GF(2^{283})$ | Sparse | 10 | 14.382 | 9.671 / 31.287 | 70.1 (39-114) | 34.616 | 24.968 / 61.036 |
| $GF(2^{283})$ | Dense | 10 | 35.298 | 22.836 / 56.949 | 143.7 (131-154) | 78.493 | 50.224 / 120.225 |
| $GF(2^{409})$ | Sparse | 10 | 25.581 | 13.896 / 32.955 | 109.5 (73-150) | 64.356 | 52.134 / 97.664 |
| $GF(2^{409})$ | Dense | 10 | 65.402 | 45.887 / 114.623 | 205.2 (182-219) | 153.561 | 104.755 / 240.363 |
| $GF(2^{571})$ | Sparse | 10 | 48.406 | 17.232 / 105.639 | 98.2 (47-166) | 141.211 | 81.883 / 218.369 |
| $GF(2^{571})$ | Dense | 10 | 133.564 | 89.039 / 231.960 | 288.1 (266-303) | 316.274 | 210.241 / 481.114 |

---

## 5. Milestone 5 Integration Guide (`app/providers.py`)

Milestone 3 isolates all Milestone 1/2 stand-in helpers inside `gf2m_m3/_reference/`. During Milestone 5 integration:

1. **Swap Reference Imports:** Point `gf2m_m3/_reference/utilities.py`, `fields.py`, and `multiply.py` imports to Milestone 1's authoritative field registry / modulo reduction / converters and Milestone 2's `gf2m.multiply`.
2. **Wire into Milestone 2's `app/providers.py`:** Expose an adapter satisfying `providers.invdiv` (`NoInverseError`, `inverse`, `divide`) while preserving the full M3 Table 4.7 and two-stage traces:

```python
from gf2m_m3 import (
    EXTENDED_EUCLID_GF2M,
    GF2M_DIVIDE,
    GF2mInverseError as NoInverseError,
    VERIFY_DIVISION,
    VERIFY_INVERSE,
)

def inverse(a: int, mod_poly: int, m: int, with_trace: bool = False):
    b_inv_int, trace = EXTENDED_EUCLID_GF2M(mod_poly, m, a)
    return (b_inv_int, trace) if with_trace else b_inv_int

def divide(a: int, b: int, mod_poly: int, m: int, with_trace: bool = False):
    quotient_int, trace = GF2M_DIVIDE(a, b, mod_poly, m)
    return (quotient_int, trace) if with_trace else quotient_int
```

See [MILESTONE3_EXPLAINED.md](./MILESTONE3_EXPLAINED.md) for detailed schemas, worked mathematical derivations, and end-to-end integration notes.

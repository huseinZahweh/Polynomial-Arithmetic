# Milestone 3 — Extended Euclid Inverse, Field Division & Verification Suite
### Full Technical Reference & Mathematical Explanation

**Project:** Polynomial Arithmetic in $GF(2^m)$ — EECE 455/632 (Project-3)  
**Assigned Owner:** Husein Zahweh  
**Textbook References:** William Stallings, *Cryptography and Network Security*, **Chapter 4** (Finite Fields), **Chapter 5** (AES), **Chapter 6** (XTS-AES over $GF(2^{128})$), and **Chapter 10** (Binary Elliptic Curve Cryptography over $GF(2^{163}) \dots GF(2^{571})$).

---

## 1. Architectural Overview & Folder Layout

Milestone 3 implements the inversion, polynomial long-division, field division, live self-verification, and multi-field verification layers in pure Python over arbitrary-precision `int` bit-strings:

```text
milestone3/
├── .gitignore
├── MILESTONE3_EXPLAINED.md
├── README.md
├── pytest.ini
├── requirements.txt
├── benchmarks/
│   ├── __init__.py
│   └── benchmark_m3.py
├── gf2m_m3/
│   ├── __init__.py
│   ├── division.py                  # GF2M_DIVIDE (Stage 1 EEA + Stage 2 Shift-and-XOR)
│   ├── exceptions.py                # GF2mInverseError, ZeroElementHasNoInverseError, NotInvertibleError
│   ├── extended_euclid.py           # EXTENDED_EUCLID_GF2M + Stallings Table 4.7 trace logger
│   ├── poly_ops.py                  # POLY_MUL_NO_MOD & POLY_DIVMOD
│   ├── verification.py              # VERIFY_INVERSE & VERIFY_DIVISION
│   └── _reference/                  # Isolated M1 & M2 stand-ins for standalone execution
│       ├── __init__.py
│       ├── fields.py                # 13 Plan-01 fields: 2 <= m <= 8 and m in {163..571}
│       ├── multiply.py              # Shift-and-XOR gf2m_multiply returning (int, trace_dict)
│       └── utilities.py             # deg, mod_reduce, Hex/Bin/Algebraic formatters, validators
└── tests/
    ├── __init__.py
    ├── test_step1_smoke.py
    ├── test_step2_poly_ops.py
    ├── test_step3_extended_euclid.py
    ├── test_step4_division_and_verify.py
    └── test_step5_multifield_verification.py
```

### Shared Integer Polynomial Contract
Every polynomial $p(x) = \sum_{i=0}^{d} c_i x^i \in GF(2)[x]$ is encoded as a **non-negative Python `int`** where bit $i$ (counting from $0$ as LSB) equals $c_i \in \{0, 1\}$. The reduction polynomial $m(x)$ of degree $m$ always has bit $m$ set to $1$:

$$
m(x) = x^8 + x^4 + x^3 + x + 1 \iff \text{100011011}_2 = \text{0x11B} = 283
$$

All public functions reject negative integers with `ValueError` and booleans or non-integers with `TypeError`.

---

## 2. Cryptographic & Textbook Field Registry (`_reference/fields.py`)

Milestone 3 ships with an isolated stand-in for Milestone 1's field registry covering all 13 Plan-01 fields:

| Category | Degree $m$ | Tap List $T$ | Irreducible Polynomial $m(x)$ | Standard / Course Role |
| :--- | :---: | :--- | :--- | :--- |
| Textbook | $2$ | `[2, 1, 0]` | $x^2 + x + 1$ | Project-2 small field |
| Textbook | $3$ | `[3, 2, 0]` | $x^3 + x^2 + 1$ | Project-2 / Plan 01 |
| Textbook | $4$ | `[4, 3, 0]` | $x^4 + x^3 + 1$ | Project-2 / Plan 01 |
| Textbook | $5$ | `[5, 2, 0]` | $x^5 + x^2 + 1$ | Project-2 small field |
| Textbook | $6$ | `[6, 1, 0]` | $x^6 + x + 1$ | Project-2 small field |
| Textbook | $7$ | `[7, 1, 0]` | $x^7 + x + 1$ | Project-2 small field |
| Textbook / AES | $8$ | `[8, 4, 3, 1, 0]` | $x^8 + x^4 + x^3 + x + 1$ | **Stallings Ch. 4 Table 4.7 & Ch. 5 AES S-Box** |
| Cryptographic | $163$ | `[163, 7, 6, 3, 0]` | $x^{163} + x^7 + x^6 + x^3 + 1$ | **Stallings Ch. 10** NIST B-163 / K-163 (Default) |
| Cryptographic | $233$ | `[233, 74, 0]` | $x^{233} + x^{74} + 1$ | **Stallings Ch. 10** NIST B-233 / K-233 |
| Cryptographic | $239$ | `[239, 158, 0]` | $x^{239} + x^{158} + 1$ | **Stallings Ch. 10** SEC `sect239k1` |
| Cryptographic | $283$ | `[283, 12, 7, 5, 0]` | $x^{283} + x^{12} + x^7 + x^5 + 1$ | **Stallings Ch. 10** NIST B-283 / K-283 |
| Cryptographic | $409$ | `[409, 87, 0]` | $x^{409} + x^{87} + 1$ | **Stallings Ch. 10** NIST B-409 / K-409 |
| Cryptographic | $571$ | `[571, 10, 5, 2, 0]` | $x^{571} + x^{10} + x^5 + x^2 + 1$ | **Stallings Ch. 10** NIST B-571 / K-571 |

> **Related Block-Cipher Context (Stallings Chapter 6):** XTS-AES tweaks rely on polynomial arithmetic in $GF(2^{128})$ modulo $x^{128} + x^7 + x^2 + x + 1$; the identical `POLY_MUL_NO_MOD`, `POLY_DIVMOD`, and `EXTENDED_EUCLID_GF2M` integer primitives generalize directly to $m = 128$ whenever supplied with that reduction polynomial.

---

## 3. Mathematical Foundations & Algorithms

### 3.1 Carry-Free Multiplication & Euclidean Long Division (`poly_ops.py`)

Over $\mathbb{Z}_2[x]$, addition and subtraction of coefficients are identical and reduce to bitwise XOR ($\oplus$) without carries:

1. **`POLY_MUL_NO_MOD(a_int, b_int) -> int`** computes the unreduced product $a(x) \cdot b(x) \in GF(2)[x]$. Because multiplication is commutative, the loop walks the bits of the smaller-degree operand so fewer shifts are needed.
2. **`POLY_DIVMOD(a_int, b_int) -> (q_int, r_int)`** finds unique $Q(x)$ and $R(x)$ satisfying:

$$
A(x) = Q(x) \cdot B(x) \oplus R(x), \quad R(x) = 0 \text{ or } \deg(R) < \deg(B)
$$

At each step where $\deg(R) \ge \deg(B)$, let $s = \deg(R) - \deg(B)$; setting bit $s$ in $Q(x)$ and XORing $R(x)$ with $(B(x) \ll s)$ eliminates the leading $x^{\deg(R)}$ term. Calling `POLY_DIVMOD` with `b_int == 0` raises `ZeroDivisionError`.

### 3.2 Extended Euclidean Algorithm (`extended_euclid.py`)

Given modulus $m(x)$ of degree $m$ and input polynomial $b(x)$:

1. **Initial Modulo Reduction:** Reduce $b(x)$ first via `b_red, b_mod_trace = mod_reduce(b_int, m_poly_int, m_degree)` so inputs with $\deg(b) \ge m$ (including $b(x) = m(x)$) map faithfully into $GF(2^m)$.
2. **Initialization (Step 0):**

$$
(A_1, A_2, A_3) \leftarrow (1, 0, m(x)), \qquad (B_1, B_2, B_3) \leftarrow (0, 1, b_{\text{red}}(x))
$$

   Step `0` is always logged first into `table_4_7_rows` with `Q = None` (formatted as `"-"`).
3. **Recurrence Invariant:** At every step, $A_1 m(x) \oplus A_2 b_{\text{red}}(x) = A_3$ and $B_1 m(x) \oplus B_2 b_{\text{red}}(x) = B_3$. During each iteration (`while B3 != 1`):

$$
(Q, T_3) = \text{POLY\_DIVMOD}(A_3, B_3), \quad T_1 = A_1 \oplus (Q \cdot B_1), \quad T_2 = A_2 \oplus (Q \cdot B_2)
$$

   Then shift $(A_1, A_2, A_3) \leftarrow (B_1, B_2, B_3)$ and $(B_1, B_2, B_3) \leftarrow (T_1, T_2, T_3)$, and append the row.

4. **Both Stallings Termination Rules:**
   * **Case 1 — Inverse Found (`B3 == 1`):** Since $B_1 m(x) \oplus B_2 b_{\text{red}}(x) = 1$, $\gcd(m(x), b(x)) = 1$ and $B_2(x) \bmod m(x)$ is the unique multiplicative inverse $b(x)^{-1} \bmod m(x)$. Returns `(b_inv_int, trace_dict)`.
   * **Case 2 — No Inverse (`B3 == 0`):**
     * **At Step 0 (`b_red == 0`):** $b(x)$ is congruent to $0 \pmod{m(x)}$. No inverse exists, and $A_3 = \gcd(m(x), 0) = m(x)$. Raises `ZeroElementHasNoInverseError(gcd=A3, trace=trace_dict)` with Step `0` preserved.
     * **Mid-Loop (`B3 == 0` after $\ge 1$ steps):** Occurs when a reducible modulus $m(x)$ shares a non-trivial factor $A_3 = \gcd(m(x), b(x))$ ($\deg(A_3) \ge 1$) with $b(x)$. Raises `NotInvertibleError(gcd=A3, trace=trace_dict)` preserving all rows up to `B3 == 0`.

### 3.3 Worked Textbook Reproduction: Stallings Chapter 4 Table 4.7

For $m(x) = x^8 + x^4 + x^3 + x + 1 = \text{0x11B}$ and $b(x) = x^7 + x + 1 = \text{0x83}$:

| Step | $Q(x)$ | $A_1(x)$ | $A_2(x)$ | $A_3(x)$ | $B_1(x)$ | $B_2(x)$ | $B_3(x)$ |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `0` | `-` | `1` (`01`) | `0` (`00`) | $x^8+x^4+x^3+x+1$ (`11B`) | `0` (`00`) | `1` (`01`) | $x^7+x+1$ (`83`) |
| `1` | $x$ (`02`) | `0` (`00`) | `1` (`01`) | $x^7+x+1$ (`83`) | `1` (`01`) | $x$ (`02`) | $x^4+x^3+x^2+1$ (`1D`) |
| `2` | $x^3+x^2+1$ (`0D`) | `1` (`01`) | $x$ (`02`) | $x^4+x^3+x^2+1$ (`1D`) | $x^3+x^2+1$ (`0D`) | $x^4+x^3+x+1$ (`1B`) | $x$ (`02`) |
| `3` | $x^3+x^2+x$ (`0E`) | $x^3+x^2+1$ (`0D`) | $x^4+x^3+x+1$ (`1B`) | $x$ (`02`) | $x^6+x^2+x+1$ (`47`) | **$x^7$ (`80`)** | **`1` (`01`)** |

At Step 3, $B_3(x) = 1$, so $b(x)^{-1} = B_2(x) = x^7 = \text{0x80}$ in 3 division iterations (4 table rows including Step 0). Similarly, for the Chapter 5 AES S-Box example $b(x) = \{95\}$, `EXTENDED_EUCLID_GF2M(0x11B, 8, 0x95)` returns $\{8\text{A}\} = x^7 + x^3 + x$ in 3 division iterations.

### 3.4 Field Division (`division.py`) & Live Self-Verifiers (`verification.py`)

Field division computes:

$$
\frac{a(x)}{b(x)} \bmod m(x) = a(x) \times \left(b(x)^{-1} \bmod m(x)\right) \bmod m(x)
$$

1. `GF2M_DIVIDE(a_int, b_int, m_poly_int, m_degree)` reduces `a_int` and `b_int`, runs `EXTENDED_EUCLID_GF2M` on `b_int` (Stage 1), and multiplies `a_red` by `b_inv_int` via `gf2m_multiply` (Stage 2).
2. `VERIFY_INVERSE(b_int, b_inv_int, m_poly_int, m_degree)` verifies `b_inv_int < 2^m_degree` and $b(x) \cdot b(x)^{-1} \bmod m(x) = 1$.
3. `VERIFY_DIVISION(a_int, b_int, q_int, m_poly_int, m_degree)` verifies `b_red != 0`, `q_int < 2^m_degree`, and $(a(x)/b(x)) \cdot b(x) \bmod m(x) = a(x) \bmod m(x)$.

---

## 4. Public Function Signatures, Exceptions & Trace JSON Schemas

### 4.1 Exact Public Signatures (`gf2m_m3`)

```python
from gf2m_m3 import (
    EXTENDED_EUCLID_GF2M,
    GF2M_DIVIDE,
    GF2mInverseError,
    NotInvertibleError,
    POLY_DIVMOD,
    POLY_MUL_NO_MOD,
    VERIFY_DIVISION,
    VERIFY_INVERSE,
    ZeroElementHasNoInverseError,
)
```

* `POLY_MUL_NO_MOD(a_int: int, b_int: int) -> int`
* `POLY_DIVMOD(a_int: int, b_int: int) -> Tuple[int, int]`
* `EXTENDED_EUCLID_GF2M(m_poly_int: int, m_degree: int, b_int: int) -> Tuple[int, Dict[str, Any]]`
* `GF2M_DIVIDE(a_int: int, b_int: int, m_poly_int: int, m_degree: int) -> Tuple[int, Dict[str, Any]]`
* `VERIFY_INVERSE(b_int: int, b_inv_int: int, m_poly_int: int, m_degree: int) -> Dict[str, Any]`
* `VERIFY_DIVISION(a_int: int, b_int: int, q_int: int, m_poly_int: int, m_degree: int) -> Dict[str, Any]`

### 4.2 Custom Exception Attributes

Both `ZeroElementHasNoInverseError` and `NotInvertibleError` inherit from `GF2mInverseError(ValueError)` and attach:
* `.gcd` (`int`): $A_3(x) = \gcd(m(x), b(x))$ (`m_poly_int` when $b_{\text{red}} = 0$, or the shared non-trivial factor for reducible $m(x)$).
* `.trace` (`Dict[str, Any]`): The full Table 4.7 `trace_dict` captured up to the `B3 == 0` termination row so the API and GUI can still render the exact Table 4.7 explanation.

### 4.3 Table 4.7 Trace Schema (`EXTENDED_EUCLID_GF2M`)

```json
{
  "trace_type": "extended_euclid_table_4_7",
  "m_degree": 8,
  "m_poly_int": 283,
  "m_poly_formatted": {"int": 283, "hex": "11B", "bin": "100011011", "algebraic": "x^8 + x^4 + x^3 + x + 1", "degree": 8},
  "b_input_int": 131,
  "b_reduced_int": 131,
  "initial_reduction": {
    "was_reduced": false,
    "note": "Input b(x) already satisfied deg(b) < m; no initial reduction required.",
    "mod_trace": {"trace_type": "mod_reduce", "was_reduced": false, "step_count": 0, "steps": []}
  },
  "termination": {
    "status": "invertible",
    "b3_final": 1,
    "gcd_int": 1,
    "inverse_int": 128,
    "iterations": 3,
    "total_rows": 4
  },
  "table_4_7_rows": [
    {
      "step": 0,
      "Q": null,
      "A1": 1, "A2": 0, "A3": 283,
      "B1": 0, "B2": 1, "B3": 131,
      "cells": {
        "Q": {"int": null, "hex": "-", "bin": "-", "algebraic": "-", "degree": null},
        "A1": {"int": 1, "hex": "01", "bin": "00000001", "algebraic": "1", "degree": 0},
        "B3": {"int": 131, "hex": "83", "bin": "10000011", "algebraic": "x^7 + x + 1", "degree": 7}
      }
    }
  ]
}
```

### 4.4 Two-Stage Division Trace & Verification Schemas

* `GF2M_DIVIDE` returns `(quotient_int, trace_dict)` with:
  * `trace_type`: `"gf2m_division_two_stage"`
  * `initial_reduction`: `a_was_reduced`, `b_was_reduced`, `a_mod_trace`, `b_mod_trace`
  * `inverse_of_b_int` & `inverse_of_b` (formatted `{int, hex, bin, algebraic, degree}`)
  * `quotient_int` & `quotient_formatted`
  * `stage_1_inverse`: full Table 4.7 trace dict from `EXTENDED_EUCLID_GF2M`
  * `stage_2_multiply`: full Shift-and-XOR trace dict from `gf2m_multiply`
* `VERIFY_INVERSE` and `VERIFY_DIVISION` return:

```json
{
  "verified": true,
  "passed": true,
  "label": "b(x) * b^-1(x) mod m(x) == 1",
  "equation": "b(x) * b^-1(x) mod m(x) == 1",
  "check_result": 1,
  "expected_result": 1,
  "is_reduced_element": true
}
```

---

## 5. Complexity Analysis

Let $m = m_{\text{degree}}$, $d_a = \deg(a)$, and $d_b = \deg(b)$:

| Function | Time Complexity (Bit Ops) | Space / Trace Complexity | Notes |
| :--- | :--- | :--- | :--- |
| `POLY_MUL_NO_MOD` | $O(\min(d_a, d_b) \cdot (d_a + d_b))$ | $O(d_a + d_b)$ | Loops over shorter operand |
| `POLY_DIVMOD` | $O((d_a - d_b + 1) \cdot d_a)$ | $O(d_a)$ | $O(1)$ when $d_a < d_b$ |
| `EXTENDED_EUCLID_GF2M` | $O(m^2)$ | $O(m^2)$ | $\le m$ steps (avg $\approx m/2$) |
| `GF2M_DIVIDE` | $O(m^2)$ | $O(m^2)$ | 1 EEA + 1 Shift-and-XOR |
| `VERIFY_INVERSE` / `VERIFY_DIVISION` | $O(m^2)$ | $O(m)$ | Single modular multiply check |

---

## 6. Verification & Benchmark Results

### 6.1 Automated Test Suite (`87` tests in `tests/`)
* `test_step1_smoke.py` (`19` tests): Package exports, exception attributes, all 13 Plan-01 field polynomials (including $m=3 \rightarrow [3,2,0]$ and $m=4 \rightarrow [4,3,0]$), formatting helpers, negative integer validation, and reference Ch. 4/5 smoke vectors.
* `test_step2_poly_ops.py` (`23` tests): Zero/identity operands, GF(2) carry-free cancellation, commutativity/distributivity, $\deg(A) < \deg(B)$, $\deg(A) = \deg(B)$, exact divisibility, `ZeroDivisionError`, and `POLY_DIVMOD` round-trips across all 13 fields ($m = 2 \dots 571$).
* `test_step3_extended_euclid.py` (`9` tests): Exact 4-row Ch. 4 Table 4.7 reproduction, Ch. 5 AES $\{95\}^{-1} = \{8\text{A}\}$, `b = 0`, `b = m(x)` and multiples, `b = 1` at Step 0, unreduced inputs, negative inputs, and single/multi-step reducible modulus `NotInvertibleError`.
* `test_step4_division_and_verify.py` (`9` tests): Ch. 4/5 division identities, `0 / b = 0`, `a / 1 = a`, `a / a = 1`, two-stage trace completeness, unreduced `a` & `b`, zero/modulus divisors, reducible modulus propagation, and true/corrupted false tests for `VERIFY_INVERSE` and `VERIFY_DIVISION`.
* `test_step5_multifield_verification.py` (`27` tests): Exhaustive check of all 255 non-zero elements in $GF(2^8)$ (bijection + double inverse + division), exhaustive small fields $2 \le m \le 7$, seeded sparse/dense/unreduced tests across $m \in \{163, 233, 239, 283, 409, 571\}$, and benchmark runner smoke check.

### 6.2 Measured Benchmarks (`python benchmarks/benchmark_m3.py --trials 10 --seed 455632`)

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

Average EEA iterations on dense operands closely track $m / 2$ (from $3.5$ at $m=8$ up to $288.1$ at $m=571$), while sparse operands require significantly fewer iterations and multiplications.

---

## 7. Milestone 5 Integration Guide (`app/providers.py` & `gf2m_m3/_reference`)

1. **Swap `_reference/` for Real M1 & M2 Modules:**
   * Update `gf2m_m3/_reference/utilities.py` and `fields.py` imports to use Milestone 1's authoritative `MOD_REDUCE`, `DEG`, `FIELD_REGISTRY`, and converters (`INT_TO_HEX`, `INT_TO_BIN`, `INT_TO_ALGEBRAIC`).
   * Update `gf2m_m3/_reference/multiply.py` to delegate `gf2m_multiply` to Milestone 2's `gf2m.multiply.multiply_traced` (and `multiply` inside verification fast paths if desired).
2. **Connect Milestone 3 to Milestone 2's `app/providers.py`:**
   * Milestone 2 routes `inverse` and `divide` through `providers.invdiv` and catches `providers.invdiv.NoInverseError`.
   * Bind `providers.invdiv` to a lightweight adapter over `gf2m_m3` so Milestone 2's `app/services.py` receives full Table 4.7 and two-stage traces plus `VERIFY_INVERSE` / `VERIFY_DIVISION` proof payloads without rewriting API routes:

```python
# Inside Milestone 2's app/providers.py (or an integration adapter module):
from gf2m_m3 import (
    EXTENDED_EUCLID_GF2M,
    GF2M_DIVIDE,
    GF2mInverseError as NoInverseError,
    VERIFY_DIVISION,
    VERIFY_INVERSE,
)

class Milestone3InvDivProvider:
    NoInverseError = NoInverseError

    @staticmethod
    def inverse(a: int, mod_poly: int, m: int, with_trace: bool = False):
        inv_int, trace = EXTENDED_EUCLID_GF2M(mod_poly, m, a)
        return (inv_int, trace) if with_trace else inv_int

    @staticmethod
    def divide(a: int, b: int, mod_poly: int, m: int, with_trace: bool = False):
        q_int, trace = GF2M_DIVIDE(a, b, mod_poly, m)
        return (q_int, trace) if with_trace else q_int

    verify_inverse = staticmethod(VERIFY_INVERSE)
    verify_division = staticmethod(VERIFY_DIVISION)

invdiv = Milestone3InvDivProvider()
```

This preserves HTTP `400` educational error messages (with `err.gcd` and `err.trace` available for debugging or richer error payloads) and feeds Milestone 4's Table 4.7 cell-notation toggle directly via `row["cells"][col]["hex" | "bin" | "algebraic"]`.

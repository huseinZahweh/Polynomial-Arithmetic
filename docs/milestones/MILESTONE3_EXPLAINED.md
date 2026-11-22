# Milestone 3 — Extended Euclid Inverse, Field Division & Verification Suite

**Project:** EECE 455 — Project-3: Polynomial Arithmetic in $GF(2^m)$  
**Assigned Owner:** Husein Zahweh  
**Unified Code Locations:** [backend/engine/poly_ops.py](../../backend/engine/poly_ops.py), [backend/engine/extended_euclid.py](../../backend/engine/extended_euclid.py), [backend/engine/division.py](../../backend/engine/division.py), [backend/engine/verification.py](../../backend/engine/verification.py), [backend/engine/exceptions.py](../../backend/engine/exceptions.py), and [benchmarks/benchmark_gf2m.py](../../benchmarks/benchmark_gf2m.py)  
**Textbook References:** William Stallings, *Cryptography and Network Security*, **Chapter 4** (Finite Fields — Table 4.7), **Chapter 5** (AES S-Box), **Chapter 6** (XTS-AES over $GF(2^{128})$), and **Chapter 10** (Binary Elliptic Curve Cryptography over $GF(2^{163}) \dots GF(2^{571})$).

---

## 1. Architectural Overview & Shared Contract

Milestone 3 implements unreduced polynomial multiplication, Euclidean polynomial long division, Extended Euclidean multiplicative inversion with Stallings Table 4.7 tracing, two-stage field division, live algebraic self-verification, and multi-field performance benchmarking. In the unified layout, all Milestone 3 modules import directly from the canonical `backend.engine` field registry, modulo reducer, and Shift-and-XOR multiplier (eliminating the earlier standalone `_reference/` stand-ins).

Every polynomial $p(x) = \sum_{i=0}^{d} c_i x^i \in GF(2)[x]$ is represented as a non-negative Python `int` where bit $i$ (LSB $= 0$) equals $c_i \in \{0, 1\}$, and $m(x)$ has bit $m$ explicitly set to $1$:

$$
m(x) = x^8 + x^4 + x^3 + x + 1 \iff \text{100011011}_2 = \text{0x11B} = 283
$$

All public functions reject negative integers with `ValueError` and booleans or non-integers with `TypeError`.

---

## 2. Mathematical Foundations & Algorithms

### 2.1 Carry-Free Multiplication & Long Division (`backend/engine/poly_ops.py`)

Over $\mathbb{Z}_2[x]$, addition and subtraction of coefficients collapse to bitwise XOR ($\oplus$) with no carry propagation:

1. **`POLY_MUL_NO_MOD(a_int, b_int) -> int`** computes $a(x) \cdot b(x)$ over $GF(2)[x]$, walking the shorter-degree operand to minimize iterations.
2. **`POLY_DIVMOD(a_int, b_int, *, steps=None) -> tuple[int, int]`** computes unique $Q(x)$ and $R(x)$ satisfying:

$$
A(x) = Q(x) \cdot B(x) \oplus R(x), \quad R(x) = 0 \text{ or } \deg(R) < \deg(B)
$$

At each step with $\deg(R) \ge \deg(B)$, let $s = \deg(R) - \deg(B)$; setting bit $s$ in $Q(x)$ and XORing $R(x)$ with $B(x) \ll s$ cancels the leading term. An optional `steps` list records each `DivisionStep(shift, before, shifted_divisor, after)` for the Multiplication Comparison lab. Calling `POLY_DIVMOD` with `b_int == 0` raises `ZeroDivisionError`.

### 2.2 Extended Euclidean Algorithm (`backend/engine/extended_euclid.py`)

Given modulus $m(x)$ of degree $m$ and input polynomial $b(x)$:

1. **Initial Reduction:** Reduce $b(x)$ via `MOD_REDUCE` so inputs with $\deg(b) \ge m$ (including $b(x) = m(x)$) map cleanly into $GF(2^m)$.
2. **Initialization (Step 0):**

$$
(A_1, A_2, A_3) \leftarrow (1, 0, m(x)), \qquad (B_1, B_2, B_3) \leftarrow (0, 1, b_{\text{red}}(x))
$$

   Step `0` is recorded into `table_4_7_rows` with `Q = None` (formatted as `"-"`).
3. **Bezout Recurrence (`while B3 != 1`):** Maintaining $A_1 m(x) \oplus A_2 b_{\text{red}}(x) = A_3$ and $B_1 m(x) \oplus B_2 b_{\text{red}}(x) = B_3$:

$$
(Q, T_3) = \text{POLY\_DIVMOD}(A_3, B_3), \quad T_1 = A_1 \oplus (Q \cdot B_1), \quad T_2 = A_2 \oplus (Q \cdot B_2)
$$

   Shift $(A_1, A_2, A_3) \leftarrow (B_1, B_2, B_3)$ and $(B_1, B_2, B_3) \leftarrow (T_1, T_2, T_3)$, appending each row with pre-formatted `hex`, `bin`, and `algebraic` cells.
4. **Both Stallings Termination Rules:**
   * **Inverse Found (`B3 == 1`):** $\gcd(m(x), b(x)) = 1$ and $B_2(x) \bmod m(x)$ is the unique multiplicative inverse $b(x)^{-1} \bmod m(x)$.
   * **No Inverse (`B3 == 0`):**
     * At Step 0 ($b_{\text{red}} = 0$): $A_3 = \gcd(m(x), 0) = m(x)$ $\rightarrow$ raises `ZeroElementHasNoInverseError(gcd=A3, trace=trace_dict)`.
     * Mid-loop (reducible $m(x)$ sharing a factor with $b(x)$): raises `NotInvertibleError(gcd=A3, trace=trace_dict)` preserving all rows up to `B3 == 0`.

### 2.3 Worked Textbook Reproduction: Stallings Chapter 4 Table 4.7

For $m(x) = x^8 + x^4 + x^3 + x + 1$ (`0x11B`) and $b(x) = x^7 + x + 1$ (`0x83`):

| Step | $Q(x)$ | $A_1(x)$ | $A_2(x)$ | $A_3(x)$ | $B_1(x)$ | $B_2(x)$ | $B_3(x)$ |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `0` | `-` | `1` (`01`) | `0` (`00`) | $x^8+x^4+x^3+x+1$ (`11B`) | `0` (`00`) | `1` (`01`) | $x^7+x+1$ (`83`) |
| `1` | $x$ (`02`) | `0` (`00`) | `1` (`01`) | $x^7+x+1$ (`83`) | `1` (`01`) | $x$ (`02`) | $x^4+x^3+x^2+1$ (`1D`) |
| `2` | $x^3+x^2+1$ (`0D`) | `1` (`01`) | $x$ (`02`) | $x^4+x^3+x^2+1$ (`1D`) | $x^3+x^2+1$ (`0D`) | $x^4+x^3+x+1$ (`1B`) | $x$ (`02`) |
| `3` | $x^3+x^2+x$ (`0E`) | $x^3+x^2+1$ (`0D`) | $x^4+x^3+x+1$ (`1B`) | $x$ (`02`) | $x^6+x^2+x+1$ (`47`) | **$x^7$ (`80`)** | **`1` (`01`)** |

At Step 3, $B_3(x) = 1$, giving $\{83\}^{-1} = B_2(x) = \{80\}$ in 3 division iterations. Likewise, for the Chapter 5 AES S-Box vector $b(x) = \{95\}$, `EXTENDED_EUCLID_GF2M(0x11B, 8, 0x95)` returns $\{8\text{A}\} = x^7 + x^3 + x$ in 3 iterations.

### 2.4 Field Division (`division.py`) & Live Self-Verifiers (`verification.py`)

Field division computes:

$$
\frac{a(x)}{b(x)} \bmod m(x) = a(x) \times \left(b(x)^{-1} \bmod m(x)\right) \bmod m(x)
$$

* **`GF2M_DIVIDE`** runs Stage 1 (`EXTENDED_EUCLID_GF2M`) on $b(x)$ and Stage 2 (`multiply_traced` from `backend/engine/multiply.py`) on $a_{\text{red}} \times b^{-1}$, returning a unified `gf2m_division_two_stage` trace rendered directly by the frontend.
* **`VERIFY_INVERSE`** checks $b^{-1} < 2^m$ and $b(x) \cdot b(x)^{-1} \bmod m(x) = 1$ using fast-path `multiply`.
* **`VERIFY_DIVISION`** checks $b_{\text{red}} \neq 0$, $q < 2^m$, and $(a(x)/b(x)) \cdot b(x) \bmod m(x) = a(x) \bmod m(x)$.

---

## 3. Complexity Analysis

Let $m = m_{\text{degree}}$, $d_a = \deg(a)$, and $d_b = \deg(b)$:

| Function | Time Complexity (Bit Ops) | Space / Trace Complexity | Notes |
| :--- | :--- | :--- | :--- |
| `POLY_MUL_NO_MOD` | $O(\min(d_a, d_b) \cdot (d_a + d_b))$ | $O(d_a + d_b)$ | Loops over shorter operand |
| `POLY_DIVMOD` | $O((d_a - d_b + 1) \cdot d_a)$ | $O(d_a)$ | $O(1)$ when $d_a < d_b$ |
| `EXTENDED_EUCLID_GF2M` | $O(m^2)$ | $O(m^2)$ | $\le m$ steps (avg $\approx m/2$) |
| `GF2M_DIVIDE` | $O(m^2)$ | $O(m^2)$ | 1 EEA + 1 Shift-and-XOR |
| `VERIFY_INVERSE` / `VERIFY_DIVISION` | $O(m^2)$ | $O(m)$ | Single untraced modular multiply |

---

## 4. Verification & Benchmark Suite

Run the multi-field benchmark directly from the repository root:

```bash
python -m benchmarks.benchmark_gf2m --trials 10 --seed 455
```

### Reference Benchmark Snapshot (`--trials 10 --seed 455`, Full Traced Execution)

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

All 87 original Milestone 3 verification tests are preserved under [tests/engine/test_poly_ops.py](../../tests/engine/test_poly_ops.py), [tests/engine/test_extended_euclid.py](../../tests/engine/test_extended_euclid.py), [tests/engine/test_division_and_verify.py](../../tests/engine/test_division_and_verify.py), and [tests/engine/test_multifield_verification.py](../../tests/engine/test_multifield_verification.py), covering exhaustive checks across all 255 nonzero elements of $GF(2^8)$, all small fields $2 \le m \le 7$, and sparse/dense/unreduced vectors across $m \in \{163, 233, 239, 283, 409, 571\}$.

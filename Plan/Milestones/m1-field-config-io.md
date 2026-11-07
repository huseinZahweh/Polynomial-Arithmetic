# Milestone 1: Field Configuration, Multi-Base I/O & Additive/Modulo Engine

**Assigned Owner:** Husein Zahweh  
**Execution Mode:** Parallel & Independent (operates on integer bit-strings and string converters)

---

## 1. Objective
Build the modular Field Configuration Registry for $m \in \{163, 233, 239, 283, 409, 571\}$ (plus small verification fields $2 \le m \le 8$), the lossless **Binary / Hexadecimal / Algebraic** converters, and the **Addition, Subtraction, and Modulo Reduction** engine with step-by-step educational traces.

---

## 2. Modular Field Registry Specification

To make the platform modular and extensible across all required degrees, define a central registry mapping each degree $m$ to its irreducible polynomial $m(x)$ specified as a descending list of non-zero exponent taps:

### 2.1 Standard Cryptographic Binary Fields (Project-3)
* **$m = 163$ (Default Primary Field):** $m(x) = x^{163} + x^7 + x^6 + x^3 + 1 \rightarrow [163, 7, 6, 3, 0]$
* **$m = 233$:** $m(x) = x^{233} + x^{74} + 1 \rightarrow [233, 74, 0]$
* **$m = 239$:** $m(x) = x^{239} + x^{158} + 1 \rightarrow [239, 158, 0]$
* **$m = 283$:** $m(x) = x^{283} + x^{12} + x^7 + x^5 + 1 \rightarrow [283, 12, 7, 5, 0]$
* **$m = 409$:** $m(x) = x^{409} + x^{87} + 1 \rightarrow [409, 87, 0]$
* **$m = 571$:** $m(x) = x^{571} + x^{10} + x^5 + x^2 + 1 \rightarrow [571, 10, 5, 2, 0]$

### 2.2 Small Textbook Verification Fields (Project-2 Reference)
* $m = 2$: $x^2 + x + 1 \rightarrow [2, 1, 0]$
* $m = 3$: $x^3 + x^2 + 1 \rightarrow [3, 2, 0]$
* $m = 4$: $x^4 + x^3 + 1 \rightarrow [4, 3, 0]$
* $m = 5$: $x^5 + x^2 + 1 \rightarrow [5, 2, 0]$
* $m = 6$: $x^6 + x + 1 \rightarrow [6, 1, 0]$
* $m = 7$: $x^7 + x + 1 \rightarrow [7, 1, 0]$
* $m = 8$: $x^8 + x^4 + x^3 + x + 1 \rightarrow [8, 4, 3, 1, 0]$

* **Bitmask Construction Rule:** From any tap list $T$, construct the integer representation of $m(x)$ via:
  $$m_{\text{int}} = \sum_{k \in T} 2^k$$

---

## 3. Multi-Format Input / Output Converters

1. **Degree Helper (`DEG(poly_int)`):**
   * Returns `poly_int.bit_length() - 1` for `poly_int > 0`, and `-1` for `poly_int == 0`.
2. **Binary String $\leftrightarrow$ Integer (`BIN_TO_INT`, `INT_TO_BIN`):**
   * Sanitize input by removing spaces and optional `0b` prefixes; validate that all characters are in `{'0', '1'}`.
   * Format output padded with leading zeros to $m$ bits for reduced field elements.
3. **Hexadecimal String $\leftrightarrow$ Integer (`HEX_TO_INT`, `INT_TO_HEX`):**
   * Sanitize input by removing spaces, braces `{...}`, and optional `0x` prefixes; validate that all characters are in `{'0'-'9', 'A'-'F', 'a'-'f'}`.
   * Format output in uppercase Hexadecimal padded to $\lceil m / 4 \rceil$ hex digits (e.g., $41$ hex digits for $m = 163$).
4. **Algebraic Polynomial Formatter (`INT_TO_ALGEBRAIC`):**
   * Scan set bits from `DEG(poly_int)` down to $0$ and join terms as `"x^k"` (with `"x"` for $k=1$ and `"1"` for $k=0$, or `"0"` if `poly_int == 0`).

---

## 4. Addition, Subtraction & Modulo Reduction Algorithms

### 4.1 Addition and Subtraction in $GF(2^m)$
* **Mathematical Rule:** In $\mathbb{Z}_2$, coefficient addition and subtraction are both bitwise $\text{XOR}$ ($\oplus$):
  $$f(x) + g(x) = f(x) - g(x) = f(x) \oplus g(x)$$
* **Algorithmic Pseudocode (with Educational Trace):**
  ```text
  Algorithm: GF2M_ADD_SUB(f_int, g_int, m_poly_int, m_degree)
  Input: Polynomials f_int, g_int; irreducible polynomial m_poly_int of degree m_degree
  Output: Tuple (result_int, trace_dict)

  1. (a_red, _) <- MOD_REDUCE(f_int, m_poly_int, m_degree)
  2. (b_red, _) <- MOD_REDUCE(g_int, m_poly_int, m_degree)
  3. result_int <- a_red XOR b_red
  4. Record trace_dict containing aligned Binary, Hex, and Algebraic representations of a_red, b_red, and result_int
  5. Return (result_int, trace_dict)
  ```

### 4.2 Standalone Modulo Reduction: $f(x) \bmod m(x)$
* **Mathematical Rule:** Whenever $\deg(r) = d \ge m$, eliminate the $x^d$ term by $\text{XOR}$ing $r(x)$ with $x^{d-m} \cdot m(x)$.
* **Algorithmic Pseudocode (with Educational Trace):**
  ```text
  Algorithm: MOD_REDUCE(f_int, m_poly_int, m_degree)
  Input: Unreduced polynomial f_int, irreducible polynomial m_poly_int of degree m_degree
  Output: Tuple (r_int, trace_steps) where DEG(r_int) < m_degree

  1. r_int <- f_int
  2. trace_steps <- empty list
  3. While DEG(r_int) >= m_degree do:
  4.     d <- DEG(r_int)
  5.     shift <- d - m_degree
  6.     reducer <- m_poly_int << shift
  7.     r_next <- r_int XOR reducer
  8.     Append { "target_degree": d, "shift": shift, "before": r_int, "reducer": reducer, "after": r_next } to trace_steps
  9.     r_int <- r_next
  10. Return (r_int, trace_steps)
  ```

---

## 5. Deliverables & Verification Criteria
* [ ] Field Registry module returning `m_poly_int` and formatted metadata for $m \in \{163, 233, 239, 283, 409, 571\}$ and $2 \le m \le 8$.
* [ ] Lossless Binary, Hexadecimal, and Algebraic string converters verified on $8$-bit and $163$-bit polynomials.
* [ ] `GF2M_ADD_SUB` and `MOD_REDUCE` verified against Chapter 4 examples (e.g., `01010111` $\oplus$ `10000011` $=$ `11010100`).
# Milestone 1: Field Configuration, Multi-Base I/O, Additive/Modulo Engine & Utilities

**Assigned Owner:** Hussein Abbas  
**Execution Mode:** Parallel & Independent (operates on integer bit-strings, formatters, file parsers, and educational content data)

---

## 1. Objective
Build the modular Field Configuration Registry for $m \in \{163, 233, 239, 283, 409, 571\}$ and small verification fields $2 \le m \le 8$, lossless **Binary / Hexadecimal / Algebraic** converters, the **Addition, Subtraction, and Modulo Reduction** engine with step traces, the **Random $GF(2^m)$ Operand Generator**, the **Batch Polynomial File Parser**, the **Calculation Summary Formatter**, and the structured **`tutorial_slides.json`** classroom content.

---

## 2. Modular Field Registry Specification

Define a central registry mapping each degree $m$ to its irreducible polynomial $m(x)$ specified as a descending list of exponent positions with non-zero coefficients:

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

$$
m_{\text{int}} = \sum_{k \in T} 2^k
$$

---

## 3. Multi-Format Input / Output Converters

1. **Degree & Weight Helpers (`DEG(poly_int)`, `HAMMING_WEIGHT(poly_int)`):**
   * `DEG` returns `poly_int.bit_length() - 1` for `poly_int > 0`, and `-1` for `poly_int == 0`.
   * `HAMMING_WEIGHT` returns the count of `1` bits (number of non-zero polynomial terms) for complexity metrics.
2. **Binary String $\leftrightarrow$ Integer (`BIN_TO_INT`, `INT_TO_BIN`):**
   * Sanitize spaces and optional `0b` prefixes; validate characters in `{'0', '1'}`.
   * Pad output with leading zeros to $m$ bits for reduced field elements.
3. **Hexadecimal String $\leftrightarrow$ Integer (`HEX_TO_INT`, `INT_TO_HEX`):**
   * Sanitize spaces, braces `{...}`, and optional `0x` prefixes; validate characters in `{'0'-'9', 'A'-'F', 'a'-'f'}`.
   * Pad output in uppercase Hexadecimal to $\lceil m / 4 \rceil$ hex digits, e.g., 41 hex digits for $m = 163$.
4. **Algebraic Polynomial Formatter (`INT_TO_ALGEBRAIC`) & Optional Parser (`ALGEBRAIC_TO_INT` — *Optional Stretch*):**
   * `INT_TO_ALGEBRAIC` scans set bits from `DEG(poly_int)` down to $0$ and joins terms as `"x^k"` (`"x"` for $k = 1$, `"1"` for $k = 0$, `"0"` if zero).
   * *(Optional Stretch)* `ALGEBRAIC_TO_INT` parses user-typed algebraic strings (e.g., `x^7 + x + 1`) back into `poly_int` to simplify classroom use.

---

## 4. Addition, Subtraction & Modulo Reduction Algorithms

### 4.1 Addition and Subtraction in $GF(2^m)$
* **Mathematical Rule:** In $\mathbb{Z}_2$, coefficient addition and subtraction are both bitwise XOR $\oplus$:

$$
f(x) + g(x) = f(x) - g(x) = f(x) \oplus g(x)
$$

* **Algorithmic Pseudocode (with Educational Trace):**
```text
Algorithm: GF2M_ADD_SUB(f_int, g_int, m_poly_int, m_degree)
Input: Polynomials f_int, g_int; irreducible polynomial m_poly_int of degree m_degree
Output: Tuple (result_int, trace_dict)

1. (a_red, a_mod_trace) <- MOD_REDUCE(f_int, m_poly_int, m_degree)
2. (b_red, b_mod_trace) <- MOD_REDUCE(g_int, m_poly_int, m_degree)
3. result_int <- a_red XOR b_red
4. Record trace_dict containing pre-reduction traces (if any) and aligned Binary, Hex, and Algebraic rows
5. Return (result_int, trace_dict)
```

### 4.2 Standalone Modulo Reduction: $f(x) \bmod m(x)$
* **Mathematical Rule:** Whenever $\deg(r) = d \ge m$, eliminate the $x^d$ term by XORing $r(x)$ with $x^{d-m} \cdot m(x)$.
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

## 5. Random Operand Generator, File Parser, Summary Formatter & Tutorial Data

### 5.1 Random $GF(2^m)$ Operand Generator (`GENERATE_RANDOM_POLY`)
* Generates random non-zero test operands $A(x), B(x) \in GF(2^m) \setminus \{0\}$ using OS randomness (`secrets` in Python) strictly for classroom testing and GUI population:
  * **Dense Mode (Default):** Uniformly random $m$-bit integer in $[1, 2^m - 1]$.
  * **Sparse Mode (Educational):** Selects $k$ random exponent positions (e.g., $3$ to $6$ set bits) so students can observe shorter Shift-and-XOR traces even at $m = 163$.

### 5.2 Batch Polynomial File Parser
* Parses uploaded `.txt` or `.json` files containing pairs of Binary or Hexadecimal polynomial operands for quick loading into the GUI.
* Validates input base formatting and rejects malformed `.txt`/`.json` uploads with structured educational error messages.

### 5.3 Calculation Summary Formatter
* Formats a completed calculation payload (field metadata, parsed inputs, result, verification badge, runtime metrics, and educational trace) into downloadable Markdown (`.md`) or `.json` summary reports.

### 5.4 Structured Tutorial & Classroom Preset Content (`tutorial_slides.json`)
* Authors the concise 4-slide educational JSON content covering:
  1. $GF(2^m)$ axioms and $\mathbb{Z}_2$ polynomial arithmetic.
  2. Irreducible polynomial modulo reduction, i.e., $f(x) \bmod m(x)$.
  3. Shift-and-XOR multiplication and Extended Euclidean inverse walkthroughs.
  4. Chapter 4 and Chapter 5 textbook classroom presets (consumed via `GET /api/tutorial` by Milestone 4's Tutorial Drawer UI).

---

## 6. Deliverables & Verification Criteria
* [ ] Fully commented Field Registry module for $m \in \{163, 233, 239, 283, 409, 571\}$ and $2 \le m \le 8$.
* [ ] Lossless `BIN_TO_INT`, `INT_TO_BIN`, `HEX_TO_INT`, `INT_TO_HEX`, and `INT_TO_ALGEBRAIC` converters verified on $8$-bit and $163$-bit polynomials (plus `ALGEBRAIC_TO_INT` if implemented as an *Optional Stretch* feature).
* [ ] `GF2M_ADD_SUB` and `MOD_REDUCE` verified against Chapter 4 examples (e.g., $\{57\} \oplus \{83\} = \{\text{D4}\}$, i.e., `01010111` $\oplus$ `10000011` $=$ `11010100`).
* [ ] `GENERATE_RANDOM_POLY` reliably produces valid non-zero sparse and dense test operands $A(x)$ and $B(x)$ across all supported field sizes.
* [ ] Batch Polynomial File Parser cleanly parses valid `.txt`/`.json` operand-pair files and returns clear errors for malformed inputs.
* [ ] Calculation Summary Formatter generates valid downloadable `.md` and `.json` reports, and `tutorial_slides.json` validates against the 4-slide + preset schema.
* [ ] Automated `pytest` unit test suite covering Field Registry, converters, Add/Sub/Mod traces, Random Operand Generator, Batch File Parser, Summary Formatter, and tutorial content.

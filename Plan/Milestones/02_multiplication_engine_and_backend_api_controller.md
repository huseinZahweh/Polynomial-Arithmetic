# Milestone 2: Shift-and-XOR Multiplication Engine & Backend API Controller

**Assigned Owner:** Hassan Tarhini  
**Execution Mode:** Parallel & Independent (accepts integer bit-strings for math and exposes the full REST API contract)

---

## 1. Objective
Implement modular polynomial multiplication $f(x) \times g(x) \bmod m(x)$ using the **Shift-and-XOR** methodology from **Chapter 4** of the course notes (with step-by-step educational tracing), and build the **FastAPI Backend Controller** exposing the 6 aligned API endpoints for arithmetic, random operand generation, batch polynomial file parsing, calculation summary export, and tutorial content.

---

## 2. Shift-and-XOR Modular Multiplication Specification

### 2.1 Mathematical Rule (Chapter 4 Alignment)
* Multiplying a reduced polynomial $a(x) \in GF(2^m)$ by $x$ modulo $m(x)$ inspects its most significant bit $b_{m-1}$, the coefficient of $x^{m-1}$:
  * Shift $a(x)$ left by $1$ bit and mask to the lower $m$ bits.
  * If $b_{m-1} = 1$, reduce the overflow term $x^m$ by XORing with the lower $m$ bits of $m(x)$:

$$
x \cdot a(x) \bmod m(x) = \begin{cases} (a(x) \ll 1) & \text{if } b_{m-1} = 0 \\ ((a(x) \ll 1) \text{ AND } (2^m - 1)) \oplus (m(x) - x^m) & \text{if } b_{m-1} = 1 \end{cases}
$$

* The full product $f(x) \times g(x) \bmod m(x)$ is the $\text{XOR}$ sum of $x^i \cdot f(x) \bmod m(x)$ for every bit position $i$ where bit $i$ of $g(x)$ is $1$:

$$
f(x) \times g(x) \bmod m(x) = \bigoplus_{i=0}^{m-1} g_i \cdot \left(x^i \cdot f(x) \bmod m(x)\right)
$$

### 2.2 Algorithmic Pseudocode (with Educational Trace)

```text
Algorithm: GF2M_MULTIPLY(f_int, g_int, m_poly_int, m_degree)
Input: Polynomials f_int, g_int (auto-reduced if unreduced); irreducible polynomial m_poly_int of degree m_degree
Output: Tuple (product_int, trace_dict)

1. (a, f_mod_trace) <- MOD_REDUCE(f_int, m_poly_int, m_degree)
2. (b, g_mod_trace) <- MOD_REDUCE(g_int, m_poly_int, m_degree)
3. product_int <- 0
4. low_m_mask <- (1 << m_degree) - 1
5. reduction_poly <- m_poly_int AND low_m_mask
6. shift_steps <- empty list
7. selected_terms <- empty list
8. deg_b <- DEG(b)
9. For i from 0 to deg_b do:
10.    bit_i <- (b >> i) AND 1
11.    If bit_i == 1 then:
12.        product_int <- product_int XOR a
13.        Append { "exponent_i": i, "term_value": a, "running_xor": product_int } to selected_terms
14.    If i < deg_b then:
15.        msb_set <- (a >> (m_degree - 1)) AND 1
16.        a_shifted <- (a << 1) AND low_m_mask
17.        If msb_set == 1 then:
18.            a_next <- a_shifted XOR reduction_poly
19.        Else:
20.            a_next <- a_shifted
21.        Append { "power_next": i + 1, "msb_overflow": msb_set, "after_shift": a_shifted, "after_reduction": a_next } to shift_steps
22.        a <- a_next
23. trace_dict <- { "trace_type": "shift_and_xor", "f_mod_trace": f_mod_trace, "g_mod_trace": g_mod_trace, "shift_steps": shift_steps, "selected_terms": selected_terms }
24. Return (product_int, trace_dict)
```

---

## 3. FastAPI Backend Controller Specification

Build the web API layer connecting the mathematical engine to the GUI with clean input validation, CORS support, execution-time instrumentation (`elapsed_ms`), interactive OpenAPI (`/docs`) documentation, and HTTP `400` educational error messages:

### 3.1 Aligned API Endpoints
1. **`GET /api/fields`**
   * Returns all supported degrees $m \in \{163, 233, 239, 283, 409, 571\}$ and $2 \le m \le 8$ with their irreducible polynomials in Algebraic, Hexadecimal, and Binary formats.
2. **`POST /api/calculate`**
   * Accepts `{ "m", "operation", "input_base", "poly_a", "poly_b" }`.
   * Dispatches to `add`, `sub`, `mod`, `mul`, `inv`, or `div`.
   * Returns `{ "field_info", "inputs_parsed", "result", "verification", "metrics", "educational_trace" }` with runtime timing (`elapsed_ms`), operand metrics (`bit_length`, `hamming_weight`), and algebraic self-verification status for inverse/division.
   * Returns clear HTTP `400` educational error messages for invalid characters, malformed base strings, or zero-inverse / division-by-zero attempts.
3. **`POST /api/random-polynomials`**
   * Accepts `{ "m", "count", "sparsity", "output_base" }` (default `count: 2`).
   * Calls M1's `GENERATE_RANDOM_POLY` to return `{ "m", "output_base", "polynomials": [...] }` so the GUI fills both $A(x)$ and $B(x)$ in one click.
4. **`POST /api/parse-polynomials`**
   * Accepts an uploaded `.txt` or `.json` file and invokes M1's Batch Polynomial File Parser to return validated operand pairs (or HTTP `400` error details on malformed files).
5. **`POST /api/export-calculation`**
   * Accepts a calculation payload and invokes M1's Calculation Summary Formatter to return a downloadable `.md` or `.json` summary file.
6. **`GET /api/tutorial`**
   * Serves M1's structured `tutorial_slides.json` content (4 educational slides and Chapter 4/5 presets) to the GUI.

---

## 4. Deliverables & Verification Criteria
* [x] Well-commented `GF2M_MULTIPLY` reproducing **Chapter 4**: `01010111` $\times$ `10000011` $\bmod$ `100011011` $=$ `11000001`, i.e., $\{\text{C1}\}$, and **Chapter 5 AES**: $\{02\} \cdot \{87\} \bmod \{11\text{b}\} = \{15\}$.
* [x] `GF2M_MULTIPLY` runs efficiently across $m = 163$ through $m = 571$ with full step-by-step Shift-and-XOR traces.
* [x] FastAPI server serves all 6 endpoints cleanly with CORS enabled and interactive OpenAPI (`/docs`) documentation.
* [x] Automated `pytest` + `TestClient` suite verifying Shift-and-XOR vectors, all 6 API endpoints, and HTTP `400` validation error handling.

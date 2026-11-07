# Milestone 2: Shift-and-XOR Multiplication Engine & Backend API Controller

**Assigned Owner:** Student 2  
**Execution Mode:** Parallel & Independent (accepts integer bit-strings for math and exposes the REST contract)

---

## 1. Objective
Implement modular polynomial multiplication $f(x) \times g(x) \bmod m(x)$ using the **Shift-and-XOR** methodology from **Chapter 4** of the course notes (including its step-by-step educational trace logger), and build the **FastAPI Backend Controller** that exposes the standardized endpoints to the GUI.

---

## 2. Shift-and-XOR Modular Multiplication Specification

### 2.1 Mathematical Rule (Chapter 4 Alignment)
* Multiplying a reduced polynomial $a(x) \in GF(2^m)$ by $x$ modulo $m(x)$ is performed by inspecting its most significant bit $b_{m-1}$ (the coefficient of $x^{m-1}$):
  * Shift $a(x)$ left by $1$ bit and mask to the lower $m$ bits.
  * If $b_{m-1} = 1$, the shift produced an overflow term $x^m$, which is reduced modulo $m(x)$ by $\text{XOR}$ing with the lower $m$ bits of $m(x)$:
    $$x \cdot a(x) \bmod m(x) = \begin{cases} (a(x) \ll 1) & \text{if } b_{m-1} = 0 \\ ((a(x) \ll 1) \text{ AND } (2^m - 1)) \oplus (m(x) - x^m) & \text{if } b_{m-1} = 1 \end{cases}$$
* The full product $f(x) \times g(x) \bmod m(x)$ is the $\text{XOR}$ sum of $x^i \cdot f(x) \bmod m(x)$ for every bit position $i$ where bit $i$ of $g(x)$ is $1$:
  $$f(x) \times g(x) \bmod m(x) = \bigoplus_{i=0}^{m-1} g_i \cdot \left(x^i \cdot f(x) \bmod m(x)\right)$$

### 2.2 Algorithmic Pseudocode (with Educational Trace)
```text
Algorithm: GF2M_MULTIPLY(f_int, g_int, m_poly_int, m_degree)
Input: Reduced polynomials f_int, g_int in GF(2^m); irreducible polynomial m_poly_int of degree m_degree
Output: Tuple (product_int, trace_dict)

1. a <- f_int
2. b <- g_int
3. product_int <- 0
4. low_m_mask <- (1 << m_degree) - 1
5. reduction_poly <- m_poly_int AND low_m_mask
6. shift_steps <- empty list
7. selected_terms <- empty list
8. For i from 0 to DEG(b) do:
9.     bit_i <- (b >> i) AND 1
10.    If bit_i == 1 then:
11.        product_int <- product_int XOR a
12.        Append { "exponent_i": i, "term_value": a, "running_xor": product_int } to selected_terms
13.    msb_set <- (a >> (m_degree - 1)) AND 1
14.    a_shifted <- (a << 1) AND low_m_mask
15.    If msb_set == 1 then:
16.        a_next <- a_shifted XOR reduction_poly
17.    Else:
18.        a_next <- a_shifted
19.    Append { "power_next": i + 1, "msb_overflow": msb_set, "after_shift": a_shifted, "after_reduction": a_next } to shift_steps
20.    a <- a_next
21. trace_dict <- { "trace_type": "shift_and_xor", "shift_steps": shift_steps, "selected_terms": selected_terms }
22. Return (product_int, trace_dict)
```

---

## 3. FastAPI Backend Controller Specification

This module also encompasses the web API controller layer that routes GUI requests to the arithmetic engine:

### 3.1 Endpoints
1. `GET /api/fields`
   * Returns the list of all supported degrees $m \in \{163, 233, 239, 283, 409, 571\}$ (and $2 \le m \le 8$) along with their irreducible polynomials in Algebraic, Hexadecimal, and Binary formats.
2. `POST /api/calculate`
   * Accepts `{ "m", "operation", "input_base", "poly_a", "poly_b" }`.
   * Validates inputs, dispatches to the requested operation (`add`, `sub`, `mod`, `mul`, `inv`, `div`), formats all outputs and trace steps in Binary, Hexadecimal, and Algebraic notation, and returns the standardized JSON response.
   * Returns clear HTTP `400` educational error messages for invalid characters or division/inversion by zero.

---

## 4. Deliverables & Verification Criteria
* [ ] `GF2M_MULTIPLY` reproduces the **Chapter 4** $GF(2^8)$ example (`01010111` $\times$ `10000011` $\bmod$ `100011011` $=$ `11000001` / `{C1}`) and the **Chapter 5 AES** example (`{02}` $\cdot$ `{87}` $\bmod$ `{11b}` $=$ `{15}`).
* [ ] `GF2M_MULTIPLY` executes smoothly on $163$-bit through $571$-bit polynomials.
* [ ] FastAPI server (`/api/fields` and `/api/calculate`) runs and serves the agreed JSON schema.
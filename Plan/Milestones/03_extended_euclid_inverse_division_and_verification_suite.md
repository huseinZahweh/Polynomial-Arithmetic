# Milestone 3: Polynomial Long Division, Extended Euclid Inverse, Field Division & Verification Suite

**Assigned Owner:** Husein Zahweh  
**Execution Mode:** Parallel & Independent (operates on integer bit-strings following Chapter 4 Table 4.7)

---

## 1. Objective
Design and verify polynomial Euclidean long division (`POLY_DIVMOD`), the Extended Euclidean Algorithm (`EXTENDED EUCLID(m(x), b(x))`) for finding multiplicative inverses $b(x)^{-1} \bmod m(x)$ with full **Table 4.7** educational trace logging, polynomial field division $a(x) / b(x) \bmod m(x)$, live **Algebraic Self-Verification** helpers, and the **Multi-Field Automated Test & Benchmark Suite**.

---

## 2. Algorithmic Specifications

### 2.1 Helper 1: Carry-Free Polynomial Multiplication (No Modulo)
Inside the Extended Euclidean Algorithm, updating $T_i(x) = A_i(x) \oplus (Q(x) \times B_i(x))$ requires standard carry-free polynomial multiplication over $GF(2)$ prior to any modular reduction:
```text
Algorithm: POLY_MUL_NO_MOD(Q_int, B_int)
Input: Polynomials Q_int, B_int over GF(2)
Output: Unreduced product P_int = Q(x) * B(x) over GF(2)

1. P_int <- 0
2. temp_B <- B_int
3. temp_Q <- Q_int
4. While temp_Q > 0 do:
5.     If (temp_Q AND 1) == 1 then:
6.         P_int <- P_int XOR temp_B
7.     temp_B <- temp_B << 1
8.     temp_Q <- temp_Q >> 1
9. Return P_int
```

### 2.2 Helper 2: Polynomial Euclidean Long Division over $GF(2)$
* **Mathematical Rule:** Given dividend $A(x)$ and non-zero divisor $B(x)$, find unique quotient $Q(x)$ and remainder $R(x)$ such that:

$$
A(x) = Q(x) \cdot B(x) \oplus R(x), \quad \deg(R) < \deg(B)
$$

* **Algorithmic Pseudocode:**
```text
Algorithm: POLY_DIVMOD(A_int, B_int)
Input: Dividend A_int, non-zero divisor B_int
Output: Tuple (Q_int, R_int)

1. If B_int == 0 then raise DivisionByZeroError
2. Q_int <- 0
3. R_int <- A_int
4. deg_B <- DEG(B_int)
5. While R_int != 0 and DEG(R_int) >= deg_B do:
6.     shift <- DEG(R_int) - deg_B
7.     Q_int <- Q_int XOR (1 << shift)
8.     R_int <- R_int XOR (B_int << shift)
9. Return (Q_int, R_int)
```

### 2.3 Multiplicative Inverse via `EXTENDED EUCLID(m(x), b(x))`
* **Mathematical Rule (Chapter 4 & Table 4.7):**
  Initialize:

$$
(A_1(x), A_2(x), A_3(x)) \leftarrow (1, 0, m(x))
$$

$$
(B_1(x), B_2(x), B_3(x)) \leftarrow (0, 1, b(x) \bmod m(x))
$$

  In each step, compute $(Q(x), R(x)) = \text{POLY\_DIVMOD}(A_3(x), B_3(x))$ and update:

$$
T_1(x) = A_1(x) \oplus (Q(x) \times B_1(x)), \quad T_2(x) = A_2(x) \oplus (Q(x) \times B_2(x)), \quad T_3(x) = R(x)
$$

  Shift $(A_1, A_2, A_3) \leftarrow (B_1, B_2, B_3)$ and $(B_1, B_2, B_3) \leftarrow (T_1, T_2, T_3)$ until one of Stallings' two termination states holds:
  * **If $B_3(x) = 1$:** $\gcd(m(x), b(x)) = 1$, and $B_2(x)$ is the multiplicative inverse $b(x)^{-1} \bmod m(x)$.
  * **If $B_3(x) = 0$:** No multiplicative inverse exists, and $A_3(x) = \gcd(m(x), b(x))$ — for $b_{\text{red}}(x) = 0$, $A_3(x) = m(x)$; mid-loop $B_3(x) = 0$ occurs only if a non-irreducible $m(x)$ shares a non-trivial factor $A_3(x)$ with $b(x)$.

* **Algorithmic Pseudocode (with Table 4.7 Trace):**
```text
Algorithm: EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_int)
Input: Irreducible polynomial m_poly_int of degree m_degree, polynomial b_int (auto-reduced if unreduced)
Output: Tuple (inv_int, table_4_7_rows)

1. (b_red, _) <- MOD_REDUCE(b_int, m_poly_int, m_degree)
2. (A1, A2, A3) <- (1, 0, m_poly_int)
3. (B1, B2, B3) <- (0, 1, b_red)
4. table_4_7_rows <- [ { "step": 0, "Q": None, "A1": A1, "A2": A2, "A3": A3, "B1": B1, "B2": B2, "B3": B3 } ]
5. If B3 == 0 then raise ZeroElementHasNoInverseError(gcd=A3, trace=table_4_7_rows)  // No inverse; A3 = gcd(m, b) = m(x)
6. step_num <- 1
7. While B3 != 1 do:
8.     (Q, T3) <- POLY_DIVMOD(A3, B3)
9.     T1 <- A1 XOR POLY_MUL_NO_MOD(Q, B1)
10.    T2 <- A2 XOR POLY_MUL_NO_MOD(Q, B2)
11.    (A1, A2, A3) <- (B1, B2, B3)
12.    (B1, B2, B3) <- (T1, T2, T3)
13.    Append { "step": step_num, "Q": Q, "A1": A1, "A2": A2, "A3": A3, "B1": B1, "B2": B2, "B3": B3 } to table_4_7_rows
14.    step_num <- step_num + 1
15.    If B3 == 0 then raise NotInvertibleError(gcd=A3, trace=table_4_7_rows)        // No inverse; A3 = gcd(m, b) != 1
16. Return (B2, table_4_7_rows)                                                      // B3 == 1: gcd(m, b) = 1, B2 = b^-1 mod m
```

### 2.4 Field Division: $a(x) / b(x) \bmod m(x)$
* **Mathematical Rule:**

$$
\frac{a(x)}{b(x)} \bmod m(x) = a(x) \times \left(b(x)^{-1} \bmod m(x)\right) \bmod m(x)
$$

* First invokes `EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_int)` to obtain `b_inv` and its Table 4.7 trace, then multiplies `a_int` by `b_inv` modulo `m_poly_int` and returns both the division result and the combined two-stage educational trace.

---

## 3. Live Self-Verification & Multi-Field Benchmark Suite

To guarantee mathematical correctness at runtime across both classroom examples and cryptographic field sizes:
1. **Live Verification Helpers (`VERIFY_INVERSE`, `VERIFY_DIVISION`):**
   * Returns a structured proof object `{ "passed": True, "equation": "b(x) * b^-1(x) mod m(x) == 1" }` displayed as a green verification badge in the GUI.
2. **Multi-Field Automated `pytest` Verification & Performance Benchmark Suite:**
   * Verifies algebraic identities across $m = 8$, including Chapter 4 Table 4.7 and Chapter 5 AES $\{95\}^{-1} = \{8\text{A}\}$, plus all standard cryptographic degrees $m \in \{163, 233, 239, 283, 409, 571\}$ over randomized test vectors, measuring average runtime in ms and Extended Euclid iteration counts.

---

## 4. Deliverables & Verification Criteria
* [ ] Well-commented `POLY_MUL_NO_MOD`, `POLY_DIVMOD`, `EXTENDED_EUCLID_GF2M`, and Field Division functions citing Stallings Chapter 4.
* [ ] Reproduce **Table 4.7** from Chapter 4 using $m(x) = x^8 + x^4 + x^3 + x + 1$ and $b(x) = x^7 + x + 1 \rightarrow$ inverse $B_2(x) = x^7$, i.e., $\{80\}$, in 3 iterations.
* [ ] Reproduce the **Chapter 5 AES S-Box** inverse table: $\{95\}^{-1} \bmod (x^8 + x^4 + x^3 + x + 1) = \{8\text{A}\}$ or $x^7 + x^3 + x$.
* [ ] Live algebraic self-verification (`VERIFY_INVERSE`, `VERIFY_DIVISION`) and automated `pytest` verification & benchmark suite confirming $b(x) \times b(x)^{-1} \bmod m(x) = 1$ and $(a(x) / b(x)) \times b(x) \bmod m(x) = a(x)$ across $m = 8$ and $m \in \{163, 233, 239, 283, 409, 571\}$.

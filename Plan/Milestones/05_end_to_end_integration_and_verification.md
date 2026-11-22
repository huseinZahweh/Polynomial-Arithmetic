# Milestone 5: End-to-End Integration & System Verification

**Assigned Owners:** Team (Collaborative Integration Phase)  
**Prerequisite:** Completion of Parallel Milestones 1, 2, 3, and 4

---

## 1. Objective
Unify all four parallel engineering tracks into a single steady, cohesive application, run the complete 8-row end-to-end verification matrix across textbook degree $m = 8$ and cryptographic degrees $m = 163$ through $571$, and complete final code quality and course deliverable sign-off.

---

## 2. End-to-End Synchronization Checklist

### Step 1: Backend Engine Alignment (M1, M2, & M3)
* **Field Config, I/O & Utilities (M1) $\leftrightarrow$ FastAPI Controller (M2):**
  * Verify `poly_a` and `poly_b` parsing via `BIN_TO_INT` and `HEX_TO_INT` (plus `ALGEBRAIC_TO_INT` if implemented as *(Optional Stretch)*), and consistent output formatting across all supported degrees.
  * Verify `/api/random-polynomials` invokes `GENERATE_RANDOM_POLY`, `/api/parse-polynomials` invokes the Batch Polynomial File Parser, `/api/export-calculation` invokes the Calculation Summary Formatter, and `/api/tutorial` serves M1's `tutorial_slides.json`.
* **Extended Euclid & Division (M3) $\leftrightarrow$ Multiplication & API (M2):**
  * Verify `POST /api/calculate` dispatches cleanly across `add`, `sub`, `mod`, `mul`, `inv`, and `div`.
  * Verify Field Division invokes `EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_int)` and `GF2M_MULTIPLY`, returning both traces and M3's live self-verification badge.

### Step 2: Frontend-to-Backend Live Wiring (M1, M2, M3, & M4)
* Switch the M4 GUI client from mock JSON to the exact 6 live FastAPI endpoints (`GET /api/fields`, `POST /api/calculate`, `POST /api/random-polynomials`, `POST /api/parse-polynomials`, `POST /api/export-calculation`, and `GET /api/tutorial`).
* Verify clean line wrapping and responsive scrolling for $163$-bit to $571$-bit binary/hex outputs and trace tables.
* Verify Hexadecimal-encoded Shareable URL links reload exact field states (converting back cleanly when `base=binary`) on a fresh browser tab.

### Step 3: Edge-Case & Error Handling Alignment (Cross-Module)
* **Zero Inverse / Division by Zero:** Confirm `0` triggers a clear HTTP `400` response and educational GUI alert explaining why $0$ has no multiplicative inverse in $GF(2^m)$—matching Stallings' $B_3(x) = 0$ termination rule with $A_3(x) = \gcd(m(x), b(x)) = m(x)$.
* **Unreduced Inputs with $\deg \ge m$, including $b(x) = m(x)$:** Confirm automatic initial reduction modulo $m(x)$ with an explicit note in the educational trace, and confirm $b(x) = m(x)$ reduces to $0$ prior to inversion so multiplicative inverse/division raises the clear zero-inverse error.
* **Malformed `.txt`/`.json` Polynomial Uploads:** Confirm uploading malformed `.txt` or `.json` operand files triggers a clean non-crashing HTTP `400` validation alert in the GUI.

---

## 3. Comprehensive End-to-End Verification Matrix

All four teammates verify the integrated application end-to-end across the 8-row test matrix in both **Binary** and **Hexadecimal** modes:

| Test Category | Field Degree $m$ | Test Case / Identity Checked | Expected Outcome |
| :--- | :--- | :--- | :--- |
| **Course Ch. 4 Addition / Subtraction** | $m = 8$ | $\{57\} \oplus \{83\}$ | $\{\text{D4}\}$: `11010100` / $x^7 + x^6 + x^4 + x^2$ |
| **Course Ch. 4 Multiplication** | $m = 8$ | $\{57\} \times \{83\} \bmod (x^8+x^4+x^3+x+1)$ | $\{\text{C1}\}$: `11000001` / $x^7 + x^6 + 1$ |
| **Course Ch. 5 AES Multiplication** | $m = 8$ | $\{02\} \times \{87\} \bmod (x^8+x^4+x^3+x+1)$ | $\{15\}$: `00010101` / $x^4 + x^2 + 1$ |
| **Course Ch. 4 Table 4.7 Inverse** | $m = 8$ | $\{83\}^{-1} \bmod (x^8+x^4+x^3+x+1)$ | $\{80\}$: `10000000` / $x^7$ in 3 EEA steps |
| **Course Ch. 5 AES S-Box Inverse** | $m = 8$ | $\{95\}^{-1} \bmod (x^8+x^4+x^3+x+1)$ | $\{8\text{A}\}$: `10001010` / $x^7 + x^3 + x$ in 3 EEA steps |
| **Additive Self-Inverse Identity** | $m \in \{163, 233, 239, 283, 409, 571\}$ | $A(x) + A(x)$ and $A(x) - A(x)$ | `0` across all 6 standard degrees |
| **Multiplicative Inverse Identity** | $m \in \{163, 233, 239, 283, 409, 571\}$ | $B(x) \times B(x)^{-1} \bmod m(x)$ | `1` (`00...01`) with green Verified badge |
| **Division Round-Trip Identity** | $m \in \{163, 233, 239, 283, 409, 571\}$ | $(A(x) / B(x)) \times B(x) \bmod m(x)$ | $A(x) \bmod m(x)$ across all 6 standard degrees |

---

## 4. Course Deliverables & Final Integration Sign-Off
* [x] **1. Clean Commented Source Code:** All milestone feature branches merged cleanly into `main`; codebase audited for clear variable naming, function docstrings, dead-code removal, and inline citations referencing **Stallings Chapters 4, 5, 6 (XTS-AES), and 10 (ECC)**.
* [ ] **2. Full Project Report:** Complete written report documenting architecture, finite-field algorithms, setup steps, verification results across all 8 test categories and `pytest` suites, and application testing screenshots.
* [ ] **3. 20-Minute Presentation & Q&A:** Group presentation slides and live walkthrough prepared covering $GF(2^m)$ foundations, implementation design, and verification methodology.
* [ ] **4. 5-Minute Max Demo Video:** Recorded system demonstration (maximum 5 minutes) showcasing interactive $GF(2^m)$ operations, step-by-step educational visualizers, tutorial mode, and textbook test cases.

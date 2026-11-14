# Project Plan & 4-Student Parallel Milestone Roadmap

This directory contains the structured engineering plan for **Project-3: Polynomial Arithmetic in $GF(2^m)$**, designed for a **4-student team working in parallel** with equal (~25% each) application engineering contributions.

* **Milestones 1, 2, 3, and 4** are four independent, parallel workstreams—one assigned to each student (each owning both implementation and unit tests for their track).
* **Milestone 5** is the joint team milestone for end-to-end backend/frontend integration, full system verification, and course deliverable sign-off.

---

## 1. Parallel Milestone Ownership (~25% Application Work Each)

| Milestone File | Assigned Student | Balanced Independent Scope |
| :--- | :--- | :--- |
| **[Milestone 1](./Milestones/01_field_config_io_additive_mod_and_utilities.md)** | **Hussein Abbas** | **Field Registry, Multi-Base I/O, Additive/Modulo Engine, Utilities & Tutorial Data:**<br>Configures $m \in \{163, 233, 239, 283, 409, 571\}$ and $2 \le m \le 8$, Binary/Hex/Algebraic converters (`ALGEBRAIC_TO_INT` as *Optional Stretch*), $+$, $-$, $\bmod\ m(x)$, Random Operand Generator, Batch Polynomial File Parser, Calculation Summary Formatter, `tutorial_slides.json`, and M1 `pytest` suite. |
| **[Milestone 2](./Milestones/02_multiplication_engine_and_backend_api_controller.md)** | **Hassan Tarhini** | **Shift-and-XOR Multiplication, 6-Endpoint FastAPI Controller & API Tests:**<br>Implements modular multiplication $f(x) \times g(x) \bmod m(x)$ with step traces, execution timing, CORS, HTTP `400` validation errors, all 6 aligned endpoints (`/api/fields`, `/api/calculate`, `/api/random-polynomials`, `/api/parse-polynomials`, `/api/export-calculation`, `/api/tutorial`), and M2 `pytest` + `TestClient` suite. |
| **[Milestone 3](./Milestones/03_extended_euclid_inverse_division_and_verification_suite.md)** | **Husein Zahweh** | **Extended Euclid Inverse, Division & Multi-Field Verification Suite:**<br>Implements `POLY_MUL_NO_MOD`, `POLY_DIVMOD`, `EXTENDED_EUCLID_GF2M` with **Table 4.7** traces, field division, live self-verification (`VERIFY_INVERSE`, `VERIFY_DIVISION`), and automated `pytest` verification + benchmarks across $m = 8$ and $m \in \{163, 233, 239, 283, 409, 571\}$. |
| **[Milestone 4](./Milestones/04_educational_gui_and_step_visualizers.md)** | **Student 4** | **Educational GUI Shell, Workbench, 4 Trace Visualizers & Tutorial Drawer:**<br>Builds the single-view web GUI with top field/base bar (Hex-encoded Share Link rule), operand cards, Ch. 4/5 presets, random/upload toolbar, 6 operation buttons, result card with export, 4 custom trace visualizers, Tutorial drawer (`GET /api/tutorial`), and *(Optional Stretch)* UI enhancements. |
| **[Milestone 5](./Milestones/05_end_to_end_integration_and_verification.md)** | **Team** | **End-to-End Integration, 8-Row Matrix Verification & Deliverables Sign-Off:**<br>Connects M1–M4 across all 6 live FastAPI endpoints, verifies all 8 textbook and cryptographic test identities plus edge cases, and completes code audit and course deliverables sign-off. |

---

## 2. Synchronization Contract (How All 4 Students Work in Parallel)

To ensure that all four teammates can build and test their milestones simultaneously without blocking each other, all modules adhere to two shared contracts:

### 2.1 Backend Internal Polynomial Contract (M1, M2, & M3)
* Every polynomial is passed internally between backend functions as a **non-negative integer (`int`)** where bit $i$ (counting from $0$ as the least significant bit) equals the coefficient $b_i \in \{0, 1\}$ of $x^i$.
* The irreducible polynomial $m(x)$ of degree $m$ is represented as an integer with bit $m$ set to $1$, e.g., for $m = 8$, $m(x) = x^8 + x^4 + x^3 + x + 1 \leftrightarrow \text{100011011}_2 = 283$.
* Every arithmetic function in Milestones 1, 2, and 3 returns a tuple `(result_int, trace_dict)`.

### 2.2 API-to-GUI JSON Contract (M2 & M4)
1. **`GET /api/fields`**
   * Returns metadata and irreducible polynomials (Algebraic, Hex, Binary) for all supported degrees $m \in \{163, 233, 239, 283, 409, 571\}$ and $2 \le m \le 8$.
2. **`POST /api/calculate`**
   * **Request:** `{ "m", "operation", "input_base", "poly_a", "poly_b" }` where `operation` is in `["add", "sub", "mod", "mul", "inv", "div"]` and `input_base` is `"binary"` or `"hex"` (plus `"algebraic"` if *(Optional Stretch)* `ALGEBRAIC_TO_INT` is enabled).
   * **Response:** `{ "field_info", "inputs_parsed", "result", "verification", "metrics", "educational_trace" }`, where `metrics` includes `elapsed_ms`, `bit_length`, and `hamming_weight`.
3. **`POST /api/random-polynomials`**
   * **Request:** `{ "m", "count", "sparsity", "output_base" }` with default `count: 2`.
   * **Response:** `{ "m", "output_base", "polynomials": [...] }` generated via M1's `GENERATE_RANDOM_POLY` to populate both operands $A(x)$ and $B(x)$ in one click.
4. **`POST /api/parse-polynomials`**
   * Accepts an uploaded `.txt` or `.json` file and invokes M1's Batch Polynomial File Parser to return validated operand pairs.
5. **`POST /api/export-calculation`**
   * Accepts a calculation payload and invokes M1's Calculation Summary Formatter to return a cleanly formatted downloadable `.md` or `.json` summary file.
6. **`GET /api/tutorial`**
   * Serves M1's structured `tutorial_slides.json` content (4 educational slides and Chapter 4/5 presets) to the GUI.

---

## 3. Shared Coding & Documentation Standards
* **Commented, Readable Code:** Every module, class, and function must include concise docstrings explaining its inputs, outputs, complexity, and exact references to **Stallings Chapter 4 (Finite Fields), Chapter 5 (AES), Chapter 6 (Block Cipher Operation — XTS-AES over $GF(2^{128})$ arithmetic), and Chapter 10 (Elliptic Curve Cryptography over $GF(2^m)$ curves)**.
* **Consistent Naming:** Keep variable names mathematically transparent, e.g., `m_poly_int`, `a_int`, `b_inv_int`, `q_int`, `r_int`, to simplify cross-module integration and team code reviews.

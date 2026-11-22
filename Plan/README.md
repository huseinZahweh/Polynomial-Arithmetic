# Project Plan & Parallel Milestone Roadmap

This directory contains the structured engineering plan for **Project-3: Polynomial Arithmetic in $GF(2^m)$**, designed for a **4-student team working in parallel** with equal (~25% each) application engineering contributions, followed by joint integration (**Milestone 5**) and iterative UI/educational refinements (**Milestone 6**).

* **Milestones 1, 2, 3, and 4** are four independent, parallel workstreams—one assigned to each student (each owning both implementation and unit tests for their track).
* **Milestone 5** is the joint team milestone for end-to-end backend/frontend integration, full system verification, and unified repository refactoring.
* **Milestone 6** is the post-integration refinement track covering the zero-horizontal-scroll interactive trace inspector, the standalone animated **Lessons** curriculum (`#lessons`), the **Tutorial tour** rename, API plan synchronization, and expanded Playwright E2E testing.

---

## 1. Milestone Ownership

| Milestone File | Assigned Owner | Scope & Deliverables |
| :--- | :--- | :--- |
| **[Milestone 1](./Milestones/01_field_config_io_additive_mod_and_utilities.md)** | **Hussein Abbas** | **Field Registry, Multi-Base I/O, Additive/Modulo Engine, Utilities & Tutorial Data:**<br>Configures $m \in \{163, 233, 239, 283, 409, 571\}$ and $2 \le m \le 8$, Binary/Hex/Algebraic converters (`ALGEBRAIC_TO_INT` as *Optional Stretch*), $+$, $-$, $\bmod\ m(x)$, Random Operand Generator, Batch Polynomial File Parser, Calculation Summary Formatter, `tutorial_slides.json`, and M1 `pytest` suite. |
| **[Milestone 2](./Milestones/02_multiplication_engine_and_backend_api_controller.md)** | **Hassan Tarhini** | **Shift-and-XOR Multiplication, 6-Endpoint FastAPI Controller & API Tests:**<br>Implements modular multiplication $f(x) \times g(x) \bmod m(x)$ with step traces, execution timing, CORS, HTTP `400` validation errors, all 6 core endpoints (`/api/fields`, `/api/calculate`, `/api/random-polynomials`, `/api/parse-polynomials`, `/api/export-calculation`, `/api/tutorial`), and M2 `pytest` + `TestClient` suite. |
| **[Milestone 3](./Milestones/03_extended_euclid_inverse_division_and_verification_suite.md)** | **Husein Zahweh** | **Extended Euclid Inverse, Division & Multi-Field Verification Suite:**<br>Implements `POLY_MUL_NO_MOD`, `POLY_DIVMOD`, `EXTENDED_EUCLID_GF2M` with **Table 4.7** traces, field division, live self-verification (`VERIFY_INVERSE`, `VERIFY_DIVISION`), and automated `pytest` verification + benchmarks across $m = 8$ and $m \in \{163, 233, 239, 283, 409, 571\}$. |
| **[Milestone 4](./Milestones/04_educational_gui_and_step_visualizers.md)** | **Ali Zahreddine** | **Educational GUI Shell, Workbench, 4 Trace Visualizers & Tutorial Tour:**<br>Builds the single-view web GUI with top field/base bar (Hex-encoded Share Link rule), operand cards, Ch. 4/5 presets, random/upload toolbar, 6 operation buttons, result card with export, 4 custom trace visualizers, Tutorial drawer (`GET /api/tutorial`), and *(Optional Stretch)* UI enhancements. |
| **[Milestone 5](./Milestones/05_end_to_end_integration_and_verification.md)** | **Team** | **End-to-End Integration, 8-Row Matrix Verification & Deliverables Sign-Off:**<br>Connects M1–M4 across all live FastAPI endpoints, verifies all 8 textbook and cryptographic test identities plus edge cases, and completes unified repository refactoring and code documentation audit. |
| **[Milestone 6](./Milestones/06_refinements_interactive_lessons_and_testing.md)** | **Team (UI & E2E: Ali Zahreddine)** | **Refinements, Interactive Trace Redesign, Standalone Animated Lessons & Extended Testing:**<br>Eliminates horizontal table scrolling with `Step view`, `All steps grid`, `Classic table`, and `Expand full view` modal; adds `Compact values` formatting, 5-button playback + step scrubber, `Tutorial tour` rename, a standalone 7-lesson animated **Lessons** page (`#lessons`), and expanded Playwright E2E tests. |

---

## 2. Synchronization Contract (Live Unified Engine & API Schemas)

All backend modules (`backend/engine/`, `backend/api/`) and frontend modules (`frontend/`) adhere to two shared contracts:

### 2.1 Backend Internal Polynomial Contract (M1, M2, & M3)
* Every polynomial is passed internally between backend functions as a **non-negative integer (`int`)** where bit $i$ (counting from $0$ as the least significant bit) equals the coefficient $b_i \in \{0, 1\}$ of $x^i$.
* The irreducible polynomial $m(x)$ of degree $m$ is represented as an integer with bit $m$ set to $1$, e.g., for $m = 8$, $m(x) = x^8 + x^4 + x^3 + x + 1 \leftrightarrow \text{100011011}_2 = 283$.
* Traced arithmetic functions return `(result_int, trace_dict)` (or `(result_int, MultiplyTrace)` in `multiply_traced`), while fast-path helpers (`add`, `subtract`, `modulo`, `multiply`) return `result_int`.

### 2.2 Live API-to-GUI JSON Contract (`backend/api/schemas.py`)
1. **`GET /api/fields`** (`?include_textbook=true`)
   * **Response:** `{ "count": 13, "fields": [{ "m", "category", "name", "reduction_poly_hex", "reduction_poly_bin", "reduction_poly", "element_bits" }, ...] }` for $m \in \{163, 233, 239, 283, 409, 571\}$ and $2 \le m \le 8$.
2. **`POST /api/calculate`**
   * **Request:** `{ "m", "operation", "a", "b", "input_base", "output_base", "trace" }` (also accepts aliases `"poly_a"` and `"poly_b"` for `"a"` and `"b"`, short operation aliases `"sub"`, `"mod"`, `"mul"`, `"inv"`, `"div"` alongside `"add"`, `"subtract"`, `"modulo"`, `"multiply"`, `"inverse"`, `"divide"`, and bases `"hex"`, `"bin"`, `"binary"`, `"algebraic"`).
   * **Response (`200`):** `{ "operation", "field", "operands": { "a", "b" }, "result", "trace", "initial_reduction", "verification", "metrics": { "elapsed_ms", "result_bit_length", "result_hamming_weight" }, "share_token" }`.
   * **Error (`400`):** `{ "detail", "gcd"?, "trace"? }` (preserving Extended Euclid Table 4.7 termination rows when $B_3(x) = 0$).
3. **`POST /api/random-polynomials`**
   * **Request:** `{ "m", "density" (or alias "sparsity": "sparse" | "dense" | "random"), "seed"?, "count": 2, "output_base": "hex" | "bin" | "binary" | "algebraic" }`.
   * **Response:** `{ "field", "density", "seed", "a", "b", "m", "output_base", "polynomials": [...] }` generated via `GENERATE_RANDOM_POLY`.
4. **`POST /api/parse-polynomials`**
   * **Request:** `{ "content": "<raw .txt or .json string>", "filename": "...", "default_base": "hex" | "bin" | "binary" }`.
   * **Response:** `{ "count", "pairs": [{ "a", "b", "base" }, ...] }` validated by the Batch Polynomial File Parser.
5. **`POST /api/export-calculation`**
   * **Request:** `{ "calculation": <CalculateResponse>, "format": "md" | "json", "download": true | false }`.
   * **Response:** Streams a downloadable `.md` or `.json` summary attachment when `download: true`, or returns `{ "filename", "media_type", "content" }`.
6. **`GET /api/tutorial`**
   * **Response:** `{ "version": "1.0", "title": "...", "slides": [...] }` serving `data/tutorial_slides.json` (4 educational slides and Chapter 4/5 presets).
7. **Bonus Interactive Exploration Routes (`/api/explorations/*`)**
   * `POST /api/explorations/modulus`, `POST /api/explorations/aes-sbox`, `POST /api/explorations/compare-multiplication`, and `GET /api/explorations/multiplication-benchmarks` (see [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for full schemas).

---

## 3. Shared Coding & Documentation Standards
* **Commented, Readable Code:** Every module, class, and function includes docstrings/JSDoc explaining its inputs, outputs, complexity, and exact references to **Stallings Chapter 4 (Finite Fields), Chapter 5 (AES), Chapter 6 (Block Cipher Operation — XTS-AES over $GF(2^{128})$ arithmetic), and Chapter 10 (Elliptic Curve Cryptography over $GF(2^m)$ curves)**.
* **Consistent Naming:** Variable names remain mathematically transparent (`m_poly_int`, `a_int`, `b_inv_int`, `q_int`, `r_int`) across all engine, API, and test modules.

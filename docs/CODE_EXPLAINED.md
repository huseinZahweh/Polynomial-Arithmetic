# Codebase Explained — File-by-File & Function-by-Function Guide

This reference walks through every Python and JavaScript module in the unified **EECE 455 Project-3 ($GF(2^m)$ Polynomial Arithmetic)** repository so any teammate or grader can trace how every operation, endpoint, visualizer, and benchmark works.

---

## 1. Root Entry Point

### `run.py` — Ali Zahreddine (Milestone 4 & Integration)
Clean CLI launcher for the unified application (`python run.py` or `python run.py --host 127.0.0.1 --port 8000 --reload`):
* **`parse_args(argv)`:** Parses `--host`, `--port`, and `--reload` flags via `argparse`.
* **`main(argv)`:** Invokes `uvicorn.run("backend.api.main:app", ...)` serving both the API and `/workbench/`.

---

## 2. Pure-Python Finite-Field Engine (`backend/engine/`)

### `backend/engine/__init__.py` — Team
Re-exports all public engine classes, functions, exceptions, and exploration helpers as a clean, framework-free package interface.

### `backend/engine/fields.py` — Hussein Abbas (Milestone 1)
Canonical $O(1)$ lookup table for all 13 supported binary finite fields ($2 \le m \le 8$ from Project-2 and $m \in \{163, 233, 239, 283, 409, 571\}$ from NIST FIPS 186-4 / SECG SEC 2):
* **`Field` (frozen dataclass):** Stores `m`, `mod_poly` (full bitmask with bit $m$ set), `category` (`"textbook"` or `"nist"`), and `name` (`"GF(2^m)"`). Properties `reduction_poly_terms` (ascending exponents) and `taps` (descending exponents).
* **`DEFAULT_DEGREE = 163`:** Project-3 primary field degree.
* **`is_supported(m)` / `get_field(m)` / `get_m_poly_int(m)`:** Exact-integer $O(1)$ lookups rejecting booleans, floats, and unconfigured degrees.
* **`list_fields(include_textbook=True)` / `list_supported_degrees(include_textbook=True)`:** Ascending catalogs with optional filtering to cryptographic fields only.

### `backend/engine/polyrepr.py` — Hussein Abbas (M1), Hassan Tarhini (M2), Husein Zahweh (M3), Ali Zahreddine (M4)
Single unified representation, validation, and base-conversion module:
* **`validate_non_negative_poly(value, name)` / `validate_modulus(m_poly_int, m_degree)`:** Enforces strict non-boolean integer bitmasks and checks $\deg(m(x)) = m$.
* **`DEG(poly_int)` / `HAMMING_WEIGHT(poly_int)`:** $O(1)$ degree via `bit_length() - 1` (`-1` for `0`) and term count via `bit_count()`.
* **`BIN_TO_INT(text)` / `HEX_TO_INT(text)`:** Parses grouped binary/hex strings (allowing whitespace grouping, Stallings Ch. 5 `{...}` braces, and `0b`/`0x` prefixes; strictly rejecting `+`, `-`, and `_`).
* **`ALGEBRAIC_TO_INT(text)`:** Parses monomial sums like `x^7 + x + 1`, cancelling duplicate terms modulo 2 via XOR and capping exponents below $4096$.
* **`parse_value(text, base)`:** Strict REST API parser for `"hex"`, `"bin"`/`"binary"`, and `"algebraic"` (rejecting embedded spaces in hex/binary).
* **`INT_TO_BIN(poly_int, m)` / `INT_TO_HEX(poly_int, m)` / `to_hex(value, m)` / `INT_TO_ALGEBRAIC(poly_int)`:** Lossless formatters zero-padded to field width without truncating overflow bits.
* **`format_poly_representations(value_int, m_degree, uppercase_hex=True)`:** Builds `{int, hex, bin, algebraic, degree}` dicts used in Table 4.7 cells and proof objects.
* **`ElementRepr` (frozen dataclass):** Stores `{hex, bin, poly, degree, bit_length, hamming_weight}` returned by REST endpoints.

### `backend/engine/additive.py` — Hussein Abbas (Milestone 1)
Characteristic-2 addition, subtraction, and polynomial modulo reduction (Stallings Ch. 4 & 5):
* **`_reduce(value_int, m_poly_int, m_degree, steps=None)`:** Core shift-and-XOR loop canceling each leading term $x^d$ ($d \ge m$) with `m_poly_int << (d - m_degree)` in $O((d - m + 1) \cdot d)$ bit operations.
* **`MOD_REDUCE(f_int, m_poly_int, m_degree)`:** Returns `(reduced_int, trace_dict)` with `trace_type="mod_reduce"` and per-step `{target_degree, shift, before, reducer, after}`.
* **`xor_trace(a, b, m)`:** Builds MSB-to-LSB aligned bit columns and formatted hex/bin/poly rows (`algorithm="bitwise-xor"`).
* **`GF2M_ADD_SUB(f_int, g_int, m_poly_int, m_degree)`:** Reduces both operands, computes $a_{\text{red}} \oplus b_{\text{red}}$, and merges pre-reduction traces with `xor_trace`.
* **`modulo`, `add`, `subtract`:** Fast untraced scalar functions (`subtract = add` in characteristic 2).

### `backend/engine/multiply.py` — Hassan Tarhini (Milestone 2)
Iterative Shift-and-XOR modular multiplication (Stallings Ch. 4, 5, 6, & 10):
* **`reduce_mod` / `carryless_mul`:** Clean wrappers delegating to `additive.modulo` and `poly_ops.POLY_MUL_NO_MOD`.
* **`multiply(a, b, mod_poly, m)`:** Fast untraced $O(m^2)$ Shift-and-XOR product used by verification, untraced division, and benchmarks. Reduces overflow $x^m$ via single `t ^= mod_poly` when `t & (1 << m)` is set.
* **`ShiftStep` & `MultiplyTrace`:** Structured dataclasses serializing Table 1 (`partial_hex`, `partial_poly`, `reduced`) and Table 2 (`multiplier_bit`, `added`, `accumulator_hex`) plus `summary` (`reductions`, `partial_products`, `truncated`).
* **`multiply_traced(a, b, mod_poly, m, max_steps=2048)`:** Records every Shift-and-XOR step while remaining exact even if `max_steps` caps huge dense traces.

### `backend/engine/poly_ops.py` — Husein Zahweh (Milestone 3)
Unreduced polynomial ring primitives over $GF(2)[x]$ (Stallings Ch. 4):
* **`POLY_MUL_NO_MOD(a_int, b_int)`:** Carry-free multiplication looping over the shorter operand in $O(\min(d_a, d_b) \cdot (d_a + d_b))$ bit ops.
* **`DivisionStep` (frozen dataclass):** Captures `(shift, before, shifted_divisor, after)` for each leading-term cancellation.
* **`POLY_DIVMOD(a_int, b_int, *, steps=None)`:** Euclidean long division returning `(q_int, r_int)` with $A(x) = Q(x) B(x) \oplus R(x)$ and $\deg(R) < \deg(B)$ (raises `ZeroDivisionError` if $B = 0$).

### `backend/engine/exceptions.py` — Husein Zahweh (Milestone 3)
Structured inverse error hierarchy carrying `.gcd` and `.trace` for educational HTTP 400 display:
* **`GF2mInverseError(ValueError)`:** Shared base class with `.gcd` and `.trace`.
* **`ZeroElementHasNoInverseError`:** Raised when $b(x) \bmod m(x) = 0$ at Step 0 ($B_3 = 0$, $A_3 = m(x)$).
* **`NotInvertibleError`:** Raised when $B_3 = 0$ mid-loop for a reducible modulus ($A_3 = \gcd(m(x), b(x)) \neq 1$).

### `backend/engine/extended_euclid.py` — Husein Zahweh (Milestone 3)
Stallings Chapter 4 Table 4.7 Extended Euclidean Algorithm:
* **`_build_table_4_7_row(...)` / `_build_trace_dict(...)`:** Constructs raw integer columns and pre-formatted multi-base `cells` (`hex`, `bin`, `algebraic`) plus initial reduction and termination metadata.
* **`EXTENDED_EUCLID_GF2M(m_poly_int, m_degree, b_int)`:** Reduces $b(x)$ via `MOD_REDUCE`, runs the Bezout triple recurrence in $O(m^2)$ time, returns `(b_inv_int, trace_dict)` on $B_3 = 1$, or raises `ZeroElementHasNoInverseError` / `NotInvertibleError` on $B_3 = 0$.

### `backend/engine/division.py` — Husein Zahweh (Milestone 3)
Two-stage finite-field division $a(x) / b(x) = a(x) \times b(x)^{-1} \bmod m(x)$:
* **`GF2M_DIVIDE(a_int, b_int, m_poly_int, m_degree)`:** Runs Stage 1 (`EXTENDED_EUCLID_GF2M`) and Stage 2 (`multiply_traced`), returning `(quotient_int, trace_dict)` with `trace_type="gf2m_division_two_stage"`.

### `backend/engine/verification.py` — Husein Zahweh (Milestone 3)
Live algebraic proof builders:
* **`VERIFY_INVERSE(b_int, b_inv_int, m_poly_int, m_degree)`:** Confirms `b_inv_int < 2^m` and `multiply(b_int, b_inv_int, m_poly_int, m_degree) == 1`.
* **`VERIFY_DIVISION(a_int, b_int, q_int, m_poly_int, m_degree)`:** Confirms `b_red != 0`, `q_int < 2^m`, and `multiply(q_int, b_red, m_poly_int, m_degree) == a_red`.

### `backend/engine/randomops.py` — Hussein Abbas (Milestone 1)
* **`GENERATE_RANDOM_POLY(m, sparsity="dense", *, seed=None)`:** Uses `secrets.SystemRandom()` (or seeded `random.Random`) to sample uniform dense values in $[1, 2^m - 1]$ or sparse 3–6 term elements.
* **`generate_operand(m, density="random", seed=None)`:** Maps API `"random"` density to uniform `"dense"`.

### `backend/engine/parser.py` — Hussein Abbas (Milestone 1)
* **`OperandFileError(ValueError)`:** Carries `.pair`, `.line`, and `.field` diagnostics.
* **`parse_operand_file(content, filename="", default_base="hex")`:** Auto-detects `.json` vs. `.txt` (supporting BOM removal, `#` comments, `---`/`===` delimiters, and optional unary `B`) and validates every digit via `HEX_TO_INT`/`BIN_TO_INT`.

### `backend/engine/formatter.py` — Hussein Abbas (Milestone 1) & Ali Zahreddine (Integration)
* **`make_share_token` / `parse_share_token`:** Encodes/decodes `v1|{m}|{op}|{a_hex}|{b_hex}|{base}` as lowercase UTF-8 hex.
* **`to_json` / `to_markdown` / `render(calc, fmt)`:** Builds downloadable Markdown or JSON reports with regex-sanitized attachment filenames.

### `backend/engine/tutorial.py` — Hussein Abbas (Milestone 1)
* **`load_tutorial()`:** Reads `data/tutorial_slides.json` relative to the package root regardless of working directory.

### `backend/engine/explorations.py` — Ali Zahreddine (Milestone 4 & Integration) & Husein Zahweh (Milestone 6 Applications)
Pure-Python exploration and cryptographic application engines:
* **`_poly_gcd(a, b)` & `_split_square_free(polynomial)`:** Euclidean GCD over $GF(2)[x]$ plus Berlekamp $Q - I$ column elimination (**bonus mathematical extension beyond Stallings Ch. 4**) to split equal-degree square-free products.
* **`explore_modulus(polynomial)`:** Checks irreducibility for degrees $2 \le d \le 571$ via $\gcd(f, x^{2^i} + x)$ and extracts two nonzero factor witnesses when reducible.
* **`compute_xts_tweak(t0_hex, steps=6)`:** Computes the IEEE 1619-2007 / Stallings Ch. 6 XTS-AES $GF(2^{128})$ tweak sequence $T_j = T_0 \otimes \alpha^j \pmod{x^{128} + x^7 + x^2 + x + 1}$, flagging every $b_{127} = 1$ overflow reduction (`⊕ 0x87`).
* **`ECC_CURVES`, `ecc_is_on_curve`, `ecc_double`, `ecc_add`, `ecc_scalar_mul`, `explore_binary_ecc(curve, n_a, n_b)`:** Binary elliptic curve explorer ($E_{2^m}(a,b)$: $y^2 + xy = x^3 + ax^2 + b$) supporting both Teaching Curve $GF(2^4)$ ($G = (\text{3}, \text{C})$) and official NIST FIPS 186-4 / SEC 2 **NIST B-163** ($GF(2^{163})$), reusing canonical `backend.engine` `add`, `multiply`, `EXTENDED_EUCLID_GF2M`, and `GF2M_DIVIDE` primitives for point doubling ($R = 2P$), point addition ($R = P + Q$), curve membership verification, and ECDH ($K = n_A P_B = n_B P_A$).
* **`gcm_ghash(h_hex, blocks_hex)`:** NIST SP 800-38D / Stallings Ch. 12 GCM GHASH authenticator over $GF(2^{128})$ modulo $x^{128} + x^7 + x^2 + x + 1$, chaining canonical `add` (XOR) and `multiply` (Shift-and-XOR) across $1$–$8$ 128-bit blocks to compute $Y_i = (Y_{i-1} \oplus X_i) \cdot H \bmod m(x)$ and returning per-block steps, `tag_hex`, `tag_poly`, and `elapsed_ms`.
* **`compare_multiplication(m, a, b)`:** Runs Shift-and-XOR (`multiply_traced`) alongside `POLY_MUL_NO_MOD` + traced `POLY_DIVMOD`.
* **`benchmark_multiplication(seed=455, trials=31, degrees=(163, 571))`:** Alternates untraced execution order across 31 trials per method and reports median microseconds.

---

## 3. FastAPI Web Layer (`backend/api/`)

### `backend/api/schemas.py` — Hassan Tarhini (M2) & Ali Zahreddine (Integration)
Defines Pydantic v2 enums (`Operation` with aliases `sub`/`mod`/`mul`/`inv`/`div`, `Base` mapping `binary` $\rightarrow$ `bin`, `Density`, `ExportFormat`) and typed request/response models for all 6 core endpoints.

### `backend/api/services.py` — Hassan Tarhini (M2) & Ali Zahreddine (Integration)
* **`CalculationError`:** Domain error mapped to HTTP 400 (preserving optional `.gcd` and `.trace`).
* **`build_field_info` / `field_info` / `element_model`:** Converts engine objects into Pydantic response models.
* **`_reduce` / `_parse_operand` / `_dispatch` / `calculate(req)`:** Orchestrates strict input parsing (4096-bit cap), initial reduction hex formatting, engine dispatch across all 6 operations, `perf_counter()` timing, live verification badges, and `v1` share-token generation.

### `backend/api/exploration_routes.py` — Ali Zahreddine (Milestone 4 & Integration) & Husein Zahweh (Milestone 6 Applications)
Defines Pydantic request models (`ModulusRequest`, `XTSTweakRequest`, `BinaryECCRequest`, `GCMGHashRequest`, `MultiplicationRequest`), strict input validation helper `_parse_input` (HTTP 400 on error), and the six `/api/explorations/*` FastAPI endpoints delegating to `backend.engine.explorations`.

### `backend/api/main.py` — Hassan Tarhini (M2) & Ali Zahreddine (Integration)
Creates the single FastAPI `app`, configures CORS, exposes meta routes (`GET /`, `GET /api/health`) and all 6 core endpoints, includes `explorations_router`, and mounts `frontend/` at `/workbench/`.

---

## 4. Educational Web Workbench (`frontend/`)

Authored by **Ali Zahreddine (Milestones 4 & 5)** with **Milestone 6** refinements by **Husein Zahweh**:

### `frontend/index.html`, `frontend/lab.css` & `frontend/gf2m-badge.png`
* **Custom Brand Emblem & Favicon (`frontend/gf2m-badge.png`):** Crisp $GF(2^m)$ logo asset served under `/workbench/gf2m-badge.png`, rendered inside the header `.brand-badge` rounded crest (`42px × 42px` desktop, `36px × 36px` mobile) and wired as the browser tab `<link rel="icon">`, paired with the header subtitle **`GF(2ᵐ) Polynomial Arithmetic · EECE 455`** (`<sup>m</sup>`).
* **Single-Document Five-View Workbench:** Serves `#calculator`, `#lessons`, `#modulus`, `#applications`, and `#compare`, plus the top-center error alert (`#error-popup`), Full-Value Inspector (`#inspector-popup`), Step Derivation (`#derivation-popup`), upload modal (`#upload-modal`), and toast (`#feedback-popup`).

### `frontend/notation.js`
* **`bases`:** Notation configuration table (`hex`, `binary`, `algebraic`) with non-numeric prompt metadata.
* **`toSuperscriptDigits` / `formatPolyWithSuperscripts` / `normalizeAlgebraicInput` / `applyInputFormatting`:** Live input formatting auto-uppercasing Hex letters (`a-f` → `A-F`) and raising Polynomial exponents to Unicode superscripts (`x^6` → `x⁶`) while preserving caret position, and normalizing Unicode superscripts back to plain ASCII `x^k` before parsing, API requests, exports, or share links.
* **`parseOperand(text, base)` / `formatOperand(value, base, m)` / `polynomial(value)` / `degreeOf(value)`:** Exact client-side `BigInt` parsing and formatting matching backend validation up to $4096$ bits (omitting leading hex zeros).
* **`mathFragment(text)` / `appendMathText(node, text)` / `setMathText(node, text)` / `mathElement(tag, text, className)`:** XSS-safe DOM builders (never `innerHTML`) converting exponents (`GF(2^163)`, `x^4`, `x^-1`, `x^(2^i)`, `α^j`, Unicode superscripts) and subscripts (`b_1x` → `b<sub>1</sub>x`, `A1`-`A3`, `B1`-`B3`, `T1`-`T3`, `b_127`, `P_A`) into true `<sup>`/`<sub>` elements.
* **`attachSlidingIndicator(container, activeSelector)`:** Attaches a smooth slow-gliding `.sliding-pill` highlight across floating navigation strips, segmented bars, operation grids, and sub-tabs.
* **`showErrorPopup({ title, message, onViewTrace })` / `closeErrorPopup()`:** Controls the sleek top-center floating error alert card (`#error-popup`) with left red accent strip, `×` close button, `Esc` dismissal, and optional trace jump without obscuring operand inputs.
* **`showInspectorPopup({ title, valueBigInt, mDegree, subtitle })` / `showDerivationPopup({ title, subtitle, formula, steps, result })`:** Dismissible `<dialog>` modals powering the Full-Value Inspector (complete Hex, Binary, and Polynomial with Copy buttons) and step-specific mathematical derivation breakdowns.
* **`copyToClipboard(text)` / `showFeedbackPopup(title, detail, variant)`:** Reliable clipboard copy helper and non-blocking bottom-right confirmation toast (`#feedback-popup`).

### `frontend/traces.js`
* **`polyMulNoModBigInt` / `polyDivModBigInt` / `openEuclidDerivationPopup` / `openShiftXorIllustrationPopup`:** Client-side `BigInt` derivation engines powering the 4 Extended Euclid step breakdown buttons (`How Q / T₁ / T₂ / T₃ is calculated`) and the Shift-and-XOR `Show Shift & XOR illustration` popup for the currently displayed step.
* **`createDiffLegend()` / `createTableColorLegend()` / `attachValueInteraction` / `buildDiffValueNode`:** WCAG AA step diff legend, `Classic table` color legend, and automatic click-to-inspect **Full Value Inspector** trigger (with subtle expand cue `⤢`) on truncated large-field cells.
* **`multiplyStepCard`:** Streamlined two-block Shift-and-XOR card (no redundant blue summary banner, intuitive `A(x)` / `<< 1` / bit `bᵢ` descriptions, calculation steps ordered **above** the bold resulting `Shifted value` and `Running Sum`, `Show Shift & XOR illustration` button, and bottom live running formula strip).
* **`reductionStepCard`:** Full untruncated hex Modulo Reduction card removing the duplicate banner and separate `Shift` row, placing `Shifted modulus · m(x) << k` directly between `Before` and `After XOR`.
* **`euclidInspectorSquare`:** Zero-horizontal-scroll Table 4.7 Step Inspector Square with 4 consistent breakdown buttons (`Q`, `T₁`, `T₂`, `T₃`, disabled with note on Step 0), carried **Triple A** / updated **Triple B** diff cards, and Full-Value Inspector popups on truncated values.
* **`createTraceView(panel, body, tools)`:** Always defaults to **`Step view`** across all 13 field sizes (`m in {2..8, 163..571}`) with built-in side-by-side **Previous → Current** comparison from Step 1 onward (single card on Step 0), inline single-column **`All steps grid`** loading 4 steps initially with **`Show more`** (+4 per click), **`Classic table`** with color highlight legend, automatic playback & keyboard locking outside `Step view`, `First changed bit` jump, and sequential cascade.

### `frontend/lesson-data.js`
* **`LESSONS`:** Self-contained 7-lesson curriculum array aligned with William Stallings Chapters 4, 6 (XTS-AES), and 10 (Binary ECC), containing clean 4-row $\mathbb{Z}_2$ truth tables (`1.2` and `2.1`), embedded worked classroom tables (`{2B79} mod {11B} = {C1}`, `{57} × {83} = {C1}`, Stallings Table 4.7 `{83}⁻¹ = {80}`, `{C1} ÷ {83} = {57}`), interactive sandboxes, and self-check quizzes.

### `frontend/lessons.js`
* **`renderVisual(visual)` / `buildBitSandbox()` / `buildXorActivity()` / `buildQuiz(quiz)`:** Renders `truth-table`, `worked-table`, `cards`, `xor-columns`, `reduction-step`, `shift-register`, `mul-walkthrough`, `poly-divmod`, and `pipeline` stages in one clean scrollable section card.
* **`setupLessons()`:** Manages the `#lessons` catalog hub, gliding top section bar (`#lesson-subtabs`), and linear **`Previous section`** / **`Next section`** footer navigation across all sections of the 7-lesson curriculum (no playback toolbar, no Calculator handoff buttons).

### `frontend/tour.js`
* **`calculatorSteps` & `walkthroughs`:** Spotlight walkthrough registries for all five views (`calculator`, `lessons`, `modulus`, `applications`, `compare`), including explicit Calculator guidance for Full-Value Inspector and step breakdown popups.
* **`setupPageTour()`:** Floating **`Tutorial tour`** controller rendering `<sup>`/`<sub>` math tooltips, dynamic fallback targets, `Escape` dismissal, and live re-highlighting on `lab:calculation-result`.

### `frontend/explorations.js`
* **`bindExperiment` / `setupNavigation`:** Hash router (`#calculator`, `#lessons`, `#lessons/<id>`, `#modulus`, `#applications`, `#compare`) with floating gliding `.lab-nav` pill indicator and top-center error routing.
* **`setupModulus`:** Modulus irreducibility lab with Unicode superscript Polynomial & auto-uppercase Hex input formatting, factor witnesses, and plain-English GCD checkpoint explanation.
* **`setupApplications`:** Gliding 3-sub-tab controller for **XTS-AES $GF(2^{128})$ Tweak Multiplier** (`POST /api/explorations/xts-tweak`, randomize, step next block, overflow `XOR 0x87` highlights), **Polynomial / Binary ECC Explorer** (`POST /api/explorations/binary-ecc`, Teaching $GF(2^4)$ & NIST B-163 aligned with classroom slide notation `P = (Xp, Yp)`, `Q = (Xq, Yq)`, `R = (Xr, Yr)`, slope `s`, tagged steps, verified badges, Full-Value Inspector on 163-bit coordinates, and ECDH card), and **GCM · GHASH ($GF(2^{128})$) Authenticator** (`POST /api/explorations/gcm-ghash`, full 128-bit XOR & Shift-and-XOR block table, Full-Value Inspector popups, and `?app=ghash&h=...&blocks=...#applications` share links).
* **`setupComparison` & `setupExplorations`:** Side-by-side multiplication comparison lab (`Compare multiplication methods` transfer queue, auto-uppercase hex inputs) and 163/571-bit benchmark table.

### `frontend/lab.js`
* **`api(path, data, download)`:** Shared `fetch()` client preserving HTTP 400 `.payload` (`gcd` + `trace`).
* **`renderBits` / `renderOperands` / `changeNotation`:** Live `applyInputFormatting` (auto-uppercase Hex, Unicode superscript Polynomial), non-numeric placeholders (`Enter A(x)`, `Enter B(x)`), interactive $m \le 8$ checkboxes, read-only **Modulus $m(x)$** card on `modulo`/`inverse`, and lossless base conversion.
* **`renderResult` / `calculate`:** Displays full untruncated Hex, Binary, and Polynomial results (wrapped/scrollable for large fields), `Compare multiplication methods` + helper note, untouched timing/bit/Hamming metric badges, and Unicode-normalized API payloads.
* **`makeShareURL` / `readShareURL` / `handleUploadFile` / `init`:** Hex-compressed share links, drag-and-drop upload modal (`#upload-modal`), textbook presets, and parallel startup initialization.

---

## 5. Benchmarks (`benchmarks/benchmark_gf2m.py`) — Husein Zahweh (Milestone 3)

* **`BenchmarkRow`:** Frozen record aggregating EEA timing, EEA iterations, and division timing per `(m_degree, mode)`.
* **`run_benchmarks(degrees, trials, seed)`:** Deterministic sparse/dense benchmark across $m \in \{8, 163, 233, 239, 283, 409, 571\}$, cross-checking every result outside the timed window with `VERIFY_INVERSE` and `VERIFY_DIVISION`.
* **`format_markdown_table(rows)` & `main(argv)`:** Emits GitHub-Flavored Markdown tables directly from the CLI (`python -m benchmarks.benchmark_gf2m`).

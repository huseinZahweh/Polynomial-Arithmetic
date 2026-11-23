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

### `backend/engine/explorations.py` — Ali Zahreddine (Milestone 4 & Integration)
Pure-Python exploration engines:
* **`_poly_gcd(a, b)` & `_split_square_free(polynomial)`:** Euclidean GCD over $GF(2)[x]$ plus Berlekamp $Q - I$ column elimination (**bonus mathematical extension beyond Stallings Ch. 4**) to split equal-degree square-free products.
* **`explore_modulus(polynomial)`:** Checks irreducibility for degrees $2 \le d \le 571$ via $\gcd(f, x^{2^i} + x)$ and extracts two nonzero factor witnesses when reducible.
* **`compute_aes_sbox(byte)`:** Full FIPS 197 §5.1.1 / Stallings Ch. 5 SubBytes (EEA inverse + 4 cyclic left rotations + `0x63` affine XOR).
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

### `backend/api/exploration_routes.py` — Ali Zahreddine (Milestone 4 & Integration)
Defines Pydantic request models (`ModulusRequest`, `SBoxRequest`, `MultiplicationRequest`), strict input validation helper `_parse_input` (HTTP 400 on error), and the four `/api/explorations/*` FastAPI endpoints delegating to `backend.engine.explorations`.

### `backend/api/main.py` — Hassan Tarhini (M2) & Ali Zahreddine (Integration)
Creates the single FastAPI `app`, configures CORS, exposes meta routes (`GET /`, `GET /api/health`) and all 6 core endpoints, includes `explorations_router`, and mounts `frontend/` at `/workbench/`.

---

## 4. Educational Web Workbench (`frontend/`)

All seven ES modules and HTML/CSS were authored by **Ali Zahreddine (Milestone 4, Integration & Milestone 6)**:

### `frontend/notation.js`
* **`bases`:** Notation configuration table (`hex`, `binary`, `algebraic`).
* **`parseOperand(text, base)` / `formatOperand(value, base, m)` / `polynomial(value)` / `degreeOf(value)`:** Exact client-side `BigInt` parsing and formatting matching the backend's validation and padding rules up to $4096$ bits.
* **`significantDigits(text)` / `element(tag, text, className)`:** Leading-zero trimmer for large-field previews and safe DOM builder (`textContent` only).
* **`mathFragment(text)` / `appendMathText(node, text)` / `setMathText(node, text)` / `mathElement(tag, text, className)`:** XSS-safe DOM builders (never `innerHTML`) converting exponents (`GF(2^163)`, `x^4`, `x^-1`, `x^(2^i)`, Unicode superscripts) and indexed variables (`A1`–`A3`, `B1`–`B3`, `T1`–`T3`, `b0`–`b7`, Unicode subscripts) into true `<sup>`/`<sub>` elements while keeping hex literals untouched.
* **`attachSlidingIndicator(container, activeSelector)`:** Attaches a smooth gliding `.sliding-pill` background/border indicator across navigation strips, segmented bars, operation grids, and step timelines.
* **`showErrorPopup({ title, message, onViewTrace })` / `closeErrorPopup()`:** Opens/closes the top-level `#error-popup` modal dialog with formatted math typography and optional trace-jump action.

### `frontend/traces.js`
* **`createDiffLegend()` / `buildDiffValueNode(displayValue, meta)`:** Shared WCAG AA visual diff legend (`.diff-carried`, `.diff-updated`, `.diff-reduced`, `.diff-unchanged`) and styled diff value box renderer with micro-badges and inline `was:` / `prev → now` deltas.
* **`euclidKnowledgeTitle` / `multiplyKnowledgeTitle` / `reductionKnowledgeTitle` / `xorKnowledgeTitle`:** Educational step title generators (`.step-knowledge-title`) summarizing the exact mathematical transformation of every step (with Stage 1/Stage 2 prefixes on Division).
* **`formatCellText` / `makeCopyableValue`:** Large-field cell formatter (`Compact values` vs. `Full m-bit`) and click-to-copy value helper.
* **`table(title, headers, rows, selected, diffOpts)` / `stepCard(eyebrow, knowledgeTitle, labels, values, isCurrentRegion, options)`:** Accessible wrapped table (supporting `<sup>`/`<sub>` headers, educational subtitles, and previous/current row diff tinting) and diff-aware step card builders.
* **`euclidInspectorSquare(trace, rowIndex, notation, compactValues, isCurrentRegion, stagePrefix)`:** Zero-horizontal-scroll **Extended Euclid Step Inspector Square** rendering step eyebrow, educational `.step-knowledge-title`, quotient pill $Q(x)$, step-change transition banner, live recurrence formula callout, and side-by-side **Triple A** (`← prev B1..B3`) and **Triple B** (`New T1..T3`) cards with true `<sub>`/`<sup>` labels, inline `was:` values, and termination badges.
* **`reduction`, `xor`, `multiply`, `euclid`:** The four custom trace visualizers supporting three layout modes (`Step view`, auto-maximized `All steps grid`, `Classic table`), `prev → now` shift/reduction and accumulator deltas, roving-tabindex multiplier-bit strips with linked Table 1/Table 2 row highlights, and Table 4.7 cell-notation switching.
* **`createTraceView(panel, body, tools)`:** Stateful controller managing the 3 layout modes with a gliding pill switcher, auto-maximization on `All steps grid` (`Exit maximized view` + `Esc`), sequential step cascade (`cascadeTo`) on non-adjacent bit/scrubber jumps, side-by-side `Compare prev → curr` mode, uncluttered 2-row toolbar (`First step`, `Previous`, `Play animation`/`Pause` + speed selector, `Next`, `Last step`, interactive scrubber), `Compact values` / `Full m-bit` toggle, and the `Expand full view` modal dialog (`#trace-fullscreen`).

### `frontend/lesson-data.js`
* **`LESSONS`:** Comprehensive 7-lesson curriculum array (21 sub-lessons) aligned with William Stallings Chapters 4, 5, 6 (XTS-AES), and 10 (Binary ECC), containing step titles, `diffSummary` slide-transition descriptions, mathematical formulas, zero-scroll visual specifications (`cards`, `xor-columns`, `reduction-step`, `shift-register`, `mul-walkthrough`, `poly-divmod`, `euclid-step`, `pipeline`), interactive mini-activities, self-check quizzes, and Calculator preset handoffs.

### `frontend/lessons.js`
* **`renderVisual(visual, prevVisual)`:** Renders animated zero-horizontal-scroll visual stages with true `<sup>`/`<sub>` typography and automatic Previous-to-Current value-level diff highlights (`.diff-carried`, `.diff-updated`, `.diff-reduced`, `.diff-unchanged`), micro-badges, and inline `was:` / `prev → now` deltas.
* **`buildLessonStepFrame(sub, steps, idx, isPreviousSnapshot)`:** Builds each slide frame with prominent `.step-knowledge-title`, `"From Step k-1 → Step k"` transition banners for active slides, and clean read-only snapshots for comparison mode.
* **`buildBitSandbox()` / `buildXorActivity()` / `buildQuiz(quiz)`:** Interactive 8-bit polynomial coefficient builder, 4-bit XOR challenge, and instant-feedback multiple-choice check cards.
* **`setupLessons({ openInCalculator })`:** Initializes the `#lessons` catalog hub, gliding sub-lesson tabs (`#lesson-subtabs`), gliding step dots (`#lesson-step-dots`) with sequential step cascade (`cascadeToStep`), 5-button animation playback controller, `#lesson-compare` (`Compare prev → curr`) side-by-side slide toggle, keyboard shortcuts (`ArrowLeft`, `ArrowRight`, `Home`, `End`, `Space`), deep-link selector `selectLessonById(id)`, and one-click Calculator handoffs.

### `frontend/tour.js`
* **`calculatorSteps` & `walkthroughs`:** Step registries for all five views (`calculator`, `lessons`, `modulus`, `aes`, `compare`).
* **`setupPageTour()`:** Floating **`Tutorial tour`** spotlight walkthrough controller rendering `<sup>`/`<sub>` math tooltips, dynamic fallback targets, `Escape` dismissal, and live re-highlighting on `lab:calculation-result` events.

### `frontend/explorations.js`
* **`bindExperiment` / `setupNavigation(closeTour, onLessonRoute)`:** Hash router (`#calculator`, `#lessons`, `#lessons/<id>`, `#modulus`, `#aes`, `#compare`) with gliding `.lab-nav` pill indicator, pop-up error routing (`showErrorPopup`), and busy-locked async form wrapper.
* **`setupModulus`, `setupAES`, `setupComparison`, `setupExplorations`:** UI controllers for the three exploration tabs, including `<sup>`/`<sub>` status formatting, the `Compare this product` transfer queue, and the 163/571-bit benchmark table.

### `frontend/lab.js`
* **`api(path, data, download)`:** Shared `fetch()` client preserving HTTP 400 `.payload` (`gcd` + `trace`).
* **`renderBits` / `renderOperands` / `changeNotation`:** Interactive $m \le 8$ coefficient checkboxes (`x⁷`–`1`), live validation previews with `<sup>`, dynamic read-only **Modulus $m(x)$** card on `modulo`/`inverse` (preserving typed `B(x)` across switches), pop-up error modal alerts, gliding notation & operation indicators, and lossless base conversion.
* **`renderResult` / `previewValue` / `calculate`:** Compact large-field previews with `Show full value`, full-value clipboard copy, verification/metric badges, and revision-guarded async requests.
* **`makeShareURL` / `readShareURL`:** Hexadecimal-compressed query-string serialization and restoration.
* **`presetButton` / `renderSlide` / `loadPair` / `setupLessons` / `init`:** Textbook preset launchers, 4-slide concepts modal, batch upload pair selector, Lesson-to-Calculator handoff bridge, and parallel startup initialization.

---

## 5. Benchmarks (`benchmarks/benchmark_gf2m.py`) — Husein Zahweh (Milestone 3)

* **`BenchmarkRow`:** Frozen record aggregating EEA timing, EEA iterations, and division timing per `(m_degree, mode)`.
* **`run_benchmarks(degrees, trials, seed)`:** Deterministic sparse/dense benchmark across $m \in \{8, 163, 233, 239, 283, 409, 571\}$, cross-checking every result outside the timed window with `VERIFY_INVERSE` and `VERIFY_DIVISION`.
* **`format_markdown_table(rows)` & `main(argv)`:** Emits GitHub-Flavored Markdown tables directly from the CLI (`python -m benchmarks.benchmark_gf2m`).

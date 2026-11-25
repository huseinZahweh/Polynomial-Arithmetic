# Milestone 6: Refinements, Breakdown Popups, Self-Contained Lessons & Applications

**Assigned Owner:** **Husein Zahweh**  
**Prerequisite:** Completion of Milestones 1–5 Unified Application Layout

---

## 1. Objective

Refine the integrated **Finite Field Lab** user experience across all five tabs (`Calculator`, `Lessons`, `Modulus explorer`, `Applications`, `Compare multiplication`), standardize `Step view` with built-in Previous → Current comparison and on-demand mathematical derivation / full-value popups across all 13 fields ($m \in \{2 \dots 8, 163 \dots 571\}$), streamline `Lessons` into a self-contained visual study guide with $\mathbb{Z}_2$ truth tables, add real-world **XTS-AES $GF(2^{128})$** and **Binary ECC (NIST B-163)** application labs, keep all planning and technical docs synchronized with the 11-endpoint FastAPI contract, and verify everything end-to-end with Chromium Playwright E2E tests.

---

## 2. Refinement & Enhancement Scope

### 2.1 Plan-to-Code API Contract Synchronization (12 Endpoints)
* Synchronize all endpoint specifications in `Plan/` and `docs/` with the authoritative Pydantic v2 schemas in `backend/api/schemas.py` and `backend/api/exploration_routes.py`:
  * **6 Core Routes:** `GET /api/fields`, `POST /api/calculate`, `POST /api/random-polynomials`, `POST /api/parse-polynomials`, `POST /api/export-calculation`, `GET /api/tutorial`.
  * **6 Exploration & Application Routes (`/api/explorations/*`):**
    * `POST /api/explorations/modulus` (irreducibility & Berlekamp factor witnesses)
    * `POST /api/explorations/xts-tweak` (IEEE 1619-2007 / Stallings Ch. 6 $GF(2^{128})$ tweak multiplier)
    * `POST /api/explorations/binary-ecc` (Stallings Ch. 10 / NIST FIPS 186-4 Teaching $GF(2^4)$ & NIST B-163 curve explorer + ECDH)
    * `POST /api/explorations/gcm-ghash` (NIST SP 800-38D / Stallings Ch. 12 $GF(2^{128})$ GCM GHASH authenticator)
    * `POST /api/explorations/compare-multiplication`
    * `GET /api/explorations/multiplication-benchmarks`

### 2.2 Calculator UX Simplification & On-Demand Popups (`#calculator`)
* **Inputs & Typography:** Auto-uppercase Hex inputs (`a-f` → `A-F`) preserving caret position, Unicode superscript Polynomial `<input>` formatting (`x⁶ + x⁴ + 1` normalized cleanly back to ASCII `x^k`), and non-numeric placeholders (`Enter A(x)`, `Enter B(x)`, `Enter modulus m(x)`).
* **Full Untruncated Results & Top-Center Alerts:** Show complete Hex, Binary, and Polynomial values directly on the Result card (wrapped/scrollable on large fields) while keeping timing, bit-width, and Hamming-weight metric badges untouched; clarify `Compare multiplication methods` with a concise helper note; redesign `#error-popup` as a sleek top-center floating alert card that never obscures operand inputs.
* **Streamlined Trace Modes & Playback Locking:**
  * Default to **`Step view`** across all 13 field sizes with built-in side-by-side **Previous → Current** comparison from Step 1 onward (single card on Step 0).
  * Rework **`All steps grid`** as a full-width inline single-column stack loading **4 steps initially** + **`Show more (showing 4 of N)`** pagination (+4 steps per click; no maximized modal).
  * Add a concise color highlight legend right above every **`Classic table`**.
  * Automatically pause animation and lock playback controls and step arrow keys whenever **`All steps grid`** or **`Classic table`** is active.
* **Interactive Breakdown & Full-Value Popups:**
  * Add 4 step-specific breakdown buttons (`How Q / T₁ / T₂ / T₃ is calculated`) on every Extended Euclid step card (disabled on Step 0 with `Available from Step 1 onward`) computing exact client-side `BigInt` derivations for that step only.
  * Streamline Shift-and-XOR cards (no redundant blue summary banner, explicit `A(x)` / `<< 1` / bit `bᵢ` wording, calculation steps placed **above** the bold `Shifted value` / `Running Sum`, plus `Show Shift & XOR illustration` popup) and Modulo Reduction cards (full untruncated hex, `Shifted modulus · m(x) << k` between `Before` and `After XOR`).
  * Replace silent click-to-copy on truncated large-field cells with a click-to-inspect **Full Value Inspector Popup** (`#inspector-popup`) displaying full Hex, Binary, and Polynomial (`<sup>`) representations with Copy buttons.

### 2.3 Self-Contained Visual `Lessons` Study Guide (`#lessons`)
* Remove the top animation/playback toolbar, step dots, diff legend, and Calculator handoff buttons; keep only the gliding top section bar (`#lesson-subtabs`) and linear **`Previous section`** / **`Next section`** footer controls across the 7-lesson curriculum.
* Embed self-contained visual study cards grounded in Stallings Chapters 4, 6, and 10: fix the `1.1` `b_1x` typo (`b<sub>1</sub>x`), keep the 8-bit polynomial sandbox, add 4-row $\mathbb{Z}_2$ Addition / XOR truth tables in `1.2` and `2.1`, and present complete worked classroom examples throughout.

### 2.4 Modulus Explorer Polish (`#modulus`) & `Applications` Tab (`#applications`)
* Apply Unicode superscript Polynomial input, auto-uppercase Hex input, non-numeric placeholder, and a 1-sentence plain-English GCD checkpoint explanation in `#modulus`.
* Introduces the dedicated **`Applications`** tab (`#applications`) hosting gliding sub-tabs for **XTS-AES $GF(2^{128})$** and **Binary ECC ($E_{2^m}(a,b)$: Teaching $GF(2^4)$ + NIST B-163)**.

---

## 3. Deliverables & Verification Criteria

* [x] **Core Milestone 6 Waves 1–3:** Full-width de-nested layout, read-only **Modulus $m(x)$** card on unary operations, XSS-safe `<sup>`/`<sub>` math typography, gliding `.sliding-pill` navigation indicators, WCAG AA visual diff grammar, `Tutorial tour` rename, and `Plan/` schema sync.
* [x] **Playback Polish, Upload Modal & Toasts:** Boundary disabled states, instant `First changed bit` jump, bottom-right confirmation toasts (`#feedback-popup`), drag-and-drop upload modal (`#upload-modal`) with sample downloads, cleaned hero badge, and zero em/en-dashes in `frontend/` and `data/tutorial_slides.json`.
* [x] **Comprehensive UX Simplification & Popups:** Auto-uppercase Hex & Unicode superscript Polynomial inputs, non-numeric placeholders, untruncated Results & Modulo Reduction (`m(x) << k`), top-center `#error-popup`, `Step view` default with built-in Previous → Current, inline 4-step paginated `All steps grid`, `Classic table` color legend, playback locking outside `Step view`, EEA `Q / T₁ / T₂ / T₃` & Shift-and-XOR `<< 1 / ⊕ m(x)` derivation popups, and Full-Value Inspector popup (`#inspector-popup`).
* [x] **Self-Contained `Lessons` & Real-World `Applications` Tab:** Streamlined section-only `#lessons` curriculum with truth tables in `1.2` and `2.1`, `#modulus` polish, and `#applications` with XTS-AES $GF(2^{128})$ (`POST /api/explorations/xts-tweak`) and Binary ECC NIST B-163 (`POST /api/explorations/binary-ecc`) + updated `Tutorial tour`, Markdown docs, and Chromium Playwright E2E suite.
* [x] **Wave 5 Flat De-Boxed UI, Gentler Speeds, Global `Share link` & Applications Form Alignment:** Site-wide de-boxed visual hierarchy (single outer `.panel` cards, inline colored metrics, dot-accented borderless `Step diff` legends, hairline/left-accent dividers across all 5 tabs & popups), gentler animation speeds (`450ms` / `900ms` / `1800ms`), global `Share link` serialization/restoration across all 5 tabs, single-line Applications subscript labels (`T₀`, `n_A`, `n_B`), uniform input/select heights, and dynamic Applications hero badge (`GF(2¹²⁸) · IEEE 1619` ↔ `GF(2¹⁶³) · NIST B-163`).
* [x] **Wave 6 GCM / GHASH ($GF(2^{128})$) Sub-Tab & Polynomial ECC Slide Alignment:** Pure-Python `gcm_ghash` engine & `POST /api/explorations/gcm-ghash` endpoint (NIST SP 800-38D / Stallings Ch. 12), third gliding Applications sub-tab (`GCM · GHASH (GF(2¹²⁸))`) with dynamic hero badge (`GF(2¹²⁸) · NIST SP 800-38D`), Full-Value Inspector popups, global `?app=ghash&h=...&blocks=...#applications` share links, Lesson `7.2` + tour updates, and Binary ECC display notation aligned to classroom Polynomial ECC slides (`Xp`, `Yp`, `s`, `Xr`, `Yr`).
* [x] **Wave 7 Clean ASCII Input Exponents, Dynamic Two-Notation Previews & Empty Initial State:** Uniform non-wavy `x^k` caret inputs (accepting pasted Unicode superscripts), dynamic two-non-selected-notations previews beneath `Operand A(x)`/`B(x)`/Result, and clean empty initial load state across all pages (`#calculator`, `#modulus`, `#applications`, `#compare`) with one-click Random/preset helpers and preserved Share link restoration.

### Remaining Course Deliverables (Open)
* [ ] Finalize updated Project Report PDF (`deliverables/Polynomial-Arithmetic-Report.pdf`), 20-minute presentation slides, and 5-minute max demo video (`deliverables/Finite-Field-Lab-Demo.mp4`) reflecting the unified layout and Milestone 6 features.

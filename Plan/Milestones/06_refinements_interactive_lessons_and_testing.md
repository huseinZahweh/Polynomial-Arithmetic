# Milestone 6: Refinements, Interactive Lessons & Extended Testing

**Assigned Owners:** Team (Collaborative Post-Integration Refinement & Testing Phase — UI/UX & E2E led by **Ali Zahreddine**)  
**Prerequisite:** Completion of Milestones 1–5 Unified Application Layout

---

## 1. Objective

Continuously refine the integrated **Finite Field Lab** user experience, eliminate horizontal table scrolling on large cryptographic fields ($m \in \{163, 233, 239, 283, 409, 571\}$), introduce a standalone animated **Lessons** curriculum (`#lessons`) alongside the contextual **Tutorial tour**, keep all planning documents synchronized with the live FastAPI schemas, and expand automated unit, API, and Chromium Playwright E2E test coverage prior to final course report, presentation slides, and demo video sign-off.

---

## 2. Refinement & Enhancement Scope

### 2.1 Plan-to-Code API Contract Synchronization
* Synchronize all draft endpoint specifications in `Plan/README.md` and `Plan/Milestones/02`–`05` with the authoritative Pydantic v2 schemas in `backend/api/schemas.py` and `docs/ARCHITECTURE.md`:
  * `POST /api/calculate`: canonical operand keys `a` and `b` (accepting `poly_a` and `poly_b` via `AliasChoices`), full and short `operation` names (`add`, `subtract`/`sub`, `modulo`/`mod`, `multiply`/`mul`, `inverse`/`inv`, `divide`/`div`), `input_base` and `output_base` in `{"hex", "bin", "binary", "algebraic"}`, `trace: bool`, and response keys `{ "operation", "field", "operands", "result", "trace", "initial_reduction", "verification", "metrics", "share_token" }`.
  * `POST /api/random-polynomials`: `{ "m", "density" (alias "sparsity"), "seed", "count", "output_base" }` returning `{ "field", "density", "seed", "a", "b", "m", "output_base", "polynomials" }`.
  * `POST /api/parse-polynomials`: JSON body `{ "content", "filename", "default_base" }` returning `{ "count", "pairs": [{ "a", "b", "base" }] }`.
  * `POST /api/export-calculation`: `{ "calculation", "format" ("md" | "json"), "download" }`.
  * `GET /api/fields` (`include_textbook: bool = true`) and `GET /api/tutorial`.
  * Bonus teaching exploration routes under `/api/explorations/*` (`POST /modulus`, `POST /aes-sbox`, `POST /compare-multiplication`, `GET /multiplication-benchmarks`).

### 2.2 Spotlight Walkthrough Rename (`Tutorial tour`)
* Rename the top-right walkthrough trigger button from `Tutorial` to **`Tutorial tour`** across the masthead and all view tours (`frontend/index.html`, `frontend/tour.js`).
* Add a dedicated spotlight walkthrough for the new standalone **Lessons** page (`#lessons`) so every top-level view (`Calculator`, `Lessons`, `Modulus explorer`, `AES S-box`, `Compare multiplication`) has its own interactive guided tour.

### 2.3 Zero-Horizontal-Scroll Interactive `Calculation steps` Visualizer
* Redesign `frontend/traces.js` and `frontend/lab.css` so large-field traces ($m = 163 \dots 571$) and 8-column Extended Euclid Table 4.7 traces require **zero horizontal scrolling**:
  * **Three Layout Modes:**
    1. **`Step view` (Default for $m > 8$ and narrow screens):** Renders an interactive **Step Inspector Square** showing the step badge, quotient $Q(x)$, live recurrence formula callout ($Q = A_3 \text{ div } B_3$, $T_i = A_i \oplus Q \cdot B_i$, $B \rightarrow A$, $T \rightarrow B$), and side-by-side / stacked **Triple $A(x)$** and **Triple $B(x)$** cards with animated state-transfer highlights, click-to-copy values, and green $B_2(x)$ ($B_3 = 1$) or amber/red $A_3(x) = \gcd(m, b)$ ($B_3 = 0$) termination badges.
    2. **`All steps grid`:** Displays all steps simultaneously as a responsive grid of stacked step cards with zero horizontal scrolling.
    3. **`Classic table` (Default on desktop for $m \le 8$):** Renders the compact textbook table with smart cell wrapping.
  * **`Expand full view` Modal:** Opens the active trace inside a wide (~95% viewport width) focus dialog so complete 8-column Table 4.7 and Shift-and-XOR tables can be inspected comfortably on widescreen displays.
  * **`Compact values` vs. `Full m-bit` Toggle:** Defaults to `Compact values` when $m > 8$ (stripping leading zero padding and offering click-to-copy on long dense strings) and `Full m-bit` when $m \le 8$.
  * **5-Button Playback Bar & Step Scrubber:** `First step` (`|<`), `Previous step` (`<`), `Play animation` / `Pause` with speed selector (`Slow`, `Normal`, `Fast`), `Next step` (`>`), `Last step` (`>|`), and an interactive range slider (`Step k of N`) for scrubbing across 163-bit to 571-bit traces.

### 2.4 Standalone Interactive & Animated `Lessons` Page (`#lessons`)
* Build a dedicated top-level **Lessons** view (`frontend/lesson-data.js`, `frontend/lessons.js`) routed via `#lessons` and `#lessons/<lesson-id>` (completely separate from the Calculator view):
  * **7-Lesson Curriculum with Sub-Lessons & Prerequisites:**
    1. *Foundations:* Bits, Polynomials, Modulo-2 Arithmetic, Irreducible $m(x)$, and Cryptographic Context (Stallings Ch. 4, 5, 6, 10) with a live 8-bit polynomial builder.
    2. *Addition ($+$):* Modulo-2 truth table, animated column-by-column XOR walkthrough of $\{57\} + \{83\} = \{\text{D4}\}$, and interactive XOR bit check.
    3. *Subtraction ($-$) & Additive Inverses:* Why $-1 \equiv +1 \pmod{2}$, self-inverse cancellation $A(x) \oplus A(x) = 0$, and $\{57\} - \{83\} = \{\text{D4}\}$.
    4. *Modulo Reduction ($\bmod\, m(x)$):* Degree overflow, identity $x^m \equiv m(x) - x^m \pmod{m(x)}$, and animated leading-term cancellation on $\{10\text{E}\} \bmod \{11\text{B}\} = \{15\}$ and $\{11\text{B}\} \bmod \{11\text{B}\} = \{00\}$.
    5. *Multiplication ($\times$):* Why lookup tables fail at $GF(2^{163})$, animated 8-bit shift-register multiply-by-$x$ ($\{02\} \times \{87\} = \{15\}$), and full Shift-and-XOR walkthrough of $\{57\} \times \{83\} = \{\text{C1}\}$.
    6. *Number Theory & Multiplicative Inverse ($x^{-1}$):* Animated Euclidean polynomial long division (`POLY_DIVMOD`), polynomial GCD & Bézout invariant, and animated Stallings Table 4.7 for $\{83\}^{-1} \bmod \{11\text{B}\} = \{80\}$ covering both $B_3 = 1$ and $B_3 = 0$ termination cases.
    7. *Division ($\div$):* Two-stage pipeline $A(x)/B(x) = A(x) \times B(x)^{-1} \bmod m(x)$ walking through $\{\text{C1}\} \div \{83\} = \{57\}$ and live verification.
  * **Interactive Playback & Calculator Handoff:** Every sub-lesson features the 5-button playback bar (`First step`, `Previous`, `Play animation`/`Pause` with speed control, `Next`, `Last step`), clickable progress dots, keyboard shortcuts (`ArrowLeft`, `ArrowRight`, `Home`, `End`, `Space`), interactive check questions, and **"Open in Calculator"** deep-link buttons.

---

## 3. Deliverables & Verification Criteria

### Wave 1 — UI/UX Refinements, Animated Lessons & Plan Sync (Completed)
* [x] Synchronize `Plan/README.md` and `Plan/Milestones/02`–`05` API contracts with the live FastAPI schemas and aliases in `backend/api/schemas.py`.
* [x] Rename the header walkthrough trigger to **`Tutorial tour`** and add a dedicated spotlight tour for the `Lessons` view.
* [x] Upgrade `Calculation steps` (`frontend/traces.js`) with zero-horizontal-scroll `Step view`, `All steps grid`, `Classic table`, `Expand full view` modal, `Compact values` / `Full m-bit` toggle, 5-button playback controls, speed selector, and interactive step scrubber.
* [x] Build the standalone 7-lesson animated **Lessons** page (`frontend/lesson-data.js`, `frontend/lessons.js`) covering all 6 $GF(2^m)$ operations and number-theory prerequisites with interactive mini-activities and one-click Calculator handoffs.
* [x] Document all Milestone 6 modules and architecture in `docs/milestones/MILESTONE6_EXPLAINED.md`, `docs/ARCHITECTURE.md`, `docs/CODE_EXPLAINED.md`, and `README.md`, and verify with expanded Chromium Playwright E2E tests in `tests/e2e/test_workbench_e2e.py`.

### Wave 2 — Previous-to-Current Visual Diff Tracking (Completed)
* [x] **Shared Color-Blind-Safe Visual Diff Grammar (`frontend/lab.css`):** Added compact `.diff-legend` bar and persistent WCAG AA surface/border/micro-badge states (`.diff-carried` Indigo, `.diff-updated` Emerald, `.diff-reduced` Amber, `.diff-unchanged` Neutral), inline `.diff-prev-value` (`was:` / `prev → now`) sub-rows, and responsive zero-scroll `.diff-compare-grid` layout.
* [x] **Calculator Trace Visual Diffs & `Compare prev → curr` (`frontend/traces.js`):** Added `Compare prev → curr` side-by-side previous/current step toggle in `Step view`, Table 4.7 Triple A (`← prev B1..B3`) & Triple B (`New T1..T3`) carried/updated badges with `was:` values, Shift-and-XOR `prev → now` shift/reduction and accumulator deltas, Modulo Reduction & Bitwise XOR cancellation badges, and previous/current row tinting in `All steps grid` and `Classic table`.
* [x] **Standalone Lessons Visual Diffs & Slide Comparison (`frontend/lessons.js`, `frontend/lesson-data.js`):** Added `#lesson-compare` (`Compare prev → curr`) side-by-side slide view, `"From Step k-1 → Step k"` transition banners, and automatic value-level diff highlighting across XOR bit grids, modulo reduction, `xtime` shift registers, Shift-and-XOR rows, `POLY_DIVMOD`, Table 4.7 triples, and two-stage division pipelines.
* [x] **Extended Wave 2 Playwright E2E Tests (`tests/e2e/test_workbench_e2e.py`):** Verified Table 4.7 and Lesson visual diffs, `was:` deltas, `Compare prev → curr` side-by-side mode, and zero horizontal overflow on desktop and mobile (`390x840`).

### Wave 3 — Full-Width Layout, Read-Only Modulus Card, Math Typography, Pop-Up Errors & Transitions (Completed)
* [x] **Read-Only Modulus $m(x)$ Card on Unary Operations (`frontend/index.html`, `frontend/lab.js`):** Selecting `Reduce` (`modulo`) or `Inverse` (`inverse`) preserves typed `B(x)` in state while replacing the dimmed box with a read-only **Modulus $m(x)$** card (`Locked to GF(2^m)`, context subtitle, and active-notation value synced to field and notation).
* [x] **True HTML `<sup>` & `<sub>` Math Typography (`frontend/notation.js`):** Added XSS-safe `mathFragment`, `appendMathText`, `setMathText`, and `mathElement` builders rendering exponents (`GF(2^163)`, `x^4`, `x^-1`, `x^(2^i)`) and indexed variables (`A1`–`A3`, `B1`–`B3`, `T1`–`T3`, `b0`–`b7`) with real `<sup>`/`<sub>` DOM elements without altering raw inputs or exports.
* [x] **Pop-Up Error Modal Overlay (`frontend/index.html`, `frontend/notation.js`, `frontend/lab.js`, `frontend/explorations.js`):** Replaced inline error text with a prominent modal `<dialog id="error-popup">` supporting `Esc`, backdrop click, `OK / Dismiss`, and a direct **"View Step 0 / GCD trace"** shortcut on zero-inverse HTTP 400 errors.
* [x] **Full-Width De-Nested Layout & 2-Row Toolbar (`frontend/index.html`, `frontend/lab.css`, `frontend/traces.js`):** Removed the left sidebar dead column on `#calculator`, placed settings & textbook presets in a top `.top-controls-bar`, softened nested borders, removed redundant `Show all` / `Show step cards` buttons, and organized `Calculation steps` into a clean 2-row toolbar with zero pill clipping.
* [x] **Smooth Navigation Cross-Fades & Gliding Active Pill (`attachSlidingIndicator`):** Added smooth CSS color transitions and dynamic sliding highlight pills across `.lab-nav`, `.segments.notation`, `.operations`, `.trace-modes`, `#lesson-subtabs`, and `#lesson-step-dots`.
* [x] **Informative `.step-knowledge-title` Headers, Auto-Maximize & Sequential Step Cascade (`frontend/traces.js`, `frontend/lessons.js`):** Rendered educational step titles above every step in Traces & Lessons, auto-maximized `#trace-panel` when selecting `All steps grid` (with `Exit maximized view` + `Esc`), and added sequential intermediate-step cascading (`2 → 3 → 4 → 5`) on non-adjacent bit/dot/scrubber jumps.

### Remaining Course Deliverables (Open)
* [ ] Finalize updated Project Report PDF (`deliverables/Polynomial-Arithmetic-Report.pdf`), 20-minute presentation slides, and 5-minute max demo video (`deliverables/Finite-Field-Lab-Demo.mp4`) reflecting the unified layout and Milestone 6 features.

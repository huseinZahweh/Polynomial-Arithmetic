# Milestone 6 Explained: Interactive Trace Redesign, Standalone Animated Lessons & Refinements

> **Milestone Scope:** UI/UX Refinements, Zero-Horizontal-Scroll Trace Visualizer, Standalone Interactive & Animated `Lessons` Curriculum (`#lessons`), `Tutorial tour` Rename, `Plan/` API Schema Sync, and Extended Playwright E2E Verification  
> **Primary Contributors:** Team (Lead UI Refinements, Interactive Lessons & E2E Testing: **Ali Zahreddine**)  
> **Textbook Alignment:** William Stallings, *Cryptography and Network Security: Principles and Practice* (8th Ed.), Chapters 4, 5, 6 (XTS-AES), and 10 (Binary ECC); NIST FIPS 197 & FIPS 186-4

---

## 1. Pedagogical & Architectural Goals

Following the Milestone 5 end-to-end unification of the $GF(2^m)$ mathematical engine, FastAPI service layer, and zero-build web workbench, **Milestone 6** addresses four high-impact classroom and usability goals prior to final report, presentation slides, and demo video delivery:

1. **Zero-Horizontal-Scroll Trace Visualization (`frontend/traces.js`, `frontend/lab.css`):**
   - In cryptographic binary fields ($m \in \{163, 233, 239, 283, 409, 571\}$), a single element occupies up to $143$ hexadecimal digits, $571$ binary bits, or dozens of polynomial terms.
   - Standard 8-column Extended Euclidean Algorithm (Stallings Table 4.7: $\text{Step}, Q, A_1, A_2, A_3, B_1, B_2, B_3$) and Shift-and-XOR tables previously required extensive horizontal scrolling on large fields.
   - Milestone 6 introduces a **Three-Mode Layout Switcher** (`Step view`, `All steps grid`, `Classic table`), an interactive **Extended Euclid Step Inspector Square** pairing **Triple A** $(A_1, A_2, A_3)$ and **Triple B** $(B_1, B_2, B_3)$, a **`Compact values` vs. `Full m-bit`** toggle pill, a **5-button playback bar + step scrubber**, and an **`Expand full view`** modal dialog (`#trace-fullscreen`).

2. **Standalone Interactive & Animated `Lessons` Curriculum (`#lessons`):**
   - While the header spotlight tour (`Tutorial tour`) guides users around the active page's UI controls, students also benefit from a dedicated, self-paced curriculum that visually teaches **how and why** each $GF(2^m)$ operation and number-theory tool works step by step.
   - Milestone 6 adds a standalone top-level **`Lessons`** tab (`#lessons`) implemented in `frontend/lesson-data.js` and `frontend/lessons.js` covering 7 complete lessons (21 sub-lessons), with 5-button animation controls, interactive sandboxes, self-check quizzes, and one-click **"Open in Calculator"** handoffs.

3. **Clear Terminology (`Tutorial tour` vs. `Lessons`):**
   - Renames the top-right spotlight walkthrough trigger from `Tutorial` to **`Tutorial tour`** across all five views (`#calculator`, `#lessons`, `#modulus`, `#aes`, `#compare`) and adds a 5-step guided tour for the new `Lessons` page in `frontend/tour.js`.

4. **Specification & Plan Synchronization (`Plan/`):**
   - Synchronizes early planning drafts in `Plan/README.md` and `Plan/Milestones/02`, `04`, `05` with the live FastAPI contract in `backend/api/schemas.py` (`m`, `input_base`, `output_base`, `density`, `filename`, `default_base`, `format`, `download`, plus backward-compatible aliases) and documents Milestone 6 in `Plan/Milestones/06_refinements_interactive_lessons_and_testing.md`.

---

## 2. Zero-Horizontal-Scroll Trace Redesign (`frontend/traces.js`)

### 2.1 Three-Mode Layout Switcher & Smart Defaults

Every trace panel (`#trace-panel`, `#aes-trace`, `#aes-affine`, `#compare-shift`, `#compare-division-trace`) provides a segmented mode switcher:

| Layout Mode | Default Trigger | Visual Representation |
|---|---|---|
| **`Step view`** | Default when $m > 8$ or viewport $\le 600\text{ px}$ | Displays one rich, zero-horizontal-scroll card or **Extended Euclid Step Inspector Square** (`role="region"`, `aria-label="Current trace step"`) for the active step. |
| **`All steps grid`** | User-selectable on any viewport | Renders all steps simultaneously as a vertical stack of cards (`.trace-grid-cards`) with zero horizontal scrolling. |
| **`Classic table`** | Default on desktop when $m \le 8$ | Renders traditional multi-column tables (`Table 1`, `Table 2`, `Table 4.7`, `Bitwise XOR`, `Modulo reduction`) with wrapped cells (`overflow-wrap: anywhere; word-break: break-word`). |

In addition, clicking **`Expand full view`** opens `<dialog id="trace-fullscreen">` (~95% viewport width / 90% viewport height) displaying the full classic tables in a dedicated focus overlay.

### 2.2 Extended Euclid Step Inspector Square (Stallings Table 4.7)

Instead of squeezing 8 wide columns into a single horizontal table row, `Step view` and `All steps grid` render each Extended Euclidean Algorithm iteration as an **Extended Euclid Step Inspector Square** (`.euclid-inspector-square`):

```text
+-----------------------------------------------------------------------------------+
| Extended Euclid · step k   [Iteration k]                 [ Q(x) = A3(x) div B3(x) ]|
| Q = A3 div B3 · T1 = A1 ⊕ Q·B1 · T2 = A2 ⊕ Q·B2 · T3 = A3 mod B3                  |
+-----------------------------------------+-----------------------------------------+
| Triple A(x)            A ← prev B       | Triple B(x)            B ← A ⊕ Q·B      |
|   A1(x): <wrapped / copyable value>     |   B1(x): <wrapped / copyable value>     |
|   A2(x): <wrapped / copyable value>     |   B2(x): <wrapped / copyable value> [*] |
|   A3(x): <wrapped / copyable value>     |   B3(x): <wrapped / copyable value>     |
+-----------------------------------------+-----------------------------------------+
```

- **State-Transfer Animation:** On each step transition ($k - 1 \to k$), Triple A highlights with `.is-carried` (`slideCarry` keyframe) to show that $(A_1, A_2, A_3)$ was carried directly from step $k-1$'s $(B_1, B_2, B_3)$, while Triple B highlights with `.is-updated` (`pulseUpdate` keyframe) to show the auxiliary recurrence update $T_i(x) = A_i(x) \oplus Q(x) \cdot B_i(x)$.
- **Termination Highlighting:**
  - When $B_3(x) = 1$, $B_2(x)$ is highlighted in emerald green (`.picked`) as $b(x)^{-1} \bmod m(x)$.
  - When $B_3(x) = 0$, $A_3(x) = \gcd(m(x), b(x))$ is highlighted in amber/red (`.picked.is-gcd`).
- **Compact vs. Full $m$-Bit Values:** When `Compact values` is active (default for $m > 8$), leading zero padding is trimmed in Hex/Binary modes and middle terms of long algebraic polynomials are summarized (`x^162 + x^159 + … + 1`). Toggling **`Full m-bit`** displays the full unshortened string wrapped across lines inside the card with zero horizontal overflow. Every value is click-to-copy.

### 2.3 5-Button Playback Bar & Interactive Scrubber

The trace toolbar provides full media-style playback controls:
- **`First step`** (jump to step 1), **`Previous step`**, **`Play animation` / `Pause`** with speed selector (**`Slow`** $900\text{ ms}$, **`Normal`** $450\text{ ms}$, **`Fast`** $200\text{ ms}$), **`Next step`**, and **`Last step`**.
- An interactive `<input type="range" class="trace-scrubber" aria-label="Trace step scrubber">` slider synchronized with the live `Step X of Y` / `All steps` status indicator.

---

## 3. Standalone Animated `Lessons` Curriculum (`#lessons`)

### 3.1 Module Architecture (`frontend/lesson-data.js` & `frontend/lessons.js`)

The standalone `#lessons` view is structured into two clean ES modules:
1. **`frontend/lesson-data.js`**: Pure data specification exporting the `LESSONS` array of 7 lessons and 21 sub-lessons, including step formulas, visual payloads, interactive mini-activities, self-check quizzes, and Calculator preset handoffs.
2. **`frontend/lessons.js`**: Interactive controller exporting `setupLessons({ openInCalculator })`, managing the 7-card Lesson Catalog Hub (`#lesson-catalog`), sub-lesson tabs (`#lesson-subtabs`), 5-button animation playback (`#lesson-first`, `#lesson-prev`, `#lesson-play`, `#lesson-speed`, `#lesson-next`, `#lesson-last`), clickable step timeline dots (`#lesson-step-dots`), keyboard shortcuts (`ArrowLeft`, `ArrowRight`, `Home`, `End`, `Space`), and deep-link routing (`#lessons/<lesson-id>`).

### 3.2 Seven-Lesson Syllabus & Cryptographic Alignment

| Lesson | Symbol | Sub-Lessons & Core Mathematical Content | Calculator / Exploration Handoff |
|---|---|---|---|
| **1. Foundations of $GF(2^m)$ & Polynomial Representation** | `GF(2^m)` | **1.1** Bits as coefficients in $GF(2)[x]$ (`bit-sandbox`); **1.2** Why integers $\bmod 2^m$ fail to form a field vs. irreducible $m(x)$; **1.3** Standard moduli ($m = 2 \dots 8$, AES $0\text{x}11\text{B}$, NIST curves $163 \dots 571$). | `{57} × {83}` in $GF(2^8)$ + `#modulus` |
| **2. Addition & Subtraction ($A(x) \oplus B(x)$)** | `＋ / −` | **2.1** Coefficient arithmetic in $GF(2)$ ($1 \oplus 1 = 0$, $A + B = A - B$, $-A = A$); **2.2** Term alignment by power of $x$; **2.3** Animated 8-bit walkthrough `{57} ⊕ {83} = {D4}` + 4-bit XOR activity + quiz. | `{57} + {83} = {D4}` in $GF(2^8)$ |
| **3. Modular Reduction ($A(x) \bmod m(x)$)** | `mod` | **3.1** Substitution rule $x^m \equiv m(x) - x^m \pmod{m(x)}$ ($x^8 \equiv x^4 + x^3 + x + 1$); **3.2** Iterative shift-and-XOR degree cancellation; **3.3** Walkthrough reducing degree-14 `{2B79}` modulo `{11B}` to `{C1}` + quiz. | `{2B79} mod {11B} = {C1}` in $GF(2^8)$ |
| **4. Multiplication ($A(x) \times B(x) \bmod m(x)$)** | `×` | **4.1** `xtime` left shift & conditional XOR with $0\text{x}1\text{B}$ (`{02} × {87} = {15}`); **4.2** Distributive law & Shift-and-XOR algorithm; **4.3** Full 8-step walkthrough of Stallings Ch. 4 `{57} × {83} = {C1}` (Tables 1 & 2) + quiz. | `{57} × {83} = {C1}` in $GF(2^8)$ + `#compare` |
| **5. Multiplicative Inverse & Extended Euclid ($A(x)^{-1}$)** | `x⁻¹` | **5.1** Polynomial long division (`POLY_DIVMOD`) $A_3 = Q \cdot B_3 \oplus R$; **5.2** Bézout identity $m \cdot B_1 + b \cdot B_2 = B_3$ & Table 4.7 invariants; **5.3** Animated walkthroughs of `{83}⁻¹ = {80}` and `{95}⁻¹ = {8A}`; **5.4** Failure mode $B_3 = 0$. | `{95}⁻¹ = {8A}` in $GF(2^8)$ + `#aes` |
| **6. Polynomial Division ($A(x) \div B(x)$)** | `÷` | **6.1** Division via inverse $A / B = A \otimes B^{-1} \bmod m(x)$; **6.2** Two-stage pipeline walkthrough `{C1} ÷ {83} = {57}` (Stage 1 Table 4.7 + Stage 2 Shift-and-XOR) and multiplicative identity verification $(Q \otimes B) \bmod m(x) = A$. | `{C1} ÷ {83} = {57}` in $GF(2^8)$ |
| **7. Cryptographic Applications (AES, XTS-AES & Binary ECC)** | `AES / ECC` | **7.1** AES `SubBytes` S-box & `MixColumns` (Stallings Ch. 5); **7.2** XTS-AES tweakable block cipher $\alpha = x$ multiplication in $GF(2^{128})$ (Stallings Ch. 6); **7.3** Binary Elliptic Curve Cryptography over $GF(2^{163}) \dots GF(2^{571})$ (Stallings Ch. 10). | $GF(2^{163})$ multiplication + `#aes` |

---

## 4. Wave 2: Previous-to-Current Visual Diff & Color-Coded Change Tracking

Wave 2 adds a shared, color-blind-safe visual diff system across both `Calculation steps` (`frontend/traces.js`) and `Lessons` (`frontend/lessons.js`, `frontend/lesson-data.js`) so every step transition makes exact state changes unmistakable without relying on color alone or transient animations:

| Visual Diff State | CSS Class | Color Palette | Text Micro-Badges | Meaning |
| :--- | :--- | :--- | :--- | :--- |
| **Carried / Shifted** | `.diff-carried` | Indigo / Blue | `← prev B1..B3`, `Shifted left`, `Shifted m(x)`, `Completed` | Values copied or shifted forward from Step $k-1$. |
| **New / Updated** | `.diff-updated` | Emerald / Green | `New T1..T3`, `XOR'd (bit = 1)`, `Set to 1`, `Reduced`, `Inverse Found` | Newly computed values, updated accumulators, or active stage results. |
| **Reduced / Cancelled** | `.diff-reduced` | Amber / Orange | `Shifted + Reduced ⊕ m(x)`, `1 ⊕ 1 → 0`, `Cancel x^d`, `GCD / No Inverse` | Overflow reductions modulo $m(x)$, characteristic-2 bit cancellations, or leading-term eliminations. |
| **Unchanged** | `.diff-unchanged` | Neutral Muted | `Unchanged`, `Unchanged (bit = 0)`, `Init`, `Pending` | Values that stayed identical from Step $k-1$ to Step $k$. |

### Key Wave 2 Capabilities
1. **Shared Legend Bar (`.diff-legend`) & Transition Banners (`.diff-banner`):** Rendered unobtrusively above active stepping stages in both `#calculator` and `#lessons`, paired with 1-line transition summaries (e.g., `Step 1 → Step 2: B shifted into A; Q = 0D produced new B1, B2, B3` and `From Step 1 → Step 2: ...`).
2. **Inline `was:` & `prev → now` Deltas (`.diff-prev-value`):** Changed Extended Euclid cells display `was: <prev>` underneath the current value; Shift-and-XOR cards display `prev: <old> → now: <new>` for both shifted operand $A$ and the running XOR accumulator.
3. **Side-by-Side `Compare prev → curr` Toggle (`.diff-compare-grid`):** Available in both `Calculation steps` (`Step view`) and `#lessons` (`#lesson-compare`), placing a read-only **Previous Step ($k-1$)** snapshot card directly beside (or stacked above on viewports $\le 840\text{ px}$) the **Current Step ($k$)** card with a connecting arrow (`→`) and zero horizontal overflow.

---

## 5. Wave 3: Full-Width Layout, Read-Only Modulus Card, Real `<sup>`/`<sub>` Typography, Pop-Up Errors, Smooth Transitions & Sequential Cascade

Wave 3 delivers eight holistic visual and interaction refinements across `frontend/` without touching backend endpoints or math contracts:

1. **Read-Only Modulus $m(x)$ Card on Unary Ops (`frontend/lab.js`, `frontend/index.html`):** Choosing **Reduce (`modulo`)** or **Inverse (`inverse`)** preserves the user's typed `Operand B(x)` value in memory while transforming the second card into a locked **Modulus $m(x)$** display showing `Locked to GF(2^m)`, operation context (`Reducing A(x) mod m(x)` or `Inverting A(x)⁻¹ mod m(x)`), and the active field modulus synced with the selected notation (`Hex`, `Binary`, or `Polynomial`).
2. **True HTML `<sup>` and `<sub>` Typography (`frontend/notation.js`):** Safe DOM tokenizers (`mathFragment`, `appendMathText`, `setMathText`, `mathElement`) convert exponents (`GF(2^163)`, `x^4`, `x^-1`, `x^(2^i)`) and indexed variables (`A1`–`A3`, `B1`–`B3`, `T1`–`T3`, `b0`–`b7`) into true `<sup>`/`<sub>` nodes across UI labels, step titles, Table 4.7 headers/cells, bit-builders, errors, and lessons—while keeping raw `<input>` fields, clipboard copies, share URLs, and `.md`/`.json` downloads plain ASCII.
3. **Elevated Pop-Up Error Dialog (`#error-popup`):** Routes all validation, batch-upload, exploration, and zero-inverse errors into a accessible `<dialog id="error-popup">` supporting `Esc`, backdrop click, `OK / Dismiss`, and an optional **"View Step 0 / GCD trace"** shortcut when an Extended Euclid failure trace is attached.
4. **Full-Width De-Nested Workspace & Uncluttered 2-Row Toolbar:** Eliminates the dead left sidebar on `#calculator` by arranging field settings and textbook presets in a top `.top-controls-bar`, giving `Calculator`, `Result`, and `Calculation steps` full container width, flattening nested borders, removing redundant `Show all` / `Show step cards` buttons, and laying out trace controls in two clean non-clipping rows.
5. **Smooth Color Cross-Fades & Gliding Active Pill (`attachSlidingIndicator`):** Pairs CSS color transitions (`240ms ease`) with a dynamic `.sliding-pill` highlight gliding smoothly across `.lab-nav`, `.segments.notation`, `.operations`, `.trace-modes`, `#lesson-subtabs`, and `#lesson-step-dots`.
6. **Informative Educational Step Titles (`.step-knowledge-title`):** Renders a descriptive mathematical summary heading on every step card across both `Calculation steps` (with `Stage 1` / `Stage 2` prefixes on Division) and `Lessons`.
7. **Auto-Maximize on `All steps grid`:** Selecting **`All steps grid`** expands `#trace-panel` (`.is-maximized`, ~95% viewport width/height) into a spacious multi-column grid, complete with `Exit maximized view` and `Esc` dismissal.
8. **Sequential Step Cascade (`2 → 3 → 4 → 5`):** Jumping non-adjacently across multiplier bits, trace scrubber positions, or lesson timeline dots animates sequentially through intermediate steps (capped at 12 hops, cancelled on rapid clicks, and disabled cleanly under `prefers-reduced-motion`).

---

## 6. Verification & Playwright E2E Coverage

Milestone 6 expands `tests/e2e/test_workbench_e2e.py` with five dedicated Milestone 6 end-to-end browser tests alongside updated core workflow assertions (bringing the total suite to **363 automated tests**: `269` engine + `79` API + `15` Playwright E2E):

1. `test_milestone6_zero_scroll_trace_modes_and_playback`:
   - Verifies `#tutorial-open` label (**`Tutorial tour`**), $GF(2^{163})$ Inverse Step view default, Step Inspector Square zero overflow, 5-button playback, `Full m-bit` / `Compact values` toggle, `All steps grid`, `Classic table`, and `Expand full view` modal across desktop (`1280x900`) and mobile (`390x840`).
2. `test_milestone6_standalone_lessons_page_and_handoff`:
   - Verifies `#lessons` 7-lesson catalog, 5-step `Lessons` Spotlight tour, interactive 8-bit sandbox, Lesson 2 playback + quiz, and Lesson 6 Calculator handoff (`{83}^-1 = {80}`).
3. `test_milestone6_wave2_trace_visual_diffs_and_compare_mode`:
   - Verifies `.diff-legend`, `.diff-banner`, `.diff-carried` (`← prev B`), `.diff-updated` (`New T`), inline `was:` values, and `Compare prev → curr` side-by-side mode on $GF(2^{163})$ traces.
4. `test_milestone6_wave2_lessons_visual_diffs_and_compare_mode`:
   - Verifies `"From Step k-1 → Step k"` diff summaries, persistent badges, `was:` deltas, and `Compare prev → curr` side-by-side slides in `#lessons`.
5. `test_milestone6_wave3_layout_modulus_card_math_popup_maximize_cascade`:
   - Verifies gliding `.sliding-pill` indicators, read-only **Modulus $m(x)$** card on `modulo`/`inverse` + preserved `B(x)` restore, real `<sup>`/`<sub>` DOM elements, `#error-popup` (`Esc` & `OK`), non-empty `.step-knowledge-title` headings, auto-maximized `All steps grid` + `Exit maximized view`, sequential step cascade (`0 → 1 → 2 → 3`), zero console/page errors, and zero horizontal overflow on desktop and mobile (`390x840`).

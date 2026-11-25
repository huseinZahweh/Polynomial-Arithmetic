# Milestones 4 & 5 — Educational Web Workbench, Explorations & End-to-End Integration

**Project:** EECE 455 — Project-3: Polynomial Arithmetic in $GF(2^m)$  
**Assigned Owner:** Ali Zahreddine (Milestone 4 GUI & Bonus Explorations; Milestone 5 End-to-End Integration with the full team)  
**Unified Code Locations:** [frontend/](../../frontend/index.html), [backend/engine/explorations.py](../../backend/engine/explorations.py), [backend/api/exploration_routes.py](../../backend/api/exploration_routes.py), [backend/api/main.py](../../backend/api/main.py), [run.py](../../run.py), and [tests/e2e/test_workbench_e2e.py](../../tests/e2e/test_workbench_e2e.py)  
**Textbook References:** William Stallings, *Cryptography and Network Security*, **Chapter 4** (Finite Fields), **Chapter 5** (AES $GF(2^8)$ arithmetic), **Chapter 6** (XTS-AES over $GF(2^{128})$), **Chapter 10** (Binary ECC over $GF(2^{163}) \dots GF(2^{571})$), and **Chapter 12** (GCM / GHASH over $GF(2^{128})$).

---

## 1. Educational Web Workbench (`frontend/`)

The frontend is a zero-build, accessible ES-module web application hosted directly by FastAPI at `/workbench/`. All client-side parsing, base conversion, and live algebraic preview use native JavaScript `BigInt` (`frontend/notation.js`) so elements up to $571$ bits stay lossless without external libraries.

### 1.1 Core Calculator Features (`frontend/lab.js`, `frontend/index.html`)

* **Field & Modulus Controls:** Dropdown populated dynamically from `GET /api/fields`, defaulting to the Project-3 primary field $GF(2^{163})$ and supporting all 13 fields ($2 \le m \le 8$ and $m \in \{163, 233, 239, 283, 409, 571\}$). Displays the active irreducible polynomial $m(x)$ in Algebraic, Hexadecimal, and Binary forms.
* **Live Lossless Notation Toggle:** Switches seamlessly between **Hex**, **Binary**, and **Polynomial** (`algebraic`), automatically converting current inputs and results via `BigInt`.
* **Six Operations & Unary Awareness:** Supports Add (`+`), Subtract (`-`), Modulo Reduction (`mod`), Multiply (`×`), Multiplicative Inverse (`x⁻¹`), and Division (`÷`). Automatically dims and disables Operand $B(x)$ for unary operations (`modulo` and `inverse`).
* **Classroom Presets, Random Generator & Batch Upload:**
  * One-click textbook presets loaded from `GET /api/tutorial`: **Chapter 4** ($\{57\} \times \{83\} = \{\text{C1}\}$) and **Chapter 5** ($\{95\}^{-1} = \{8\text{A}\}$).
  * One-click **Sparse** or **Dense** random operands via `POST /api/random-polynomials`.
  * Local `.txt`/`.json` batch file upload via `POST /api/parse-polynomials` (with a pair picker dropdown and [data/demo-operands.json](../../data/demo-operands.json) ready for classroom demos).
* **Result Card, Previews, Export & Share Links:**
  * Displays the primary notation alongside the other two notations, live verification badges (**Mathematically verified** for inverse and division), and performance/complexity badges (`elapsed_ms`, bit length, Hamming weight).
  * For large fields ($m \ge 163$), shows compact previews with a **Show full value** toggle while **Copy result** always copies the complete padded value.
  * **Export** downloads formatted Markdown (`.md`) or JSON (`.json`) summaries via `POST /api/export-calculation`.
  * **Copy calculation link** encodes `(m, operation, base, poly_a, poly_b)` into URL query parameters using **Hexadecimal URL Compression** (operands always serialized in hex even when `base=binary`) and restores the exact scenario on reload.

### 1.2 Four Custom Trace Visualizers (`frontend/traces.js`)

1. **Bitwise XOR Visualizer (Add / Subtract):** Column-aligned bits of $A(x)$, $B(x)$, and $A(x) \oplus B(x)$ indexed from $x^{m-1}$ down to $x^0$.
2. **Modulo Reduction Visualizer (`MOD_REDUCE`):** Iterative leading-term shifts $x^{d-m} \cdot m(x)$ and XOR cancellations, also embedded inside collapsible initial-reduction panels whenever unreduced inputs ($\deg \ge m$) are supplied.
3. **Shift-and-XOR Visualizer (Multiply — Tables 1 & 2):** Renders Table 1 ($x^i A(x) \bmod m(x)$ with overflow reduction flags) and Table 2 (selected partial products and cumulative XOR), enhanced with an interactive **Multiplier bits** strip supporting click and keyboard navigation (`ArrowLeft`, `ArrowRight`, `Home`, `End`) that highlights linked rows in both tables and shows the live running XOR equation.
4. **Extended Euclid Table 4.7 Visualizer (Inverse & Division):** Renders the 8-column Stallings Table 4.7 (`Step`, `Q(x)`, `A1(x)`..`B3(x)`) with an inline **Hexadecimal / Binary / Algebraic** cell toggle. Highlights $B_2(x)$ when $B_3(x) = 1$, or highlights $A_3(x) = \gcd(m(x), b(x))$ with an educational alert when $B_3(x) = 0$ (even on HTTP `400` zero-inverse errors). Division renders Stage 1 (Table 4.7) and Stage 2 (Shift-and-XOR) together.

### 1.3 All Three Optional Stretch Goals Completed

* **Interactive Bit-Builder ($m \le 8$):** Clickable checkboxes for coefficients $x^{m-1} \dots 1$ updating Hex, Binary, and Algebraic representations simultaneously.
* **Algebraic Text Input (`ALGEBRAIC_TO_INT`):** Full support for typing polynomials like `x^7 + x + 1` in both the frontend (`notation.js`) and backend (`polyrepr.py`).
* **Animated Stepper & Responsive Step Cards:** `Previous step`, `Next step`, `Play animation` (450 ms interval), `Show all`, and automatic narrow-screen labelled step cards (`Show step cards` / `Show tables`).

### 1.4 Guided Spotlight Tours & Field Concepts Modal (`frontend/tour.js`)

Clicking **Tutorial tour** launches a context-aware spotlight walkthrough tailored to whichever tab is open (Calculator, Lessons, Modulus explorer, Applications, or Compare multiplication). Each step highlights the target control, falls back gracefully to the action button if a result panel is not yet visible, and updates live when calculations complete. From the Calculator tour, **Field concepts** opens the 4-slide `<dialog>` modal served by `GET /api/tutorial`.

---

## 2. Interactive Teaching Explorations & Real-World Applications

Built in [backend/engine/explorations.py](../../backend/engine/explorations.py), exposed by [backend/api/exploration_routes.py](../../backend/api/exploration_routes.py), and rendered by [frontend/explorations.js](../../frontend/explorations.js):

1. **Modulus Explorer (`#modulus` / `POST /api/explorations/modulus`):**
   * Checks irreducibility of any binary polynomial of degree $2 \le d \le 571$ by computing Frobenius GCD checkpoints $\gcd(f(x), x^{2^i} + x)$ for $1 \le i \le \lfloor d / 2 \rfloor$.
   * When $f(x)$ is reducible, extracts and verifies two nonzero factors $a(x), b(x)$ whose product equals $f(x)$ (remainder $0$). When all irreducible factors have equal degree so the first nontrivial GCD equals $f(x)$ itself, splits $f(x)$ via Berlekamp's $GF(2)$ linear kernel (**bonus mathematical extension beyond Stallings Chapter 4**).
2. **Applications (`#applications` — upgraded in Milestone 6 from the initial byte-level walkthrough to full multi-standard $GF(2^m)$ demos):**
   * **XTS-AES $GF(2^{128})$ Tweak Multiplier (`POST /api/explorations/xts-tweak`):** Demonstrates IEEE 1619-2007 / Stallings Chapter 6 sector tweak shifts modulo $x^{128} + x^7 + x^2 + x + 1$ (`XOR 0x87` on $b_{127} = 1$).
   * **Polynomial / Binary ECC ($E_{2^m}(a,b)$) Explorer (`POST /api/explorations/binary-ecc`):** Demonstrates Stallings Chapter 10 & NIST FIPS 186-4 / SEC 2 point doubling ($R = 2P$), point addition ($R = P + Q$) in classroom slide notation (`Xp`, `Yp`, `s`, `Xr`, `Yr`), curve membership verification, and ECDH key exchange on both Teaching Curve $GF(2^4)$ and official **NIST B-163** ($GF(2^{163})$).
   * **GCM · GHASH ($GF(2^{128})$) Authenticator (`POST /api/explorations/gcm-ghash`):** Demonstrates NIST SP 800-38D / Stallings Chapter 12 authenticated encryption hashing $Y_i = (Y_{i-1} \oplus X_i) \cdot H \pmod{x^{128} + x^7 + x^2 + x + 1}$ across $1$–$8$ 128-bit blocks using canonical XOR and Shift-and-XOR multiplication.
3. **Compare Multiplication (`#compare` / `POST /api/explorations/compare-multiplication` & `GET /api/explorations/multiplication-benchmarks`):**
   * Runs interleaved Shift-and-XOR alongside deferred carry-free multiplication (`POLY_MUL_NO_MOD`) + Euclidean long division (`POLY_DIVMOD`) on identical operands, displaying both traces side-by-side.
   * **Compare multiplication methods** in the calculator transfers the active degree and operands directly into `#compare`.
   * **Run benchmark** executes 31 untraced trials per method on seeded full-width operands at $m = 163$ and $m = 571$, confirming exact agreement and reporting median microsecond timings.

---

## 3. Milestone 5 End-to-End Integration & Verification

During Milestone 5 unification, the four parallel tracks were consolidated into a single Python package (`backend/engine/` + `backend/api/`), single frontend (`frontend/`), single data folder (`data/`), single launcher (`run.py`), and unified `pytest` suite (`tests/`):

* **Zero `_reference/` stand-ins:** Every operation and exploration invokes the single canonical engine implementation directly.
* **8-Row Verification Matrix:** Automated across both Hex and Binary inputs in [tests/api/test_integration_matrix.py](../../tests/api/test_integration_matrix.py).
* **Chromium Playwright E2E Suite:** [tests/e2e/test_workbench_e2e.py](../../tests/e2e/test_workbench_e2e.py) verifies the live server in desktop and mobile (`390×840`) viewports across presets, share links, exports, batch upload (`data/demo-operands.json`), zero-inverse alerts, linked multiplier-bit highlighting, all 3 explorations, and all 4 guided tours with zero console/page errors and zero horizontal overflow.

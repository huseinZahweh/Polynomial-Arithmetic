# Milestone 4: Educational GUI & Step-by-Step Visualizers

**Assigned Owner:** Student 4  
**Execution Mode:** Parallel & Independent (built against the shared 6-endpoint JSON API contract using textbook mock traces until Milestone 5 integration)

---

## 1. Objective
Design and build a polished, single-view Educational Web Graphical User Interface (GUI) tailored for classroom instruction in **EECE 455/632**. Beyond performing and visualizing the six $GF(2^m)$ operations across $m \in \{163, 233, 239, 283, 409, 571\}$ and $2 \le m \le 8$, the GUI simplifies classroom exploration with an **Interactive Tutorial Drawer**, one-click Chapter 4/5 presets, random/batch operand loading, downloadable calculation summaries, and **Hexadecimal-encoded Shareable Calculation Links**.

---

## 2. GUI Architecture & Single-View Layout Specification

### 2.1 Persistent Top Bar: Field, Base, Tutorial & Share Controls
1. **Standard Field Degree Selector $m$:**
   * Dropdown menu populated from `GET /api/fields`, defaulting to **$GF(2^{163})$ (Project-3 Primary Field)** and supporting extended standard powers **$GF(2^{233}), GF(2^{239}), GF(2^{283}), GF(2^{409}), GF(2^{571})$** plus textbook verification fields **$GF(2^2)$ to $GF(2^8)$**.
2. **Active Irreducible Polynomial Banner:**
   * Dynamically displays $m(x)$ in Algebraic form, e.g., $x^{163} + x^7 + x^6 + x^3 + 1$, Hexadecimal, and Binary.
3. **Input / Output Format Toggle:**
   * Segmented switch between **Binary** and **Hexadecimal** with automatic live conversion of existing inputs when toggling bases.
4. **"Interactive Tutorial" Button:**
   * Fetches `GET /api/tutorial` (Milestone 1's `tutorial_slides.json`) and opens the 4-slide guided educational walkthrough drawer.
5. **"Share Link" Button (URL Snapshot Rule):**
   * Copies a shareable URL encoding `(m, operation, base, poly_a, poly_b)` in query parameters and restores full GUI state on load.
   * **Hexadecimal URL Compression Rule:** Always encodes `poly_a` and `poly_b` in **Hexadecimal** inside URL query parameters (even when `base=binary`) so $571$-bit links remain compact, converting back to Binary on page load when `base=binary` is specified.

---

### 2.2 Main Workbench: Arithmetic Controls & 4 Custom Trace Visualizers
1. **Operand Input Cards $A(x)$ and $B(x)$:**
   * Real-time character validation (`0-1` in Binary; `0-9, A-F` in Hex), live bit-length/degree counter, and live **Algebraic Polynomial Preview** $x^k + \dots + 1$.
   * **Operand $B(x)$** automatically dims and disables for unary operations (`Modulo Reduction` and `Multiplicative Inverse`).
2. **Classroom Preset, Random & Upload Toolbar:**
   * **"Load Ch. 4 $GF(2^8)$ Example"**: Pre-fills $f(x) = \{57\}$ and $g(x) = \{83\}$ in $GF(2^8)$.
   * **"Load Ch. 5 AES $\{95\}^{-1}$ Example"**: Pre-fills $A(x) = \{95\}$ in $GF(2^8)$.
   * **"Generate Random Polynomials"**: Calls `POST /api/random-polynomials` (`count: 2`, sparse or dense mode) to populate both $A(x)$ and $B(x)$ in one click.
   * **"Upload Polynomials (.txt/.json)"**: Calls `POST /api/parse-polynomials` to load validated operand pairs from a local `.txt` or `.json` file and displays structured validation alerts if a file is malformed.
3. **Six Operation Action Buttons:**
   * `Addition (A + B)`, `Subtraction (A - B)`, `Modulo Reduction (A mod m(x))`, `Multiplication (A x B)`, `Multiplicative Inverse (A^-1)`, and `Division (A / B)` (calling `POST /api/calculate`).
4. **Primary Result Display Card:**
   * Displays the result in the selected primary base (**Binary** or **Hexadecimal**), secondary base, and **Algebraic Polynomial** notation with one-click `Copy` and `Export Summary (.md/.json)` buttons calling `POST /api/export-calculation`.
   * Displays a green **"Mathematically Verified"** badge (for Inverse/Division) and a **Performance Metrics Badge** (`elapsed_ms`, `bit_length`, `hamming_weight`).
5. **Four Custom Educational Trace Visualizers:**
   * **Addition / Subtraction View:** Bit-aligned bitwise $\text{XOR}$ rows showing modulo-$2$ cancellation.
   * **Modulo Reduction View:** Each iterative shift $x^{d-m} \cdot m(x)$ and $\text{XOR}$ step until $\deg(r) < m$.
   * **Multiplication (Shift-and-XOR) View:** Table 1 showing shifted powers $x^i \cdot f(x) \bmod m(x)$ (highlighting $b_{m-1} = 1$ overflow reductions); Table 2 showing selected partial products and cumulative $\text{XOR}$.
   * **Multiplicative Inverse & Division (Extended Euclid Table 4.7) View:** Renders the exact 8-column textbook table (`Step`, `Q(x)`, `A1(x)`, `A2(x)`, `A3(x)`, `B1(x)`, `B2(x)`, `B3(x)`) with a cell-notation toggle (**Algebraic / Hex / Binary**).

---

### 2.3 Interactive Tutorial Drawer
A concise, 4-slide interactive mini-guide UI rendered dynamically from `GET /api/tutorial`:
1. **Slide 1 — What is $GF(2^m)$?** Bit-strings as polynomials and why coefficients obey $b_i + b_i = 0 \pmod{2}$.
2. **Slide 2 — Why Irreducible Polynomials $m(x)$ Matter:** Visualizing overflow reduction and standard NIST/ECC powers from $m = 163$ to $m = 571$.
3. **Slide 3 — How Shift-and-XOR & Extended Euclid Work:** Interactive annotated walkthroughs matching Stallings Chapter 4.
4. **Slide 4 — Try It Yourself:** Quick-launch preset buttons that load Chapter 4 and Chapter 5 examples directly into the workbench.

---

### 2.4 Optional Stretch Goals
The following UI enhancements are explicitly scoped as *(Optional Stretch)* items after all core deliverables above are complete:
* **Interactive Bit-Builder for $m \le 8$ *(Optional Stretch)*:** Clickable checkboxes for powers $x^{m-1} \dots 1$ so beginners can toggle bits visually and watch Binary, Hex, and Algebraic forms update simultaneously.
* **Algebraic Text Input (`ALGEBRAIC_TO_INT`) *(Optional Stretch)*:** Allows users to type algebraic polynomials directly (e.g., `x^7 + x + 1`) alongside Binary and Hexadecimal entry.
* **Animated Stepper (`Play Animation`) *(Optional Stretch)*:** Adds `Previous Step`, `Next Step`, `Play Animation`, and `Show All` playback controls over the 4 educational trace visualizers.

---

## 3. Deliverables & Verification Criteria
* [ ] Clean, commented single-view frontend components with degree selector for $m \in \{163, 233, 239, 283, 409, 571\}$ and $2 \le m \le 8$, active $m(x)$ banner, and Binary/Hex auto-converting toggles.
* [ ] All four custom educational trace visualizers (Add/Sub XOR, Mod Reduce, Shift-and-XOR Tables 1 & 2, Extended Euclid Table 4.7 with Algebraic/Hex/Binary cell toggle) rendering cleanly with mock JSON.
* [ ] Interactive Tutorial drawer (`GET /api/tutorial`), Ch. 4/5 presets, Random/Upload operand toolbar (`/api/random-polynomials`, `/api/parse-polynomials`), Export Summary button (`/api/export-calculation`), and Hexadecimal-encoded Shareable URL loader verified prior to Milestone 5 integration.

# Milestone 4: Educational GUI & Interactive Step-by-Step Visualizers

**Assigned Owner:** Student 4  
**Execution Mode:** Parallel & Independent (built against the shared JSON API contract using textbook mock traces until Milestone 5 integration)

---

## 1. Objective
Design and build a user-friendly, responsive Graphical User Interface (GUI) tailored for classroom instruction in **EECE 455/632**, enabling users to select standard field degrees ($m = 163, 233, 239, 283, 409, 571$ and $2 \le m \le 8$), input and view polynomials in **Binary** or **Hexadecimal**, and inspect interactive step-by-step mathematical breakdowns.

---

## 2. GUI Architecture & Layout Specification

The interface is structured into four intuitive sections:

### 2.1 Top Configuration Bar: Field & Base Controls
1. **Standard Field Degree Selector ($m$):**
   * Dropdown menu defaulting to **$GF(2^{163})$ (Project-3 Primary Field)**.
   * Includes extended standard powers: **$GF(2^{233})$, $GF(2^{239})$, $GF(2^{283})$, $GF(2^{409})$, $GF(2^{571})$**, plus classroom verification degrees **$GF(2^2)$ to $GF(2^8)$**.
2. **Active Irreducible Polynomial Banner:**
   * Dynamically displays the active $m(x)$ in Algebraic form (e.g., $x^{163} + x^7 + x^6 + x^3 + 1$), Hexadecimal, and Binary whenever $m$ is changed.
3. **Input / Output Format Toggle:**
   * Segmented toggle between **Binary** and **Hexadecimal** modes.
   * Includes a convenient **"Convert Current Inputs"** feature so switching between Binary and Hexadecimal automatically converts any polynomial already typed into the input fields.

### 2.2 Middle Panel: Polynomial Inputs & Six Operation Controls
1. **Operand $A(x)$ Input Card:**
   * Monospaced input box with real-time character validation (only `0-1` in Binary mode; `0-9, A-F` in Hex mode).
   * Displays live bit-length/degree counter and a live **Algebraic Polynomial Preview** ($x^k + \dots + 1$) underneath the input box.
2. **Operand $B(x)$ Input Card:**
   * Identical validation and live algebraic preview; automatically dimmed/disabled when unary operations (`Modulo Reduction` or `Multiplicative Inverse`) are selected.
3. **Classroom Preset & Random Generator Toolbar:**
   * **"Load Ch. 4 $GF(2^8)$ Example"**: Pre-fills $f(x) = \text{57}_{16}$ and $g(x) = \text{83}_{16}$ in $GF(2^8)$.
   * **"Load Ch. 5 AES $\{95\}^{-1}$ Example"**: Pre-fills $A(x) = \text{95}_{16}$ in $GF(2^8)$.
   * **"Generate Random $GF(2^m)$ Polynomials"**: Generates valid random $m$-bit polynomials in the current base so users can test $163$-bit to $571$-bit arithmetic with one click without typing $163$ bits manually.
4. **Six Operation Action Buttons:**
   * `Addition (A + B)`
   * `Subtraction (A - B)`
   * `Modulo Reduction (A mod m(x))`
   * `Multiplication (A × B)`
   * `Multiplicative Inverse (A⁻¹)`
   * `Division (A / B)`

### 2.3 Primary Result Display Card
* Highlights the final result in the user's selected primary base (**Binary** or **Hexadecimal**) with a one-click `Copy` button, alongside the secondary base and the full **Algebraic Polynomial** representation.

### 2.4 Bottom Panel: Interactive "Step-by-Step Educational Breakdown"
Renders the `educational_trace` array returned by the backend depending on the active operation:
* **Addition / Subtraction View:** Displays bit-aligned bitwise $\text{XOR}$ rows showing how matching powers of $x$ cancel modulo $2$.
* **Modulo Reduction View:** Displays each iterative shift $x^{d-m} \cdot m(x)$ and $\text{XOR}$ reduction until $\deg(r) < m$.
* **Multiplication (Shift-and-XOR) View:**
  * Table 1: Shows each shifted power $x^i \cdot f(x) \bmod m(x)$, highlighting rows where $b_{m-1} = 1$ triggered a modular $\text{XOR}$ with $m(x) - x^m$.
  * Table 2: Shows the partial products selected by the non-zero bits of $g(x)$ and their cumulative $\text{XOR}$ sum.
* **Multiplicative Inverse & Division (Extended Euclid Table 4.7) View:**
  * Renders the exact 8-column textbook table: `Step`, `Q(x)`, `A1(x)`, `A2(x)`, `A3(x)`, `B1(x)`, `B2(x)`, `B3(x)` with a mini-toggle allowing users to view table cells in Algebraic, Hex, or Binary notation.

---

## 3. Deliverables & Verification Criteria
* [ ] Responsive GUI layout with degree selector ($163 \dots 571$ and $2 \dots 8$) and Binary/Hexadecimal mode toggles.
* [ ] Real-time input validation, preset loaders, and random $m$-bit input generator.
* [ ] All four custom educational trace visualizers rendering cleanly using mock JSON payloads prior to Milestone 5 integration.
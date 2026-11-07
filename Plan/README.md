# Project Plan & 4-Student Parallel Milestone Roadmap

This directory contains the structured engineering plan for **Project-3: Polynomial Arithmetic in $GF(2^m)$**, specifically designed for a **4-student team working in parallel**.

* **Milestones 1, 2, 3, and 4** are four independent, parallel workstreams—one assigned to each student.
* **Milestone 5** is the joint team milestone where all four modules are connected, aligned end-to-end, and verified across all cryptographic field degrees.

---

## 1. Parallel Milestone Ownership

| Milestone File | Assigned Owner | Independent Scope |
| :--- | :--- | :--- |
| **[Milestone 1](./Milestones/m1-field-config-io.md)** | **Husein Zahweh** | **Field Registry, Multi-Base I/O & Additive/Modulo Engine:**<br>Configures $m \in \{163, 233, 239, 283, 409, 571\}$ (and $2\dots 8$), Binary $\leftrightarrow$ Hex $\leftrightarrow$ Algebraic converters, Addition ($+$), Subtraction ($-$), and Modulo Reduction ($\bmod\ m(x)$) with step traces. |
| **[Milestone 2](./Milestones/m2-multiplication-api.md)** | **Student 2** | **Shift-and-XOR Multiplication Engine & Backend API Controller:**<br>Implements modular multiplication $f(x) \times g(x) \bmod m(x)$ with Shift-and-XOR step traces, plus the FastAPI REST endpoints (`/fields`, `/calculate`). |
| **[Milestone 3](./Milestones/m3-euclid-and-division.md)** | **Student 3** | **Polynomial Long Division, Extended Euclid Inverse & Field Division:**<br>Implements Euclidean long division (`POLY_DIVMOD`), `EXTENDED EUCLID(m(x), b(x))` with **Table 4.7** iteration traces, and field division $a(x) / b(x) \bmod m(x)$. |
| **[Milestone 4](./Milestones/m4-educational-gui.md)** | **Student 4** | **Educational GUI & Interactive Step-by-Step Visualizers:**<br>Builds the user-friendly web GUI, degree selector, Binary/Hex toggles, live algebraic previewer, and interactive breakdown tables for Shift-and-XOR and Extended Euclid. |
| **[Milestone 5](./Milestones/m5-integration-testing.md)** | **Team** | **End-to-End Integration, Synchronization & Final Verification:**<br>Connects M1–M3 into the FastAPI controller, links M4's GUI to the live backend, and verifies all textbook and large-field test vectors. |

---

## 2. Synchronization Contract (How All Modules Work in Parallel)

To ensure that all four milestone tracks can be built and tested simultaneously without waiting on each other, all modules adhere to two shared contracts:

### 2.1 Backend Internal Polynomial Contract (M1, M2, & M3)
* Every polynomial is passed internally between backend functions as a **non-negative integer (`int`)** where bit $i$ (counting from $0$ as the least significant bit) equals the coefficient $b_i \in \{0, 1\}$ of $x^i$.
* The irreducible polynomial $m(x)$ of degree $m$ is also represented as an integer with bit $m$ set to $1$ (e.g., for $m = 8$, $m(x) = x^8 + x^4 + x^3 + x + 1 \leftrightarrow \text{100011011}_2 = 283$).
* Every arithmetic function in Milestones 1, 2, and 3 returns a tuple `(result_int, trace_dict)`.

### 2.2 API-to-GUI JSON Contract (M2 & M4)
* **Request Payload (`POST /calculate`):**
  * `m`: Integer degree (e.g., `163`, `233`, `239`, `283`, `409`, `571`, or `2`..`8`).
  * `operation`: One of `["add", "sub", "mod", "mul", "inv", "div"]`.
  * `input_base`: `"binary"` or `"hex"`.
  * `poly_a`: String representation of the first operand.
  * `poly_b`: String representation of the second operand *(optional for `"mod"` and `"inv"`)*.
* **Response Payload:**
  * `field_info`: `{ "m": 163, "irreducible_poly_algebraic": "...", "irreducible_poly_hex": "...", "irreducible_poly_bin": "..." }`
  * `inputs_parsed`: Formatted Binary, Hexadecimal, and Algebraic strings for `poly_a` and `poly_b`.
  * `result`: `{ "binary": "...", "hex": "...", "algebraic": "..." }`
  * `educational_trace`: `{ "trace_type": "...", "steps": [ ... ] }`
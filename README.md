# Polynomial Arithmetic in $GF(2^m)$ — Educational Platform & GUI

**Course:** EECE 455/632 — Cryptography and Network Security  
**Topic:** Project-3: Polynomial Arithmetic (More Challenging)  
**Primary Field:** $GF(2^{163})$  
**Extended Standard Fields:** $m \in \{163, 233, 239, 283, 409, 571\}$  

---

## 1. Project Overview

Finite fields of the form $GF(2^m)$—also known as binary Galois Fields—are foundational to modern symmetric and public-key cryptography. While $GF(2^8)$ underpins the byte-level operations in the Advanced Encryption Standard (AES), larger binary fields such as $GF(2^{163})$ through $GF(2^{571})$ form the mathematical backbone of Binary Elliptic Curve Cryptography $E_{2^m}(a,b)$.

This project provides a modular computational engine and an interactive, user-friendly Graphical User Interface (GUI) designed specifically for educational purposes. It enables students and instructors to perform, inspect, and visualize polynomial arithmetic over $GF(2^{163})$ and other standard cryptographic binary fields using the exact polynomial basis methodologies taught in **EECE 455/632**, enhanced with an interactive tutorial, step-by-step trace visualizers, classroom presets, random operand generation, batch polynomial file loading, downloadable calculation summaries, and Hexadecimal-encoded shareable calculation links.

---

## 2. Core Objectives & Enhanced Features

### 2.1 Core Project-3 Mathematical Requirements
1. **Primary Arithmetic in $GF(2^{163})$:** Perform polynomial arithmetic in $GF(2^m)$ with $m = 163$.
2. **Six Core Field Operations:**
   * **Addition:** $f(x) + g(x) \bmod m(x)$
   * **Subtraction:** $f(x) - g(x) \bmod m(x)$
   * **Modulo Reduction:** $f(x) \bmod m(x)$
   * **Multiplication:** $f(x) \times g(x) \bmod m(x)$
   * **Multiplicative Inverse:** $b(x)^{-1} \bmod m(x)$
   * **Division:** $a(x) / b(x) \bmod m(x)$
3. **Modular Extensibility:** Dynamically switch between standard cryptographic powers:

$$
m \in \{163, 233, 239, 283, 409, 571\}
$$

*Also supports small textbook degrees $2 \le m \le 8$ from Project-2 for classroom verification.*
4. **Dual Data Representation:** Accept user inputs and display outputs in either **Binary** or **Hexadecimal**, alongside human-readable algebraic polynomial notation $x^{162} + \dots + x + 1$.

### 2.2 Educational & User-Experience Enhancements
* **Interactive Tutorial & Step Visualizers:** Built-in 4-slide guided tutorial explaining $GF(2^m)$ axioms plus custom step-by-step trace visualizers for Add/Sub XOR rows, Modulo Reduction, Shift-and-XOR Tables 1 & 2, and Extended Euclid Table 4.7, plus *(Optional Stretch)* animated playback and an $m \le 8$ bit-builder.
* **Random Operand & Batch File Loader:** One-click generator for sparse or dense random $GF(2^m)$ test operands $A(x)$ and $B(x)$, plus `.txt`/`.json` operand-pair file upload alongside Chapter 4 and Chapter 5 textbook presets.
* **Share & Export Calculations:** Download formatted `.md` or `.json` calculation summaries and copy compact Hexadecimal-encoded shareable URL links that reload exact test scenarios even when switching back to Binary display.
* **Live Verification & Complexity Badges:** Automatic algebraic self-verification badges—such as confirming $B(x) \times B(x)^{-1} \bmod m(x) = 1$—execution timing (`elapsed_ms`), bit length, and Hamming weight indicators.

---

## 3. Mathematical Summary (Course Alignment)

All arithmetic strictly follows **Chapter 4 (Finite Fields)**, **Chapter 5 (AES)**, **Chapter 6 (Block Cipher Operation — XTS-AES over $GF(2^{128})$ arithmetic)**, and **Chapter 10 (Elliptic Curve Cryptography over $GF(2^m)$ curves)** of the course textbook (*Cryptography and Network Security* by William Stallings):

* **Polynomial Basis Representation:** Every element in $GF(2^m)$ is a polynomial of degree at most $m - 1$ with coefficients in $\mathbb{Z}_2 = \{0, 1\}$, represented compactly as an $m$-bit string $(b_{m-1}b_{m-2}\dots b_1b_0)_2$.
* **Addition & Subtraction (Bitwise XOR):** Because coefficient arithmetic is modulo $2$, addition and subtraction are identical bitwise XOR $\oplus$ operations.
* **Modulo Reduction & Multiplication (Shift-and-XOR):** Overflow terms $x^m$ are reduced via $x^m \equiv m(x) - x^m \pmod{m(x)}$. Modular multiplication iteratively shifts $f(x)$ left by $1$ bit, conditionally XORing with the lower terms of $m(x)$ whenever $b_{m-1} = 1$, and accumulates partial products for each set bit of $g(x)$.
* **Multiplicative Inverse & Division (Extended Euclidean Algorithm):** Non-zero inverses $b(x)^{-1} \bmod m(x)$ are computed via `EXTENDED_EUCLID_GF2M` tracking $(A_1, A_2, A_3)$ and $(B_1, B_2, B_3)$ until $B_3(x) = 1$. Division computes $a(x) / b(x) = a(x) \times b(x)^{-1} \bmod m(x)$.

---

## 4. Team Work Distribution (4 Equal Parallel Tracks + Integration)

| Milestone | Assigned Owner | Primary Application Deliverable (~25% Each) |
| :--- | :--- | :--- |
| **[Milestone 1](./Plan/Milestones/01_field_config_io_additive_mod_and_utilities.md)** | **Hussein Abbas** | Modular Field Registry for $m \in \{163, 233, 239, 283, 409, 571\}$ and $2 \le m \le 8$, Multi-Base Converters (`ALGEBRAIC_TO_INT` as *Optional Stretch*), Addition/Subtraction/Modulo Engine, Random Operand Generator, Batch File Parser, Summary Formatter, `tutorial_slides.json`, and M1 `pytest` Suite |
| **[Milestone 2](./Plan/Milestones/02_multiplication_engine_and_backend_api_controller.md)** | **Hassan Tarhini** | Shift-and-XOR Multiplication Engine with Step Trace, 6-Endpoint FastAPI Backend Controller (`/api/fields`, `/api/calculate`, `/api/random-polynomials`, `/api/parse-polynomials`, `/api/export-calculation`, `/api/tutorial`), and M2 `pytest` + `TestClient` Suite |
| **[Milestone 3](./Plan/Milestones/03_extended_euclid_inverse_division_and_verification_suite.md)** | **Husein Zahweh** | Carry-Free Multiplication, Polynomial Long Division, Extended Euclid Inverse (`EXTENDED_EUCLID_GF2M`), Field Division Engine, Table 4.7 Trace Logger, Live Self-Verifiers (`VERIFY_INVERSE`, `VERIFY_DIVISION`), and Multi-Field Benchmark & `pytest` Suite |
| **[Milestone 4](./Plan/Milestones/04_educational_gui_and_step_visualizers.md)** | **Student 4** | Single-View Educational Web GUI (Top Bar & Hex Share Link URL State, Operand Workbench, Ch. 4/5 Presets, Random/Upload Toolbar, 4 Custom Trace Visualizers, Tutorial Drawer UI, and *(Optional Stretch)* Controls) |
| **[Milestone 5](./Plan/Milestones/05_end_to_end_integration_and_verification.md)** | **Team** | End-to-End Integration across 6 FastAPI Endpoints, 8-Row Verification Matrix, Edge-Case Validation, and Course Deliverables Sign-Off |

---

## 5. Repository Structure

```text
├── Guidelines/                                  # Project handout, Project-3 spec, and classwork slides (Ch. 4 & 5)
├── Plan/                                        # Parallel 4-student project roadmap and milestone specifications
│   ├── README.md                                # Overview of parallel tracks and shared data contracts
│   └── Milestones/                              # Modular milestone documents (M1 to M5)
│       ├── 01_field_config_io_additive_mod_and_utilities.md
│       ├── 02_multiplication_engine_and_backend_api_controller.md
│       ├── 03_extended_euclid_inverse_division_and_verification_suite.md
│       ├── 04_educational_gui_and_step_visualizers.md
│       └── 05_end_to_end_integration_and_verification.md
├── Related_Findings/                            # Literature review, standards, and reference links
│   └── related_findings_and_literature_review.md
└── README.md                                    # Main project overview and documentation
```

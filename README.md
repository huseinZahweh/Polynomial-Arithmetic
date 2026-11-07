# Polynomial Arithmetic in $GF(2^m)$ — Educational Platform & GUI

**Course:** EECE 455/632 — Cryptography and Network Security  
**Topic:** Project-3: Polynomial Arithmetic (More Challenging)  
**Primary Field:** $GF(2^{163})$  
**Extended Standard Fields:** $m \in \{163, 233, 239, 283, 409, 571\}$  

---

## 1. Project Overview

Finite fields of the form $GF(2^m)$—also known as binary Galois Fields—are foundational to modern symmetric and public-key cryptography. While $GF(2^8)$ underpins the byte-level operations in the Advanced Encryption Standard (AES), larger binary fields such as $GF(2^{163})$ through $GF(2^{571})$ form the mathematical backbone of Binary Elliptic Curve Cryptography ($E_{2^m}(a,b)$).

This project provides a modular computational engine and an interactive, user-friendly Graphical User Interface (GUI) designed specifically for educational purposes. It enables students and instructors to perform, inspect, and visualize polynomial arithmetic over $GF(2^{163})$ and other standard cryptographic binary fields using the exact polynomial basis methodologies taught in **EECE 455/632**.

---

## 2. Core Objectives & Requirements

In accordance with the **Project-3** specification:
1. **Primary Arithmetic in $GF(2^{163})$:** Perform polynomial arithmetic in $GF(2^m)$ with $m = 163$.
2. **Six Core Field Operations:**
   * **Addition:** $f(x) + g(x) \bmod m(x)$
   * **Subtraction:** $f(x) - g(x) \bmod m(x)$
   * **Modulo Reduction:** $f(x) \bmod m(x)$
   * **Multiplication:** $f(x) \times g(x) \bmod m(x)$
   * **Multiplicative Inverse:** $b(x)^{-1} \bmod m(x)$
   * **Division:** $a(x) / b(x) \bmod m(x)$
3. **Modular Extensibility:** Easily switch between standard cryptographic powers:
   ```math
   m \in \{163, 233, 239, 283, 409, 571\}
   ```
   *(Also supports small textbook degrees 2 ≤ m ≤ 8 from Project-2 for classroom verification).*
4. **Dual Data Representation:** Accept user inputs and display outputs in either **Binary** or **Hexadecimal**, alongside human-readable algebraic polynomial notation ($x^{162} + \dots + x + 1$).
5. **Educational Visualization:** Present step-by-step intermediate traces—including Shift-and-XOR multiplication breakdowns and Extended Euclidean Algorithm iteration tables—rather than acting as a black-box calculator.

---

## 3. Mathematical Summary (Course Alignment)

All arithmetic strictly follows **Chapter 4 (Finite Fields)** and **Chapter 5 (AES)** of the course textbook (*Cryptography and Network Security* by William Stallings):

* **Polynomial Basis Representation:** Every element in $GF(2^m)$ is a polynomial of degree at most $m - 1$ with coefficients in $\mathbb{Z}_2 = \{0, 1\}$:

  ```math
  f(x) = b_{m-1}x^{m-1} + b_{m-2}x^{m-2} + \dots + b_1x + b_0
  ```

  Each polynomial is compactly represented as an $m$-bit string $(b_{m-1}b_{m-2}\dots b_1b_0)_2$.
* **Addition & Subtraction (Bitwise XOR):** Coefficient arithmetic is performed modulo $2$, where $1 + 1 \equiv 1 - 1 \equiv 0 \pmod 2$. Addition and subtraction are identical bitwise XOR ($\oplus$) operations.
* **Modulo Reduction & Multiplication (Shift-and-XOR):** Using an irreducible polynomial $m(x)$ of degree $m$, any overflow term $x^m$ is reduced via the equivalence $x^m \equiv m(x) - x^m \pmod{m(x)}$. Multiplication $f(x) \times g(x) \bmod m(x)$ is computed by iteratively shifting $f(x)$ left by $1$ bit, conditionally XORing with the lower terms of $m(x)$ whenever the most significant bit $b_{m-1} = 1$, and XORing the partial products corresponding to the set bits of $g(x)$.
* **Multiplicative Inverse & Division (Extended Euclidean Algorithm):** For any non-zero $b(x) \in GF(2^m)$, its inverse $b(x)^{-1} \bmod m(x)$ is computed via `EXTENDED EUCLID(m(x), b(x))` by tracking polynomial tuples $(A_1, A_2, A_3)$ and $(B_1, B_2, B_3)$ until $B_3(x) = 1$. Division is then computed as $a(x) / b(x) = a(x) \times b(x)^{-1} \bmod m(x)$.

---

## 4. Team Work Distribution (4 Parallel Tracks + End-to-End Integration)

The project is organized into four parallel milestones (one per team member) followed by a fifth collaborative integration milestone:

| Milestone | Assigned Owner | Primary Deliverable |
| :--- | :--- | :--- |
| **[Milestone 1](./Plan/Milestones/m1-field-config-io.md)** | **Husein Zahweh** | Modular Field Registry ($m \in \{163\dots 571\}$), Binary/Hex/Algebraic I/O Converters, Addition, Subtraction, and Modulo Reduction Engine |
| **[Milestone 2](./Plan/Milestones/m2-multiplication-api.md)** | **Student 2** | Shift-and-XOR Multiplication Engine, Multiplication Step-by-Step Trace Logger, and FastAPI Backend Controller |
| **[Milestone 3](./Plan/Milestones/m3-euclid-and-division.md)** | **Student 3** | Polynomial Long Division, Extended Euclidean Algorithm Inverse (`EXTENDED EUCLID`), Field Division Engine, and Table 4.7 Trace Logger |
| **[Milestone 4](./Plan/Milestones/m4-educational-gui.md)** | **Student 4** | Interactive Educational GUI, Field/Base Controls, Live Polynomial Previewer, and Step-by-Step Breakdown Visualizers |
| **[Milestone 5](./Plan/Milestones/m5-integration-testing.md)** | **Team** | End-to-End System Integration, API-to-GUI Synchronization, and Comprehensive Multi-Field Verification |

---

## 5. Repository Structure

```text
├── Guidelines/                  # Project handout, Project-3 spec, and classwork slides (Ch 4 Finite Fields & Ch 5 AES)
├── Plan/                        # Parallel 4-student project roadmap and milestone specifications
│   ├── README.md                # Overview of parallel tracks, shared data contracts, and milestone index
│   └── Milestones/              # Modular milestone documents (M1 to M5)
│       ├── m1-field-config-io.md
│       ├── m2-multiplication-api.md
│       ├── m3-euclid-and-division.md
│       ├── m4-educational-gui.md
│       └── m5-integration-testing.md
└── README.md                    # Main project overview and documentation
```
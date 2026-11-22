# Polynomial Arithmetic in $GF(2^m)$ — Educational Platform & GUI

**Course:** EECE 455/632 — Cryptography and Network Security  
**Topic:** Project-3: Polynomial Arithmetic (More Challenging)  
**Primary Field:** $GF(2^{163})$  
**Extended Standard Fields:** $m \in \{163, 233, 239, 283, 409, 571\}$  

---

## Run the Finite Field Lab

From the repository root, in PowerShell with Python 3.10 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn lab:app --host 127.0.0.1 --port 8000
```

If `python --version` shows 3.9, use your Python 3.12 executable for the first command. On macOS or Linux, use `.venv/bin/python` in place of `.\.venv\Scripts\python.exe`.

Open [the workbench](http://127.0.0.1:8000/workbench/) or [the API documentation](http://127.0.0.1:8000/docs). The web workbench and API run from the same process.

Click **Tutorial** on any lab view for a guided tour that highlights that view's controls and results. The Modulus explorer tour uses a reducible example, the AES S-box tour follows byte `53`, and the multiplication tour explains the two methods and the benchmark. **Field concepts** in the calculator tour opens the four slides on finite-field arithmetic.

Select a multiplier bit in a multiplication trace to highlight its shift and partial product and see its running XOR. On narrow screens, traces open as one labelled step at a time. Use **Show tables** to expand them. The calculator brings the result into view after a calculation, and **Back to inputs** returns to operand A. For large fields, **Show full value** reveals field-width padding and any digits omitted from the preview. **Copy result** always copies the full value. **Compare this product** runs both multiplication methods with the same field and operands.

### Explore the algorithms

- **Modulus explorer** checks a custom binary polynomial of degree 2 through 571 using polynomial GCDs. Test the AES modulus, then load `x^8 + 1` to see two nonzero factors whose product has remainder zero.
- **AES S-box** shows the multiplicative inverse, then each row of the affine XOR calculation from [FIPS 197, §5.1.1](https://csrc.nist.gov/pubs/fips/197/final). Input `53` produces inverse `CA` and S-box output `ED`. Input `00` gives `63` through the AES zero-input rule.
- **Compare multiplication** runs the shift-and-XOR engine and the independent carry-free product plus long division. For `57 × 83` at 8 bits, both methods yield `C1`. The benchmark reports medians over 31 trials per method on the same seeded full-width operands at 163 and 571 bits. Timings use arithmetic without traces or network requests.

### Verify the application

1. Open **Chapter 4 · GF(2⁸)**. Multiplication of `57` and `83` produces `C1` and both shift-and-XOR tables. Switch to **Binary** and confirm `11000001`.
2. Keep those operands and select **Add** or **Subtract**. Both give `D4` in hex. Select **Reduce**, enter `100` in hex, and confirm `1B` with one cancellation step.
3. Open **Chapter 5 · AES inverse**. `95` gives `8A`, Table 4.7, and a verification badge. Enter `11B` in the same field and confirm a zero-inverse alert with the gcd.
4. Select **Divide** in the degree-8 field. `C1` divided by `83` gives `57` and displays both stages. Click **Copy calculation link** in binary mode, reopen it in a new tab, and confirm the same calculation. Use **Export** to download Markdown or JSON.

For an upload demonstration, select the 8-bit field and upload [demo-operands.json](demo-operands.json). Choose a pair by its operands in the dropdown. **Pair 1** and **Pair 2** give `C1` and `15` with Multiply. **Pair 3** gives `57` with Divide. **Pair 4** gives `8A` with Inverse.

The uploader accepts a JSON pair, an array of pairs, or an object such as `{"base":"hex","pairs":[{"a":"57","b":"83"},{"a":"02","b":"87"}]}`. In `.txt` files, put `base: hex`, `A: 57`, and `B: 83` on separate lines. Use `---` to separate pairs. When a file omits the base, the uploader uses the active binary or hex notation. With polynomial notation active, omitted upload bases default to hex.

To run the integrated API matrix and the Chromium checks, open a second PowerShell window at the repository root. The tests start an isolated test server automatically.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest -q tests
```

The standalone milestone suites can also be run individually. Run each command separately so each suite loads its own configuration.

```powershell
.\.venv\Scripts\python.exe -m pytest -q milestone1/tests
.\.venv\Scripts\python.exe -m pytest milestone2/milestone2/tests
.\.venv\Scripts\python.exe -m pytest -q milestone3/tests
```

The [project report](deliverables/Polynomial-Arithmetic-Report.pdf) and [captioned browser demo](deliverables/Finite-Field-Lab-Demo.mp4) are in `deliverables/`.

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
├── lab.py                                       # Integrated FastAPI entry point
├── web/                                         # Browser workbench and trace views
├── tests/                                       # Integration matrix and browser acceptance tests
├── milestone1/                                  # Field setup, input and output, utilities, and additive arithmetic
├── milestone2/                                  # Shift-and-XOR engine and FastAPI controller
├── milestone3/                                  # Extended Euclid, field division, and verification
├── deliverables/                                # Project report and demo video
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

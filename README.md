# Polynomial Arithmetic in $GF(2^m)$ — Educational Platform & Finite Field Lab

**Course:** EECE 455 — Cryptography and Network Security  
**Topic:** Project-3: Polynomial Arithmetic (More Challenging)  
**Live Workbench:** [https://finite-field-lab.onrender.com](https://finite-field-lab.onrender.com)  
**Primary Field:** $GF(2^{163})$  
**Extended Standard Fields:** $m \in \{163, 233, 239, 283, 409, 571\}$  
**Textbook Verification Fields:** $2 \le m \le 8$ (including AES $GF(2^8)$ modulo $x^8 + x^4 + x^3 + x + 1$)

---

## 1. Quickstart: Run the Finite Field Lab

From the repository root with Python 3.10 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

You can also launch the ASGI server directly with Uvicorn:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.api.main:app --reload
```

On macOS or Linux, use `.venv/bin/python` in place of `.\.venv\Scripts\python.exe`.

Open [the web workbench](http://127.0.0.1:8000/workbench/) or [the interactive OpenAPI docs](http://127.0.0.1:8000/docs). The browser workbench and all **12 REST API endpoints** (6 core arithmetic/utility routes + 6 exploration/application routes) run from the same FastAPI process. You can also use the hosted deployment at [https://finite-field-lab.onrender.com](https://finite-field-lab.onrender.com).

### Run Automated Tests & Benchmarks

```powershell
# Install test & Playwright browser dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium

# Run the unified test suite (engine, API, explorations, and Chromium Playwright E2E)
.\.venv\Scripts\python.exe -m pytest -v

# Run the multi-field Extended Euclid & Division benchmark (m = 8 and m in {163..571})
.\.venv\Scripts\python.exe -m benchmarks.benchmark_gf2m --trials 10 --seed 455
```

---

## 2. Using the Workbench & Teaching Explorations

Click **Tutorial tour** on any view for a context-aware spotlight walkthrough of that tab's controls and results. From the Calculator tour, **Field concepts** opens the 4-slide guided introduction to $GF(2^m)$ arithmetic.

* **Calculator (`#calculator`):** Supports all 13 binary finite fields (default $GF(2^{163})$) in a Precision Instrument layout with a dark modulus-bit-strip hero, flat borderless polynomial readouts, auto-uppercase Hex inputs, true non-wavy `<sup>` overlays on unfocused Polynomial inputs (editing as plain ASCII `x^k` on focus while accepting pasted Unicode superscripts), dynamic two-non-selected-notation previews, empty initial state on fresh load, non-numeric placeholders, dynamic read-only **Modulus $m(x)$** card on `Reduce` and `Inverse`, true `<sup>`/`<sub>` math typography, top-center floating error alerts, untruncated full-value Results, **Compare multiplication methods** shortcut, $m \le 8$ bit-builder, Chapter 4 & 5 presets, random operands, `.txt`/`.json` batch upload modal ([data/demo-operands.json](./data/demo-operands.json)), live algebraic verification badges, Markdown/JSON export, global `Share link`, and streamlined zero-scroll step visualizers (`Step view` default with Previous → Current, inline 4-step paginated `All steps grid`, `Classic table` color legend, automatic playback locking, EEA/Shift-XOR derivation popups, and Full-Value Inspector popup).
* **Lessons (`#lessons`):** Clean, self-contained 7-lesson visual study guide teaching $GF(2^m)$ polynomial representation, modulo-2 XOR truth tables (`1.2` and `2.1`), subtraction self-inverses, modular reduction (`{2B79} mod {11B} = {C1}`), Shift-and-XOR multiplication, Extended Euclid (`POLY_DIVMOD` & Stallings Table 4.7), field division, and real-world cryptography (XTS-AES, Binary ECC & GCM/GHASH), navigated via the top section bar and linear `Previous section` / `Next section` footer controls with interactive sandboxes and self-check quizzes.
* **Visual Lab (`#visual`):** Interactive small-field ($GF(2^2)$–$GF(2^8)$) learning lab featuring a 5-screen guided primer, live hex/binary/polynomial inputs with clickable coefficient bit tiles, column-by-column XOR board, animated Shift-and-XOR belt, 3D rotatable Powers-of-$g$ ring, a context-scoped **`Visual | Classic`** header switch (visible only on Visual lab to flip between animations and static textbook tables), a dedicated `Tutorial tour`, and deep-link handoff to `#calculator`.
* **Modulus Explorer (`#modulus`):** Tests irreducibility of any binary polynomial of degree $2 \le d \le 571$ (with true `<sup>` Polynomial input overlay and auto-uppercase Hex input formatting) using Frobenius GCD checkpoints (`gcd(f, x^(2^i) + x) = 1` with plain-English explanation) and Berlekamp equal-degree splitting, showing two nonzero factor witnesses whose product leaves remainder zero when reducible.
* **Applications (`#applications`):** Four gliding sub-tabs demonstrating real-world $GF(2^m)$ cryptography directly on our engine, each with compact **`Export JSON`** and **`Import JSON`** controls and global **`Share link`** support:
  * **XTS-AES $GF(2^{128})$ Tweak Multiplier (Stallings Ch. 6 / IEEE 1619-2007):** Computes $T_j = T_0 \otimes \alpha^j \pmod{x^{128} + x^7 + x^2 + x + 1}$ with random 128-bit tweak generation, block-by-block stepping ($j \to j+1$), and clear overflow highlighting (`b₁₂₇ = 1 → x¹²⁸ overflow → XOR 0x87`).
  * **Polynomial / Binary ECC ($E_{2^m}(a,b)$) Explorer (Stallings Ch. 10 / NIST FIPS 186-4 & SEC 2):** Supports both **Teaching Curve $GF(2^4)$** and official **NIST B-163 ($GF(2^{163})$)** using classroom Polynomial ECC slide notation (`P = (Xp, Yp)`, `Q = (Xq, Yq)`, `R = (Xr, Yr)`, slope `s`), tagged Point Doubling ($R = 2P$) and Point Addition ($R = P + Q$) steps (`÷ / EEA`, `× Shift-and-XOR`, `⊕ XOR`), automatic green **Verified on curve** badges, Full-Value Inspector popups on 163-bit coordinates, and a live **ECDH Key Exchange** ($K = n_A P_B = n_B P_A$).
  * **GCM · GHASH ($GF(2^{128})$) Authenticator (Stallings Ch. 12 / NIST SP 800-38D):** Iteratively computes $Y_i = (Y_{i-1} \oplus X_i) \cdot H \pmod{x^{128} + x^7 + x^2 + x + 1}$ across $1$–$8$ 128-bit blocks using NIST SP 800-38D block bit ordering, clickable Full-Value Inspector popups, **`Save key`** (`ghash-key-H.json`), and **`Share key`** (key-only URL `?app=ghash&h=...#applications`).
  * **AES S-Box ($GF(2^8)$) Byte Substitution (Stallings Ch. 5 / FIPS 197 §5.1.1):** Traces one byte through $GF(2^8)$ inversion modulo `0x11B` (with `00 → 00` and collapsible Table 4.7 trace) and the 8-bit affine XOR transformation with constant `0x63`, with Random byte and `{53}` / `{95}` / `{00}` presets.
* **Compare Multiplication (`#compare`):** Runs Shift-and-XOR alongside carry-free multiplication + Euclidean long division on identical operands (with a one-click **Compare multiplication methods** transfer from the Calculator) plus a 31-trial untraced median benchmark at $m = 163$ and $m = 571$.

### Manual Walkthrough Checklist

1. Click **Chapter 4 · $GF(2^8)$** (`{57} × {83}`) $\rightarrow$ result `C1` (`11000001`) with Tables 1 & 2 and linked multiplier-bit selection.
2. With those operands, run **Add** and **Subtract** $\rightarrow$ both give `D4`. Run **Reduce** on hex `100` $\rightarrow$ `1B` in one cancellation step.
3. Click **Chapter 5 · AES inverse** (`{95}`) $\rightarrow$ `8A`, Stallings Table 4.7, and a verified badge. Enter `11B` in $GF(2^8)$ to see the zero-inverse alert with $A_3(x) = \gcd(m(x), 0) = m(x)$.
4. Run **Divide** on `C1 / 83` in $GF(2^8)$ $\rightarrow$ `57` with Stage 1 (Table 4.7) + Stage 2 (Shift-and-XOR). Copy a calculation link in Binary mode, reopen it in a new tab, and export Markdown or JSON.
5. Upload [data/demo-operands.json](./data/demo-operands.json) in $GF(2^8)$: Pairs 1 & 2 give `C1` and `15` (Multiply), Pair 3 gives `57` (Divide), and Pair 4 gives `8A` (Inverse).

---

## 3. Mathematical Foundation & Course Alignment

All arithmetic follows **William Stallings, *Cryptography and Network Security***:

* **Chapter 4 (Finite Fields):** Polynomial-basis bitmask encoding over $\mathbb{Z}_2[x] / \langle m(x) \rangle$, characteristic-2 XOR addition/subtraction, shifted-modulus reduction, Shift-and-XOR modular multiplication, and Extended Euclidean inversion (Table 4.7, covering both $B_3(x) = 1$ and $B_3(x) = 0$ termination outcomes).
* **Chapter 5 (AES):** Byte arithmetic in $GF(2^8)$ modulo $x^8 + x^4 + x^3 + x + 1$ (`0x11B`), MixColumns multiplication, and FIPS 197 §5.1.1 SubBytes S-box.
* **Chapter 6 (Block Cipher Operation):** Same polynomial-basis bit-shift/XOR arithmetic generalizes directly to XTS-AES tweaks over $GF(2^{128})$.
* **Chapter 10 (Elliptic Curve Cryptography):** Standard NIST/SEC binary elliptic curve fields:

$$
m \in \{163, 233, 239, 283, 409, 571\}
$$

* **Chapter 12 (Authenticated Encryption — GCM / GHASH):** Universal polynomial hashing over $GF(2^{128})$ modulo $x^{128} + x^7 + x^2 + x + 1$ (NIST SP 800-38D).

---

## 4. Team Contributions

| Track | Team Member | Core Ownership |
| :--- | :--- | :--- |
| **[Milestone 1](./docs/milestones/MILESTONE1_EXPLAINED.md)** | **Hussein Abbas** | 13-Field Registry (`fields.py`), Multi-Base Converters (`polyrepr.py`), Add/Sub/Modulo Engine (`additive.py`), Random Operands (`randomops.py`), Batch File Parser (`parser.py`), Export Formatter (`formatter.py`), Tutorial Loader & Slides (`tutorial.py`, `data/tutorial_slides.json`) |
| **[Milestone 2](./docs/milestones/MILESTONE2_EXPLAINED.md)** | **Hassan Tarhini** | Shift-and-XOR Multiplication Engine with Tables 1 & 2 Traces (`multiply.py`), Core 6-Endpoint FastAPI Controller, Pydantic v2 Schemas, Service Dispatch & CORS (`backend/api/`) |
| **[Milestone 3](./docs/milestones/MILESTONE3_EXPLAINED.md)** | **Husein Zahweh** | Carry-Free Multiply & Long Division (`poly_ops.py`), Table 4.7 Extended Euclid Inverse (`extended_euclid.py`), Two-Stage Division (`division.py`), Live Self-Verifiers (`verification.py`), Structured Exceptions (`exceptions.py`), Multi-Field Benchmarks (`benchmarks/benchmark_gf2m.py`) |
| **[Milestones 4 & 5](./docs/milestones/MILESTONE4_5_EXPLAINED.md)** | **Ali Zahreddine** | Educational Web Workbench (`frontend/`), 4 Custom Trace Visualizers, Bit-Builder, Algebraic Parser (`ALGEBRAIC_TO_INT`), Guided Spotlight Tours, 3 Bonus Teaching Explorations (`explorations.py`, `exploration_routes.py`), Unified Integration & Playwright E2E Suite |
| **[Milestone 6](./docs/milestones/MILESTONE6_EXPLAINED.md)** | **Husein Zahweh** | Comprehensive UX Simplification & Interactive Breakdown Popups (`Step view` default with built-in Previous → Current across all 13 fields, inline 4-step paginated `All steps grid`, `Classic table` color legend, playback locking outside `Step view`, step-specific EEA `Q / T₁ / T₂ / T₃` & Shift-and-XOR `<< 1 / ⊕ m(x)` derivation popups, Full-Value Inspector popup, top-center error alerts, auto-uppercase Hex & Unicode superscript Polynomial inputs), Self-Contained `Lessons` Study Guide with $\mathbb{Z}_2$ Truth Tables (`lesson-data.js`, `lessons.js`), **Applications** Tab (XTS-AES $GF(2^{128})$ & Binary ECC NIST B-163), Upload Modal, Toasts & Extended E2E Tests |

---

## 5. Documentation Hub

* **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md):** System diagram, layer responsibilities, complete 13-endpoint REST API contract, and run/test instructions.
* **[docs/CODE_EXPLAINED.md](./docs/CODE_EXPLAINED.md):** File-by-file, function-by-function technical guide across `backend/`, `frontend/`, `benchmarks/`, and `run.py`.
* **Milestone Explanations:** [Milestone 1](./docs/milestones/MILESTONE1_EXPLAINED.md) · [Milestone 2](./docs/milestones/MILESTONE2_EXPLAINED.md) · [Milestone 3](./docs/milestones/MILESTONE3_EXPLAINED.md) · [Milestones 4 & 5](./docs/milestones/MILESTONE4_5_EXPLAINED.md) · [Milestone 6](./docs/milestones/MILESTONE6_EXPLAINED.md).
* **Planning & Research:** [Project Plan](./Plan/README.md) · [Literature Review & Related Findings](./Related_Findings/related_findings_and_literature_review.md).
* **Course Deliverables:** [Project Report](./deliverables/Polynomial-Arithmetic-Report.pdf) · [Demo Video](./deliverables/Finite-Field-Lab-Demo.mp4).

---

## 6. Repository Structure

```text
Polynomial-Arithmetic/
├── backend/
│   ├── __init__.py
│   ├── engine/                       # Unified GF(2^m) pure-Python math & utilities
│   │   ├── __init__.py               # Clean public re-exports
│   │   ├── fields.py                 # 13-field registry (2 <= m <= 8 and m in {163..571})
│   │   ├── polyrepr.py               # Lossless Binary / Hex / Algebraic converters & shared 4096-bit check
│   │   ├── additive.py               # Add, subtract, modulo reduction & traces
│   │   ├── multiply.py               # Shift-and-XOR multiplication & Tables 1 & 2 traces
│   │   ├── poly_ops.py               # Carry-free multiply & POLY_DIVMOD long division
│   │   ├── extended_euclid.py        # Stallings Table 4.7 EEA inverse + gcd/trace errors
│   │   ├── division.py               # Two-stage GF(2^m) field division
│   │   ├── verification.py           # Live algebraic self-verifiers (inverse & division)
│   │   ├── exceptions.py             # GF2mInverseError, ZeroElementHasNoInverseError, NotInvertibleError
│   │   ├── randomops.py              # Sparse/dense nonzero random operand generator
│   │   ├── parser.py                 # Batch .txt/.json operand file parser (hex, bin, algebraic)
│   │   ├── formatter.py              # .md/.json summary exporter & v1 share-token codec
│   │   ├── tutorial.py               # Tutorial slide loader (reads data/tutorial_slides.json)
│   │   └── explorations.py           # Irreducibility/Berlekamp, AES S-Box, XTS-AES GF(2^128), Binary ECC (B-163), GCM/GHASH, Mul comparison
│   └── api/                          # Unified FastAPI server & service layer
│       ├── __init__.py
│       ├── main.py                   # FastAPI entrypoint (6 core + 7 exploration/application routes + /workbench/)
│       ├── schemas.py                # Pydantic v2 request/response contracts
│       ├── services.py               # Operation dispatcher, timing, verification, error mapping
│       └── exploration_routes.py     # /api/explorations/* FastAPI router
├── frontend/                         # Zero-build ES-module educational web workbench + self-hosted fonts/
│   ├── fonts/                        # Self-hosted IBM Plex Sans & JetBrains Mono woff2 assets + OFL licenses
│   ├── index.html
│   ├── lab.css
│   ├── theme.css                     # Precision Instrument visual theme layer
│   ├── theme.js                      # Hero modulus bit-strip renderer
│   ├── visual.css                    # Visual lab & scoped Visual | Classic styles
│   ├── visual.js                     # Interactive Visual lab (5-screen intro, XOR board, belt, 3D ring)
│   ├── lab.js
│   ├── notation.js
│   ├── traces.js
│   ├── lesson-data.js
│   ├── lessons.js
│   ├── explorations.js
│   └── tour.js
├── data/                             # Canonical static JSON classroom data
│   ├── tutorial_slides.json
│   └── demo-operands.json
├── benchmarks/
│   ├── __init__.py
│   └── benchmark_gf2m.py             # Multi-field EEA & division benchmark CLI
├── tools/                            # Independent 10,000-case verification campaign & supplemental checks
│   ├── independent_audit.py
│   └── supplemental_checks.py
├── tests/                            # Unified root pytest suite (engine, API, audit regressions, & Chromium E2E)
│   ├── conftest.py
│   ├── engine/                       # Pure-Python math, utilities, & exploration unit tests
│   ├── api/                          # FastAPI endpoint, 8-row matrix, & exploration route tests
│   └── e2e/                          # Chromium Playwright workbench & tour acceptance tests
├── docs/                             # Technical architecture, codebase guide, & milestone docs
│   ├── ARCHITECTURE.md
│   ├── CODE_EXPLAINED.md
│   └── milestones/
│       ├── MILESTONE1_EXPLAINED.md
│       ├── MILESTONE2_EXPLAINED.md
│       ├── MILESTONE3_EXPLAINED.md
│       ├── MILESTONE4_5_EXPLAINED.md
│       └── MILESTONE6_EXPLAINED.md
├── Guidelines/                       # Course project handout & lecture slides (Ch. 4, 5, 6, 10, & 12)
├── Plan/                             # Parallel milestone specifications & verification matrix
├── Related_Findings/                 # Literature review, standards, & tool comparisons
├── deliverables/                     # Project report PDF & demo video
├── run.py                            # Root Uvicorn server launcher
├── pytest.ini                        # Root pytest configuration
├── requirements.txt                  # Runtime dependencies
├── requirements-dev.txt              # Development & testing dependencies
├── .gitignore
└── README.md
```

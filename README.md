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

Open [the web workbench](http://127.0.0.1:8000/workbench/) or [the interactive OpenAPI docs](http://127.0.0.1:8000/docs). The browser workbench and all **10 REST API endpoints** (6 core arithmetic/utility routes + 4 exploration routes) run from the same FastAPI process. You can also use the hosted deployment at [https://finite-field-lab.onrender.com](https://finite-field-lab.onrender.com).

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

* **Calculator (`#calculator`):** Supports all 13 binary finite fields (default $GF(2^{163})$) in a full-width de-nested layout, dynamic read-only **Modulus $m(x)$** card on `Reduce` and `Inverse`, true `<sup>`/`<sub>` math typography, elevated pop-up error alerts, live **Hex / Binary / Polynomial** conversion with gliding selection indicators, an $m \le 8$ interactive coefficient bit-builder, Chapter 4 & 5 presets, sparse/dense random operands, `.txt`/`.json` batch upload (demo file at [data/demo-operands.json](./data/demo-operands.json)), live algebraic verification badges, Markdown/JSON export, Hex-compressed share links, large-field previews with **Show full value**, and zero-horizontal-scroll step visualizers (educational `.step-knowledge-title` headings, `Step view` Inspector Square, auto-maximized `All steps grid`, `Classic table`, `Compare prev → curr`, `Expand full view` modal, `Compact values` / `Full m-bit` toggle, sequential step cascade, 5-button playback bar, and step scrubber).
* **Lessons (`#lessons`):** Standalone interactive & animated 7-lesson curriculum teaching $GF(2^m)$ polynomial representation, XOR addition/subtraction, modular reduction, Shift-and-XOR multiplication, Extended Euclidean Algorithm (Stallings Table 4.7), polynomial division, and cryptographic applications (AES, XTS-AES, Binary ECC) with 5-button animation controls, interactive sandboxes, self-check quizzes, and one-click **Open in Calculator** handoffs.
* **Modulus Explorer (`#modulus`):** Tests irreducibility of any binary polynomial of degree $2 \le d \le 571$ using Frobenius GCD checkpoints and Berlekamp equal-degree splitting, showing two nonzero factor witnesses whose product leaves remainder zero when reducible.
* **AES S-Box Walkthrough (`#aes`):** Traces any byte `00`–`FF` through Extended Euclid inversion in $GF(2^8)$ and each affine XOR row from [FIPS 197, §5.1.1](https://csrc.nist.gov/pubs/fips/197/final) (e.g., `53` $\rightarrow$ inverse `CA` $\rightarrow$ output `ED`; `00` $\rightarrow$ `63`).
* **Compare Multiplication (`#compare`):** Runs Shift-and-XOR alongside carry-free multiplication + Euclidean long division on identical operands (with a one-click **Compare this product** transfer from the Calculator) plus a 31-trial untraced median benchmark at $m = 163$ and $m = 571$.

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

---

## 4. Team Contributions

| Track | Team Member | Core Ownership |
| :--- | :--- | :--- |
| **[Milestone 1](./docs/milestones/MILESTONE1_EXPLAINED.md)** | **Hussein Abbas** | 13-Field Registry (`fields.py`), Multi-Base Converters (`polyrepr.py`), Add/Sub/Modulo Engine (`additive.py`), Random Operands (`randomops.py`), Batch File Parser (`parser.py`), Export Formatter (`formatter.py`), Tutorial Loader & Slides (`tutorial.py`, `data/tutorial_slides.json`) |
| **[Milestone 2](./docs/milestones/MILESTONE2_EXPLAINED.md)** | **Hassan Tarhini** | Shift-and-XOR Multiplication Engine with Tables 1 & 2 Traces (`multiply.py`), Core 6-Endpoint FastAPI Controller, Pydantic v2 Schemas, Service Dispatch & CORS (`backend/api/`) |
| **[Milestone 3](./docs/milestones/MILESTONE3_EXPLAINED.md)** | **Husein Zahweh** | Carry-Free Multiply & Long Division (`poly_ops.py`), Table 4.7 Extended Euclid Inverse (`extended_euclid.py`), Two-Stage Division (`division.py`), Live Self-Verifiers (`verification.py`), Structured Exceptions (`exceptions.py`), Multi-Field Benchmarks (`benchmarks/benchmark_gf2m.py`) |
| **[Milestones 4 & 5](./docs/milestones/MILESTONE4_5_EXPLAINED.md)** | **Ali Zahreddine** | Educational Web Workbench (`frontend/`), 4 Custom Trace Visualizers, Bit-Builder, Algebraic Parser (`ALGEBRAIC_TO_INT`), Guided Spotlight Tours, 3 Bonus Teaching Explorations (`explorations.py`, `exploration_routes.py`), Unified Integration & Playwright E2E Suite |
| **[Milestone 6](./docs/milestones/MILESTONE6_EXPLAINED.md)** | **Team** | Zero-Horizontal-Scroll Trace Redesign & Visual Diffs (`Step view` Inspector Square, auto-maximized `All steps grid`, `Classic table`, `Compare prev → curr`, sequential step cascade, educational step titles), Standalone Animated `Lessons` Page (`lesson-data.js`, `lessons.js`), Full-Width Layout, Read-Only Modulus Card, True `<sup>`/`<sub>` Math, Pop-Up Errors, Gliding Pills & Extended E2E Tests |

---

## 5. Documentation Hub

* **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md):** System diagram, layer responsibilities, complete 10-endpoint REST API contract, and run/test instructions.
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
│   │   ├── polyrepr.py               # Lossless Binary / Hex / Algebraic converters
│   │   ├── additive.py               # Add, subtract, modulo reduction & traces
│   │   ├── multiply.py               # Shift-and-XOR multiplication & Tables 1 & 2 traces
│   │   ├── poly_ops.py               # Carry-free multiply & POLY_DIVMOD long division
│   │   ├── extended_euclid.py        # Stallings Table 4.7 EEA inverse + gcd/trace errors
│   │   ├── division.py               # Two-stage GF(2^m) field division
│   │   ├── verification.py           # Live algebraic self-verifiers (inverse & division)
│   │   ├── exceptions.py             # GF2mInverseError, ZeroElementHasNoInverseError, NotInvertibleError
│   │   ├── randomops.py              # Sparse/dense nonzero random operand generator
│   │   ├── parser.py                 # Batch .txt/.json operand file parser
│   │   ├── formatter.py              # .md/.json summary exporter & v1 share-token codec
│   │   ├── tutorial.py               # Tutorial slide loader (reads data/tutorial_slides.json)
│   │   └── explorations.py           # Irreducibility/Berlekamp, AES S-box, Mul comparison
│   └── api/                          # Unified FastAPI server & service layer
│       ├── __init__.py
│       ├── main.py                   # FastAPI entrypoint (6 core + 4 exploration routes + /workbench/)
│       ├── schemas.py                # Pydantic v2 request/response contracts
│       ├── services.py               # Operation dispatcher, timing, verification, error mapping
│       └── exploration_routes.py     # /api/explorations/* FastAPI router
├── frontend/                         # Zero-build ES-module educational web workbench
│   ├── index.html
│   ├── lab.css
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
├── tests/                            # Unified root pytest suite (363 tests)
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
├── Guidelines/                       # Course project handout & lecture slides (Ch. 4 & 5)
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

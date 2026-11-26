# System Architecture — Finite Field Lab ($GF(2^m)$)

**Course:** EECE 455 — Cryptography and Network Security (Project-3)  
**Primary Field:** $GF(2^{163})$ | **Extended Standard Fields:** $m \in \{163, 233, 239, 283, 409, 571\}$ | **Textbook Fields:** $2 \le m \le 8$

---

## 1. High-Level Architecture

The platform runs as a single local FastAPI ASGI application (`backend.api.main:app`) that serves both the **13-endpoint JSON REST API** and the **zero-build ES-module web workbench** mounted at `/workbench/`. Pure finite-field mathematics live strictly inside `backend/engine/` with zero web-framework dependencies.

```mermaid
flowchart LR
    Browser["Browser Workbench<br/>(frontend/*.js, BigInt previews)"]
    Static["FastAPI Static Mount<br/>/workbench/"]
    CoreAPI["Core REST API<br/>(6 endpoints in backend/api/main.py)"]
    ExpAPI["Explorations & Applications Router<br/>(7 endpoints in exploration_routes.py)"]
    Services["Service & Dispatch Layer<br/>(backend/api/services.py)"]
    Engine["Pure-Python GF(2^m) Engine<br/>(backend/engine/*.py)"]
    Data["Static JSON Data<br/>(data/tutorial_slides.json,<br/>data/demo-operands.json)"]

    Browser -->|GET /workbench/| Static
    Browser -->|JSON over HTTP| CoreAPI
    Browser -->|JSON over HTTP| ExpAPI
    CoreAPI --> Services
    Services --> Engine
    ExpAPI --> Engine
    Engine --> Data
```

---

## 2. Layer & Module Responsibilities

| Layer | Directory | Ownership | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Pure Math & Utilities** | `backend/engine/` | Hussein Abbas (M1), Hassan Tarhini (M2), Husein Zahweh (M3, M6), Ali Zahreddine (Explorations) | Canonical 13-field registry, lossless Binary/Hex/Algebraic converters, traced $+$, $-$, $\bmod$, Shift-and-XOR $\times$, carry-free $\times$, `POLY_DIVMOD`, Table 4.7 Extended Euclid $b^{-1}$, two-stage division, live verifiers, random generator, batch parser, exporter, tutorial loader, Modulus irreducibility/Berlekamp, XTS-AES $GF(2^{128})$ tweak multiplier, Binary ECC ($GF(2^4)$ & NIST B-163), and multiplication comparison/benchmarks. |
| **Web API & Service Layer** | `backend/api/` | Hassan Tarhini (M2 Core), Ali Zahreddine (Integration & Explorations), Husein Zahweh (M6 Applications) | Pydantic v2 schemas (`schemas.py`), operation dispatch / timing / verification assembly (`services.py`), 7 exploration & application endpoints (`exploration_routes.py`), 6 core endpoints + CORS + `/workbench/` mount (`main.py`). |
| **Educational Web GUI** | `frontend/` | Ali Zahreddine (M4–M5), Husein Zahweh (M6), Hassan Tarhini (Visual Lab & Theme) | Single-document 6-view lab (`index.html`, `lab.css`, `theme.css`, `theme.js`, `visual.css`, `visual.js` serving `#calculator`, `#lessons`, `#visual`, `#modulus`, `#applications`, `#compare`), client `BigInt` formatting + true `<sup>` Polynomial input overlays + Full-Value Inspector & Derivation popups + top-center error alerts (`notation.js`), `Step view`-default traces (`traces.js`), self-contained 7-lesson study guide (`lesson-data.js`, `lessons.js`), interactive `Visual lab` with context-scoped `Visual \| Classic` toggle (`visual.js`), interactive `Tutorial tour` spotlight walkthroughs across all 6 views (`tour.js`), Modulus / Applications (XTS-AES + Binary ECC + GCM/GHASH + AES S-Box, Export/Import JSON, GHASH Save/Share key) / Compare labs (`explorations.js`), and calculator controller (`lab.js`). |
| **Static Classroom Data** | `data/` | Hussein Abbas (M1), Ali Zahreddine (M4) | Single source of truth for the 4 tutorial slides + Ch. 4/5 presets (`tutorial_slides.json`) and 4-pair classroom upload demo (`demo-operands.json`). |
| **Benchmarks & Tests** | `benchmarks/`, `tests/` | Husein Zahweh (M3), Full Team | Multi-field EEA/division CLI benchmark (`benchmark_gf2m.py`) and unified root `pytest` suite (`tests/engine/`, `tests/api/`, `tests/e2e/`). |

---

## 3. Shared Data Contract: Polynomial Bitmask Encoding

All modules in `backend/engine/` represent every polynomial $p(x) = \sum_{i=0}^{d} c_i x^i \in GF(2)[x]$ as a **non-negative Python `int`** where bit $i$ (LSB $= 0$) equals the coefficient $c_i \in \{0, 1\}$:

* Example: $x^6 + x^4 + x^2 + x + 1 \leftrightarrow \text{01010111}_2 \leftrightarrow \text{0x57} = 87$.
* Reduction modulus $m(x)$ of degree $m$ always includes bit $m$ set to $1$, e.g., AES $x^8 + x^4 + x^3 + x + 1 \leftrightarrow \text{100011011}_2 = \text{0x11B} = 283$.
* **Stallings Course Mapping:**
  * **Chapter 4:** Polynomial basis over $\mathbb{Z}_2$, XOR add/sub, modulo reduction, Shift-and-XOR multiplication, Extended Euclid Table 4.7.
  * **Chapter 5:** AES byte arithmetic in $GF(2^8)$ modulo `0x11B` and FIPS 197 §5.1.1 SubBytes S-box.
  * **Chapter 6:** Same bit-level polynomial representation extends directly to XTS-AES tweaks in $GF(2^{128})$.
  * **Chapter 10:** Binary elliptic curves $E_{2^m}(a, b)$ over standard NIST/SEC fields $m \in \{163, 233, 239, 283, 409, 571\}$.
  * **Chapter 12:** GCM / GHASH polynomial authentication over $GF(2^{128})$ modulo $x^{128} + x^7 + x^2 + x + 1$ (NIST SP 800-38D).

---

## 4. Complete REST API Reference (13 Application Endpoints + Meta)

Base URL (default): `http://127.0.0.1:8000` · Swagger OpenAPI UI: `/docs` · Web Workbench: `/workbench/`

### 4.1 Meta & Health Routes
* `GET /` — Redirects to `/workbench/`.
* `GET /api` — Returns `{"service": "gf2m-api", "version": "1.0.0", "docs": "/docs", "workbench": "/workbench/"}`.
* `GET /api/health` — Returns `{"status": "ok"}`.

### 4.2 Core Arithmetic & Utility Endpoints (6 Routes)

#### 1. `GET /api/fields`
* **Query:** `include_textbook: bool = true`
* **Response (`200`):** `{"count": 13, "fields": [{"m", "category", "name", "reduction_poly_hex", "reduction_poly_bin", "reduction_poly", "element_bits"}, ...]}`

#### 2. `POST /api/calculate`
* **Request:**
  ```json
  {
    "m": 163,
    "operation": "multiply",
    "a": "57",
    "b": "83",
    "input_base": "hex",
    "output_base": "hex",
    "trace": true
  }
  ```
  * Accepts aliases `poly_a` / `poly_b`, short operation names (`sub`, `mod`, `mul`, `inv`, `div`), and `input_base` / `output_base` in `{"hex", "bin", "binary", "algebraic"}`.
* **Response (`200`):**
  ```json
  {
    "operation": "multiply",
    "field": { "...": "..." },
    "operands": { "a": { "hex": "...", "bin": "...", "poly": "...", "degree": 6, "bit_length": 7, "hamming_weight": 5 }, "b": { "...": "..." } },
    "result": { "hex": "...", "bin": "...", "poly": "...", "degree": 13, "bit_length": 14, "hamming_weight": 9 },
    "trace": { "...": "..." },
    "initial_reduction": null,
    "verification": null,
    "metrics": { "elapsed_ms": 0.12, "result_bit_length": 14, "result_hamming_weight": 9 },
    "share_token": "76317c..."
  }
  ```
* **Errors (`400`):** Returns `{"detail": "..."}` on invalid base/digits, unsupported degree, or missing operand `B`. On zero inverse or division by zero (`b mod m(x) == 0`), also includes `"gcd"` and `"trace"` (Table 4.7 Step 0 with $B_3 = 0$).

#### 3. `POST /api/random-polynomials`
* **Request:** `{"m": 163, "density": "sparse", "count": 2, "output_base": "hex", "seed": null}` (`sparsity` accepted as alias for `density`).
* **Response (`200`):** `{"field", "density", "seed", "a", "b", "m", "output_base", "polynomials": [...]}`.

#### 4. `POST /api/parse-polynomials`
* **Request:** `{"content": "<raw .txt or .json text>", "filename": "demo-operands.json", "default_base": "hex"}`.
* **Response (`200`):** `{"count": 4, "pairs": [{"a": "57", "b": "83", "base": "hex"}, ...]}` (`400` with `"parse error: ..."` on malformed files).

#### 5. `POST /api/export-calculation`
* **Request:** `{"calculation": <CalculateResponse>, "format": "md" | "json", "download": false}`.
* **Response (`200`):** Either JSON `{"filename", "media_type", "content"}` or streamed file download with `Content-Disposition: attachment` when `download: true`.

#### 6. `GET /api/tutorial`
* **Response (`200`):** `{"version": "1.0", "title": "...", "slides": [ ...4 slides + presets on Slide 4... ]}`.

### 4.3 Interactive Exploration & Application Endpoints (7 Routes)

| Method | Path | Request Body | Response Highlights |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/explorations/modulus` | `{"polynomial": "x^8 + 1", "input_base": "algebraic"}` | `irreducible`, `degree`, `checks` (GCD checkpoints), `witness` (two nonzero factors with remainder `0`), `split_with_berlekamp`. |
| `POST` | `/api/explorations/aes-sbox` | `{"byte": "53", "input_base": "hex"}` | FIPS 197 §5.1.1 / Stallings Ch. 5 AES S-Box trace (`input`, `inverse`, optional Table 4.7 `inverse_trace`, 6 `affine_rows`, `output`). |
| `POST` | `/api/explorations/xts-tweak` | `{"t0_hex": "5000...0001", "steps": 6}` | IEEE 1619-2007 $GF(2^{128})$ tweak chain ($m(x) = x^{128} + x^7 + x^2 + x + 1$, mask `0x87`), returning `blocks[]` with `block_index`, `tweak_hex`, `msb_before_shift`, `overflowed`, `shifted_hex`, `reduced_xor_87`. |
| `POST` | `/api/explorations/binary-ecc` | `{"curve": "nist_b163", "n_a": 5, "n_b": 9}` | Curve parameters (`gf2_4` or official NIST FIPS 186-4 / SEC 2 `nist_b163`), `base_point_g`, tagged `doubling` ($R = 2P$) & `addition` ($R = P + Q$) step lists (`÷ / EEA`, `× Shift-and-XOR`, `⊕ XOR`), curve verification flags, and `ecdh` shared secret ($K_A = K_B$). |
| `POST` | `/api/explorations/gcm-ghash` | `{"h_hex": "66E9...2B2E", "blocks_hex": ["0388...FE78", "..."]}` | NIST SP 800-38D / Stallings Ch. 12 $GF(2^{128})$ GHASH tag (`tag_hex`, `tag_poly`, `elapsed_ms`) and per-block `steps[]` (`block_index`, `x_i_hex`, `prev_y_hex`, `xor_input_hex`, `y_i_hex`). |
| `POST` | `/api/explorations/compare-multiplication` | `{"m": 8, "a": "57", "b": "83", "input_base": "hex"}` | `agree`, `shift_result`, `shift_trace`, `raw_product`, `quotient`, `remainder`, `division_steps`. |
| `GET` | `/api/explorations/multiplication-benchmarks` | *(none)* | `{"seed": 455, "trials": 31, "rows": [{"m": 163, "agree": true, "shift_xor_us": ..., "long_division_us": ...}, {"m": 571, ...}]}`. |

---

## 5. Local Setup, Launch & Verification Commands

```powershell
# 1. Create virtual environment and install runtime dependencies
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Launch the server (either command works from the repository root)
.\.venv\Scripts\python.exe run.py
# or:
.\.venv\Scripts\python.exe -m uvicorn backend.api.main:app --reload

# 3. Install dev/test dependencies and run the full unified test suite
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest -v

# 4. Run the multi-field Extended Euclid & Division benchmark
.\.venv\Scripts\python.exe -m benchmarks.benchmark_gf2m --trials 10 --seed 455
```

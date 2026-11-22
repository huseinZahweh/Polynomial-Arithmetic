# Milestone 2 — Shift-and-XOR Multiplication Engine & Core FastAPI Backend

**Project:** EECE 455 — Project-3: Polynomial Arithmetic in $GF(2^m)$  
**Assigned Owner:** Hassan Tarhini  
**Unified Code Locations:** [backend/engine/multiply.py](../../backend/engine/multiply.py), [backend/api/main.py](../../backend/api/main.py), [backend/api/schemas.py](../../backend/api/schemas.py), and [backend/api/services.py](../../backend/api/services.py)  
**Textbook References:** William Stallings, *Cryptography and Network Security*, **Chapter 4** (Finite Fields), **Chapter 5** (AES), **Chapter 6** (XTS-AES over $GF(2^{128})$), and **Chapter 10** (Binary Elliptic Curve Cryptography over $GF(2^{163}) \dots GF(2^{571})$).

---

## 1. Role in the Unified System

Milestone 2 provides two pillars of the application:

1. **The Shift-and-XOR Multiplication Engine (`backend/engine/multiply.py`):** Computes $c(x) = a(x) \times b(x) \bmod m(x)$ in both a fast untraced path (`multiply`) and a structured educational path (`multiply_traced`) driving Tables 1 and 2 in the web workbench.
2. **The Core FastAPI Backend (`backend/api/`):** Exposes the six primary REST endpoints (`/api/fields`, `/api/calculate`, `/api/random-polynomials`, `/api/parse-polynomials`, `/api/export-calculation`, `/api/tutorial`), Pydantic v2 schemas, CORS middleware, timing/complexity metrics, HTTP `400` validation errors, and interactive OpenAPI documentation at `/docs`.

During Milestone 5 unification, the temporary standalone `_reference/` shims and `providers.py` bridge were retired so `backend/api/services.py` and `backend/api/main.py` import directly from the canonical `backend.engine` modules.

---

## 2. Shift-and-XOR Multiplication Algorithm (`backend/engine/multiply.py`)

For reduced operands $a(x), b(x) \in GF(2^m)$, multiplying by $x$ is a 1-bit left shift followed by conditional XOR with $m(x)$ whenever bit $m$ overflows:

$$
x \cdot t(x) \bmod m(x) = \begin{cases} t(x) \ll 1 & \text{if } b_{m-1} = 0 \\ (t(x) \ll 1) \oplus m(x) & \text{if } b_{m-1} = 1 \end{cases}
$$

Walking the bits of $b(x)$ from LSB ($i = 0$) to MSB accumulates $t_i = a(x) \cdot x^i \bmod m(x)$ whenever bit $i$ of $b(x)$ equals $1$:

$$
a(x) \times b(x) \bmod m(x) = \bigoplus_{i=0}^{\deg(b)} b_i \cdot \left(a(x) \cdot x^i \bmod m(x)\right)
$$

### Worked Example — AES Byte Identity $\{53\} \times \{\text{CA}\} = \{01\}$ in $GF(2^8)$

With $m(x) = x^8 + x^4 + x^3 + x + 1$ (`0x11B`) and $b = \{\text{CA}\} = \text{11001010}_2$ (set bits at positions $1, 3, 6, 7$):

| $i$ | Bit of $b$ | $t_i = a \cdot x^i \bmod m$ (hex) | Reduced? | Added? | Running XOR (hex) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `0` | `0` | `53` | No | No | `00` |
| `1` | `1` | `A6` | No | **Yes** | `A6` |
| `2` | `0` | `57` | **Yes** | No | `A6` |
| `3` | `1` | `AE` | No | **Yes** | `08` |
| `4` | `0` | `47` | **Yes** | No | `08` |
| `5` | `0` | `8E` | No | No | `08` |
| `6` | `1` | `07` | **Yes** | **Yes** | `0F` |
| `7` | `1` | `0E` | No | **Yes** | **`01`** |

### Engine Entry Points & Complexity

* **`multiply(a, b, mod_poly, m) -> int`:** Fast untraced path used by untraced field division, live algebraic verification, and the 163/571-bit comparison benchmarks. Time $O(m^2)$ bit operations, space $O(1)$ auxiliary.
* **`multiply_traced(a, b, mod_poly, m, max_steps=2048) -> tuple[int, MultiplyTrace]`:** Emits `ShiftStep` records (`i`, `multiplier_bit`, `partial_hex`, `partial_poly`, `reduced`, `added`, `accumulator_hex`) plus summary counts (`reductions`, `partial_products`, `truncated`). Stops as soon as all remaining high bits of $b$ are zero, so sparse multipliers stay concise even in $GF(2^{571})$. Bounding `max_steps` never alters the mathematical product.

---

## 3. Core REST API Layer (`backend/api/`)

| Method | Path | Responsibility |
| :--- | :--- | :--- |
| `GET` | `/api/fields` | Lists all 13 fields (or 6 cryptographic fields with `?include_textbook=false`). |
| `POST` | `/api/calculate` | Parses operands (hex, binary, or algebraic), reduces into $GF(2^m)$, dispatches to the owning engine, records `elapsed_ms`, attaches `verification` for inverse/division, and encodes a `v1` hex `share_token`. |
| `POST` | `/api/random-polynomials` | Generates sparse or dense nonzero operands via `backend.engine.randomops`. |
| `POST` | `/api/parse-polynomials` | Validates uploaded `.txt`/`.json` batches via `backend.engine.parser`. |
| `POST` | `/api/export-calculation` | Renders downloadable Markdown or JSON reports via `backend.engine.formatter`. |
| `GET` | `/api/tutorial` | Serves the 4-slide educational tutorial and Ch. 4/5 presets from `data/tutorial_slides.json`. |

All domain validation errors (unsupported degrees, missing operand B, signed or invalid digits, zero inverse / division by zero) are translated cleanly to HTTP `400` responses; non-invertible errors preserve `.gcd` and `.trace` in the JSON body so the workbench displays the exact Table 4.7 termination row.

---

## 4. Verification Coverage

Milestone 2's full 147-test suite (original standalone count after textbook alignment and strict validation hardening) has been migrated cleanly into the unified root test suite:

* [tests/engine/test_multiply.py](../../tests/engine/test_multiply.py): Cross-checks Shift-and-XOR against independent carry-free multiply + reduction across all 13 fields, verifies Stallings Ch. 4 ($\{57\} \times \{83\} = \{\text{C1}\}$) and Ch. 5 ($\{02\} \times \{87\} = \{15\}$, $\{53\} \times \{\text{CA}\} = \{01\}$), checks field algebra laws (identity, zero, commutativity, associativity, distributivity), verifies Table 2 product reconstruction, and validates `max_steps` trace truncation.
* [tests/api/test_endpoints.py](../../tests/api/test_endpoints.py) & [tests/api/test_integration_matrix.py](../../tests/api/test_integration_matrix.py): Exercises all six core endpoints, HTTP `400` error contracts, structured `gcd`/`trace` preservation, share-token round-trips, and the full 8-row verification matrix across $m \in \{3, 8, 163, 233, 239, 283, 409, 571\}$.

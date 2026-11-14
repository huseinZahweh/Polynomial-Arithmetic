# Milestone 2 — Multiplication Engine & Backend API Controller
### Full Technical Explanation

**Project:** Polynomial Arithmetic in GF(2^m) — EECE 455/632 (Cryptography and Network Security), Project-3
**This milestone owns:** the shift-and-XOR **multiplication engine** (with a step-by-step trace), the **6-endpoint FastAPI backend**, and the **automated test suite** — all built so the other three student tracks can merge into it later without rewrites.

This document explains *what* was built, *why* each piece exists, *how* the mathematics works, and *how* the code is organised, in enough depth to both understand it and present it.

---

## 1. The big picture

A finite field GF(2^m) (a "binary Galois field") is a set of `2^m` elements on which you can add, subtract, multiply, and divide — just like ordinary numbers, but every coefficient is a single bit. These fields are the arithmetic layer underneath AES (which uses GF(2⁸)) and binary elliptic-curve cryptography (which uses large fields such as GF(2¹⁶³)…GF(2⁵⁷¹)).

Milestone 2 is the **backend brain** of the project. It does two jobs:

1. **Owns the multiplication engine** — the hardest of the six field operations — and produces a detailed trace so the GUI can *show* each step to a student.
2. **Is the API controller** — a web server exposing six HTTP endpoints that the GUI (Milestone 4) calls. Those endpoints also tie together the field registry + add/sub (Milestone 1) and the inverse + division (Milestone 3).

Because M1 and M3 aren't finished yet, M2 ships **self-contained reference versions** of their parts so the whole thing runs and can be graded today — and it isolates them behind a single file so swapping in the real code later is a one-line change per module.

---

## 2. Technology stack

| Technology | Role | Why it was chosen |
| :-- | :-- | :-- |
| **Python 3** | Implementation language | Python's arbitrary-precision integers (`int`) are perfect for GF(2^m): a field element up to 571 bits is just a normal integer, so bit-shifts and XOR work natively with no special big-number library. |
| **FastAPI** | Web framework (the 6 endpoints) | Modern, fast, and auto-generates interactive API docs (Swagger UI at `/docs`). Type hints become validation for free. |
| **Pydantic v2** | Request/response data models | Validates incoming JSON and defines the "shared data contracts" the four tracks agree on. Bad input is rejected automatically with a clear error. |
| **Uvicorn** | ASGI server | Runs the FastAPI app (`uvicorn app.main:app`). |
| **pytest + Starlette TestClient** | Test suite | TestClient calls the API in-process (no live server needed), so tests are fast and CI-friendly. 111 tests total. |

**Core idea that makes it simple:** every field element is stored as a Python integer where **bit *i* is the coefficient of xⁱ**. So:
- the polynomial `x⁶ + x⁴ + x + 1` → bits `0101 0011` → hex `0x53`,
- "add two elements" → `a ^ b` (XOR),
- "multiply by x" → shift left by one bit (`<< 1`).

This single representation choice is why the whole engine is short and fast.

---

## 3. The mathematics, operation by operation

Throughout, `m(x)` is the **reduction polynomial** (an irreducible polynomial of degree `m`) that defines the field. It's stored as a full integer *including* its xᵐ bit — e.g. the AES field's `x⁸ + x⁴ + x³ + x + 1` is `0x11b`.

### 3.1 Representation and conversion (`gf2m/polyrepr.py`)

Helpers convert one integer into its three display forms and back:
- `to_hex`, `to_bin` — zero-padded to the field width.
- `to_poly` — walks the set bits from high to low and prints `x^k` terms (`x^1`→`x`, `x^0`→`1`).
- `parse_value` — reads a hex or binary string back into an integer.
- `degree` = position of the highest set bit; `hamming_weight` = number of set bits.

Example: `0x53` → `01010011` → `x^6 + x^4 + x + 1`, degree 6, Hamming weight 4.

### 3.2 Addition and subtraction = XOR

Because coefficients live in ℤ₂ (integers mod 2), `1 + 1 = 0`. So adding two field elements is just a **bitwise XOR**, with no carries:

```
a(x) + b(x) = a ^ b
```

And since `+1` and `−1` are the same thing mod 2, **subtraction is identical to addition**. The result already has degree < m, so no reduction is needed.

### 3.3 Modulo reduction

Reduction brings any polynomial back down to degree < m. The algorithm: while the value's degree is ≥ m, line up `m(x)` under the top bit and XOR it away:

```python
while degree(value) >= m:
    shift = degree(value) - m
    value ^= mod_poly << shift
```

Each XOR cancels the current highest term and replaces it with the lower-degree "tail" of `m(x)`, so the degree strictly drops until it's below m.

### 3.4 Multiplication — shift-and-XOR (★ the core of this milestone)

To compute `c(x) = a(x) · b(x) mod m(x)`, we use the classic **shift-and-XOR** ("shift and add") method from Stallings Ch. 4. The intuition: multiplying a polynomial by `x` is a left shift; multiplying by `b(x)` means adding up `a(x)·xⁱ` for every bit `i` that is set in `b(x)`.

The algorithm keeps two things:
- `t` = a running copy of `a(x)·xⁱ mod m(x)` ("the shifted multiplicand")
- `result` = the accumulator (the running product)

For each bit of `b` from least-significant to most-significant:

```
if current bit of b is 1:   result ^= t        # add this partial product
t <<= 1                                          # multiply the multiplicand by x
if t now has an x^m term:   t ^= m(x)            # reduce it back into the field
```

Two things happen in parallel, which is exactly what the GUI visualises as **two tables**:

- **Table 1 — "shift / reduce":** the sequence of `t` values (`a·xⁱ mod m`), flagging each step where a reduction (`t ^= m(x)`) was needed.
- **Table 2 — "accumulate":** for each `1` bit of `b`, the current `t` is XORed into the accumulator; the accumulator after the last bit **is the product**.

**Worked example — `0x53 × 0xCA` in GF(2⁸)** (the AES textbook case; the answer is `0x01`):

`b = 0xCA = 11001010`, so bits 1, 3, 6, 7 are set — those are the four steps that "add".

| i | bit of b | `t = a·xⁱ mod m` | reduced? | added? | accumulator |
|---|----------|------------------|----------|--------|-------------|
| 0 | 0 | 53 | – | no | 00 |
| 1 | 1 | a6 | no | **yes** | a6 |
| 2 | 0 | 57 | **yes** | no | a6 |
| 3 | 1 | ae | no | **yes** | 08 |
| 4 | 0 | 47 | **yes** | no | 08 |
| 5 | 0 | 8e | no | no | 08 |
| 6 | 1 | 07 | **yes** | **yes** | 0f |
| 7 | 1 | 0e | no | **yes** | **01** |

Reading it: at `i=1`, `t=0x53` shifted to `0xa6` (no overflow, so no reduce) and because bit 1 of b is 1, it's XORed in → accumulator `a6`. At `i=2`, the shift *did* overflow past x⁸, so `t` was reduced by `0x11b` down to `57` (`reduced:true`), but bit 2 of b is 0 so nothing is added. Continuing to the last bit gives accumulator `0x01` — the final product.

The engine has **two entry points**:
- `multiply(...)` — fast, no trace (used for division, big fields, benchmarking).
- `multiply_traced(...)` — returns `(result, trace)` with every step recorded.

A performance detail: the loop stops once the remaining high bits of `b` are all zero, so a sparse multiplier in GF(2⁵⁷¹) still produces a short trace. The *result* is always computed fully; only the recorded trace is bounded (`max_steps`).

### 3.5 Multiplicative inverse — Extended Euclidean Algorithm

Every non-zero element has an inverse `b(x)⁻¹` such that `b(x)·b(x)⁻¹ ≡ 1 (mod m(x))`. We find it with the **Extended Euclidean Algorithm** over polynomials (Stallings Table 4.7). It runs the GCD of `b(x)` and `m(x)` while tracking the coefficients; since `m(x)` is irreducible, the GCD is `1`, and the tracked coefficient of `b(x)` at the end **is** the inverse:

```
(old_r, r) = (m(x), a)        # remainders
(old_s, s) = (0, 1)           # coefficients of a
while r != 0:
    q = old_r // r            # polynomial (carry-less) division quotient
    (old_r, r) = (r, old_r − q·r)
    (old_s, s) = (s, old_s − q·s)
# old_r == 1; inverse = old_s mod m(x)
```

In GF(2) arithmetic, "−" is XOR and "·" is a carry-less multiply, so the code uses `^` and `carryless_mul`. Supporting helpers: `_poly_divmod` (carry-less polynomial long division → quotient + remainder) and `carryless_mul` (XOR product with no reduction).

### 3.6 Division

Division reduces to the two operations above:

```
a(x) / b(x) = a(x) · b(x)⁻¹ mod m(x)
```

So we invert `b` (Extended Euclid) and multiply (shift-and-XOR).

### 3.7 Self-verification (the "live badges")

For the two hard operations, the backend re-checks its own answer and returns a pass/fail badge:
- **Inverse:** confirms `A(x) · A(x)⁻¹ mod m(x) = 1`.
- **Division:** confirms `(A/B) · B mod m(x) = A`.

This is what the project spec calls the "Live Verification badges," and it's a cheap guard that the engines agree with each other.

---

## 4. Software architecture

The code is layered so responsibilities are clean and the merge with other milestones is trivial.

```
milestone2/
├── gf2m/                      PURE MATH (no web framework here)
│   ├── multiply.py            ★ M2-OWNED: shift-and-XOR engine + step trace
│   ├── polyrepr.py            shared hex / binary / polynomial representations
│   └── _reference/            standalone stand-ins for the other tracks:
│       ├── fields.py          M1: field registry (NIST reduction polynomials)
│       ├── additive.py        M1: add / subtract / modulo
│       ├── randomops.py       M1: random operand generator
│       ├── parser.py          M1: batch .txt/.json operand parser
│       ├── formatter.py       M1: .md/.json export + hex share-token codec
│       ├── tutorial.py        M1: tutorial-slide loader
│       └── inverse_division.py  M3: Extended-Euclid inverse + division
├── app/                       WEB LAYER (FastAPI)
│   ├── main.py                ★ M2-OWNED: the 6 endpoints
│   ├── schemas.py             Pydantic request/response contracts
│   ├── services.py            /api/calculate dispatch + response assembly
│   └── providers.py           ← the single merge seam
├── data/tutorial_slides.json  the 4 tutorial slides
└── tests/                     pytest + TestClient suite (111 tests)
```

**Why this split:**
- The **`gf2m` package is pure math** — it knows nothing about HTTP. It can be imported and unit-tested on its own, and reused by any milestone.
- The **`app` package is the web layer**. It only validates input, maps errors to HTTP codes, and shapes JSON. All real work is delegated to `gf2m`.
- **`app/providers.py` is the one and only place** that names the M1/M3 modules. Everything else imports from `providers`, so integration later = repoint those imports. Nothing else changes.

```python
# app/providers.py  — the entire merge surface
from gf2m import multiply                        # M2 — keep
from gf2m._reference import (additive, fields,   # M1 — replace on merge
                             formatter, parser, randomops, tutorial)
from gf2m._reference import inverse_division as invdiv   # M3 — replace on merge
```

---

## 5. The six API endpoints

Base URL `http://127.0.0.1:8000`. Interactive docs at `/docs`.

### 5.1 `GET /api/fields`
Lists every supported field with its reduction polynomial in hex and algebraic form. Query `?include_textbook=false` returns only the six NIST crypto fields.

Supported fields: the six standard binary-curve fields **m ∈ {163, 233, 239, 283, 409, 571}** (using the NIST/SEC reduction polynomials, so they line up with the ECC material), plus the small textbook fields **2 ≤ m ≤ 8** (including AES's GF(2⁸)) for classroom checking.

### 5.2 `POST /api/calculate` — the main endpoint
Runs one of the six operations and returns a rich result. Request:

```jsonc
{
  "m": 163,
  "operation": "multiply",   // add | subtract | modulo | multiply | inverse | divide
  "a": "a3f1",
  "b": "1f",                 // required for add/subtract/multiply/divide
  "input_base": "hex",       // hex | bin
  "output_base": "hex",
  "trace": true
}
```

The response echoes **both operands in all three representations**, the result, the **step trace**, a **verification badge** (for inverse/divide), **metrics** (elapsed ms, bit length, Hamming weight), and a **share token**.

Operand conventions: `modulo` reduces `A` by `m(x)` (B ignored); `inverse` inverts the single operand `A`; `divide` computes `A/B`.

How it works internally (`app/services.py`): parse `A` (and `B` if the op needs it) → reduce them into the field → dispatch to the owning engine → time it with `time.perf_counter()` → build the three representations → attach a verification badge → encode a share token. Any domain problem (unsupported field, missing operand, inverting zero) is raised as a `CalculationError` and returned as **HTTP 400** with a readable message.

### 5.3 `POST /api/random-polynomials`
Generates random operands `A(x)`, `B(x)` for one-click testing. `density` can be `sparse` (few terms, easy to follow by hand), `dense` (~half the bits), or `random`. An optional `seed` makes it reproducible (the tests rely on this).

### 5.4 `POST /api/parse-polynomials`
Parses an uploaded operand file into a list of `{a, b, base}` pairs. Accepts **JSON** (`{"base":"hex","pairs":[...]}`, a single pair, or a bare array) and **plain text** (`A: …` / `B: …` blocks separated by `---`, with `#` comments). The GUI reads a file and POSTs its contents here.

### 5.5 `POST /api/export-calculation`
Turns a completed calculation into a downloadable **Markdown** or **JSON** summary. With `"download": true` it streams the file with a `Content-Disposition: attachment` header; otherwise it returns the content as a string the GUI can save.

### 5.6 `GET /api/tutorial`
Serves the 4-slide guided tutorial (GF(2^m) basics → three representations → addition as XOR → multiplication as shift-and-XOR) from `data/tutorial_slides.json`.

Plus two meta routes: `GET /` (service info) and `GET /api/health` (returns `{"status":"ok"}`).

### The share token
`/api/calculate` returns a compact hexadecimal token encoding `version | m | operation | a | b | output_base`. It's the string `"v1|163|multiply|…"` encoded to hex. `parse_share_token` reverses it, so a URL can reload the exact scenario — **including the chosen display base** — which is the "shareable calculation link" feature in the spec.

---

## 6. The multiplication trace format (what the GUI renders)

`multiply_traced` returns a structured object. Each step carries everything both visualizer tables need:

| field | meaning | feeds |
| :-- | :-- | :-- |
| `multiplier_bit` | bit *i* of `b` | both |
| `partial_hex` / `partial_poly` | `a·xⁱ mod m(x)` | **Table 1** |
| `reduced` | was this partial formed by an `^ m(x)` reduction? | Table 1 flag |
| `added` | was this partial XORed into the accumulator? | **Table 2** |
| `accumulator_hex` | running product after this step | Table 2 |

Plus a `summary` with the total number of reductions and partial products (for the complexity badges), and a `truncated` flag if a huge dense trace was capped.

---

## 7. Testing (111 tests, all passing)

The suite proves correctness independently rather than trusting the engine against itself:

- **Engine correctness** — every product is cross-checked against an *independent* brute force (full carry-less multiply, then reduce) across all 13 fields, plus the known AES case `0x53·0xCA = 0x01`, plus agreement between the fast and traced paths.
- **Field algebra laws** — identity, zero, commutativity, associativity, and distributivity on the small fields.
- **Trace integrity** — XOR-ing the "added" partials reconstructs the product; every result stays inside the field (degree < m).
- **Inverse / division** — `a·a⁻¹ = 1` and `(a/b)·b = a` on every field; inverting zero and dividing by zero raise errors.
- **All six endpoints** through the TestClient, including the error paths (missing operand → 400, unsupported field → 400, zero inverse → 400) and a share-token round-trip.
- **An 8-row verification matrix** spanning every NIST field — the end-to-end check that anticipates the Milestone 5 sign-off.

Run them with `pytest` from the project folder.

---

## 8. How to run it

```bash
# 1. install dependencies
pip install -r requirements.txt

# 2. run the tests (optional, proves everything works)
pytest

# 3. start the server
uvicorn app.main:app --reload --port 8000
#    then open http://127.0.0.1:8000/docs  (interactive UI for all endpoints)
```

On Windows, the easiest way to try a request is the `/docs` page (click **Try it out** on any endpoint). From PowerShell you can also use `Invoke-RestMethod` instead of `curl`.

---

## 9. Integration & merge guide (for Milestone 5)

Only `app/providers.py` names the other tracks. To integrate, repoint each reference import at the real M1/M3 module. As long as they honour the same function signatures, **no endpoint, schema, or test changes.** The contracts are:

- **M1 fields:** `is_supported(m)`, `get_field(m) -> Field(m, mod_poly, category, name)`, `list_fields(include_textbook)`.
- **M1 additive:** `add/subtract(a,b,mod,m)`, `modulo(a,mod,m)`, `xor_trace(a,b,m)`.
- **M1 randomops:** `generate_operand(m, density, seed)`.
- **M1 parser:** `parse_operand_file(content, filename, default_base)`.
- **M1 formatter:** `render(calc, fmt)`, `make_share_token(...)`, `parse_share_token(token)`.
- **M1 tutorial:** `load_tutorial()`.
- **M3 invdiv:** `inverse(a,mod,m,with_trace)`, `divide(a,b,mod,m,with_trace)`, `NoInverseError`.

> Note: the reduction polynomials in `_reference/fields.py` are the NIST/SEC ones for the binary curve fields. If M1's registry defines them differently, M1's version wins on merge.

# Milestone 2 — Multiplication Engine & Backend API Controller

**Project:** Polynomial Arithmetic in GF(2^m) — EECE 455/632 Project-3
**Milestone owner deliverables:** Shift-and-XOR multiplication engine with step
trace · 6-endpoint FastAPI backend controller · `pytest` + `TestClient` suite.

This milestone is the **integration hub** of the project: it owns the
multiplication engine and the HTTP API that the GUI (M4) talks to, and it wires
together the field registry and additive engine (M1) and the inverse/division
engine (M3). It is built to run and be graded **standalone today**, and to
**merge cleanly** once the other tracks land — see
[Integration & Merge Guide](#integration--merge-guide).

---

## Quick start

```bash
pip install -r requirements.txt

# run the test suite (111 tests)
pytest

# start the API  ->  http://127.0.0.1:8000  (Swagger UI at /docs)
./run.sh        # or: uvicorn app.main:app --reload
```

---

## What's in the box

```
milestone2/
├── gf2m/
│   ├── multiply.py          ★ M2-OWNED shift-and-XOR engine + step trace
│   ├── polyrepr.py            shared hex/bin/polynomial representations
│   └── _reference/            standalone shims so M2 runs alone (swap on merge)
│       ├── fields.py          M1: field registry (NIST reduction polynomials)
│       ├── additive.py        M1: add / subtract / modulo
│       ├── randomops.py       M1: random operand generator
│       ├── parser.py          M1: batch .txt/.json operand parser
│       ├── formatter.py       M1: .md/.json export + hex share-token codec
│       ├── tutorial.py        M1: tutorial-slide loader
│       └── inverse_division.py  M3: Extended-Euclid inverse + division
├── app/
│   ├── main.py              ★ M2-OWNED FastAPI app — the 6 endpoints
│   ├── schemas.py             Pydantic request/response contracts
│   ├── services.py            /api/calculate dispatch + response assembly
│   └── providers.py           ← single merge seam (see below)
├── data/tutorial_slides.json
├── tests/                     pytest + TestClient suite
└── requirements.txt · pytest.ini · run.sh
```

---

## The multiplication engine (M2-owned)

`gf2m/multiply.py` computes `c(x) = a(x)·b(x) mod m(x)` by the classic
shift-and-XOR method (Stallings Ch. 4). Elements are Python ints (bit *i* =
coefficient of x^i); the reduction polynomial includes its x^m term.

Two entry points:

- `multiply(a, b, mod_poly, m)` — fast path, no trace (used by division,
  benchmarking, and large fields).
- `multiply_traced(a, b, mod_poly, m)` — returns `(result, MultiplyTrace)`.

The trace feeds the GUI's two visualizer tables. Each recorded step carries:

| field | meaning | drives |
| :-- | :-- | :-- |
| `partial_hex` / `partial_poly` | `a·x^i mod m(x)` | **Table 1** (shift/reduce) |
| `reduced` | was this value formed by XOR-ing m(x)? | Table 1 flag |
| `multiplier_bit` / `added` | bit *i* of b; was the partial XORed in? | **Table 2** |
| `accumulator_hex` | running product after this step | Table 2 |

The loop stops once the remaining high bits of `b` are zero, so sparse
multipliers stay cheap even in GF(2^571); `max_steps` bounds recorded rows
(`trace.truncated` flags when a huge dense trace was capped) without ever
affecting the result.

---

## API reference

Base URL `http://127.0.0.1:8000`. Interactive docs at `/docs`.

| Method | Path | Purpose |
| :-- | :-- | :-- |
| GET  | `/api/fields` | list supported fields (`?include_textbook=false` for NIST only) |
| POST | `/api/calculate` | run one of the six operations |
| POST | `/api/random-polynomials` | generate random `A(x)`, `B(x)` |
| POST | `/api/parse-polynomials` | parse an uploaded `.txt`/`.json` operand file |
| POST | `/api/export-calculation` | render a `.md`/`.json` summary (`download:true` streams a file) |
| GET  | `/api/tutorial` | the 4-slide guided tutorial |

### `/api/calculate`

```jsonc
// request
{
  "m": 163,
  "operation": "multiply",      // add|subtract|modulo|multiply|inverse|divide
  "a": "a3f1",
  "b": "1f",                    // required for add/subtract/multiply/divide
  "input_base": "hex",          // hex|bin
  "output_base": "hex",
  "trace": true
}
```

The response echoes both operands in all three representations, the result, the
step trace, a self-verification badge where meaningful
(`A·A⁻¹ = 1`; `(A/B)·B = A`), timing/bit-length/Hamming-weight metrics, and a
hex `share_token` that reloads the exact scenario (including display base).

**Operand conventions:** `modulo` reduces `A` by `m(x)` (`B` ignored);
`inverse` inverts the single operand `A`; `divide` computes `A/B = A·B⁻¹`.

---

## Integration & Merge Guide

The API and service layers import **only** from `app/providers.py`. That file is
the entire merge surface:

```python
# app/providers.py
from gf2m import multiply                       # M2 — keep
from gf2m._reference import (additive, fields,  # M1 — replace on merge
                             formatter, parser, randomops, tutorial)
from gf2m._reference import inverse_division as invdiv  # M3 — replace on merge
```

To integrate, repoint each reference import at the real module from M1/M3. As
long as the replacements honour the same small function contracts, **nothing
else changes** — not the endpoints, not the schemas, not the tests.

Contracts the shims define (and that M1/M3 must match):

- **M1 fields:** `is_supported(m)`, `get_field(m) -> Field(m, mod_poly, category, name)`, `list_fields(include_textbook)`.
- **M1 additive:** `add/subtract(a,b,mod,m)`, `modulo(a,mod,m)`, `xor_trace(a,b,m)`.
- **M1 randomops:** `generate_operand(m, density, seed)`.
- **M1 parser:** `parse_operand_file(content, filename, default_base) -> [{a,b,base}]`.
- **M1 formatter:** `render(calc, fmt)`, `make_share_token(...)`, `parse_share_token(token)`.
- **M1 tutorial:** `load_tutorial() -> {version,title,slides}`.
- **M3 invdiv:** `inverse(a,mod,m,with_trace=False)`, `divide(a,b,mod,m,with_trace=False)`, `NoInverseError`.

> The NIST/SEC reduction polynomials in `_reference/fields.py` match the binary
> curve fields (B-/K- curves); if M1's registry differs, M1's wins on merge.

---

## Tests

`pytest` → **111 tests**, covering:

- **engine correctness** — every result cross-checked against an *independent*
  brute-force (carry-less multiply + reduce) across all 13 fields; traced vs
  fast path agreement; the known AES case `0x53·0xCA = 0x01`.
- **field algebra** — identity, zero, commutativity, associativity,
  distributivity on the textbook fields.
- **trace integrity** — Table 2 reconstructs the product; results stay in-field.
- **inverse/division** — `a·a⁻¹ = 1` and `(a/b)·b = a` across every field;
  zero-inverse and divide-by-zero raise.
- **all six endpoints** via `TestClient`, including error paths (missing
  operand, unsupported field, zero inverse) and share-token round-trip.
- **8-row verification matrix** spanning every NIST field — the end-to-end
  check that anticipates the M5 sign-off.

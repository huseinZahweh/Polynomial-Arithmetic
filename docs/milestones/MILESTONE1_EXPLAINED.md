# Milestone 1 — Field Configuration, Multi-Base I/O, Additive/Modulo Engine & Utilities

**Project:** EECE 455 — Project-3: Polynomial Arithmetic in $GF(2^m)$  
**Assigned Owner:** Hussein Abbas  
**Unified Code Locations:** [backend/engine/fields.py](../../backend/engine/fields.py), [backend/engine/polyrepr.py](../../backend/engine/polyrepr.py), [backend/engine/additive.py](../../backend/engine/additive.py), [backend/engine/randomops.py](../../backend/engine/randomops.py), [backend/engine/parser.py](../../backend/engine/parser.py), [backend/engine/formatter.py](../../backend/engine/formatter.py), [backend/engine/tutorial.py](../../backend/engine/tutorial.py), and [data/tutorial_slides.json](../../data/tutorial_slides.json)  
**Textbook References:** William Stallings, *Cryptography and Network Security*, **Chapter 4** (Finite Fields), **Chapter 5** (AES), **Chapter 6** (XTS-AES over $GF(2^{128})$), and **Chapter 10** (Binary Elliptic Curve Cryptography over $GF(2^{163}) \dots GF(2^{571})$).

---

## 1. Field Registry & Polynomial Representation

`backend.engine.fields.get_field(m)` returns an immutable `Field(m, mod_poly, category, name)` entry in $O(1)$ time. The registry constructs each bitmask directly from the canonical tap lists in the [Milestone 1 plan](../../Plan/Milestones/01_field_config_io_additive_mod_and_utilities.md), using the EECE 455 Project-2 irreducible moduli for $2 \le m \le 8$ (including $x^3 + x^2 + 1$, $x^4 + x^3 + 1$, and the AES polynomial $x^8 + x^4 + x^3 + x + 1$) and the six standard NIST/SEC binary ECC moduli for $m \in \{163, 233, 239, 283, 409, 571\}$ (with $m = 163$ as `DEFAULT_DEGREE`).

Every polynomial is encoded as a non-negative Python `int` where bit $i$ (LSB $= 0$) equals the coefficient $c_i \in \{0, 1\}$ of $x^i$, and the reduction modulus $m(x)$ includes bit $m$ set to $1$:

$$
m_{\text{int}} = \sum_{k \in T} 2^k
$$

| Function (`backend/engine/polyrepr.py`) | Behavior |
| :--- | :--- |
| `BIN_TO_INT(text)`, `HEX_TO_INT(text)` | Parses binary or hex strings into non-negative `int` bitmasks, allowing whitespace digit grouping, optional `0b`/`0x` prefixes, and matching outer braces `\{...\}` while rejecting signs (`+`/`-`) and underscores. |
| `ALGEBRAIC_TO_INT(text)` | Stretch parser accepting algebraic monomial sums such as `x^7 + x + 1` (cancelling duplicate terms modulo 2 via XOR and capping exponents below $4096$). |
| `parse_value(text, base)` | Strict REST API parser for `"hex"`, `"bin"`/`"binary"`, and `"algebraic"` rejecting embedded whitespace in hex/binary inputs. |
| `INT_TO_BIN(value, m)`, `INT_TO_HEX(value, m)` | Zero-pads binary output to at least $m$ bits and uppercase hex to at least $\lceil m / 4 \rceil$ digits, retaining unreduced overflow bits without truncation. |
| `INT_TO_ALGEBRAIC(value)` | Formats set bits as descending powers of $x$ (e.g., `x^6 + x^4 + x^2 + x + 1`), returning `"0"` for the zero polynomial. |
| `DEG(value)`, `HAMMING_WEIGHT(value)` | Returns highest set-bit index ($-1$ for $0$) and total count of nonzero terms. |
| `ElementRepr.from_int(value, m)` | Produces the lowercase `hex`, `bin`, `poly`, `degree`, `bit_length`, and `hamming_weight` dictionary consumed by the REST API. |

---

## 2. Additive Arithmetic & Modulo Reduction

In `backend/engine/additive.py`:

* **`MOD_REDUCE(f_int, m_poly_int, m_degree)`** returns `(reduced_int, trace_dict)` with `trace_type="mod_reduce"`. While $\deg(r) = d \ge m$, it eliminates the leading $x^d$ term by XORing $r$ with $m(x) \ll (d - m)$, logging `target_degree`, `shift`, `before`, `reducer`, and `after` at each step. At most $\max(0, d - m + 1)$ shifted XORs are needed.
  * Stallings Chapter 5 example: reducing `0x10E` modulo `0x11B` yields `0x15` in one step. Reducing $m(x)$ itself yields `0` in one step.
* **`GF2M_ADD_SUB(f_int, g_int, m_poly_int, m_degree)`** reduces both operands modulo $m(x)$, computes $(f \bmod m) \oplus (g \bmod m)$, and returns both pre-reduction traces alongside bit-aligned `columns` and formatted `rows`. Because $GF(2^m)$ has characteristic 2, addition and subtraction are identical:

$$
\{57\} \oplus \{83\} = \{\text{D4}\} \quad (\text{01010111}_2 \oplus \text{10000011}_2 = \text{11010100}_2)
$$

* Fast-path helpers `modulo`, `add`, and `subtract` reuse the exact same reduction kernel without allocating trace dictionaries, while `xor_trace` generates aligned columns for already-reduced operands.

---

## 3. Classroom Utilities & Tutorial Data

* **Random Operand Generator ([randomops.py](../../backend/engine/randomops.py)):** `GENERATE_RANDOM_POLY(m, sparsity, seed=...)` samples uniformly from $[1, 2^m - 1]$ in dense mode or selects $3$ to $6$ distinct bit positions (clamped for small $m$) in sparse mode. Uses `secrets.SystemRandom()` by default and `random.Random(seed)` when deterministic vectors are requested.
* **Batch Polynomial File Parser ([parser.py](../../backend/engine/parser.py)):** `parse_operand_file(content, filename, default_base)` extracts validated `{"a", "b", "base"}` records from `.json` (single pair, bare array, or `{"base", "pairs"}`) and `.txt` (`A:`/`B:`/`base:` blocks separated by `---` or `===`, supporting `#` comments). Invalid inputs raise `OperandFileError` carrying `.pair`, `.line`, and `.field`.
* **Summary Exporter & Share Tokens ([formatter.py](../../backend/engine/formatter.py)):** `render(calc, fmt)` produces downloadable Markdown (`.md`) or indented JSON (`.json`) summaries with sanitized filenames. `make_share_token` / `parse_share_token` encode and decode versioned lowercase-hex `v1` calculation snapshots.
* **Tutorial Loader ([tutorial.py](../../backend/engine/tutorial.py)):** `load_tutorial()` reads [data/tutorial_slides.json](../../data/tutorial_slides.json) independently of working directory, delivering 4 structured slides (including Extended Euclid's $B_3(x) = 1$ and $B_3(x) = 0$ termination cases) and the Chapter 4/5 presets.

---

## 4. Unified Test Coverage

All original Milestone 1 tests are now integrated under the root test suite:

* [tests/engine/test_fields_and_polyrepr.py](../../tests/engine/test_fields_and_polyrepr.py): All 13 field definitions, binary/hex round trips across $m \in \{8, 163, 571\}$, strict vs. grouped parsing, and malformed input rejection.
* [tests/engine/test_additive.py](../../tests/engine/test_additive.py): Chapter 4 XOR rows, Chapter 5 AES reduction, unreduced pre-reduction traces, and modulus cancellation / self-inverse identities across all 13 fields.
* [tests/engine/test_utilities_and_tutorial.py](../../tests/engine/test_utilities_and_tutorial.py): Sparse/dense random sampling, `.txt`/`.json` batch parsing & error locations, Markdown/JSON exports, `v1` share-token compatibility, and tutorial preset verification.

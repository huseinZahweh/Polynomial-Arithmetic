# Milestone 1 — Technical Reference

## 1. Field registry and representation

`fields.get_field(m)` returns a `Field` with `m`, `mod_poly`, `category`, and `name`. The registry builds each mask from the taps in the [Milestone 1 plan](../Plan/Milestones/01_field_config_io_additive_mod_and_utilities.md). It uses the project handout's small-field moduli, including `x^3 + x^2 + 1` and `x^4 + x^3 + 1`. Degree lookup is constant time. The `nist` category is the current API label for the six larger fields, including the SEC degree-239 field.

| Function | Result |
| --- | --- |
| `BIN_TO_INT(text)`, `HEX_TO_INT(text)` | An integer bitmask. These accept digit grouping with whitespace, optional base prefixes, and matching outer braces. |
| `INT_TO_BIN(value, m)`, `INT_TO_HEX(value, m)` | Binary padded to at least `m` bits or uppercase hex padded to at least `ceil(m / 4)` digits. Both preserve unreduced high terms. |
| `INT_TO_ALGEBRAIC(value)` | Descending polynomial terms, such as `x^6 + x^4 + x^2 + x + 1`. |
| `DEG(value)`, `HAMMING_WEIGHT(value)` | The highest set-bit index and the number of set bits. The zero polynomial has degree −1 and weight 0. |

The lowercase adapters in `polyrepr.py` retain the current backend's lowercase hex, strict input parsing, and `ElementRepr` fields. Chapter 4 explains the polynomial basis, Chapter 5 supplies the AES field example, and Chapters 6 and 10 illustrate the same representation in XTS-AES and binary elliptic curves.

## 2. Additive arithmetic and reduction

`MOD_REDUCE(f_int, m_poly_int, m_degree)` returns a remainder and a `mod_reduce` trace dictionary. At each step, the leading term of degree `d` is canceled by XOR with `m_poly_int << (d - m_degree)`. Each step records `target_degree`, `shift`, `before`, `reducer`, and `after`. The trace also records the initial and reduced values, modulus, degree, and step count.

In the Chapter 5 AES example, reducing `0x10E` modulo `0x11B` gives `0x15` in one step. Reducing the modulus itself gives zero with one step. An already reduced input has an empty step list. Reduction requires at most `max(0, d - m + 1)` shifted XORs because each step strictly decreases the remainder's degree.

`GF2M_ADD_SUB(f_int, g_int, m_poly_int, m_degree)` reduces both operands and XORs the remainders. The trace includes `f_mod_trace`, `g_mod_trace`, aligned binary columns, and `rows` in binary, hex, and algebraic form. For `0x57 XOR 0x83` the result is `0xD4`, or `x^7 + x^6 + x^4 + x^2`. As Chapter 4 explains, the same XOR produces addition and subtraction in characteristic two.

The scalar `add`, `subtract`, and `modulo` functions use the same reduction logic. `xor_trace` builds the XOR rows for operands the caller has already reduced.

## 3. Classroom utilities

- `randomops.GENERATE_RANDOM_POLY(m, sparsity, seed=...)` samples uniformly from `[1, 2^m - 1]` in dense mode. Sparse mode chooses three to six distinct exponents, with smaller bounds for the smallest fields. The generator uses OS randomness by default and accepts a seed for repeatable examples. The backend's `random` density maps to the uniform mode.
- `parser.parse_operand_file(content, filename, default_base)` returns a list of `{"a", "b", "base"}` records with `hex` or `bin` as the normalized base. The base may be set for a batch or an individual pair. A is required, and a missing B becomes an empty string for unary operations. Malformed uploads raise `OperandFileError` with the applicable pair number, line number, and field.
- `formatter.render(calc, fmt)` returns content, filename, and media type for `md` or `json`. The JSON report preserves the calculation payload. Markdown presents the field, operands, result, and any verification, metrics, educational trace, or share token in the payload. The share-token codec preserves the backend's v1 format.
- `tutorial.load_tutorial()` loads four slides on field elements, modulo reduction, multiplication and inversion, and worked examples. The fourth slide carries the Chapter 4 and 5 presets using the backend's calculation request keys.

An example JSON batch follows.

```json
{
  "base": "hex",
  "pairs": [
    {"a": "57", "b": "83"},
    {"a": "95"}
  ]
}
```

A TXT upload can express the same batch. The parser also accepts `=` in place of `:` and `===` as a separator.

```text
base: hex
A: 57
B: 83
---
A: 95 # Unary inverse example
```

## 4. Verification and Milestone 5 handoff

The standalone suite checks the 13 modulus definitions, binary and hex round trips, textbook XOR and AES reduction, per-step trace consistency, invalid inputs, random sampling bounds, operand files, exports, and tutorial preset arithmetic.

The modules `fields`, `additive`, `randomops`, `parser`, `formatter`, and `tutorial` provide the interfaces expected by [Milestone 2's provider module](../milestone2/milestone2/app/providers.py). Its services also use `polyrepr` directly. During [Milestone 5](../Plan/Milestones/05_end_to_end_integration_and_verification.md), pass the original operands to the traced Milestone 1 operations so the API can expose any pre-reduction steps. Presets are part of slide 4 and fit the current tutorial response's list of slide dictionaries.

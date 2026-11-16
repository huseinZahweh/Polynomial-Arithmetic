# Milestone 1 — Field Configuration, Additive Arithmetic & Utilities

**Project** · EECE 455/632 Project-3, Polynomial Arithmetic in GF(2^m)  
**Owner** · Hussein Abbas

Milestone 1 provides the field registry, binary and hex input, three output formats, traced addition/subtraction and modulo reduction, classroom utilities, and tutorial data. It uses the team's polynomial bitmask contract. Bit `i` of a non-negative integer is the coefficient of `x^i`, and the modulus includes the leading bit `m`.

## Quick start

Run from `milestone1/` with Python 3.10 or later. The package uses the standard library. Pytest is the only test dependency.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest
```

```python
from gf2m_m1 import GF2M_ADD_SUB, HEX_TO_INT, INT_TO_HEX, get_field

field = get_field(8)
result, trace = GF2M_ADD_SUB(
    HEX_TO_INT("{57}"), HEX_TO_INT("{83}"), field.mod_poly, field.m
)
assert INT_TO_HEX(result, field.m) == "D4"
assert trace["result_bin"] == "11010100"
```

## Layout

```text
milestone1/
├── gf2m_m1/
│   ├── __init__.py
│   ├── additive.py
│   ├── fields.py
│   ├── formatter.py
│   ├── parser.py
│   ├── polyrepr.py
│   ├── randomops.py
│   └── tutorial.py
├── data/tutorial_slides.json
├── tests/
│   ├── test_additive.py
│   ├── test_fields_and_polyrepr.py
│   ├── test_tutorial.py
│   └── test_utilities.py
├── .gitignore
├── MILESTONE1_EXPLAINED.md
├── README.md
├── pytest.ini
└── requirements.txt
```

The primary field is `m = 163`. The registry also provides degrees 233, 239, 283, 409, and 571 and the classroom degrees 2 through 8. The degree-8 field uses the AES modulus `0x11B`.

See [MILESTONE1_EXPLAINED.md](./MILESTONE1_EXPLAINED.md) for trace fields, upload formats, and the Milestone 5 handoff.

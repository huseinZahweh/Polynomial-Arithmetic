"""Single integration seam between the Milestone 2 backend and the other tracks.

The API and service layers import *only* from here, never from M1/M3 modules
directly. That keeps the merge to one file: when the real milestones land,
repoint the bindings below and nothing else in ``app/`` changes.

    Current binding            ->   Replace on merge with
    ----------------------------    ---------------------------------
    multiply   (M2, permanent)      (keep — this is Milestone 2's engine)
    fields     (reference)          Milestone 1 field registry
    additive   (reference)          Milestone 1 additive/modulo engine
    randomops  (reference)          Milestone 1 random operand generator
    parser     (reference)          Milestone 1 batch file parser
    formatter  (reference)          Milestone 1 summary formatter + share codec
    tutorial   (reference)          Milestone 1 tutorial slides
    invdiv     (reference)          Milestone 3 inverse + division engine
"""
from __future__ import annotations

# Milestone 2 — owned, permanent.
from gf2m import multiply  # noqa: F401

# Milestone 1 / Milestone 3 — reference shims (swap on merge).
from gf2m._reference import additive, fields, formatter, inverse_division as invdiv
from gf2m._reference import parser, randomops, tutorial  # noqa: F401

"""GF(2^m) arithmetic package.

Ownership
---------
* ``multiply``  — Milestone 2 (shift-and-XOR engine + step trace).
* ``polyrepr``  — shared representation helpers.
* ``_reference``— standalone reference implementations of Milestone 1 (field
  registry, additive ops, random generator, file parser, summary formatter,
  tutorial) and Milestone 3 (inverse, division). These let M2 run and be
  graded on its own; see ``app/providers.py`` for the single merge swap point.
"""

from . import multiply, polyrepr  # noqa: F401

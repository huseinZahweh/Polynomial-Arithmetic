"""Backend package for the EECE 455/632 GF(2^m) Polynomial Arithmetic platform.

Combines the pure-Python finite-field arithmetic engines (:mod:`backend.engine`)
with the FastAPI REST controller and static workbench host (:mod:`backend.api`).

Team Attribution
----------------
* **Hussein Abbas (Milestone 1):** Field registry, multi-base I/O converters,
  additive/modulo engine, random operands, batch parser, exporter, tutorial data.
* **Hassan Tarhini (Milestone 2):** Shift-and-XOR multiplication engine and core
  6-endpoint FastAPI backend controller.
* **Husein Zahweh (Milestone 3):** Carry-free multiplication, polynomial long
  division, Extended Euclid Table 4.7 inverse, two-stage field division, live
  self-verifiers, and multi-field benchmarks.
* **Ali Zahreddine (Milestone 4 & Integration):** Educational web workbench,
  step visualizers, interactive tours, bonus exploration tools, and end-to-end
  system integration.
"""

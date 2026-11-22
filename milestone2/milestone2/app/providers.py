"""Select the integrated engines, with a fallback for the standalone milestone."""

from importlib.util import find_spec

from gf2m import multiply


if find_spec("gf2m_m1") and find_spec("gf2m_m3"):
    from gf2m_m1 import additive, fields, formatter, parser, polyrepr, randomops, tutorial
    from . import integrated_inverse as invdiv
else:
    from gf2m import polyrepr
    from gf2m._reference import additive, fields, formatter, inverse_division as invdiv
    from gf2m._reference import parser, randomops, tutorial

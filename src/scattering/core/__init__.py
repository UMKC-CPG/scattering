"""Foundations shared by every stage: natural units, the units
boundary, and the named real-unit presets.

Governed by pseudocode section 1 (dev/pseudocode/01-natural-units.md)
and design section 1. Everything inside the library works in the
natural units defined here; real units enter and leave only through
`units.py`, which is the single module allowed to import pint
(ARCHITECTURE section 6.6).
"""

"""Regression tests: frozen reference outputs that must not change.

Each test compares a freshly computed result against a stored file in
`reference_outputs/`. Regenerating a reference is a deliberate
act: it asserts that the new answer is the correct one, so it
belongs in its own commit, with the reason in the message, and never folded into
an unrelated change.
"""

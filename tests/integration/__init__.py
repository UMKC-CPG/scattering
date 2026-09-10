"""Integration tests: several modules together, or a whole entry
point run end to end.

These may touch the filesystem. Depend on the `run_directory` fixture from
conftest.py so that output lands in a temporary directory rather than in the
repository.
"""

"""engine — internal package backing the meta-repo engine.

This package is split by natural seam for maintainability:
  * roster.py   — meta-repo.yaml persistence (tiny hand-rolled YAML I/O)
  * git_ops.py  — git/filesystem subprocess helpers
  * scaffold.py — doc scaffold templates + symlink management
  * commands.py — CLI command implementations

The public, user-facing entrypoint is the sibling script `../meta-repo.py`
(hyphenated, not importable as a package member), which imports and
re-exports the names below and wires up argparse. See that file's module
docstring for the full "Design rules this script obeys" contract.

Not meant to be imported directly by anything other than `../meta-repo.py`.
"""
from __future__ import annotations

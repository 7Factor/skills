#!/usr/bin/env python3
"""meta-repo engine — the mechanical core of the meta-repo skill.

A "meta-repo" is a lightweight git repository that DEFINES and DOCUMENTS a
working set of several independent git repositories (a.k.a. workspace
repository; formerly "pseudo-monorepo"). Members are referenced by relative
symlinks; this engine keeps on-disk reality in sync with the roster declared
in `meta-repo.yaml`.

Design rules this script obeys (do not violate when editing):
  * `meta-repo.yaml` is written ONLY by this script (init/add/remove). Because
    this script is the sole writer, reading it back is safe string work — we do
    NOT depend on PyYAML or yq, and there is exactly ONE yaml mechanism here.
  * The script NEVER commits child-repo code and NEVER deletes a real clone.
  * `sync` ACTS on structure (clone missing, fix symlinks). `doctor` only
    REPORTS. `heal` fixes safe hygiene only and is additive to CLAUDE.md.
  * No third-party imports. Python 3.8+ stdlib only. Fully non-interactive —
    all interviewing/judgment is the agent's job (see ../SKILL.md).

Stdlib only. Run:  python3 scripts/meta-repo.py <command> [options]

This file is a thin entrypoint: it wires up argparse and dispatches to the
`engine` package sitting beside it (`scripts/engine/`), which holds the
actual implementation split by seam:
  * engine/roster.py   — meta-repo.yaml persistence (tiny hand-rolled YAML I/O)
  * engine/git_ops.py  — git/filesystem subprocess helpers
  * engine/scaffold.py — doc scaffold templates + symlink management
  * engine/commands.py — the `cmd_*` CLI command implementations

`meta-repo.py` is hyphenated because that's the documented, invoked command
name (`python3 scripts/meta-repo.py <command>`) — a hyphen can't be part of a
Python import path, so the implementation lives in the importable `engine`
package next to it instead.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# Loading this file directly as a script already puts its directory on
# sys.path (CPython does this for the script's own dir), but the test suite
# loads it via importlib.util.spec_from_file_location, which does NOT — so we
# make the sibling `engine` package importable either way.
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from engine.roster import (  # noqa: E402
    META_REPO_VERSION,
    VALID_STATUS,
)
from engine.git_ops import (  # noqa: E402
    die,
)
from engine.commands import (  # noqa: E402
    cmd_init,
    cmd_add,
    cmd_remove,
    cmd_sync,
    cmd_update,
    cmd_doctor,
    cmd_heal,
    cmd_manifest,
    cmd_docs,
)


# ----------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(prog="meta-repo", description="meta-repo engine")
    p.add_argument("--version", action="version", version=f"meta-repo {META_REPO_VERSION}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create a meta-repo in the current dir (adopts existing symlinks)")
    s.add_argument("--name")
    s.add_argument("--description")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("add", help="add a member (by --path or --remote)")
    s.add_argument("--name")
    s.add_argument("--path", help="relative path, e.g. ../api")
    s.add_argument("--remote", help="git URL; clones if not present")
    s.add_argument("--role")
    s.add_argument("--status", choices=VALID_STATUS)
    s.set_defaults(func=cmd_add)

    s = sub.add_parser("remove", help="remove a member (never deletes the real clone)")
    s.add_argument("name")
    s.set_defaults(func=cmd_remove)

    for nm, fn, h in [
        ("sync", cmd_sync, "reconcile disk to yaml: clone missing, fix symlinks"),
        ("doctor", cmd_doctor, "report health (read-only)"),
        ("heal", cmd_heal, "fix safe hygiene (additive to CLAUDE.md)"),
        ("manifest", cmd_manifest, "emit roster + computed state as JSON"),
    ]:
        sp = sub.add_parser(nm, help=h)
        sp.set_defaults(func=fn)

    s = sub.add_parser("update", help="fetch + fast-forward every member (and the meta-repo) to latest trunk")
    s.set_defaults(func=cmd_update)

    s = sub.add_parser("docs", help="scaffold docs if absent, else report drift")
    s.add_argument("--force", action="store_true", help="overwrite scaffolds (destructive to prose)")
    s.set_defaults(func=cmd_docs)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    # Every command shells out to git; fail with a clear message rather than an
    # uncaught FileNotFoundError from a raw subprocess spawn (init/clone).
    if shutil.which("git") is None:
        die("`git` was not found on PATH — the engine needs it. Install git (or fix PATH) and retry.")
    args.func(args)


if __name__ == "__main__":
    main()

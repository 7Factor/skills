"""git_ops.py — low-level git/filesystem subprocess helpers.

Nothing in this module ever commits child-repo code or deletes a real clone;
those invariants are enforced at the command layer (commands.py), which is
the only layer that decides *when* to call these.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .roster import YAML_NAME


def _git(args, cwd) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except Exception:
        return None


def is_git_repo(path: Path) -> bool:
    return path.is_dir() and _git(["rev-parse", "--git-dir"], path) is not None


def ensure_git_repo(root: Path) -> bool:
    """`git init` the meta-repo root if it isn't a git repo yet.

    A meta-repo is a git repo by definition (teammates clone it, then `sync`).
    Returns True iff this call created the repo. Never commits anything.
    """
    if (root / ".git").exists():
        return False
    subprocess.run(["git", "init"], cwd=str(root), capture_output=True, text=True)
    return (root / ".git").exists()


def remote_url(path: Path) -> str:
    return _git(["remote", "get-url", "origin"], path) or ""


def default_branch(path: Path) -> str:
    ref = _git(["symbolic-ref", "refs/remotes/origin/HEAD"], path)
    if ref:
        return ref.rsplit("/", 1)[-1]
    local = _git(["rev-parse", "--abbrev-ref", "HEAD"], path)
    # "HEAD" here means detached — not a real branch name; never leak it into the roster.
    return local if local and local != "HEAD" else "main"


def current_branch(path: Path) -> str:
    return _git(["rev-parse", "--abbrev-ref", "HEAD"], path) or ""


def find_root(start=None) -> Path | None:
    d = Path(start or os.getcwd()).resolve()
    for p in [d, *d.parents]:
        if (p / YAML_NAME).exists():
            return p
    return None


def require_root() -> Path:
    root = find_root()
    if root is None:
        die(f"no {YAML_NAME} found in this directory or any parent. Run `init` first.")
    return root


def member_dir(root: Path, rel_path: str) -> Path:
    return (root / rel_path).resolve()


def link_path(root: Path, name: str) -> Path:
    return root / name


def die(msg: str, code: int = 1):
    print(f"meta-repo: error: {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str):
    print(msg)


def _has_origin(path: Path) -> bool:
    return bool(remote_url(path))


def _detect_trunk(path: Path, fallback: str) -> str:
    """Re-resolve the repo's real trunk (origin's default branch), fresh.

    `set-head --auto` asks the remote what its default branch is *now*, so a trunk
    that changed upstream (e.g. a release branch → main) is picked up rather than
    trusting a possibly-stale value. Falls back gracefully when offline.
    """
    _git(["remote", "set-head", "origin", "--auto"], path)
    ref = _git(["symbolic-ref", "refs/remotes/origin/HEAD"], path)
    if ref:
        return ref.rsplit("/", 1)[-1]
    return fallback or default_branch(path)

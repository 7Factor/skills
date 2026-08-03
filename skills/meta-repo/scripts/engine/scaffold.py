"""scaffold.py — doc scaffold templates + on-disk symlink management.

Covers the two halves of "wiring a member into the workspace": generating the
human-facing docs (AGENTS.md/README.md/CLAUDE.md/.gitignore) and creating the
relative symlinks that make a declared member navigable on disk.
"""
from __future__ import annotations

import os
from pathlib import Path

from .git_ops import die, link_path
from .roster import YAML_NAME

GITIGNORE_START = "# meta-repo:start (managed — edits between markers may be overwritten)"
GITIGNORE_END = "# meta-repo:end"
CLAUDE_IMPORT = "@AGENTS.md"
# Files that legitimately live loose at the meta-repo root; everything else is
# a candidate to file into a working dir (doctor reports these as advisory).
CONTROL_FILES = {"README.md", "AGENTS.md", "CLAUDE.md", YAML_NAME, ".gitignore"}


# ----------------------------------------------------------------------------
# scaffold templates
# ----------------------------------------------------------------------------
def roster_table(data: dict) -> str:
    rows = ["| Repo | Role | Status |", "|------|------|--------|"]
    for r in data.get("repositories", []):
        rows.append(f"| `{r.get('name','')}` | {r.get('role','') or '—'} | {r.get('status','') or '—'} |")
    return "\n".join(rows)


def agents_md(data: dict) -> str:
    name = data.get("name", "meta-repo")
    desc = data.get("description", "")
    return f"""# AGENTS.md — {name}

> Agent instructions for this **meta-repo** (a.k.a. workspace repository; formerly
> pseudo-monorepo). `CLAUDE.md` imports this file via `@AGENTS.md`.
> This is a SCAFFOLD — prose below is yours to evolve. The meta-repo tooling will
> only *report* drift here, never overwrite it.

{desc}

## What this repo is

A thin git repo that gathers several **independent** git repositories side by
side for cross-repo navigation and coordinated change. It is NOT a monorepo and
NOT a submodule container. Each member keeps its own history, build, deploy, and
PR process. Members are referenced by relative symlinks; the canonical roster is
`meta-repo.yaml`.

## Read this first

1. Read `meta-repo.yaml` — it is the source of truth for which repos belong here.
2. Build a topology model from the roster below before making changes.
3. Use the `meta-repo` skill's engine (wherever it's installed) to run `doctor`
   (reports health) or `manifest` (emits JSON) against this workspace.

## The member repositories

{roster_table(data)}

## Scoping rules (important)

- **Infer when obvious.** A repo/path named in the request settles scope silently.
- **Ask once when broad.** If a change is mutating *and* the scope is genuinely
  ambiguous, ask one question, then proceed.
- **Default narrow.** When unsure, search workspace-wide but propose changes to the
  smallest defensible scope, and name which repos you deliberately left out.
- **Invariant:** never open a cross-repo change without stating, up front, which
  member repos you will touch and that each lands via its OWN pull request.

## Boundaries

- `meta-repo.yaml` is written ONLY by the meta-repo engine (wherever the skill is
  installed — nothing is vendored into this repo). Don't hand-edit it.
- Commits to member code go through THAT repo's PR flow. This repo commits only its
  own metadata (yaml, docs); member symlinks are git-ignored local wiring, regenerated
  by `sync` — never committed.
- Each member may have its own `CLAUDE.md`/`AGENTS.md` — its conventions win inside it.

## Notes & files: shared by default, `-local` to keep private

This is a shared workspace, so **anything you save here — docs, notes, scripts,
investigations, plans — can and should be committed and shared with the team.** That's
the point of the repo.

If you want something kept *out* of it — personal scratch, machine-specific notes,
half-formed drafts — **suffix its name with `-local`.** Any file or directory ending in
`-local` is git-ignored (e.g. `scratch-local/`, `todo-local.md`, `db-notes-local.md`). No
special "private" directory, no nesting — just the suffix; the name announces its own
intent. (For fixed-name tool files that can't take the suffix, use `.git/info/exclude`.)

`doctor` lists loose files at the root (advisory) so you can decide per file: commit it,
file it into a subdirectory, or `-local` it.
"""


def readme_md(data: dict) -> str:
    name = data.get("name", "meta-repo")
    desc = data.get("description", "")
    return f"""# {name}

> A **meta-repo** (a.k.a. workspace repository; formerly pseudo-monorepo) — a thin
> workspace that gathers several independent repositories side by side so you can
> navigate, search, and make coordinated changes in one place. Not a monorepo: each
> member has its own history, build, and deploy.

{desc}

## Member repositories

{roster_table(data)}

## Getting set up

```sh
git clone <this-repo>
cd <this-repo>
```

Then, using an AI tool with the `meta-repo` skill installed, ask it to `sync` this
workspace (clones any missing members as siblings, fixes symlinks) and run `doctor`
(reports health). Members live as **siblings** of this repo under a shared parent
dir; symlinks here are relative (`../name`). `sync` reconstructs the full layout
from `meta-repo.yaml`.

## Layout

```
parent/
├── {name.lower().replace(' ', '-')}/   # this repo: meta-repo.yaml + symlinks
├── <member>/    # real clone, sibling
└── <member>/    # real clone, sibling
```

Agent instructions live in `AGENTS.md` (imported by `CLAUDE.md`).
"""


def gitignore_block(data: dict | None = None) -> str:
    lines = [
        GITIGNORE_START,
        ".DS_Store",
        "*.swp",
        "# Everything in this repo is meant to be committed and shared with the team.",
        "# To keep something OUT, suffix its name with -local (any file or dir).",
        "*-local",
        "*-local.*",
    ]
    members = sorted(r.get("name", "") for r in (data or {}).get("repositories", []) if r.get("name"))
    if members:
        lines.append("# member symlinks — local wiring, regenerated by `sync`; never committed")
        lines += [f"/{m}" for m in members]
    lines.append(GITIGNORE_END)
    return "\n".join(lines) + "\n"


def _ensure_gitignore(root: Path, data: dict) -> bool:
    """Write/refresh the managed .gitignore block (incl. current member symlinks).

    Replaces the block in place when present, else appends it; any content outside
    the markers is left untouched. Returns True iff the file changed.
    """
    gi = root / ".gitignore"
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    block = gitignore_block(data)
    if GITIGNORE_START in existing and GITIGNORE_END in existing:
        pre = existing.split(GITIGNORE_START, 1)[0]
        post = existing.split(GITIGNORE_END, 1)[1]
        new = pre + block.rstrip("\n") + post
    else:
        sep = "" if existing.endswith("\n") or existing == "" else "\n"
        new = existing + sep + block
    if new != existing:
        gi.write_text(new, encoding="utf-8")
        return True
    return False


# ----------------------------------------------------------------------------
# scaffold writer (shared by init + docs)
# ----------------------------------------------------------------------------
def scaffold_docs(root: Path, data: dict, *, force=False) -> list[str]:
    written = []
    files = {
        "AGENTS.md": agents_md(data),
        "README.md": readme_md(data),
        "CLAUDE.md": CLAUDE_IMPORT + "\n",
    }
    for fn, content in files.items():
        p = root / fn
        if force or not p.exists():
            p.write_text(content, encoding="utf-8")
            written.append(fn)
    # .gitignore: ensure managed block present + current (incl. member symlinks)
    if _ensure_gitignore(root, data):
        written.append(".gitignore")
    # No scaffolded notes dir: files saved here are shared by default; anything a user
    # wants kept local gets a -local suffix (see the managed .gitignore block).
    return written


# ----------------------------------------------------------------------------
# symlink management
# ----------------------------------------------------------------------------
def _make_symlink(lp: Path, rel_path: str) -> None:
    """Create a member symlink, failing loudly (not with a traceback) where the OS
    won't allow it — chiefly native Windows without Developer Mode/admin, where the
    whole POSIX-symlink model doesn't apply. WSL or any POSIX host is the fix."""
    try:
        lp.symlink_to(rel_path)
    except OSError as e:
        die(f"could not create the member symlink '{lp.name}' -> {rel_path}: {e}. "
            "meta-repo wires members with POSIX relative symlinks; native Windows needs "
            "Developer Mode or admin to create them — run this under WSL or a POSIX shell.")


def ensure_symlink(root: Path, name: str, rel_path: str) -> str:
    lp = link_path(root, name)
    if lp.is_symlink():
        # Compare normalized targets so cosmetic spellings (../api vs ../api/) don't
        # churn a relink every run and defeat idempotency.
        if os.path.normpath(os.readlink(lp)) == os.path.normpath(rel_path):
            return "ok"
        lp.unlink()
        _make_symlink(lp, rel_path)
        return "fixed"
    if lp.exists():
        return "conflict"  # a real file/dir occupies the name
    _make_symlink(lp, rel_path)
    return "created"


def discover_symlinks(root: Path) -> dict[str, str]:
    """name -> target for symlinks in root that look like member wiring.

    Member symlinks are always relative and point at a sibling (`../name`) per the
    canonical layout. Restricting discovery to that shape keeps the engine from
    treating a user's own symlink (absolute, or pointing outside the parent) as an
    orphan member — and, crucially, keeps `heal` from removing it. A dangling member
    link still matches (its `../name` target just isn't cloned yet), so orphan and
    broken-member detection are unaffected.
    """
    out = {}
    for child in root.iterdir():
        if not child.is_symlink():
            continue
        target = os.readlink(child)
        if os.path.isabs(target) or not os.path.normpath(target).startswith(".."):
            continue
        out[child.name] = target
    return out

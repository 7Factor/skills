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
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

META_REPO_VERSION = "0.7.0"
YAML_NAME = "meta-repo.yaml"
GITIGNORE_START = "# meta-repo:start (managed — edits between markers may be overwritten)"
GITIGNORE_END = "# meta-repo:end"
CLAUDE_IMPORT = "@AGENTS.md"
FIELD_ORDER = ["path", "role", "remote", "default_branch", "status"]
VALID_STATUS = ["active", "legacy", "greenfield", "empty", "archived"]
# Files that legitimately live loose at the meta-repo root; everything else is
# a candidate to file into a working dir (doctor reports these as advisory).
CONTROL_FILES = {"README.md", "AGENTS.md", "CLAUDE.md", YAML_NAME, ".gitignore"}


# ----------------------------------------------------------------------------
# tiny YAML I/O for our constrained, self-written schema
# ----------------------------------------------------------------------------
def _scalar(v) -> str:
    s = "" if v is None else str(v)
    if s == "" or s != s.strip() or ": " in s or "#" in s or (s and s[0] in "\"'[]{}>|*&!%@`"):
        return json.dumps(s)
    return s


def _unquote(s: str):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        if s[0] == '"':
            try:
                return json.loads(s)
            except Exception:
                return s[1:-1]
        return s[1:-1]
    return s


def parse_yaml(text: str) -> dict:
    data = {"name": "", "description": "", "repositories": []}
    in_repos = False
    cur = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not in_repos:
            if re.match(r"^repositories:\s*$", line):
                in_repos = True
                continue
            m = re.match(r"^([A-Za-z_]\w*):\s?(.*)$", line)
            if m:
                data[m.group(1)] = _unquote(m.group(2))
            continue
        m_item = re.match(r"^\s*-\s+([A-Za-z_]\w*):\s?(.*)$", line)
        if m_item:
            cur = {m_item.group(1): _unquote(m_item.group(2))}
            data["repositories"].append(cur)
            continue
        m_kv = re.match(r"^\s+([A-Za-z_]\w*):\s?(.*)$", line)
        if m_kv and cur is not None:
            cur[m_kv.group(1)] = _unquote(m_kv.group(2))
    return data


def dump_yaml(data: dict) -> str:
    lines = [
        f"name: {_scalar(data.get('name', ''))}",
        f"description: {_scalar(data.get('description', ''))}",
        "repositories:",
    ]
    for r in data.get("repositories", []):
        lines.append(f"  - name: {_scalar(r.get('name', ''))}")
        for k in FIELD_ORDER:
            v = r.get(k)
            if v not in (None, ""):
                lines.append(f"    {k}: {_scalar(v)}")
    return "\n".join(lines) + "\n"


def load(root: Path) -> dict:
    return parse_yaml((root / YAML_NAME).read_text(encoding="utf-8"))


def save(root: Path, data: dict) -> None:
    (root / YAML_NAME).write_text(dump_yaml(data), encoding="utf-8")


# ----------------------------------------------------------------------------
# git + filesystem helpers
# ----------------------------------------------------------------------------
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
    sp = Path(__file__).resolve().parent.parent
    if (sp / YAML_NAME).exists():
        return sp
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


# ----------------------------------------------------------------------------
# scaffold templates (embedded so the vendored single file is self-contained)
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
3. `python3 scripts/meta-repo.py doctor` reports health; `manifest` emits JSON.

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

- `meta-repo.yaml` is written ONLY by `scripts/meta-repo.py`. Don't hand-edit it.
- Commits to member code go through THAT repo's PR flow. This repo commits only its
  own metadata (yaml, docs, vendored engine); member symlinks are git-ignored local
  wiring, regenerated by `sync` — never committed.
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
python3 scripts/meta-repo.py sync     # clones any missing members as siblings, fixes symlinks
python3 scripts/meta-repo.py doctor   # reports health
```

Members live as **siblings** of this repo under a shared parent dir; symlinks here
are relative (`../name`). `sync` reconstructs the full layout from `meta-repo.yaml`.

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


def vendor_self(root: Path) -> bool:
    """Copy this engine to <root>/scripts/meta-repo.py if missing or different."""
    dest = root / "scripts" / "meta-repo.py"
    src = Path(__file__).resolve()
    if dest.resolve() == src:
        return False
    dest.parent.mkdir(exist_ok=True)
    new = src.read_text(encoding="utf-8")
    if dest.exists() and dest.read_text(encoding="utf-8") == new:
        return False
    dest.write_text(new, encoding="utf-8")
    dest.chmod(0o755)
    return True


def vendored_version(root: Path) -> str | None:
    p = root / "scripts" / "meta-repo.py"
    if not p.exists():
        return None
    m = re.search(r'META_REPO_VERSION\s*=\s*"([^"]+)"', p.read_text(encoding="utf-8"))
    return m.group(1) if m else None


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


# ----------------------------------------------------------------------------
# commands
# ----------------------------------------------------------------------------
def cmd_init(args):
    root = Path(os.getcwd()).resolve()
    if (root / YAML_NAME).exists():
        die(f"{YAML_NAME} already exists here. Use add/remove/sync instead.")
    did_git_init = ensure_git_repo(root)
    name = args.name or root.name
    data = {"name": name, "description": args.description or "", "repositories": []}

    # adopt pre-existing sibling symlinks
    for ln, target in sorted(discover_symlinks(root).items()):
        md = (root / target).resolve()
        if not md.is_dir():
            continue
        rel = target if target.startswith("..") else os.path.relpath(md, root)
        entry = {"name": ln, "path": rel, "role": "", "status": "active"}
        if is_git_repo(md):
            entry["remote"] = remote_url(md)
            entry["default_branch"] = default_branch(md)
        data["repositories"].append(entry)

    save(root, data)
    written = scaffold_docs(root, data)
    vendor_self(root)
    if did_git_init:
        info("Ran `git init` — the workspace root is now a git repo (nothing committed yet).")
    info(f"Initialized meta-repo '{name}' at {root}")
    if data["repositories"]:
        info(f"Adopted {len(data['repositories'])} existing member(s): "
             + ", ".join(r["name"] for r in data["repositories"]))
    info("Scaffolded: " + ", ".join(written + ["scripts/meta-repo.py"]))
    info("Next: edit roles in meta-repo.yaml via `add`, or `add --remote <url>` to bring in repos.")


def cmd_add(args):
    root = require_root()
    data = load(root)
    name = args.name
    rel = args.path

    if args.remote and not rel:
        if not name:
            name = re.sub(r"\.git$", "", args.remote.rstrip("/").rsplit("/", 1)[-1])
        rel = f"../{name}"
    if not name:
        die("provide --name (and --path or --remote).")

    # Metadata-only edit of an already-declared member (e.g. mark a vestigial repo
    # `archived`, or set a role) — no --path/--remote required.
    existing_meta = next((r for r in data["repositories"] if r["name"] == name), None)
    if existing_meta and not rel and not args.remote:
        changed = []
        if args.role is not None:
            existing_meta["role"] = args.role
            changed.append("role")
        if args.status:
            existing_meta["status"] = args.status
            changed.append("status")
        if not changed:
            die(f"member '{name}' exists; pass --role/--status to edit, or --path/--remote to relink.")
        save(root, data)
        info(f"Updated {', '.join(changed)} for member '{name}'.")
        return
    if not rel:
        die("provide --path ../<dir> or --remote <url>.")

    md = member_dir(root, rel)

    # clone if requested and missing
    if args.remote and not md.exists():
        info(f"Cloning {args.remote} -> {md} ...")
        r = subprocess.run(["git", "clone", args.remote, str(md)])
        if r.returncode != 0:
            die("git clone failed.")

    # A real (non-symlink) file/dir squatting the member name blocks the symlink.
    # Detect it BEFORE writing yaml/.gitignore so a conflict can't leave the roster
    # half-written with no symlink on disk.
    lp = link_path(root, name)
    if lp.exists() and not lp.is_symlink():
        die(f"a real file/dir named '{name}' occupies the meta-repo root; resolve it manually, then re-run `add`.")

    entry = {"name": name, "path": rel, "role": args.role or "", "status": args.status or "active"}
    if md.is_dir() and is_git_repo(md):
        entry["remote"] = args.remote or remote_url(md)
        entry["default_branch"] = default_branch(md)
    elif args.remote:
        entry["remote"] = args.remote

    # upsert
    existing = next((r for r in data["repositories"] if r["name"] == name), None)
    if existing:
        # Overwrite path + any captured remote/branch; honor an explicit --role/--status
        # (including --role "" to clear it) while leaving unspecified fields untouched —
        # never clobber existing values with argparse defaults.
        updates = {"path": rel}
        for k in ("remote", "default_branch"):
            if k in entry:
                updates[k] = entry[k]
        if args.role is not None:
            updates["role"] = args.role
        if args.status:
            updates["status"] = args.status
        existing.update(updates)
        info(f"Updated member '{name}'.")
    else:
        data["repositories"].append(entry)
        info(f"Added member '{name}'.")
    save(root, data)
    _ensure_gitignore(root, data)

    state = ensure_symlink(root, name, rel)
    info(f"Symlink {name} -> {rel}: {state}")
    if state == "conflict":
        die(f"a real file/dir named '{name}' exists at the meta-repo root; resolve it manually.")
    if not md.is_dir():
        info(f"Note: {rel} not present on disk yet. Run `sync` to clone it from remote.")


def cmd_remove(args):
    root = require_root()
    data = load(root)
    name = args.name
    before = len(data["repositories"])
    data["repositories"] = [r for r in data["repositories"] if r["name"] != name]
    if len(data["repositories"]) == before:
        die(f"no member named '{name}'.")
    save(root, data)
    _ensure_gitignore(root, data)
    lp = link_path(root, name)
    if lp.is_symlink():
        lp.unlink()
        info(f"Removed symlink '{name}'.")
    info(f"Removed '{name}' from {YAML_NAME}. The real clone (if any) was left untouched.")


def cmd_sync(args):
    root = require_root()
    data = load(root)
    cloned, linked, problems = [], [], []
    declared = {r["name"] for r in data["repositories"]}

    for r in data["repositories"]:
        name, rel = r["name"], r.get("path", "")
        if not rel:
            problems.append(f"{name}: no path declared")
            continue
        md = member_dir(root, rel)
        if not md.exists():
            if r.get("remote"):
                info(f"Cloning {name} <- {r['remote']} ...")
                rc = subprocess.run(["git", "clone", r["remote"], str(md)]).returncode
                if rc == 0:
                    cloned.append(name)
                else:
                    problems.append(f"{name}: clone failed")
            else:
                problems.append(f"{name}: missing on disk and no remote to clone from")
        state = ensure_symlink(root, name, rel)
        if state in ("created", "fixed"):
            linked.append(f"{name} ({state})")
        elif state == "conflict":
            problems.append(f"{name}: a real file/dir occupies the symlink name")

    # orphan symlinks (present but not declared)
    for ln in discover_symlinks(root):
        if ln not in declared:
            problems.append(f"{ln}: symlink not in {YAML_NAME} (orphan; `heal` can remove if broken)")

    info("== sync ==")
    info(f"cloned:  {', '.join(cloned) if cloned else '(none)'}")
    info(f"symlinks:{' ' + ', '.join(linked) if linked else ' (all ok)'}")
    if problems:
        info("problems:")
        for p in problems:
            info(f"  - {p}")
    sys.exit(1 if problems else 0)


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


def _update_repo(path: Path, known_trunk: str, switch: bool) -> dict:
    """Fetch and advance one repo to latest trunk without ever discarding work.

    - dirty tree            -> skipped (never touched), flagged for attention
    - on trunk              -> fast-forward in place (ff-only; report if diverged)
    - on a feature branch   -> refresh local trunk ref (ff-only), STAY on the branch
                               and flag it; with `switch`, checkout trunk afterward
    Returns a result dict; the caller fills in the repo name.
    """
    res = {"branch": current_branch(path), "trunk": known_trunk, "action": "",
           "ok": True, "attention": False, "dirty": False}
    if not _has_origin(path):
        res["action"] = "no origin remote — skipped"
        return res
    status = _git(["status", "--porcelain"], path)
    if status is None:
        res["ok"] = False
        res["action"] = "git status failed"
        return res
    if status.strip():
        res.update(dirty=True, ok=False, attention=True,
                   action="DIRTY — uncommitted changes; skipped (commit or stash first)")
        return res

    _git(["fetch", "--prune", "origin"], path)
    trunk = _detect_trunk(path, known_trunk)
    res["trunk"] = trunk
    branch = res["branch"]

    if branch == trunk:
        out = _git(["merge", "--ff-only", f"origin/{trunk}"], path)
        if out is None:
            res.update(ok=False, attention=True,
                       action=f"on trunk '{trunk}' but could NOT fast-forward (diverged — resolve manually)")
        else:
            res["action"] = f"on trunk '{trunk}' — fast-forwarded to origin"
    else:
        ff = _git(["fetch", "origin", f"{trunk}:{trunk}"], path)  # ff-only local trunk, no checkout
        if switch:
            if ff is None:
                res.update(attention=True,
                           action=f"on '{branch}'; trunk '{trunk}' could not ff — left on branch")
            elif _git(["checkout", trunk], path) is None:
                res.update(attention=True,
                           action=f"trunk '{trunk}' refreshed; checkout failed — still on '{branch}'")
            else:
                res.update(branch=trunk, action=f"switched '{branch}' → '{trunk}' (latest)")
        else:
            res["attention"] = True  # parked on a feature branch — always call it out
            res["action"] = (f"on feature branch '{branch}'; local '{trunk}' refreshed (not switched)"
                             if ff is not None else
                             f"on feature branch '{branch}'; local '{trunk}' NOT refreshed (diverged)")
    return res


def cmd_update(args):
    root = require_root()
    data = load(root)
    rows = []

    # the meta-repo itself first (never auto-switch its own branch)
    rows.append(("(meta-repo)", _update_repo(root, "", switch=False)))

    changed = False
    for r in data["repositories"]:
        rel = r.get("path", "")
        md = member_dir(root, rel) if rel else None
        if not md or not md.exists() or not is_git_repo(md):
            rows.append((r["name"], {"action": "not present / not a git repo — run `sync`",
                                     "ok": False, "attention": True, "dirty": False,
                                     "branch": "", "trunk": r.get("default_branch", "")}))
            continue
        res = _update_repo(md, r.get("default_branch", ""), switch=args.switch)
        if res.get("trunk") and res["trunk"] != r.get("default_branch"):
            old = r.get("default_branch") or "(unset)"
            r["default_branch"] = res["trunk"]
            changed = True
            res["action"] += f"  [roster trunk {old} → {res['trunk']}]"
        rows.append((r["name"], res))
    if changed:
        save(root, data)

    info(f"== update: {data.get('name','meta-repo')} ==")
    for name, res in rows:
        info(f" {'!' if res.get('attention') else ' '} {name}: {res.get('action','')}")

    dirty = [n for n, r in rows if r.get("dirty")]
    parked = [n for n, r in rows if r.get("attention") and not r.get("dirty") and r.get("ok")]
    if dirty:
        info("\nDIRTY (skipped — likely unfinished work; finish/commit/stash, then re-run):")
        for n in dirty:
            info(f"  - {n}")
    if parked and not args.switch:
        info("\nON A NON-TRUNK BRANCH (review for stale/old work; `update --switch` moves the clean ones to trunk):")
        for n in parked:
            info(f"  - {n}")
    sys.exit(1 if any(not r.get("ok") for _, r in rows) else 0)


def _doc_drift(root: Path, data: dict) -> list[str]:
    issues = []
    for fn in ("README.md", "AGENTS.md"):
        p = root / fn
        if not p.exists():
            issues.append(f"{fn}: missing (run `docs`)")
            continue
        text = p.read_text(encoding="utf-8")
        for r in data["repositories"]:
            if r["name"] not in text:
                issues.append(f"{fn}: member '{r['name']}' is not mentioned (prose drift)")
    return issues


def _loose_root_files(root: Path) -> list[str]:
    """Regular files sitting loose at the meta-repo root that aren't control files.

    Directories, symlinks (members), and dotfiles are left alone. The result is
    advisory — candidates to file into a working dir, not health failures.
    """
    out = []
    for child in sorted(root.iterdir()):
        if child.is_symlink() or child.is_dir() or child.name.startswith("."):
            continue
        if child.name in CONTROL_FILES:
            continue
        out.append(child.name)
    return out


def cmd_doctor(args):
    root = require_root()
    data = load(root)
    structural, hygiene, needs_you, info_notes = [], [], [], []
    declared = {r["name"] for r in data["repositories"]}

    for r in data["repositories"]:
        name, rel = r["name"], r.get("path", "")
        md = member_dir(root, rel) if rel else None
        lp = link_path(root, name)
        if not rel:
            structural.append(f"{name}: no path declared")
        elif md and not md.exists():
            # A dangling symlink here is just a symptom of the missing clone — report
            # the clone once, not also as a separate "broken symlink" line.
            structural.append(f"{name}: missing on disk"
                              + (" — `sync` will clone it" if r.get("remote") else " and NO remote recorded"))
        elif not (lp.is_symlink() and lp.exists()):
            structural.append(f"{name}: symlink missing or broken — run `sync`")
        if md and md.is_dir() and is_git_repo(md):
            cb = current_branch(md)
            if cb and r.get("default_branch") and cb != r["default_branch"]:
                info_notes.append(f"{name}: on branch '{cb}' (default '{r['default_branch']}')")

    for ln in discover_symlinks(root):
        if ln not in declared:
            target = root / ln
            (hygiene if target.is_symlink() and not target.exists() else needs_you).append(
                f"{ln}: symlink not in {YAML_NAME} ({'broken orphan — heal removes' if not target.exists() else 'orphan — add or remove'})"
            )

    # CLAUDE.md additive-only check
    cl = root / "CLAUDE.md"
    if not cl.exists():
        hygiene.append("CLAUDE.md: missing — `heal` creates it with @AGENTS.md")
    else:
        body = cl.read_text(encoding="utf-8")
        if CLAUDE_IMPORT not in body:
            hygiene.append("CLAUDE.md: missing the `@AGENTS.md` import — `heal` adds it")
        extra = [l for l in body.splitlines() if l.strip() and l.strip() != CLAUDE_IMPORT and not l.strip().startswith("#")]
        if extra:
            needs_you.append("CLAUDE.md: has content beyond `@AGENTS.md` — should it move to AGENTS.md? (agent migrates on your OK; heal will NOT touch it)")

    if not (root / ".git").exists():
        hygiene.append("workspace root is not a git repository — `heal` runs `git init`")
    else:
        _tracked = [r["name"] for r in data["repositories"]
                    if r.get("name") and _git(["ls-files", "--", r["name"]], root)]
        if _tracked:
            hygiene.append("member symlink(s) tracked in git: " + ", ".join(_tracked)
                           + " — `heal` untracks them (local wiring, shouldn't be committed)")

    if (root / ".gitignore").exists():
        if GITIGNORE_START not in (root / ".gitignore").read_text(encoding="utf-8"):
            hygiene.append(".gitignore: missing managed block — `heal` adds it")
    else:
        hygiene.append(".gitignore: missing — `heal` creates it")

    vv = vendored_version(root)
    if vv and vv != META_REPO_VERSION:
        hygiene.append(f"scripts/meta-repo.py: vendored v{vv}, engine v{META_REPO_VERSION} — `heal` refreshes it")

    needs_you.extend(_doc_drift(root, data))

    def section(title, items):
        info(f"\n{title}")
        if not items:
            info("  (none)")
        for i in items:
            info(f"  - {i}")

    info(f"== doctor: {data.get('name','meta-repo')} ({len(data['repositories'])} members) ==")
    section("STRUCTURAL  -> run `sync`", structural)
    section("HYGIENE     -> run `heal`", hygiene)
    section("NEEDS YOU   -> judgment required", needs_you)
    section("INFO", info_notes)
    loose = _loose_root_files(root)
    section("WORKSPACE HYGIENE (advisory — file loose root files into working dirs)",
            [f"{f}" for f in loose])
    # Advisory only: loose files never fail doctor. Structural/hygiene/needs-you do.
    sys.exit(1 if (structural or hygiene or needs_you) else 0)


def cmd_heal(args):
    root = require_root()
    data = load(root)
    done = []

    # a meta-repo is a git repo by definition
    if ensure_git_repo(root):
        done.append("ran `git init` (workspace root was not a git repo)")

    # CLAUDE.md: additive only — ensure @AGENTS.md line present, NEVER delete content
    cl = root / "CLAUDE.md"
    if not cl.exists():
        cl.write_text(CLAUDE_IMPORT + "\n", encoding="utf-8")
        done.append("created CLAUDE.md with @AGENTS.md")
    else:
        body = cl.read_text(encoding="utf-8")
        if CLAUDE_IMPORT not in body:
            sep = "" if body.startswith("\n") or body == "" else "\n"
            cl.write_text(CLAUDE_IMPORT + "\n" + sep + body, encoding="utf-8")
            done.append("prepended @AGENTS.md to CLAUDE.md (existing content kept)")

    # .gitignore managed block (incl. member symlinks — local wiring, never committed)
    if _ensure_gitignore(root, data):
        done.append("updated .gitignore managed block")

    # untrack any member symlink that got committed (leaves it on disk for local nav)
    if (root / ".git").exists():
        for r in data["repositories"]:
            nm = r.get("name", "")
            if nm and _git(["ls-files", "--", nm], root):
                _git(["rm", "--cached", "--quiet", "--", nm], root)
                done.append(f"untracked committed symlink '{nm}' (git rm --cached; still on disk)")

    # refresh stale vendored script
    if vendor_self(root):
        done.append("refreshed scripts/meta-repo.py")

    # remove broken orphan symlinks (not in yaml AND dangling)
    declared = {r["name"] for r in data["repositories"]}
    for ln in discover_symlinks(root):
        if ln not in declared:
            target = root / ln
            if target.is_symlink() and not target.exists():
                target.unlink()
                done.append(f"removed broken orphan symlink '{ln}'")

    info("== heal ==")
    for d in done:
        info(f"  - {d}")
    if not done:
        info("  (nothing to heal)")
    info("Note: structural gaps (missing clones/symlinks) are `sync`'s job, not heal's.")


def cmd_manifest(args):
    root = require_root()
    data = load(root)
    out = {"name": data.get("name", ""), "description": data.get("description", ""),
           "engine_version": META_REPO_VERSION, "root": str(root), "repositories": []}
    for r in data["repositories"]:
        rel = r.get("path", "")
        md = member_dir(root, rel) if rel else None
        lp = link_path(root, r["name"])
        state = ("missing" if (md and not md.exists())
                 else "broken-symlink" if (lp.is_symlink() and not lp.exists())
                 else "no-symlink" if not lp.is_symlink()
                 else "present")
        out["repositories"].append({
            **{k: r.get(k, "") for k in ["name", "path", "role", "remote", "default_branch", "status"]},
            "on_disk": bool(md and md.exists()),
            "symlink_ok": lp.is_symlink() and lp.exists(),
            "current_branch": current_branch(md) if (md and is_git_repo(md)) else "",
            "state": state,
        })
    print(json.dumps(out, indent=2))


def cmd_docs(args):
    root = require_root()
    data = load(root)
    written = scaffold_docs(root, data, force=args.force)
    if written:
        info("Scaffolded/updated: " + ", ".join(written))
    else:
        info("Docs already present — checking drift (no files rewritten):")
        for d in _doc_drift(root, data):
            info(f"  - {d}")
        info("  (run with --force only if you intend to overwrite scaffolds)")


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
    s.add_argument("--switch", action="store_true",
                   help="also checkout trunk on clean members currently on a feature branch")
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

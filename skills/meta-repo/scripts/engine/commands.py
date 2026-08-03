"""commands.py — CLI-facing command implementations (the `meta-repo` verbs).

Each `cmd_*` function corresponds 1:1 to a subcommand wired up in
`../meta-repo.py`'s `build_parser()`. Grouped as one module because these are
all "CLI verbs" against the same roster/git-ops/scaffold layers below them,
not because each is large enough to warrant its own file (several are small).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from .git_ops import (
    _detect_trunk,
    _git,
    _has_origin,
    current_branch,
    default_branch,
    die,
    ensure_git_repo,
    info,
    is_git_repo,
    link_path,
    member_dir,
    remote_url,
    require_root,
)
from .roster import META_REPO_VERSION, YAML_NAME, load, save
from .scaffold import (
    CLAUDE_IMPORT,
    CONTROL_FILES,
    GITIGNORE_START,
    _ensure_gitignore,
    discover_symlinks,
    ensure_symlink,
    scaffold_docs,
)


def cmd_init(args):
    root = Path(os.getcwd()).resolve()
    if (root / YAML_NAME).exists():
        die(f"{YAML_NAME} already exists here. Use add/remove/sync instead.")
    did_git_init = ensure_git_repo(root)
    name = args.name or root.name
    data = {"name": name, "description": args.description or "", "repositories": []}

    # adopt pre-existing sibling symlinks
    skipped = []
    for ln, target in sorted(discover_symlinks(root).items()):
        md = (root / target).resolve()
        if not md.exists():
            skipped.append(f"{ln} -> {target}: dangling symlink (target does not exist), not added to roster")
            continue
        if not md.is_dir():
            skipped.append(f"{ln} -> {target}: target is not a directory, not added to roster")
            continue
        if not is_git_repo(md):
            skipped.append(f"{ln} -> {target}: not a git repository, not added to roster "
                            "(no remote to capture — add manually with `add --remote` if this "
                            "should be a member)")
            continue
        rel = target if target.startswith("..") else os.path.relpath(md, root)
        entry = {
            "name": ln, "path": rel, "role": "", "status": "active",
            "remote": remote_url(md), "default_branch": default_branch(md),
        }
        data["repositories"].append(entry)

    save(root, data)
    written = scaffold_docs(root, data)
    if did_git_init:
        info("Ran `git init` — the workspace root is now a git repo (nothing committed yet).")
    info(f"Initialized meta-repo '{name}' at {root}")
    if data["repositories"]:
        info(f"Adopted {len(data['repositories'])} existing member(s): "
             + ", ".join(r["name"] for r in data["repositories"]))
    if skipped:
        info(f"Skipped {len(skipped)} sibling symlink(s) not added to the roster:")
        for s in skipped:
            info(f"  - {s}")
    info("Scaffolded: " + ", ".join(written))
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
    cloned, linked, problems, orphans = [], [], [], []
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

    # orphan symlinks (present but not declared) — informational, NOT a failure: it's
    # "here's something you might want to curate" (add it, or remove a dangling link),
    # not a broken state. Still reported, just doesn't affect the exit code. Mirrors
    # doctor's NEEDS-YOU categorization for the same finding.
    for ln in discover_symlinks(root):
        if ln not in declared:
            orphans.append(f"{ln}: symlink not in {YAML_NAME} (orphan; `heal` can remove if broken)")

    info("== sync ==")
    info(f"cloned:  {', '.join(cloned) if cloned else '(none)'}")
    info(f"symlinks:{' ' + ', '.join(linked) if linked else ' (all ok)'}")
    if problems:
        info("problems:")
        for p in problems:
            info(f"  - {p}")
    if orphans:
        info("orphans (informational — not a failure):")
        for o in orphans:
            info(f"  - {o}")
    sys.exit(1 if problems else 0)


def _update_repo(path: Path, known_trunk: str) -> dict:
    """Fetch and advance one repo to latest trunk without ever discarding work.

    - dirty tree            -> skipped (never touched), flagged for attention
    - on trunk              -> fast-forward in place (ff-only; report if diverged)
    - on a feature branch   -> refresh the LOCAL trunk ref only (ff-only fetch into
                               the trunk ref, e.g. `fetch origin main:main`) so
                               `git status`/`git log` show accurate drift; the
                               member's working tree/current branch is never
                               touched. Flagged as informational.
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
        # Refresh ONLY the local trunk ref (ff-only), never the member's checkout.
        ff = _git(["fetch", "origin", f"{trunk}:{trunk}"], path)
        res["attention"] = True  # parked on a feature branch — always call it out
        if ff is None:
            res["action"] = f"on feature branch '{branch}'; local '{trunk}' NOT refreshed (diverged)"
        else:
            behind = _git(["rev-list", "--count", f"{branch}..{trunk}"], path)
            behind_note = f", {behind} commit(s) behind" if behind and behind.isdigit() else ""
            res["action"] = (f"on feature branch '{branch}'; local '{trunk}' ref refreshed"
                             f"{behind_note} (working tree untouched)")
    return res


def cmd_update(args):
    root = require_root()
    data = load(root)
    rows = []

    # the meta-repo itself first
    rows.append(("(meta-repo)", _update_repo(root, "")))

    changed = False
    skipped_archived = []
    for r in data["repositories"]:
        if r.get("status") == "archived":
            # Archived members are fully out of scope for `update`: no fetch, no
            # dirty-check, no fast-forward attempt — and they never count toward
            # the problem tally or exit code. Purely informational.
            skipped_archived.append(r["name"])
            continue
        rel = r.get("path", "")
        md = member_dir(root, rel) if rel else None
        if not md or not md.exists() or not is_git_repo(md):
            rows.append((r["name"], {"action": "not present / not a git repo — run `sync`",
                                     "ok": False, "attention": True, "dirty": False,
                                     "branch": "", "trunk": r.get("default_branch", "")}))
            continue
        res = _update_repo(md, r.get("default_branch", ""))
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
    for name in skipped_archived:
        info(f"   {name}: skipped (status: archived)")

    dirty = [n for n, r in rows if r.get("dirty")]
    parked = [n for n, r in rows if r.get("attention") and not r.get("dirty") and r.get("ok")]
    if dirty:
        info("\nDIRTY (skipped — likely unfinished work; finish/commit/stash, then re-run):")
        for n in dirty:
            info(f"  - {n}")
    if parked:
        info("\nON A NON-TRUNK BRANCH (local trunk ref refreshed; review for stale/old work):")
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

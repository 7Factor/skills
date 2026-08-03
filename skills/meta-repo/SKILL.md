---
name: meta-repo
description: meta-repo — create a new one (gather independent git repos side by side, wired with relative symlinks), onboard onto an existing one, or maintain/audit one (add/remove members, resync symlinks, refresh docs, decide task scope). Use for multi-repo workspaces, meta-repo.yaml, pseudo-monorepos, workspace repositories, or "which repos belong to this project."
compatibility: POSIX hosts (macOS, Linux) and WSL. Requires python3 ≥3.8 and git. Native Windows is unsupported — the workspace model relies on POSIX relative symlinks, which need Developer Mode/privilege there; run under WSL instead.
---

# meta-repo

A **meta-repo** is a thin git repo that gathers several *independent* git repositories
side by side for cross-repo navigation and coordinated change. It is **not** a monorepo,
**not** a submodule container, **not** a build/release tool. Each member keeps its own
history, build, deploy, and PR flow. Members are relative symlinks; the canonical roster
lives in **`meta-repo.yaml`**, which is written *only* by the engine.

## The engine does the mechanical work

All counting/parsing/cloning/symlinking is a Python package — **never hand-roll it.**
It lives only where this skill is installed: `scripts/meta-repo.py` (a thin entrypoint)
plus `scripts/engine/` (the implementation) sitting beside this `SKILL.md`. Nothing is
copied into the meta-repo you're working in — run it in place from wherever the skill is
installed, invoked from inside (or pointed at) the target meta-repo:

```sh
python3 <path-to-this-skill>/scripts/meta-repo.py <command>
```

Needs a POSIX host or WSL (see `compatibility`): the engine wires members with relative
symlinks and stops with a clear message where the OS won't create them (native Windows).

| Command | What it does | Touches |
|---------|--------------|---------|
| `init [--name N --description D]` | Create a meta-repo in cwd; `git init`s the root if needed; adopts existing member-shaped sibling symlinks as `active` members (skips dangling or non-git ones, visibly) | metadata |
| `add --name N [--path ../N \| --remote URL] [--role R] [--status S]` | Add a member (clones if `--remote` & missing); with only `--role`/`--status` on an existing member, **edits its metadata** (e.g. mark one `archived`) | working-tree |
| `remove N` | Drop from yaml + remove symlink. **Never deletes the real clone.** | working-tree |
| `sync` | Reconcile disk→yaml: clone missing from `remote`, fix symlinks | working-tree |
| `update` | Fetch + fast-forward every member and the meta-repo to latest trunk (re-detects trunk fresh); never checks out or switches a member's branch | working-tree |
| `doctor` | Report health (`sync` / `heal` / needs-you) plus an advisory list of loose root files. Read-only | none |
| `heal` | Fix safe hygiene (incl. `git init` if the root isn't a repo, removing broken orphan symlinks); **additive** to CLAUDE.md (never deletes) | working-tree |
| `manifest` | Roster + computed per-repo state as JSON (for you to consume) | none |
| `docs [--force]` | Scaffold README/AGENTS/CLAUDE if absent, else report drift | metadata |

Statuses: `active` (default) · `archived` (fully skipped by `update` — no fetch, no
dirty-check, doesn't affect exit code). There is no broader lifecycle vocabulary; put any
other nuance in the free-text `role` field.

## Always do this first when entering a meta-repo

1. **Read `meta-repo.yaml`** (or run `manifest`) — it is the source of truth for which
   repos belong here. Build a topology model before acting.
2. Don't assume every task touches every member. Apply the **scoping rules** below.

## Scoping rules (non-negotiable)

- **Infer when obvious** — a repo/path named in the request settles scope silently.
- **Ask once when broad** — if a change is *mutating and* genuinely ambiguous in scope,
  ask one question, then proceed.
- **Default narrow** — when unsure, search workspace-wide but propose changes to the
  smallest defensible scope, and name which members you deliberately left out.
- **Invariant** — never open a cross-repo change without stating, up front, which members
  you'll touch and that **each lands via its own PR**. The meta-repo commits only its own
  metadata (yaml, docs, symlinks); member code goes through that member's PR flow.

## Workflows

**Create a new meta-repo.** Confirm name + one-line description. If members already exist
as sibling dirs, `cd` into the (empty) meta-repo dir and run `init` — it `git init`s the dir,
adopts any existing member-shaped symlinks, and captures their `remote`/`default_branch`. For
repos not yet present, `add --remote <url>`. Then `docs` is already done by `init`; refine the
scaffolded prose.

**Adopt / standardize an existing workspace** (a dir that already has symlinks, working files,
maybe a hand-written README — the "clean up an existing repo to conform" path). Run it in
stages, and **never move or delete a workspace file without showing the user the plan first**:

1. `init` — builds `meta-repo.yaml` from existing symlinks and `git init`s the root if it isn't
   a repo yet. It adopts every sibling symlink that is member-shaped (relative, target exists
   and is a git repo) as `active`; a dangling symlink or one pointing at a non-git directory is
   skipped with a visible note and left out of the roster entirely. First *curate the roster*:
   fix roles, set true statuses, and park or drop non-members
   (`add --name X --status archived`, or `remove X`) before anything else.
2. `doctor` — read-only. Beyond structural/hygiene/needs-you it prints a **WORKSPACE HYGIENE**
   advisory: loose files sitting at the root that aren't control files.
3. **Present a concrete cleanup plan and get explicit confirmation.** Spell out exactly what you
   propose — every file move (source → destination working dir) and every deletion — and wait for
   the user's OK. Working-dir *names are the user's choice*; propose sensible ones, don't impose
   them. The engine never moves or deletes workspace content; that tidy-up is your judgment work,
   done only after sign-off.
4. Migrate any non-`@AGENTS.md` content out of `CLAUDE.md` into `AGENTS.md` (doctor flags it; the
   existing README/AGENTS prose is never overwritten unless you pass `docs --force`).
5. `heal` then `sync` to close the mechanical gaps.

**Add / remove a member.** `add` for new; `remove` to drop (the real clone always survives —
tell the user it remains on disk). After either, the roster prose may drift — run `doctor`
and offer to refresh README/AGENTS.

**Onboard a teammate.** They `git clone` the meta-repo, then, using this skill's engine,
run `sync`, which clones every missing member from its stored `remote` into the sibling layout
and fixes symlinks. One command → fully wired.

**Refresh the whole workspace.** `update` fetches and fast-forwards every member (and the
meta-repo) to its current trunk — re-detecting each member's real trunk from the remote, so a
trunk that moved upstream (e.g. a release branch → `main`) is caught and written back to
`meta-repo.yaml`. It never discards work and never switches a checkout: dirty members are
skipped untouched and listed for you to finish/commit/stash (treat that list as "did I leave
something unfinished here?"); a member on a feature branch stays on that branch — only its
local trunk ref is silently refreshed (so `git status`/`git log` show true drift against
trunk) — and is flagged for you to review, not acted on. `archived` members are skipped
entirely (no fetch, purely informational).

**Audit / fix.** `doctor` first (read-only). It sorts findings: structural → `sync`,
hygiene → `heal`, judgment → you. Run `sync` then `heal`. The only thing `heal` will not do
is touch non-`@AGENTS.md` content in `CLAUDE.md` — if `doctor` flags content there, ask the
user before migrating it into `AGENTS.md`.

**Architecture summary across members.** Read each member's README/CLAUDE.md/AGENTS.md plus
its top-level layout, then synthesize a cross-repo "how they fit together" narrative into the
meta-repo's `AGENTS.md`/`README.md` prose (this is judgment work — the engine doesn't do it).
Keep it grounded; cite member paths.

## Layout & boundaries (see [REFERENCE.md](REFERENCE.md) for the full contract)

Members are **siblings under a shared parent**; symlinks are relative (`../name`) and
**git-ignored** — local wiring regenerated by `sync`, never committed (the roster in
`meta-repo.yaml` is the source of truth; a committed symlink only dangles for whoever clones).
`meta-repo.yaml` + the `@AGENTS.md` line in `CLAUDE.md` + a managed `.gitignore` block (which
carries the `-local` convention and the member symlinks) are engine-owned. `README.md` /
`AGENTS.md` prose is scaffolded once then **yours** — the engine only *reports* its drift.
`meta-repo.yaml` is also structurally validated on every read, so a hand-edit that breaks the
schema (missing `repositories`, a member missing `name`/`path`) fails loudly with a clear error
instead of silently corrupting the roster.

**Notes & files — shared by default, `-local` to keep private.** Suffix any file or dir
`-local` to git-ignore it. Full rule in [REFERENCE.md](REFERENCE.md).

Full schema, ownership table, and edge cases: **[REFERENCE.md](REFERENCE.md)**.

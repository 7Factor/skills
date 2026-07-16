---
name: meta-repo
description: Create, maintain, and work inside meta-repos — lightweight git repositories that define and document a working set of several independent repos (a.k.a. workspace repository; formerly pseudo-monorepo), wired together with relative symlinks. Use when the user wants to set up or manage a multi-repo workspace, add/remove member repos, onboard a teammate to a multi-repo setup, audit symlinks or repo consistency, regenerate workspace docs (AGENTS.md/README), produce a cross-repo architecture summary, or asks about meta-repo.yaml, workspace.yaml, pseudo-monorepos, or "which repos belong to this project." Also use to decide whether a task is scoped to one member repo or the whole workspace.
---

# meta-repo

A **meta-repo** is a thin git repo that gathers several *independent* git repositories
side by side for cross-repo navigation and coordinated change. It is **not** a monorepo,
**not** a submodule container, **not** a build/release tool. Each member keeps its own
history, build, deploy, and PR flow. Members are relative symlinks; the canonical roster
lives in **`meta-repo.yaml`**, which is written *only* by the engine.

## The engine does the mechanical work

All counting/parsing/cloning/symlinking is one self-contained script — **never hand-roll
it**. From inside any meta-repo:

```sh
python3 scripts/meta-repo.py <command>
```

If `scripts/meta-repo.py` doesn't exist in the meta-repo yet, run the copy bundled with
this skill — `scripts/meta-repo.py` sitting beside this `SKILL.md`. `init`/`heal` then
vendor a copy into the meta-repo so the engine travels with the repo (zero install for
teammates — just `python3`).

| Command | What it does | Acts? |
|---------|--------------|-------|
| `init [--name N --description D]` | Create a meta-repo in cwd; `git init`s the root if needed; **greedily adopts every** sibling symlink as an `active` member (curate the roster after) | writes |
| `add --name N [--path ../N \| --remote URL] [--role R] [--status S]` | Add a member (clones if `--remote` & missing); with only `--role`/`--status` on an existing member, **edits its metadata** (e.g. mark one `archived`) | writes |
| `remove N` | Drop from yaml + remove symlink. **Never deletes the real clone.** | writes |
| `sync` | Reconcile disk→yaml: clone missing from `remote`, fix symlinks | **acts** |
| `update [--switch]` | Fetch + fast-forward every member **and** the meta-repo to latest trunk (re-detects trunk fresh); skips dirty repos, stays on feature branches but flags them; `--switch` moves clean feature-branch members onto trunk | **acts** |
| `doctor` | Report health (`sync` / `heal` / needs-you) **plus an advisory list of loose root files**. Read-only | reports |
| `heal` | Fix safe hygiene (incl. `git init` if the root isn't a repo); **additive** to CLAUDE.md (never deletes) | acts |
| `manifest` | Roster + computed per-repo state as JSON (for you to consume) | reads |
| `docs [--force]` | Scaffold README/AGENTS/CLAUDE if absent, else report drift | writes-once |

Statuses: `active · legacy · greenfield · empty · archived`.

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
adopts any existing symlinks, and captures their `remote`/`default_branch`. For repos not yet
present, `add --remote <url>`. Then `docs` is already done by `init`; refine the scaffolded prose.

**Adopt / standardize an existing workspace** (a dir that already has symlinks, working files,
maybe a hand-written README — the "clean up an existing repo to conform" path). Run it in
stages, and **never move or delete a workspace file without showing the user the plan first**:

1. `init` — builds `meta-repo.yaml` from existing symlinks and `git init`s the root if it isn't
   a repo yet. It **greedily adopts every** sibling symlink as `active`, so first *curate the
   roster*: fix roles, set true statuses, and park or drop non-members
   (`add --name X --status archived`, or `remove X`) before anything else.
2. `doctor` — read-only. Beyond structural/hygiene/needs-you it prints a **WORKSPACE HYGIENE
   advisory**: loose files sitting at the root that aren't control files.
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

**Onboard a teammate.** They `git clone` the meta-repo, then `python3 scripts/meta-repo.py
sync` clones every missing member from its stored `remote` into the sibling layout and fixes
symlinks. One command → fully wired.

**Refresh the whole workspace.** `update` fetches and fast-forwards every member (and the
meta-repo) to its current trunk — re-detecting each member's real trunk from the remote, so a
trunk that moved upstream (e.g. a release branch → `main`) is caught and written back to
`meta-repo.yaml`. It never discards work: dirty members are skipped and listed for you to
finish/commit/stash (treat that list as "did I leave something unfinished here?"); members on a
feature branch stay put with their local trunk refreshed, and are flagged as possible stale/old
work. Review the flagged ones, then `update --switch` moves the *clean* ones onto trunk — ready
for new branches/worktrees. Don't switch members silently; show the user the flagged list first.

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
`meta-repo.yaml` + `scripts/meta-repo.py` + the `@AGENTS.md` line in `CLAUDE.md` + a managed
`.gitignore` block (which carries the `-local` convention and the member symlinks) are
engine-owned. `README.md` / `AGENTS.md` prose is scaffolded once then **yours** — the engine
only *reports* its drift.

**Notes & files — shared by default, `-local` to keep private.** A meta-repo is a shared
workspace: anything saved in it (docs, notes, scripts, plans) can and should be committed.
To keep something out, suffix its name with `-local` — any file or dir ending `-local` is
git-ignored (`scratch-local/`, `todo-local.md`). No private directory, no nesting; the engine
bakes `*-local` into the managed `.gitignore` so every meta-repo honors it. Fixed-name tool
files that can't take the suffix go in `.git/info/exclude`.

Full schema, ownership table, and edge cases: **[REFERENCE.md](REFERENCE.md)**.

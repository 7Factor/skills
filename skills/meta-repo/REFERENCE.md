# meta-repo — reference

The full contract behind the [SKILL.md](SKILL.md) quick reference. Read this when you need
the exact schema, the file-ownership boundary, command flags, or edge-case behavior.

## Concept

A **meta-repo** (a.k.a. *workspace repository*; formerly *pseudo-monorepo*) is a lightweight
git repository whose only job is to **define and document a working set of several
independent git repositories**. It exists to make cross-repo navigation, search, and
coordinated change tractable in one editor window / one agent session.

It **is**: a curated collection of related repos; a stable canonical root for AI agents; a
home for project-wide instructions, notes, and automation; a portable, shareable definition
of "which repos belong to this effort."

It is **not**: a monorepo, a git-submodule container, a build artifact, or a release tool.
Member repos stay fully independent — own history, own build, own deploy, own PRs.

Friendly prior art for the name: `mateodelnorte/meta` ("turn many repos into a meta repo").

## `meta-repo.yaml` schema

Written **only** by the engine (`init` / `add` / `remove`). Do not hand-edit — that's why
the engine can safely read it back with simple string parsing instead of a YAML library.

```yaml
name: LT Platform                 # human name of the workspace
description: Backend + clients     # one line; appears in scaffolded docs
repositories:
  - name: api                      # member id; also the symlink filename
    path: ../api                   # RELATIVE path to the sibling clone (the symlink target)
    role: Backend API              # one-line human role
    remote: git@github.com:org/api.git   # captured at add-time; enables self-heal clone
    default_branch: main           # captured at add-time; informational
    status: active                 # active | legacy | greenfield | empty | archived
```

Only `name` + `path` are strictly required per member; the rest are captured automatically
when the clone is present and a git remote exists. Values containing `: ` (colon-space) or
`#` are double-quoted on write and unquoted on read; everything else is plain.

## Canonical layout

Members live as **siblings of the meta-repo under a shared parent dir**, and symlinks are
always relative. This is the *only* supported topology (not members nested inside the
meta-repo, not absolute paths).

```
parent/                  # shared parent (dev names it whatever)
├── meta/                # the git repo you clone: meta-repo.yaml + scripts/ + symlinks
│   ├── meta-repo.yaml
│   ├── scripts/meta-repo.py
│   ├── AGENTS.md  CLAUDE.md  README.md  .gitignore
│   ├── api -> ../api
│   └── web -> ../web
├── api/                 # real clone, sibling
└── web/                 # real clone, sibling
```

`sync` clones missing members into `parent/` to match each `path`. The member symlinks are
**local wiring only** — git-ignored and (re)created by `sync`, never committed; `meta-repo.yaml`
is the source of truth for which repos belong here.

## Notes & files: shared by default, `-local` to keep private

A meta-repo is a **shared** workspace, so the default is simple: **anything saved in it —
docs, notes, scripts, investigations, plans — can and should be committed and shared.** No
"private" directory, no ceremony.

To keep something *out* of the repo, **suffix its name with `-local`** — any file or
directory ending in `-local` is git-ignored (`scratch-local/`, `todo-local.md`,
`db-notes-local.md`). The suffix is the whole convention: it travels with the file, announces
its own intent, and needs no nesting. The engine writes `*-local` / `*-local.*` into the
managed `.gitignore` block, so every meta-repo honors it automatically. (Fixed-name tool
files that can't take the suffix — `.idea/`, a tool lockfile — go in `.git/info/exclude`,
local and uncommitted.)

`doctor` lists loose root files as an **advisory** so they can be filed away. Acting on that
list — moving files into working dirs or deleting stale ones — is **agent judgment, never the
engine's**, and must be done only after presenting a concrete plan and getting the user's
explicit confirmation. The engine never moves or deletes workspace content.

## File ownership boundary

The rule that keeps `heal`/`docs` from clobbering human work:

| File | Owner | Engine behavior |
|------|-------|-----------------|
| `meta-repo.yaml` | engine | written only by `init`/`add`/`remove` |
| member symlinks | engine | created/fixed by `sync`; removed by `remove`; **git-ignored, never committed** — listed in the managed `.gitignore`; `heal` untracks any that were |
| `scripts/meta-repo.py` | engine | vendored on `init`; refreshed by `heal` when stale |
| `.gitignore` (managed block only) | engine | block between `# meta-repo:start/end` maintained by `init`/`add`/`remove`/`heal` — carries the `-local` convention (`*-local`, `*-local.*`) and the member symlink names; your rules outside it are untouched |
| `CLAUDE.md` | **additive-only** | `heal` ensures the `@AGENTS.md` line *exists*; **never deletes/overwrites** other content. Extra content is *reported* by `doctor` for you to migrate |
| `README.md`, `AGENTS.md` prose | you/agent | scaffolded once on `init`; afterward engine only **reports drift**, never rewrites (unless `docs --force`) |
| `*-local` files/dirs | you | git-ignored by convention; the engine never creates, reads, or touches them |

**Git boundary:** the meta-repo commits only its own metadata (yaml, docs, vendored script). The
member **symlinks are git-ignored** — local wiring regenerated by `sync` from the yaml, never
committed (a committed symlink just dangles for anyone who clones and clutters the host). It
**never** commits member code and **never** deletes a real clone — `remove` drops only the
symlink + yaml entry.

## Commands & flags

- `init [--name N] [--description D]` — create a meta-repo in the current dir. Errors if
  `meta-repo.yaml` already exists. **Runs `git init` if the root isn't a git repo yet**
  (never commits). **Greedily adopts every** existing sibling symlink as an `active` member
  (capturing remote/branch) — the agent must curate roles/statuses and drop non-members
  afterward. Scaffolds docs + `.gitignore` (whose managed block carries the `-local`
  convention) and vendors the engine. Non-interactive: the agent gathers `--name`/members by
  interviewing the user, then calls this.
- `add --name N [--path ../N | --remote URL] [--role R] [--status S]` — add or update a
  member (upsert by name). With `--remote` and no local dir, it **clones** into the sibling
  path (aborts on clone failure). Captures `remote`/`default_branch` from the clone. Creates
  the symlink; reports `conflict` if a real file occupies the name. **Metadata edit:** on an
  already-declared member, passing only `--role`/`--status` (no `--path`/`--remote`) edits
  that member in place — e.g. `add --name ce-docs --status archived` to park a vestigial repo.
- `remove N` — remove member `N` from yaml and delete its symlink. The real clone survives.
- `sync` — for each member: clone if missing & `remote` known; create/fix the symlink. Reports
  orphans (symlink not in yaml) and phantoms (in yaml, missing, no remote). Exits non-zero if
  any problem remains. Idempotent.
- `update [--switch]` — fetch `--prune` and advance each member **and the meta-repo itself** to
  latest trunk. Re-resolves trunk via `git remote set-head origin --auto` (catches an upstream
  trunk change; writes the new `default_branch` back to the roster when it drifts). Behavior per
  repo: **dirty** tree → skipped untouched and flagged (contributes to a non-zero exit); **on
  trunk** → `merge --ff-only` in place (reports if diverged, never forces); **on a feature
  branch** → refresh the local trunk ref (`fetch origin trunk:trunk`, ff-only) but **stay on the
  branch** and flag it. `--switch` additionally `checkout`s trunk on *clean* feature-branch
  members after refreshing. Never force-updates and never discards work. A repo with no `origin`
  (e.g. a meta-repo whose remote isn't created yet) is skipped with a note. Non-zero exit if any
  repo was dirty, failed to fast-forward, or is missing (feature-branch parking alone is not a
  failure — it's an advisory).
- `doctor` — read-only health report, grouped:
  - **STRUCTURAL → `sync`**: missing clones, missing/broken symlinks for declared members.
  - **HYGIENE → `heal`**: missing `@AGENTS.md` line, missing `.gitignore` block, broken
    *orphan* symlinks, stale vendored script.
  - **NEEDS YOU**: non-`@AGENTS.md` content in `CLAUDE.md` (migrate?), live orphan symlinks
    (add or remove?), README/AGENTS prose drift (members not mentioned).
  - **INFO**: a member sitting on a non-default branch (not a problem — devs use feature
    branches; never nag about this).
  - **WORKSPACE HYGIENE (advisory)**: loose regular files at the root that aren't control
    files (see below). Purely advisory — it lists cleanup candidates but **never affects the
    exit code**. Directories, member symlinks, and dotfiles are ignored.
  - Exit non-zero if any STRUCTURAL/HYGIENE/NEEDS-YOU item exists (advisory items do not count).
- `heal` — apply safe deterministic fixes only: `git init` the root if it isn't a repo, create
  `CLAUDE.md` or prepend the `@AGENTS.md` line (keeping all existing content), add the
  `.gitignore` managed block, refresh a stale vendored script, remove broken *orphan* symlinks.
  Will **not** clone/relink declared members (that's `sync`), **not** edit other `CLAUDE.md`
  content, and **not** move or delete workspace files (that's agent judgment, post-confirmation).
- `manifest` — JSON: workspace name/description, engine version, and per member its yaml fields
  plus computed `on_disk`, `symlink_ok`, `current_branch`, and `state`
  (`present|missing|broken-symlink|no-symlink`). The machine-readable roster for agents.
- `docs [--force]` — if README/AGENTS/CLAUDE are absent, scaffold them; otherwise report prose
  drift without rewriting. `--force` overwrites scaffolds (destructive to prose — confirm with
  the user first).

## Edge cases

- **Bad/unreachable remote on `add`/`sync`** — `add` aborts before writing the entry; `sync`
  records it as a problem and continues with other members (non-zero exit).
- **SSH vs HTTPS remotes differ per teammate** — the stored `remote` is whatever was captured
  at add-time. A teammate who uses the other transport may need to adjust; `sync` uses the
  stored URL as-is.
- **Symlink name collides with a real file/dir** — reported as `conflict`; resolve manually.
- **Fresh clone of the meta-repo** — member symlinks dangle harmlessly until `sync` clones the
  siblings from their stored remotes.
- **Engine version drift** — `META_REPO_VERSION` is stamped in the file; `doctor` compares the
  vendored copy to the running engine, `heal` refreshes the vendored copy from whichever engine
  is running (higher `META_REPO_VERSION` wins).
- **No YAML library / no `yq`** — intentional. The engine is the sole writer, so it only ever
  reads back its own constrained output. One mechanism, no dependency, no fallback path.

## Relationship to the installed skill

The engine and this documentation ship with the **meta-repo skill** (published in the 7Factor
skills catalog, `github.com/7Factor/skills`). `init`/`heal` **vendor** `scripts/meta-repo.py`
into each meta-repo so the engine travels with the repo and a teammate needs only `python3` — no
skill install. Installing the skill makes an agent *better* at meta-repo judgment work
(interviewing, scoping, architecture summaries) but is not required for the repo to function.
Wherever the skill is installed, that copy is the upstream for vendoring; the catalog is the
source of truth for the skill itself. The scaffolded `AGENTS.md` carries the topology + scoping
rules so even an agent without the skill is oriented.

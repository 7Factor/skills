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
Every read also validates the parsed structure (see **Structural validation** below), so a
hand-edit that breaks the shape fails loudly rather than corrupting the roster.

```yaml
name: LT Platform                 # human name of the workspace
description: Backend + clients     # one line; appears in scaffolded docs
repositories:
  - name: api                      # member id; also the symlink filename
    path: ../api                   # RELATIVE path to the sibling clone (the symlink target)
    role: Backend API              # one-line human role
    remote: git@github.com:org/api.git   # captured at add-time; enables self-heal clone
    default_branch: main           # captured at add-time; informational
    status: active                 # active | archived
```

Only `name` + `path` are strictly required per member; the rest are captured automatically
when the clone is present and a git remote exists. Values containing `: ` (colon-space) or
`#` are double-quoted on write and unquoted on read; everything else is plain.

### Structural validation

On every read, the engine checks that the parsed file matches this schema: top level is a
mapping with a `repositories` key, `repositories` is a list, and every entry in it is a
mapping with non-empty `name` and `path`. A violation raises a clear, specific error instead
of a traceback or a silently mis-parsed roster. This is the technical backstop for the "engine
writes it, don't hand-edit" contract, which is otherwise social, not enforced.

Validation checks *structure* only, not field *values* — an unrecognized `status` (e.g. an old
`legacy` value written before `active`/`archived` became the only valid pair) is tolerated on
read. Only `add --status` rejects unrecognized values, and only on write.

## Canonical layout

Members live as **siblings of the meta-repo under a shared parent dir**, and symlinks are
always relative. This is the *only* supported topology (not members nested inside the
meta-repo, not absolute paths).

```
parent/                  # shared parent (dev names it whatever)
├── meta/                # the git repo you clone: meta-repo.yaml + symlinks + docs
│   ├── meta-repo.yaml
│   ├── AGENTS.md  CLAUDE.md  README.md  .gitignore
│   ├── api -> ../api
│   └── web -> ../web
├── api/                 # real clone, sibling
└── web/                 # real clone, sibling
```

`sync` clones missing members into `parent/` to match each `path`. The member symlinks are
**local wiring only** — git-ignored and (re)created by `sync`, never committed; `meta-repo.yaml`
is the source of truth for which repos belong here.

The engine itself (`scripts/meta-repo.py` + `scripts/engine/`) is never copied into this
layout — it lives only wherever the **meta-repo skill** is installed, and every command is run
from there against the target meta-repo. There is no vendored copy to keep in sync and no
version-drift concept to reconcile.

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
| `meta-repo.yaml` | engine | written only by `init`/`add`/`remove`; structurally validated on every read |
| member symlinks | engine | created/fixed by `sync`; removed by `remove`; **git-ignored, never committed** — listed in the managed `.gitignore`; `heal` untracks any that were, and removes broken orphans |
| `.gitignore` (managed block only) | engine | block between `# meta-repo:start/end` maintained by `init`/`add`/`remove`/`heal` — carries the `-local` convention (`*-local`, `*-local.*`) and the member symlink names; your rules outside it are untouched |
| `CLAUDE.md` | **additive-only** | `heal` ensures the `@AGENTS.md` line *exists*; **never deletes/overwrites** other content. Extra content is *reported* by `doctor` for you to migrate |
| `README.md`, `AGENTS.md` prose | you/agent | scaffolded once on `init`; afterward engine only **reports drift**, never rewrites (unless `docs --force`) |
| `*-local` files/dirs | you | git-ignored by convention; the engine never creates, reads, or touches them |

**Git boundary:** the meta-repo commits only its own metadata (yaml, docs, `.gitignore`). The
member **symlinks are git-ignored** — local wiring regenerated by `sync` from the yaml, never
committed (a committed symlink just dangles for anyone who clones and clutters the host). It
**never** commits member code and **never** deletes a real clone — `remove` drops only the
symlink + yaml entry.

## Commands & flags

- `init [--name N] [--description D]` — create a meta-repo in the current dir. Errors if
  `meta-repo.yaml` already exists. **Runs `git init` if the root isn't a git repo yet**
  (never commits). Adopts every existing sibling symlink that is *member-shaped* — relative,
  pointing at a directory that exists and is itself a git repo — as an `active` member,
  capturing its `remote`/`default_branch`. A sibling symlink that is dangling, or whose target
  exists but isn't a git repo, is **skipped**: reported by name with a visible reason and left
  out of the roster (add it manually with `add --remote`/`--path` if it should be a member). An
  absolute symlink, or one whose target isn't under the parent dir, is never touched or
  considered. The agent must still curate roles/statuses of adopted members afterward. Scaffolds
  docs + `.gitignore` (whose managed block carries the `-local` convention). Non-interactive:
  the agent gathers `--name`/members by interviewing the user, then calls this.
- `add --name N [--path ../N | --remote URL] [--role R] [--status S]` — add or update a
  member (upsert by name). With `--remote` and no local dir, it **clones** into the sibling
  path (aborts on clone failure). Captures `remote`/`default_branch` from the clone. Creates
  the symlink; reports `conflict` if a real file occupies the name. `--status` accepts only
  `active`/`archived` — any other value is rejected with a clear error. **Metadata edit:** on
  an already-declared member, passing only `--role`/`--status` (no `--path`/`--remote`) edits
  that member in place — e.g. `add --name ce-docs --status archived` to park a vestigial repo.
- `remove N` — remove member `N` from yaml and delete its symlink. The real clone survives.
- `sync` — for each member: clone if missing & `remote` known; create/fix the symlink. Reports
  orphans (symlink present but not in yaml) and phantoms (in yaml, missing, no remote). An
  orphan is informational only and does **not** affect the exit code; a phantom, a clone
  failure, or a symlink conflict does. Exits non-zero only on a genuine problem. Idempotent.
- `update` — fetch `--prune` and advance each non-`archived` member **and the meta-repo
  itself** to latest trunk. Re-resolves trunk via `git remote set-head origin --auto` (catches
  an upstream trunk change; writes the new `default_branch` back to the roster when it
  drifts). Behavior per repo: **dirty** tree → skipped untouched and flagged (contributes to a
  non-zero exit); **on trunk** → `merge --ff-only` in place (reports if diverged, never
  forces); **on a feature branch** → refresh only the local trunk ref (e.g.
  `fetch origin main:main`, ff-only) so `git status`/`git log` show true drift against trunk,
  while the member's actual checkout/branch is **never touched** — flagged as informational,
  not acted on. `archived` members are skipped entirely: no fetch, no dirty-check, no effect
  on the exit code. A repo with no `origin` (e.g. a meta-repo whose remote isn't created yet)
  is skipped with a note. There is no flag to switch or check out a branch — `update` never
  changes what a member has checked out. Non-zero exit if any repo was dirty, failed to
  fast-forward, or is missing (feature-branch parking alone is not a failure — it's an
  advisory).
- `doctor` — read-only health report, grouped:
  - **STRUCTURAL → `sync`**: missing clones, missing/broken symlinks for declared members.
  - **HYGIENE → `heal`**: missing `@AGENTS.md` line, missing `.gitignore` block, broken
    *orphan* symlinks, a member symlink tracked in git.
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
  `.gitignore` managed block, untrack any member symlink that got committed, remove broken
  *orphan* symlinks. Will **not** clone/relink declared members (that's `sync`), **not** edit
  other `CLAUDE.md` content, and **not** move or delete workspace files (that's agent judgment,
  post-confirmation).
- `manifest` — JSON: workspace name/description, `engine_version` (the running engine's
  `META_REPO_VERSION`, for your own diagnostics — not compared against anything vendored,
  since nothing is), and per member its yaml fields plus computed `on_disk`, `symlink_ok`,
  `current_branch`, and `state` (`present|missing|broken-symlink|no-symlink`). The
  machine-readable roster for agents.
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
- **Malformed `meta-repo.yaml`** — a hand-edit that breaks the documented shape (missing
  `repositories`, a member missing `name`/`path`, a non-list `repositories`) fails every
  command with a specific `YamlValidationError` message rather than a traceback or a silently
  wrong roster. An unrecognized field *value* (e.g. a `status` from before the two-value enum)
  is tolerated on read.
- **No YAML library / no `yq`** — intentional. The engine is the sole writer, so it only ever
  reads back its own constrained output (now with structural validation on top). One
  mechanism, no dependency, no fallback path.

## Relationship to the installed skill

The engine and this documentation ship with the **meta-repo skill** (published in the 7Factor
skills catalog, `github.com/7Factor/skills`). The engine is never copied into a meta-repo it
manages — it runs from wherever the skill is installed, against whichever meta-repo you point
it at. Installing the skill makes an agent *better* at meta-repo judgment work (interviewing,
scoping, architecture summaries); running the engine itself only needs `python3` and `git` on
the machine doing the work. The scaffolded `AGENTS.md` carries the topology + scoping rules so
even an agent without the skill installed is oriented once inside a meta-repo.

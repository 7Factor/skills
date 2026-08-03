# meta-repo — reference

Full contract behind [SKILL.md](SKILL.md): schema, file ownership, command flags, edge cases.

## Concept

A **meta-repo** (a.k.a. *workspace repository*; formerly *pseudo-monorepo*) is a lightweight
git repo that defines and documents a working set of several independent git repos, for
cross-repo navigation and coordinated change in one place.

**Is:** a curated collection of related repos; a stable canonical root for AI agents; a home
for project-wide instructions, notes, and automation; a portable, shareable definition of
"which repos belong to this effort."

**Is not:** a monorepo, a git-submodule container, a build artifact, a release tool. Members
stay fully independent — own history, build, deploy, PRs.

## `meta-repo.yaml` schema

Written only by the engine (`init`/`add`/`remove`). Don't hand-edit: the engine reads it back
with simple string parsing, not a YAML library, and every read validates structure (below) —
a broken hand-edit fails loudly instead of corrupting the roster.

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

Required per member: `name`, `path`. Everything else is captured automatically when the clone
is present and has a git remote. Write rule: values containing `: ` or `#` are double-quoted;
everything else is plain.

### Structural validation

Every read checks: top level is a mapping with a `repositories` key; `repositories` is a
list; each entry is a mapping with non-empty `name` and `path`. A violation raises a specific
error — no traceback, no silently mis-parsed roster.

Structure only, not field values: an unrecognized `status` (e.g. a `legacy` value from before
the two-value enum) loads fine. Only `add --status` rejects unrecognized values, and only on
write.

## Canonical layout

Members are siblings of the meta-repo under a shared parent dir; symlinks are always relative.
Only supported topology — no members nested inside the meta-repo, no absolute paths.

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

`sync` clones missing members into `parent/` to match each `path`. Member symlinks are local
wiring only: git-ignored, (re)created by `sync`, never committed. `meta-repo.yaml` is the
source of truth for membership.

The engine (`scripts/meta-repo.py` + `scripts/engine/`) is never copied into this layout. It
runs from wherever the meta-repo skill is installed, against whichever meta-repo you point it
at — no vendored copy, no version-drift to reconcile.

## Notes & files: shared by default, `-local` to keep private

Default: anything saved in the meta-repo — docs, notes, scripts, investigations, plans — is
committed and shared. No private directory.

To exclude a file, suffix its name with `-local` (`scratch-local/`, `todo-local.md`,
`db-notes-local.md`). The engine writes `*-local`/`*-local.*` into the managed `.gitignore`
block, so every meta-repo honors it. Fixed-name tool files that can't take the suffix
(`.idea/`, a tool lockfile) go in `.git/info/exclude` instead — local, uncommitted.

`doctor` lists loose root files as an advisory. Filing them away — into a working dir, or
deleting stale ones — is agent judgment, done only after the user confirms a concrete plan.
The engine itself never moves or deletes workspace content.

## File ownership boundary

Keeps `heal`/`docs` from clobbering human work:

| File | Owner | Engine behavior |
|------|-------|-----------------|
| `meta-repo.yaml` | engine | written only by `init`/`add`/`remove`; validated on every read |
| member symlinks | engine | created/fixed by `sync`; removed by `remove`; git-ignored, never committed; `heal` untracks any that were committed and removes broken orphans |
| `.gitignore` (managed block) | engine | block between `# meta-repo:start/end`, maintained by `init`/`add`/`remove`/`heal`; carries the `-local` convention and member symlink names; rules outside the block are untouched |
| `CLAUDE.md` | additive-only | `heal` ensures the `@AGENTS.md` line exists; never deletes/overwrites other content; extra content is reported by `doctor` for you to migrate |
| `README.md`, `AGENTS.md` prose | you/agent | scaffolded once on `init`; after that, engine only reports drift — never rewrites, unless `docs --force` |
| `*-local` files/dirs | you | git-ignored by convention; engine never creates, reads, or touches them |

**Git boundary:** the meta-repo commits only its own metadata (yaml, docs, `.gitignore`).
Member symlinks are git-ignored, regenerated by `sync` from the yaml, never committed — a
committed symlink just dangles for anyone who clones. Member code is never committed here;
`remove` drops only the symlink and yaml entry, never the real clone.

## Commands & flags

- **`init [--name N] [--description D]`** — create a meta-repo in the current dir. Errors if
  `meta-repo.yaml` already exists. Runs `git init` if the root isn't a git repo yet (never
  commits). Adopts every sibling symlink that is member-shaped — relative, target exists, target
  is a git repo — as an `active` member, capturing `remote`/`default_branch`. Skips (reports by
  name, with reason, not added to roster) a dangling symlink or one whose target isn't a git
  repo; add it manually with `add` if it should be a member. Ignores absolute symlinks and ones
  pointing outside the parent dir. Curate adopted members' roles/statuses afterward. Scaffolds
  docs + `.gitignore`. Non-interactive — the agent gathers `--name`/members by interviewing the
  user first.
- **`add --name N [--path ../N | --remote URL] [--role R] [--status S]`** — add or update a
  member (upsert by name). With `--remote` and no local dir, clones into the sibling path
  (aborts on failure), capturing `remote`/`default_branch`. Creates the symlink; reports
  `conflict` if a real file occupies the name. `--status` accepts only `active`/`archived`;
  any other value is rejected. **Metadata edit:** on an already-declared member, passing only
  `--role`/`--status` (no `--path`/`--remote`) edits it in place — e.g.
  `add --name ce-docs --status archived` to park a vestigial repo.
- **`remove N`** — drop member `N` from yaml, delete its symlink. Real clone survives.
- **`sync`** — for each member: clone if missing and `remote` known; create/fix the symlink.
  Reports orphans (symlink present, not in yaml) and phantoms (in yaml, missing, no remote).
  Orphans are informational and don't affect the exit code; phantoms, clone failures, and
  symlink conflicts do. Idempotent.
- **`update`** — fetch `--prune` and advance each non-`archived` member, and the meta-repo
  itself, to latest trunk. Re-resolves trunk via `git remote set-head origin --auto` (catches an
  upstream trunk rename; writes the new `default_branch` back to the roster on drift). Per repo:
  dirty tree → skipped, flagged, non-zero exit; on trunk → `merge --ff-only` in place (reports
  divergence, never forces); on a feature branch → refresh only the local trunk ref (e.g.
  `fetch origin main:main`, ff-only) so `git status`/`git log` show true drift, while the
  member's checkout is never touched — flagged as informational. `archived` members are skipped
  entirely: no fetch, no dirty-check, no effect on exit code. A repo with no `origin` is skipped
  with a note. No flag switches or checks out a branch — `update` never changes what a member
  has checked out. Non-zero exit if any repo was dirty, failed to fast-forward, or is missing.
- **`doctor`** — read-only health report, grouped:
  - **STRUCTURAL → `sync`**: missing clones, missing/broken symlinks for declared members.
  - **HYGIENE → `heal`**: missing `@AGENTS.md` line, missing `.gitignore` block, broken orphan
    symlinks, a member symlink tracked in git.
  - **NEEDS YOU**: non-`@AGENTS.md` content in `CLAUDE.md`; live orphan symlinks; README/AGENTS
    prose drift.
  - **INFO**: a member on a non-default branch — not a problem, never nag about it.
  - **WORKSPACE HYGIENE (advisory)**: loose regular files at the root that aren't control files.
    Never affects the exit code. Directories, member symlinks, dotfiles ignored.
  - Non-zero exit if any STRUCTURAL/HYGIENE/NEEDS-YOU item exists.
- **`heal`** — safe deterministic fixes only: `git init` the root if needed; create `CLAUDE.md`
  or prepend the `@AGENTS.md` line (keeping existing content); add the `.gitignore` managed
  block; untrack any committed member symlink; remove broken orphan symlinks. Never clones or
  relinks declared members (that's `sync`), never edits other `CLAUDE.md` content, never moves
  or deletes workspace files (agent judgment, post-confirmation).
- **`manifest`** — JSON: workspace name/description, `engine_version` (diagnostic only — not
  compared against a vendored copy, since none exists), and per member its yaml fields plus
  computed `on_disk`, `symlink_ok`, `current_branch`, `state`
  (`present|missing|broken-symlink|no-symlink`). The machine-readable roster for agents.
- **`docs [--force]`** — scaffold README/AGENTS/CLAUDE if absent; otherwise report prose drift
  without rewriting. `--force` overwrites scaffolds — destructive to prose, confirm with the
  user first.

## Edge cases

- **Bad/unreachable remote on `add`/`sync`** — `add` aborts before writing the entry; `sync`
  records it as a problem and continues with other members (non-zero exit).
- **SSH vs HTTPS remotes differ per teammate** — `remote` is whatever was captured at add-time.
  A teammate on the other transport may need to adjust it; `sync` uses the stored URL as-is.
- **Symlink name collides with a real file/dir** — reported as `conflict`; resolve manually.
- **Fresh clone of the meta-repo** — member symlinks dangle harmlessly until `sync` clones the
  siblings from their stored remotes.
- **Malformed `meta-repo.yaml`** — a hand-edit that breaks the schema (missing `repositories`,
  a member missing `name`/`path`, a non-list `repositories`) fails every command with a specific
  `YamlValidationError` — no traceback, no silently wrong roster. An unrecognized field value
  (e.g. a pre-enum `status`) still loads fine.
- **No YAML library** — intentional. The engine is the sole writer, so it only ever reads back
  its own constrained output, now with structural validation on top. One mechanism, no
  dependency, no fallback path.

## Relationship to the installed skill

The engine and this doc ship with the meta-repo skill (`github.com/7Factor/skills`). The
engine is never copied into a meta-repo it manages — it runs from wherever the skill is
installed, against whichever meta-repo you point it at. Installing the skill makes an agent
better at meta-repo judgment work (interviewing, scoping, architecture summaries); running the
engine itself needs only `python3` and `git`. The scaffolded `AGENTS.md` carries the topology
and scoping rules, so even an agent without the skill installed is oriented once inside a
meta-repo.

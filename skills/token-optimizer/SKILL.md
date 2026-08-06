---
name: token-optimizer
description: >
  Maintains a per-repository architecture map so future work skips
  exploratory file reading and keeps token usage down. Use when starting
  work in an unfamiliar area of the current repository, when asked "where
  does X live" or "how is this codebase organized", before any task
  spanning multiple modules, or when asked to generate, update, or
  refresh the codebase overview.
---

# Codebase Overview

This skill maintains a per-repository architecture map at
`.claude/codebase-overview.md` in the repo root.

## Step 1: Check whether the map exists

Look for `.claude/codebase-overview.md` in the current repository.

**If it exists:** read it and use it as your primary source for
architecture questions. Only fall back to exploring files when the map
doesn't cover what you need — and if you discover the map is stale or
wrong, tell the user and offer to update it.

**If it does not exist:** tell the user this repo has no architecture map
yet and offer to generate one ("This costs tokens once, then saves
exploration in every future session"). If they agree, follow Step 2.

## Step 2: Generate the map (only with user approval)

Explore the codebase efficiently — prefer directory listings and grep over
reading whole files — then write `.claude/codebase-overview.md` with these
sections, keeping the whole file under 150 lines:

- **Architecture summary** — 3-5 sentences: what the system does, major
  boundaries, how data flows
- **Directory map** — one line per important directory: path, purpose,
  key files
- **Key entry points** — where requests/jobs/events enter, with file:line
  references
- **Conventions** — naming patterns, error handling style, test locations
- **Cross-cutting concerns** — auth, logging, config, feature flags
- **Gotchas** — generated files, deprecated modules, intentional oddities

Rules for the generated file:
- Describe and point (file:line); never paste code blocks.
- Don't duplicate anything already in the repo's CLAUDE.md (commands,
  package manager, hard rules).
- Terse over complete: this file is read by an LLM, not onboarding docs.

Example directory-map and entry-point lines:
```
- `src/api/` — REST route handlers, one file per resource — `src/api/orders.ts`
- Job queue consumer starts at `src/workers/index.ts:12`
```

## Step 3: Keep it current

When completing a task that changed the architecture (new top-level
module, moved directory, new entry point), offer to update the relevant
lines of the map. Update surgically; don't regenerate.

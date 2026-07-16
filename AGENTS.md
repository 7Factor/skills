# AGENTS.md

This file provides guidance to coding agents (Claude Code, Codex, and others) when working with code in this repository.

## Workflow

`main` is protected: you **cannot push directly to `main`**. All changes land via a pull request —
branch, push the branch, and open a PR (only when the user directs a push).

## What this repo is

A catalog of company-maintained **agent skills** for 7Factor. Each skill is a directory under `skills/`
containing a `SKILL.md` (frontmatter + instructions) plus any bundled scripts/reference files it needs.
Skills are consumed two ways, which are **not** equivalent:

- **Skills CLI** (`npx skills add 7Factor/skills --skill <name>`) — copies skill files only. It does
  **not** install hooks, MCP servers, or agents. Cross-agent (Claude Code, Codex, etc.).
- **Claude Code plugin** (`/plugin marketplace add 7Factor/skills` → `/plugin install <name>@7factor`) —
  installs the skill **and** its hooks. Required whenever a skill depends on a hook.

`.claude-plugin/marketplace.json` is the plugin manifest that drives the second path.

## Repo layout gotchas

- `.claude/skills` is a **symlink** to `.agents/skills`. The repo-local `write-a-skill` skill lives at
  `.agents/skills/write-a-skill/` and is the authoring guide/checklist — use it when adding or changing a skill.
- `skills/` holds the published skills; `.agents/skills/` holds repo-local tooling skills. Don't confuse them.
- Some skills bundle Python scripts and a `tests/` dir alongside `SKILL.md` (e.g. the meta-repo skill on its
  feature branch). The SKILL.md stays concise; heavy logic and reference material live in adjacent files.

## marketplace.json: source format matters

A plugin entry that ships skills must **not** combine a bare relative-string `source` with a `skills` array —
that specific combination trips Claude Code's plugin resolver into a misleading "update Claude Code" error.
Use the `git-subdir` object form for skill-bearing plugins:

```json
"source": {
  "source": "git-subdir",
  "url": "https://github.com/7Factor/skills.git",
  "path": "skills/<name>",
  "ref": "main"
}
```

After editing `marketplace.json`, changes only take effect once pushed and the marketplace is re-pulled
(`/plugin marketplace update 7factor`); the copy under `~/.claude/plugins/marketplaces/7factor` is a cache.

## claude-usage-report skill

Two-tier, date-aware Claude Code cost reporting from local transcripts. Python 3, no third-party deps.

- `usage_report.py [today | YYYY-MM-DD | start end | 7d|week|month] [--top N]` — parses transcripts and prints
  cost aggregates (BY MODEL/DAY/PROJECT/SESSION) plus the human prompts of the costliest sessions. The **skill**
  turns this output into the report and derives no numbers itself.
- Pricing is **date-aware**: each message is costed at the rate in effect on its UTC day, read from
  `prices.json` next to the script.
- `update_pricing.py` is the **deterministic tier**: it fetches Anthropic's pricing page, parses the table,
  and only syncs `prices.json` if a sanity gate passes (appends effective-dated records, never clobbers known
  future ones). If the parse fails the gate it writes nothing and errors, so the skill can fall back to an
  **agent-repair tier** (fetch the page, fix the parser).
- Per-account attribution requires the plugin's `SessionStart` hook (`hooks/hooks.json` →
  `record_account.sh` → `record_account.py`). Transcripts don't record which account was active, so without the
  hook the "By account" table shows `unknown`. `record_account.sh` resolves a Python 3 interpreter defensively
  and **always exits 0** — a session must never be blocked by attribution.

## Conventions when adding/changing a skill

1. Follow the `write-a-skill` skill's structure and review checklist.
2. Frontmatter needs a short `name` and a trigger-focused `description` (this is what decides when the skill
   loads). Add `compatibility:` when the skill assumes a specific agent/runtime.
3. Keep `SKILL.md` concise enough to load quickly; move long examples/reference into adjacent files.
4. If a skill needs a hook/MCP/agent, remember Skills-CLI installs won't get it — document the plugin path.

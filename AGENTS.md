# AGENTS.md

This file provides guidance to coding agents (Claude Code, Codex, and others) when working with code in this repository.

## Workflow

`main` is protected: you **cannot push directly to `main`**. All changes land via a pull request to main (push only when the user directs it).

## Organization

- `.claude/skills` is a **symlink** to `.agents/skills`. The repo-local `write-a-skill` skill lives at
  `.agents/skills/write-a-skill/` and is the authoring guide/checklist — use it when adding or changing a skill.
- Some skills in `.agents/skills` may be **symlinks** to skills in `skills` to guarantee the version of a skill 
  used is the latest one in the repository. 

## Skill install paths are not equivalent

Skills in this repo are consumed two ways, and they install different things:

- **skills.sh** (`npx skills add 7Factor/skills --skill <name>`) — copies skill files only. It does
  **not** install hooks, MCP servers, or agents. Cross-agent (Claude Code, Codex, etc.).
- **Claude Code plugin** (`/plugin marketplace add 7Factor/skills` → `/plugin install <name>@7factor`) —
  installs the skill **and** its hooks. Required whenever a skill depends on a hook.

If a skill needs a hook/MCP/agent, remember skills.sh installs won't get it — document the plugin path.

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

# 7Factor Skills

Shared agent skills maintained by 7Factor Software.

This repository is a catalog for company-maintained skills. Skills live in the `skills/` directory. Each skill is a
directory with a `SKILL.md` file that describes when the skill should be loaded and how the agent should behave.

## Available Skills

- `mentor`: switches an agent into learning-first mentoring mode for developing engineers.
- `claude-usage-report`: reports Claude Code usage & cost from local session transcripts.
  (For per-account attribution across multiple accounts, install as a plugin instead — [see below](#installing-claude-usage-report-skill-vs-plugin).)
- `token-optimizer`: generates and maintains a per-repo architecture map so agents skip exploratory file reading. (For the full token savings, install as a plugin which adds a Haiku explorer subagent, a test-output filtering hook, and a repo bootstrap command — [see below](#installing-token-optimizer-skill-vs-plugin).)


## Install

The recommended installer is the Skills CLI documented at [skills.sh](https://www.skills.sh/docs).

Install a skill from this repository:

```sh
npx skills add 7Factor/skills --skill <skill-name>
```

For example:

```sh
npx skills add 7Factor/skills --skill mentor
```

Install a skill globally for Codex:

```sh
npx skills add 7Factor/skills --skill <skill-name> --agent codex --global
```

During local development from this checkout:

```sh
npx skills add . --skill <skill-name>
```

The CLI can target different agents and scopes. Check the current options with:

```sh
npx skills add --help
```

To opt out of Skills CLI telemetry:

```sh
DISABLE_TELEMETRY=1 npx skills add 7Factor/skills --skill <skill-name>
```

## Installing `claude-usage-report` (skill vs. plugin)

`claude-usage-report` can be installed two ways, and they are **not** equivalent:

- **As a Claude Code plugin (recommended):** installs the skill **and** a `SessionStart`
  hook. The hook records which Claude account is active for each session — the only local
  source of that information, since transcripts don't capture it. Without it the report's
  **By account** table shows every session as `unknown`.

  ```sh
  /plugin marketplace add 7Factor/skills
  /plugin install claude-usage-report@7factor
  ```

- **As a plain skill via the Skills CLI:** installs the skill **only**. The `npx skills`
  CLI copies skill files; it does **not** install hooks (or MCP servers, or agents). So the
  report still runs, but account attribution degrades to `unknown` for every session going
  forward.

  ```sh
  npx skills add 7Factor/skills --skill claude-usage-report
  ```

**The tradeoff:** `npx` is the quick, cross-agent way to get the report, at the cost of
per-account attribution. If you need to know *which account* a report or session belongs to
— e.g. splitting spend across a personal and a work login — install it as a plugin instead.
Everything else (pricing, per-session detail, totals) is identical between the two.

## Installing `token-optimizer` (skill vs. plugin)

- **As a Claude Code plugin (recommended):** installs the skill **plus** an `explorer` subagent (routes verbose work to Haiku), a `PreToolUse` hook that filters test output to failures-only, and a `/token-optimizer:setup` command that bootstraps a repo with a lean CLAUDE.md. The hook and subagent are where most of the token savings come from; the Skills CLI cannot install them.

  /plugin marketplace add 7Factor/skills
  /plugin install token-optimizer@7factor

- **As a plain skill via the Skills CLI:** installs the codebase-overview behavior only — architecture-map generation, but no output filtering, no Haiku delegation, and no setup command.

  npx skills add 7Factor/skills --skill token-optimizer

After installing the plugin, run `/token-optimizer:setup` once per repo.


## Use

Invoke installed skills by asking the agent for the relevant behavior. The exact phrasing depends on the skill.

For example, after installing `mentor`:

```text
Use mentor mode while helping me debug this issue.
```

## Contributing

When adding or changing a skill:

1. Use the repo-local `write-a-skill` skill in `.agents/skills/write-a-skill` to guide the structure and review checklist.
2. Keep the skill name short and specific.
3. Put the main instructions in `skills/<skill-name>/SKILL.md`.
4. Keep `SKILL.md` concise enough for an agent to load quickly.
5. Move lengthy examples or reference material into adjacent files only when needed.
6. Verify the frontmatter includes a clear `name` and trigger-focused `description`.

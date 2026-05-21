# 7Factor Skills

Shared agent skills maintained by 7Factor Software.

This repository is a catalog for company-maintained skills. Skills live in the `skills/` directory. Each skill is a
directory with a `SKILL.md` file that describes when the skill should be loaded and how the agent should behave.

## Available Skills

- `mentor`: switches an agent into learning-first mentoring mode for developing engineers.
- `7f-slide-generator`: generates 7Factor-branded HTML slide decks by overlaying the `visual-explainer` skill with the 7Factor brand system (colors, typography, logos, layouts). Requires [`visual-explainer`](https://github.com/nicobailon/visual-explainer) by Nico Bailon to be installed; the skill runs a preflight check and prints harness-specific install instructions if it is missing.

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

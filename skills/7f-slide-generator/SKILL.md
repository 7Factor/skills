---
name: 7f-slide-generator
description: Generate 7Factor-branded HTML slide decks by delegating slide mechanics to the visual-explainer skill and applying the 7Factor brand system (colors, typography, logos, layouts). Use when the user asks for 7Factor slides, 7F slides, company-branded slides, or invokes /generate-7f-slides.
---

# 7Factor Slide Generator

An overlay skill that composes with the [`visual-explainer`](https://github.com/nicobailon/visual-explainer) skill by Nico Bailon. It does not replace `visual-explainer` — it constrains its aesthetics to the 7Factor brand.

## Dependency: visual-explainer

This skill is **non-functional without `visual-explainer` installed**. It delegates all slide mechanics (viewport-fit single-file HTML, navigation, diagram rendering) to that skill and only applies the brand overlay on top.

### Preflight check (run before anything else)

1. Detect the agent harness from environment markers (in priority order):
   - Claude Code: `~/.claude/` exists or `$CLAUDECODE`/`$CLAUDE_CODE_*` env vars set
   - Codex CLI: `~/.codex/` exists
   - Pi: `~/.pi/` exists
   - OpenCode: `~/.config/opencode/` exists
   - Cursor: `.cursor/` in the working tree
   - OpenClaw: `~/.openclaw/` exists
2. Check whether `visual-explainer` is installed at the harness-appropriate path:
   - Claude Code: `~/.claude/plugins/**/visual-explainer/` or `~/.claude/skills/visual-explainer/` or `.claude/skills/visual-explainer/`
   - Codex: `~/.codex/skills/visual-explainer/`
   - Pi: `~/.pi/agent/skills/visual-explainer/`
   - OpenCode: `~/.config/opencode/skill/visual-explainer/`
   - Cursor / OpenClaw / unknown: any of the above
3. If not found, **stop and print the install message below.** Do not attempt to generate slides without it — the brand contract assumes visual-explainer's slide-deck mechanics.

### Install instructions bookmark

The install commands below were captured against the upstream `visual-explainer` repo at:

- **Commit**: `8f1d0e3` ("feat: add cross-harness package compatibility")
- **Date**: 2026-04-27
- **Source**: https://github.com/nicobailon/visual-explainer/blob/main/README.md

**Before printing the install message**, verify the bookmark is still current:

1. Fetch the upstream README's install section (e.g. `gh api repos/nicobailon/visual-explainer/contents/README.md` or a `WebFetch` of the raw README).
2. Confirm the install commands for the detected harness still match what is printed below.
3. If they do **not** match (renamed marketplace, changed path, new install tool, etc.), tell the user:
   > The 7f-slide-generator install instructions for `visual-explainer` appear to be out of date relative to the upstream README at https://github.com/nicobailon/visual-explainer. Please notify Scott Pfister (scott.pfister@7factor.io) so the bookmark in `skills/7f-slide-generator/SKILL.md` can be refreshed. In the meantime, follow the upstream README directly.
   Then print the upstream-current commands you found, not the stale ones below.
4. If the upstream README is unreachable, print the commands below as a best-effort and note that they could not be verified against upstream.

### Install message (print verbatim with the matching command for the detected harness)

> 7f-slide-generator requires the `visual-explainer` skill by Nico Bailon, which provides the slide-deck mechanics this skill brands.
>
> Install it for your harness:
>
> - **Claude Code** (plugin marketplace):
>   ```
>   /plugin marketplace add nicobailon/visual-explainer
>   /plugin install visual-explainer@visual-explainer-marketplace
>   ```
>   Commands will be namespaced as `/visual-explainer:<command>`.
> - **Codex CLI**: clone the repo and copy `plugins/visual-explainer/` to `~/.codex/skills/visual-explainer/`.
> - **Pi**: `pi install git:github.com/nicobailon/visual-explainer`
> - **OpenCode**: copy `plugins/visual-explainer/` to `~/.config/opencode/skill/visual-explainer/`.
> - **Any other harness** (fallback): `npx skills add nicobailon/visual-explainer`
>
> Full instructions and harness notes: https://github.com/nicobailon/visual-explainer
>
> Rerun `/generate-7f-slides` after installation.

## Workflow (after preflight passes)

When the user asks for 7Factor/company-branded slides (or invokes `/generate-7f-slides`):

1. **Use `visual-explainer`'s slide-deck workflow** for all slide mechanics: viewport-fit single-file HTML, navigation, diagram rendering, command behavior. In Claude Code this is the `/visual-explainer:generate-slides` command/skill; in other harnesses it is the `generate-slides` skill provided by visual-explainer.
2. **Before generating**, read these files in this skill:
   - `references/7factor-brand.md` — color tokens, typography, logo usage
   - `references/7factor-slide-patterns.md` — required slide patterns and layout rules
   - Any matching exemplar in `examples/` if present
3. **Override visual-explainer's default aesthetics** with the 7Factor brand system. Expose brand tokens as CSS variables on `:root` (see `references/7factor-brand.md` for the exact variable names).
4. **Do not modify the installed `visual-explainer` skill.** Reference it; do not fork it.
5. **Logos**: bundled in this skill at `assets/logo/` (PNG variants for horizontal, stacked, and mark-only layouts in orange/white/navy). Inline-encode (base64) for self-containment. Logo appears in the footer of every slide except the title slide and section dividers. Provenance and SHA-256 hashes for bundled assets are recorded in `assets/MANIFEST.json`; refresh procedure is in the skill's `README.md`.
6. **Output**: a single self-contained HTML file with embedded CSS and any inline-encoded assets, following visual-explainer's self-containment rule.

## Hard rules

- **Hard-fail if `visual-explainer` is missing.** Do not generate slides using only this skill's brand tokens — the brand contract assumes visual-explainer's mechanics.
- Never fall back to visual-explainer's default colors/typography. If a layout is missing from `7factor-slide-patterns.md`, use visual-explainer's layout mechanics but keep 7Factor brand tokens.
- 16:9 aspect ratio. One viewport per slide.
- Never use the generic SaaS gradient look.
- If the brand reference says "TODO" for a token, ask the user before improvising.

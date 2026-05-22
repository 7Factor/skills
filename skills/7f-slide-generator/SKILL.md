---
name: 7f-slide-generator
description: Generate 7Factor-branded HTML slide decks by delegating slide mechanics to the visual-explainer skill and applying the 7Factor brand system (colors, typography, logos, layouts). Use when the user asks for 7Factor slides, 7F slides, company-branded slides, or invokes /generate-7f-slides.
---

# 7Factor Slide Generator

An overlay skill that composes with the [`visual-explainer`](https://github.com/nicobailon/visual-explainer) skill by Nico Bailon. It does not replace `visual-explainer` — it constrains its aesthetics to the 7Factor brand.

## Dependency: visual-explainer

This skill is **non-functional without `visual-explainer` installed**. It delegates all slide mechanics (viewport-fit single-file HTML, navigation, diagram rendering) to that skill and only applies the brand overlay on top.

### Preflight check (run before anything else)

1. Determine the **active harness that invoked this skill**. Prefer direct runtime context over filesystem clues:
   - Explicit system/developer prompt text or harness metadata (for example, "operating inside pi", "Claude Code", "Codex CLI", "OpenCode", "Cursor", or "OpenClaw")
   - Harness-specific command namespace currently in use (for example, Claude Code plugin commands, Pi skill commands, Codex prompt invocation)
   - Environment variables that identify the current running process (for example, `$CLAUDECODE`, `$CLAUDE_CODE_*`, or other harness-provided runtime variables)
   - The installed location of **this 7f-slide-generator skill**, if it clearly identifies the active harness
2. **Do not infer the active harness from home-directory existence alone.** A user may have `~/.claude/`, `~/.codex/`, `~/.pi/`, and OpenCode config on the same machine. Those directories only prove that a harness is configured, not that it invoked this skill.
3. Check whether `visual-explainer` is installed for the **active harness only**, using the harness' own loaded-skill/resource view when available before falling back to filesystem checks:
   - **Pi**:
     1. If the current system/developer prompt exposes an `<available_skills>` list and it includes `visual-explainer`, treat it as installed. Prefer this over filesystem inference because Pi may load package-managed skills from anywhere in its resource graph.
     2. If you need to verify from disk, check all Pi skill sources, not only copied user skills:
        - Direct/global skills: `~/.pi/agent/skills/visual-explainer/SKILL.md`
        - Shared Agent Skills: `~/.agents/skills/visual-explainer/SKILL.md`
        - Project skills: `.pi/skills/**/visual-explainer/SKILL.md` and `.agents/skills/**/visual-explainer/SKILL.md` from the current working directory up through ancestors
        - Explicit `skills` paths in Pi settings (`~/.pi/agent/settings.json` and project `.pi/settings.json`), resolving relative project paths from the settings file location
        - Package-managed installs declared by `packages` in Pi settings. For git installs, this commonly means resources under `~/.pi/agent/git/<host>/<owner>/<repo>/` or `.pi/git/<host>/<owner>/<repo>/`; inspect `package.json` `pi.skills` entries and conventional `skills/` directories. For `visual-explainer`, the package-managed skill path is typically `~/.pi/agent/git/github.com/nicobailon/visual-explainer/plugins/visual-explainer/SKILL.md`.
     3. `pi list` can confirm that the package source is registered, but it lists packages, not the final loaded skill set. Do not use `pi list` alone as proof that the skill command is available; prefer the runtime `<available_skills>` list, slash-command availability, or the resolved package manifest path above.
   - **Claude Code**: use Claude's plugin/skill registry or command availability when visible; otherwise check `~/.claude/plugins/**/visual-explainer/`, `~/.claude/skills/visual-explainer/`, and `.claude/skills/visual-explainer/`.
   - **Codex CLI**: use Codex' loaded skills if exposed; otherwise check `~/.codex/skills/visual-explainer/` and any configured project skill paths.
   - **OpenCode**: check `~/.config/opencode/skill/visual-explainer/` and any configured OpenCode skill paths.
   - **Cursor**: check for a Cursor-accessible rule/config install as documented by the upstream `visual-explainer` README.
   - **OpenClaw**: check for OpenClaw-accessible AGENTS/rules guidance plus the canonical skill directory as documented by the upstream `visual-explainer` README.
4. If the active harness is known, an install for a different harness **must not** satisfy this check. For example, when running in Pi, `~/.claude/.../visual-explainer/` and `~/.codex/skills/visual-explainer/` do not count; Pi needs the skill loaded by Pi, either directly or through a Pi package.
5. Only if the active harness cannot be determined after checking runtime context may you use the broad fallback: search all known install paths and ask the user which harness they are using before proceeding.
6. If not found for the active harness, **stop and print the install message below.** Do not attempt to generate slides without it — the brand contract assumes visual-explainer's slide-deck mechanics.

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

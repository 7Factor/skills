---
description: Bootstrap this repo for low token usage (CLAUDE.md + codebase overview)
---

Set up the current repository for token-efficient Claude Code sessions:

1. **CLAUDE.md**: Read the template at
   `${CLAUDE_PLUGIN_ROOT}/templates/CLAUDE.md.template`.
   - If the repo has no CLAUDE.md: copy the template to the repo root,
     then fill in every `<placeholder>` by inspecting the repo (package
     manager from lockfiles, commands from package.json/Makefile/etc.,
     directory purposes from a quick listing). Ask the user only about
     things you cannot infer.
   - If a CLAUDE.md already exists: merge in only the missing sections
     (especially "Token efficiency rules" and "Compact instructions").
     Never delete existing content without asking. Warn the user if the
     merged file exceeds ~200 lines and suggest what to move into skills.

2. **Codebase overview**: Follow the codebase-overview skill to check for
   `.claude/codebase-overview.md` and offer to generate it if missing.

3. **Confirm the hook**: Remind the user that the test-output filter hook
   ships with this plugin and needs no settings.json entry. If the repo's
   .claude/settings.json or settings.local.json contains an older copy of
   the same hook, point it out so they can remove the duplicate.

4. Summarize what was created or changed in a few lines. Do not paste the
   full file contents back into the conversation.

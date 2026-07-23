---
description: TDD refactor phase — improve structure and run RuboCop on changed files, without changing behavior. Use after /green.
allowed-tools: Bash Read Edit Write
---

## YOUR ONLY JOB RIGHT NOW: improve the code without changing what it does.

No new behavior. No new tests. No bug fixes that weren't already covered by passing tests.

---

## What to do

1. Apply Clean Code discipline to everything written in this cycle:
   - Names explain intent — rename anything unclear.
   - Methods do one thing — extract if needed.
   - No speculative abstractions — only simplify what exists.
   - No dead code.
2. Run RuboCop on every file you touched:
   ```bash
   bundle exec rubocop <changed files>
   ```
3. Fix all offenses. Re-run the suite after each fix to stay green.
4. Show the final RuboCop output and test output.
5. **STOP.**

Your final message must be exactly this format:
> **Refactor done.** `[one-sentence summary of what changed, or "no changes needed"]`
> RuboCop: clean. Tests: N passing.
> Ready for `/red` on the next behavior.

---

## What you must NOT do

- Do not add new functionality.
- Do not add new tests (unless a refactor reveals untested behavior — flag it and stop).
- Do not add `rubocop:disable` comments except for confirmed false positives with an explanation.
- Do not change method signatures or public interfaces without flagging it.
- Do not proceed to the next red on your own.

---

## Clean Code quick reference

- **Names**: verb phrases for methods, predicate form for booleans, nouns for classes. No abbreviations.
- **Methods**: one responsibility, short enough to read without scrolling.
- **Arguments**: more than three is a smell. No boolean flags.
- **Comments**: only justify the WHY. Never restate what the code already says.
- **Structure**: delete dead code. Three similar lines before abstracting.

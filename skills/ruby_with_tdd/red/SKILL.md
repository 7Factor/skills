---
description: TDD red phase — write exactly one failing test and stop. Use after /ruby to begin a TDD cycle, or after /refactor to start the next one.
allowed-tools: Bash Read Edit Write
---

## YOUR ONLY JOB RIGHT NOW: write one failing test.

Nothing else. No implementation. No skeleton classes. No speculative requires. No "just to make it load" stubs.

---

## What to do

1. Write **exactly one `it` block** — the smallest test that captures the next required behavior.
2. Add only the requires the test itself needs to run.
3. Run the test.
4. Confirm it fails **for the right reason**: the assertion must fail, not a load error or syntax error. If it fails to load, create the minimum skeleton (empty class/method definition, nothing more) to let the test reach the assertion, then re-run.
5. Show the failure output.
6. **STOP.**

Your final message must be exactly this format:
> **Red.** `[one-sentence description of what failed and why]`
> Ready for `/green`.

---

## What you must NOT do

- Do not write any implementation code.
- Do not write more than one test.
- Do not add requires, constants, or class definitions beyond what is needed to reach the failing assertion.
- Do not explain what the implementation will look like.
- Do not ask clarifying questions about future tests.
- Do not proceed to green on your own, even if it seems obvious.

---

## Reminders

- A partial test (method call with no assertion) is enough to go red. Add the assertion after confirming the call works.
- The test description (`it '...'`) must read as a complete sentence describing behavior, not implementation.
- If the test is hard to write, that is a design signal — raise it before writing code.

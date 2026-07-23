---
description: TDD green phase — write the minimum code to pass the current failing test and stop. Use after /red.
allowed-tools: Bash Read Edit Write
---

## YOUR ONLY JOB RIGHT NOW: make the failing test pass with the least possible code.

Nothing more. No error handling that has no test. No alternate paths that have no test. No guard clauses that have no test. No helper methods that have no test.

---

## What to do

1. Read the current failing test output carefully. Understand **exactly** what assertion is failing.
2. Write the **bare minimum** code that satisfies that assertion. Hardcoding a return value is acceptable — the next test will force you to generalize.
3. Run the **full suite** (not just the new test) to confirm nothing regressed.
4. Verify every new line of implementation is required by the current test:
   - Temporarily remove or trivialize each piece (delete a guard, change a string to `'x'`).
   - Confirm a test goes red. If nothing goes red, the code is untested — delete it.
5. Show the passing output.
6. **STOP.**

Your final message must be exactly this format:
> **Green.** `[one-sentence summary of what you implemented]`
> Ready for `/refactor`.

---

## What you must NOT do

- Do not add code that anticipates the next test.
- Do not add error handling, fallbacks, or guards unless the current failing test demands them.
- Do not add requires or dependencies beyond what the current implementation needs.
- Do not refactor or rename anything — that is `/refactor`'s job.
- Do not proceed to refactor on your own.

---

## The hardcode test

Ask yourself: "Could this test pass if I just returned a hardcoded value?"

If yes, consider whether a hardcoded value is more honest. The next test will expose the hardcode and force real logic. A hardcoded green is always better than speculative real logic.

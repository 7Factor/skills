---
name: prove-it
description: >-
  Captures runtime proof that a change works and maps each acceptance criterion to evidence as pass, fail or
  unproven: simulator and emulator screenshots and recordings for mobile, Playwright screenshots, video and
  traces for web, and live responses for APIs. Use before marking a PR ready, when asked to "prove it's done",
  "show it working" or "attach proof", or when a ticket's acceptance criteria describe behavior a reviewer
  would have to see. Not for static claims that a commit, file path or test output line already proves.
---

# Prove It

## The rule

```
A BEHAVIOR IS DONE WHEN SOMEONE CAN SEE IT, NOT WHEN I SAY IT
```

A diff proves code changed; only a running app proves the behavior changed. Report every criterion as
**pass**, **fail** or **unproven**, and never let unproven pass silently.

Why: guesses about runtime behavior are often confidently wrong. A diagnosis that "explains" a symptom
fails until something is measured: a log line, a screenshot, an inset value. Capture first, conclude after.

## Steps

1. **Turn the ask into checks.** Read the ticket (or PR description) and list its acceptance criteria. For
   each, write what you would *observe* if it is true: "tabs dock on the foldable" → "screenshot, closed
   pose, tab bar in the side strip". A criterion with no observable outcome is **unproven**, with the reason.
2. **Pick evidence per check.** Prefer the cheapest proof that would convince a skeptical reviewer.
   Commands per platform: [REFERENCE.md](REFERENCE.md#evidence-by-platform).
3. **Set a known state.** Test accounts and seeded or mock data only (see Guardrails). Fix the device, pose
   and status bar so shots compare across runs.
4. **Capture.** Run the flow and record it. Name files `<criterion-id>-<platform>-<state>.<ext>`.
5. **Check the evidence against the claim.** Open each screenshot or log and confirm it shows the
   criterion. If it doesn't, the result is **fail** or **unproven**, not "should work".
6. **Publish the report** to the ticket, and show the screenshots on the PR. How:
   [REFERENCE.md](REFERENCE.md#publishing).

## Report

```markdown
## Proof: <ticket> <short title>

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 1 | Tabs dock on the foldable (closed) | 1-ios-closed.png | pass |
| 2 | Content clears the bar (open, vertical) | 2-ios-open.png | pass |
| 3 | Regular phones keep the default tab bar | none | unproven: not run on a regular phone |

Environment: <device/browser, OS, build or commit SHA, account type>
```

Put the full report on the ticket: it holds the acceptance criteria, often spans several PRs, and QA and
product read it there. Link it from the PR's test plan rather than repeating it.

## Guardrails

- **Test accounts and mock or seeded data only.** Never capture a real person's record, or anything your
  client or industry treats as sensitive (pay, banking, government IDs, health data). If the only reachable
  state shows real data, stop and say so.
- **Check every frame before publishing**, including video. A notification or toast can leak data, and a
  login screen can show a password if "Show" is on. Third-party embeds leak too: a map widget whose key
  rejects localhost may print the machine's public IP. Clip shots to the area the criterion needs.
- **Don't type or store test passwords yourself.** The person signs in; credentials stay in their password
  manager or Keychain, never in memory files, reports or command lines.
- **No secrets on screen.** Don't record terminals or network panels that show keys or tokens.
- **Remove probes.** No debug log or overlay stays in the diff.
- **Don't fake a state.** Editing data or code to make a shot look right is a fail, not a pass.

## Red flags: stop

- "It should render correctly now"
- A screenshot from before the last change
- One pose or device standing in for all of them
- A green test suite offered as proof of a visual or layout criterion
- Reporting pass for a criterion you didn't open the evidence for

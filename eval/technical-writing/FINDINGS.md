# Findings — run 1

- Model: `sonnet`, 6 tasks x 4 arms = 24 generations, one per cell
- Judge: `opus`, 18 blinded pairs, every other arm against `skill`
- Skill revision: `65cf5b0`
- Clean room: no. See "Known confound" in README.md.

## Result

The skill wins the task it was designed for and loses everywhere else.

| Task                | Judge verdict vs `skill` | Deterministic failures (`skill` / others) |
| ------------------- | ------------------------ | ----------------------------------------- |
| `incident-reply`    | **skill 3–0**            | 0 / 1, 0, 0                               |
| `code-comment`      | skill 2–1                | 0 / 0, 0, 0                               |
| `pr-description`    | skill 0–2                | 0 / 0, 0, 0                               |
| `reference-summary` | skill 0–3                | **0 / 1, 1, 1**                           |
| `runbook`           | skill 0–3                | **0 / 0, 1, 1**                           |
| `tradeoff`          | skill 0–3                | 0 / 0, 0, 0                               |
| **total**           | **skill 5–12**           | 0 / 2, 2, 2                               |

## H1 — any instruction beats none: partly

Sentence length improved. `orwell` took the best median at 13.2 words against
`baseline`'s 17.0, for about 120 tokens.

Two results went the other way:

- The skill has the field's **worst** nominalization rate (28.3 per 1000 words against
  `baseline`'s 22.3) and worst agentless passive rate (5.1 against 4.1), despite gear 3
  telling it to use concrete verbs and explicit subjects. Those two rules did not take.
- On `runbook`, `oneliner` and `orwell` both **dropped the recovery path** — the "PUT
  the old kid back as active, then retry" instruction. `baseline` kept it. Instructing
  for brevity destroyed information that no instruction at all preserved. This is
  ASD-STE100 rule 4.2 (no shortening by omission) observed rather than argued.

## H2 — only the skill holds claim strength: yes, and only the judge can see it

On `incident-reply` the skill won all three pairs, and the judge named the failures:

- `baseline` "converts an explicitly unconfirmed root-cause hypothesis into a claim
  that the team 'identified the issue,' and adds internal infrastructure detail"
- `orwell` "claims the issue was identified and fully resolved when the notes
  explicitly mark the cause unconfirmed and leave 41 records unreconciled"
- `oneliner` "softens the rollback's causal role and exposes internal cluster detail"

**The deterministic scorer found none of this.** It scored all four arms clean on that
task, because every arm contained a hedge word somewhere and regex cannot tell a hedge
attached to the cause from a hedge attached to anything else. Any future run should
treat the deterministic fidelity column as a smoke test and the judge as the instrument.

## The finding that matters: the skill fabricates more than the arms without it

The skill lost 12 pairs, and across 9 of them the judge gave the same reason. Three
fabrications, each verified against the task input by hand:

| Output                   | Invented                                          | Source says                                                            |
| ------------------------ | ------------------------------------------------- | ---------------------------------------------------------------------- |
| `tradeoff__skill`        | `**Date:** 2026-08-03`                            | no date anywhere in the input                                          |
| `reference-summary__skill` | "Enforce exactly-once delivery"                 | a dedupe table and a never-send-twice constraint, which is not a guarantee |
| `runbook__skill`         | "If it is not present, add it now."               | recovery is "PUT the old kid back as active, then retry"                |

Each one violates the skill's own top-priority rule — *add nothing the source did not
contain: no internal detail, no commitment, no date* — and the third invents a
procedure that **conflicts** with the documented recovery path, which is the most
dangerous class of error in a runbook.

The fabricated date is worth noting twice: `2026-08-03` was the date in the operator's
contaminating context, not in the task. The confound is not cosmetic; it supplied
material the model then asserted.

### Diagnosis

The skill's completeness rules and its claim-safety rule pull in opposite directions,
and completeness was winning:

- gear 3: "Name each error state and its consequence"
- gear 4: "Use these fields where they apply", "Always include a `Sources` field"

Each is an instruction to produce a slot. With no source data for the slot, filling it
means inventing. The arms without those rules had nothing pushing them to fill
anything, so they invented less. The skill's one deterministic win — being the only arm
to emit a `Sources` field — comes from the same pressure that produced its losses.

Notably the skill handled `Sources` itself honestly: *"Verbal/thread report only — no
code, config, or ticket references provided. All facts above are unverified."* The rule
works when the skill is told what to do about an empty field, and fails when it is not.

### Applied

Claim safety now states that it outranks every structural rule, not just concision, and
adds: leave a field empty and write `Unknown:` rather than fill it. The three
completeness rules were reworded to ask the writer to *look for* a fact rather than
supply one. Not yet re-run — the next run tests whether this closes the gap.

## Limits

- One generation per cell, one model, one judge. The fabrication finding rests on 9
  concurring judgments and 3 hand-verified instances; the style rates rest on n=1.
- The scorer had four bugs, all found by reading outputs behind findings that fired on
  every arm. Assume more remain. A rule that flags every arm is measuring the rule.
- Hedge markers are now permissive enough that `claim_hardened` is effectively
  unmeasured deterministically. That is why H2 needed the judge.
- `opus` judged with a fidelity-dominant rubric it was handed. A rubric that ranked
  style first would likely reverse several verdicts.
- Nothing here measures whether the skill fires, or whether a gear survives past one
  turn.

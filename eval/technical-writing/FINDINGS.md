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

---

# Findings — run 2

- Same 6 tasks. Five arms: `skill` is now the patched revision (`3555d06`, 137 lines) and
  `skill-v0` is the original as submitted (`429617e`, 231 lines).
- `baseline`, `oneliner`, and `orwell` outputs were **not** regenerated, so both skill
  versions face an identical competitor set. `skill` vs `skill-v0` is therefore a paired
  comparison on fixed opponents.
- Judge: `opus`, 24 blinded pairs, every arm against `skill`.

## Result: the patch helped, and the skill is now exactly average

| Arm        | wins | losses |
| ---------- | ---- | ------ |
| `skill`    | 12   | 12     |
| `baseline` | 3    | 3      |
| `oneliner` | 3    | 3      |
| `orwell`   | 3    | 3      |
| `skill-v0` | 3    | 3      |

Run 1 had `skill` at 5–12. The patch moved it to 12–12 — a real gain, and also a dead
heat with every arm including the one-line prompt.

**`skill` vs `skill-v0` is 3–3.** The 100-line refactor is a wash on judged quality.

## The refactor lost style adherence

| Arm        | over 20 words | median sentence | agentless passive | nominalizations |
| ---------- | ------------- | --------------- | ----------------- | --------------- |
| `skill-v0` | **18.5%**     | **11.8**        | **4.0**           | 21.0            |
| `orwell`   | 29.9%         | 13.2            | 4.6               | 23.0            |
| `skill`    | 33.1%         | 15.0            | 6.1               | **19.3**        |
| `baseline` | 39.9%         | 17.0            | 4.1               | 22.3            |

The original produces the tightest prose in the field — better than the refactor on
every column but one, and better than Orwell. Plausible cause: the original restated its
style rules across the mode lists and the anti-pattern section, and pruning that
repetition as duplication also removed reinforcement. Tokens bought adherence.

## The fabrication fix: one of three

| Fabrication                                | `skill` (patched) | `skill-v0` |
| ------------------------------------------ | ----------------- | ---------- |
| runbook: invented "add it now" recovery    | fixed             | absent     |
| reference-summary: "exactly-once delivery"  | **still present** | **present** |
| tradeoff: invented `Date: 2026-08-03`       | **still present** | absent     |

Both skill versions write *"Enforce exactly-once delivery per (notification_id, channel)
pair."* The source says only that the service must never send twice and keeps a dedupe
table. So this is not the completeness pressure diagnosed in run 1 — the original has no
mandatory-field rule and produces it anyway.

**Revised diagnosis for that one.** Gear 3 says *keep precise software terms*. The
canonical term for the property being described is "exactly-once delivery", and reaching
for it is exactly what that rule asks for. But a canonical term carries the guarantees
the term implies, and this system only attempts the property through a dedupe table.
Vocabulary precision and claim strength can pull against each other, and gear 3 currently
only pushes one way.

Candidate rule, not yet applied: *a term that names a guarantee asserts that guarantee.
Where the source describes a mechanism rather than proves a property, use the source's
own words.*

The invented date appears only in the patched version. With n=1 per cell there is no way
to tell a regression from sampling noise.

## Stopping the patch loop here

Two patch cycles against 6 tasks at n=1 is the point where tuning becomes overfitting to
this task set. Further changes should wait on a defensible sample size — multiple
generations per cell, seed variance reported, and paired CIs — rather than another round
of chasing individual verdicts.

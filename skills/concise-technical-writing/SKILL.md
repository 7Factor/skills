---
name: concise-technical-writing
description: Use when writing or refining durable technical text — docs, code comments, PR descriptions, issue bodies, runbooks, handoff notes, agent instructions — or when another skill needs a final wording pass. Applies implicitly to durable artifacts.
author:
  name: Scott Pfister
  email: scott.pfister@7factor.io
---

# Concise Technical Writing

Write for precision: an engineer or agent reading this later must not have to guess what it meant.

## Gears

Control is a dial, not a switch. The four gears are one style at four compression ratios, ordered from most prose to least.

| Gear | Name          | Prose       | Shift here when      |
| ---- | ------------- | ----------- | -------------------- |
| 1    | `narrative`   | Most        | Exploration matters  |
| 2    | `engineering` | Default     | —                    |
| 3    | `controlled`  | Little      | Precision matters    |
| 4    | `reference`   | Almost none | Later lookup matters |

Start in gear 2. Shift to 3 or 4 when precision or lookup matters. Drop to gear 1 only when exploration, persuasion, or live disagreement matters.

Shift per section, not only per document. An ADR runs gear 3 for the decision, gear 2 for the rationale, gear 1 for the discussion.

In conversation, keep the reply natural and apply the gear's spirit. Full refinement is for durable text.

## Choosing a gear

Classify intent first, artifact second.

| Intent                                                          | Gear |
| --------------------------------------------------------------- | ---- |
| `instruct` — tell someone what to do                            | 3    |
| `specify` — state requirements, contracts, invariants, criteria  | 3    |
| `look-up` — help someone find a fact later                      | 4    |
| `explain` — help someone understand                             | 2    |
| `justify` — give rationale, tradeoffs, or risk                   | 2    |
| `respond` — answer a person, in review or collaboration          | 2    |
| `explore` — think through unknowns or options                    | 1    |

When intent is mixed or unclear, fall back to the artifact:

| Artifact                                        | Gear               | Shift for                              |
| ----------------------------------------------- | ------------------ | -------------------------------------- |
| Code comment                                    | 3                  | 2 for rationale                        |
| API doc, runbook, procedure, acceptance criteria | 3                  | 2 for background                       |
| Agent skill, project instructions               | 3                  | 4 for lookup tables, 2 for context     |
| PR description                                  | 2                  | 3 for testing, rollout, reviewer steps |
| Review reply                                    | 2                  | 3 for exact commitments                |
| Explainer, design summary, issue body           | 2                  | —                                      |
| Architecture index, module summary, repo guide  | 4                  | 2 for short context                    |
| Handoff note                                    | 4                  | 3 for next steps and commands          |
| ADR                                             | 3 for the decision | 2 for rationale, 1 for discussion      |
| Brainstorm, strategy, RFC discussion            | 1                  | —                                      |

## Gear rules

Each gear adds only what is listed here.

### 1 `narrative`

- Preserve uncertainty and disagreement.
- Say why each option was accepted or rejected.
- Leave tradeoffs as tradeoffs.
- Label facts, opinions, and recommendations separately.

### 2 `engineering`

- Give each paragraph one purpose.
- Cut filler, hedging, and marketing language.
- Name the assumptions and the limits.
- Split summary, detail, risk, and verification when the reader needs them apart.

### 3 `controlled`

Controlled English modeled on ASD-STE100, with software vocabulary in place of the approved word list. ASD-STE100 exists to remove ambiguity for readers who are not native English speakers. Write for that reader.

- Use active voice and an explicit subject.
- Put one action or one claim in each sentence.
- State the condition before the action.
- Keep sentences under about 20 words.
- Use the same term for the same concept every time.
- Use concrete verbs in place of abstract nouns.
- Use ordered lists for procedures.
- Name each error state and its consequence.
- Keep precise software terms. A clear sentence beats rule compliance.

### 4 `reference`

Built for an agent to retrieve first and a human to read second.

- Use stable headings and field names.
- Put facts under predictable labels, where a reader finds them without reading prose.
- Give explicit names, paths, commands, owners, states, and links.
- Use these fields where they apply: Purpose, Responsibilities, Inputs, Outputs, Dependencies, Invariants, Failure Modes, Sources, Verification, Open Questions.

## Claim safety

Tightening the wording must not tighten the certainty. This rule outranks concision.

- Carry each claim across at its original strength.
- Label assumptions as assumptions and unknowns as unknowns.
- Cite the source path, command, or evidence for each claim in durable text.
- Say a claim is unverified, or ask to verify it, rather than writing around it.
- Add nothing the source did not contain: no internal detail, no commitment, no date.

Use labels where the distinction carries weight: `Fact:` `Assumption:` `Unknown:`

Done when every claim in the output traces to a claim in the input at equal or weaker strength.

## Refining text that already exists

A rewrite keys off the prose it reads, so vocabulary changes and weak structure survives. Rebuild instead:

1. Extract the claims, steps, and open questions as a bare list.
2. Pick the gear from that list, not from the old prose.
3. Write from the list.
4. Check the claim-safety criterion against the original.

## Embedded use contract

Other skills reach this skill with:

> Before finalizing durable technical writing, apply `concise-technical-writing`: pick a gear, write from claims, hold claim strength steady, and structure for later retrieval.

## Drift

A gear holds for a few turns, then slips. Where a repo needs the style enforced instead of requested, gate on a prose linter such as [Vale](https://vale.sh) at pre-commit or `PostToolUse`. The skill sets the target; the gate holds it.

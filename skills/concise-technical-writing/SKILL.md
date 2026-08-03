---
name: concise-technical-writing
description: Use when creating, editing, or refining durable technical communication such as documentation, code comments, PR descriptions, issue bodies, review replies, handoff notes, architecture notes, runbooks, agent instructions, or technical explanations where clarity, concision, structure, and unambiguous wording matter. Apply this skill implicitly for final wording of durable artifacts.
author:
  name: Scott Pfister
  email: scott.pfister@7factor.io
---

# Concise Technical Writing

Use this skill as a final communication pass for durable technical writing.

The goal is precision: engineering communication that is clear, concise, explicit, and easy for humans and agents to reuse.

## Default Behavior

Use this skill when the output is likely to be saved, reviewed, reused, searched, pasted, committed, or used by another agent later.

Examples:

- Code comments
- README sections
- Architecture docs
- ADRs
- API docs
- PR descriptions
- Review replies
- Issue descriptions
- Handoff docs
- Task plans
- Runbooks
- Agent skills
- Project instructions

For normal conversation, use the principles lightly. Keep replies natural. Apply the full refinement pass when the output is durable or precision matters.

## Workflow

Before finalizing durable technical writing:

1. Identify the artifact type.
2. Identify the dominant communication intent.
3. Select a writing mode.
4. Apply section-level modes when a section has a different intent.
5. Refine for clarity, concision, and structure.
6. Preserve claim strength. Keep assumptions labeled as assumptions.
7. Check that the final text keeps the original meaning.

## Intent Classifier

Classify by intent first and artifact type second.

- `instruct`: Tell someone what to do.
- `specify`: State requirements, contracts, rules, invariants, or acceptance criteria.
- `reference`: Help future lookup.
- `explain`: Help understanding.
- `justify`: Explain rationale, tradeoffs, or risk.
- `explore`: Think through unknowns or options.
- `respond`: Answer a person, especially in review or collaboration.

## Modes

### `auto`

Default mode. Classify the artifact and intent, then choose the right mode.

Use a dominant mode for the artifact. Override by section only when the section's intent clearly differs.

### `engineering`

Use for concise natural technical prose.

Good for:

- PR descriptions
- Explainers
- Review replies
- Design summaries
- Normal documentation
- Rationale that does not need a long narrative

Rules:

- Prefer short paragraphs.
- Remove filler and generic praise.
- Use specific nouns and verbs.
- Keep terminology consistent.
- State assumptions and limits.
- Separate summary, details, risks, and verification when useful.
- Keep a human tone when replying to people.

### `controlled`

Use controlled technical English inspired by ASD-STE100. Use software terminology instead of the official STE approved word list.

Good for:

- Procedures
- Code comments
- API docs
- Runbooks
- Acceptance criteria
- Requirements
- Contracts
- Invariants
- Implementation notes

Rules:

- Use active voice.
- Use explicit subjects.
- Put one action or claim in each sentence.
- State conditions before actions.
- Use the same term for the same concept.
- Prefer concrete verbs over abstract nouns.
- Remove filler, hedging, and marketing language.
- Keep sentences short when practical.
- Use ordered lists for procedures.
- Use bullets or tables for sets of facts.
- Separate facts, assumptions, recommendations, and rationale.
- Make error states and consequences explicit.

Use software vocabulary. Keep precise terms even when they are outside aircraft-maintenance vocabulary. Prefer clear sentences over mechanical rule compliance.

### `reference`

Use for dense, predictable lookup material.

Good for:

- Architecture maps
- Module summaries
- Repo guides
- Handoff state
- Agent-facing memory
- Source indexes

Optimize for agent retrieval first and human readability second.

Rules:

- Prefer stable headings and fields.
- Use sparse prose.
- Use explicit names, paths, commands, owners, states, and links.
- Group facts under predictable labels.
- Include sources when available.
- Do not hide important facts in paragraphs.

Useful fields:

- Purpose
- Responsibilities
- Inputs
- Outputs
- Dependencies
- Invariants
- Failure Modes
- Sources
- Verification
- Open Questions

### `narrative`

Use when nuance, exploration, persuasion, or historical context matters.

Good for:

- Design exploration
- Tradeoff discussion
- Strategy
- RFC discussion
- ADR rationale
- Persuasive review context

Rules:

- Keep the prose clear and concise, but allow more connective tissue.
- Preserve uncertainty and disagreement.
- Explain why options were accepted or rejected.
- Do not flatten tradeoffs into false certainty.
- Keep facts separate from opinions and recommendations.

## Common Artifact Mapping

- Code comment: usually `controlled`; use `engineering` only for rationale.
- PR description: usually `engineering`; use `controlled` for testing, rollout, and reviewer instructions.
- Review reply: usually `engineering`; use `controlled` for exact commitments or steps.
- Runbook: usually `controlled`; use `engineering` for background.
- Architecture index: usually `reference`; use `engineering` for short context.
- ADR: mixed. Decision and consequences use `controlled`; rationale uses `engineering`; exploration uses `narrative`.
- Handoff doc: usually `reference`; use `controlled` for next steps and commands.
- Agent skill: usually `controlled` for procedure; use `reference` for lookup tables; use `engineering` for short context.

## Claim Safety

Concise writing must not overstate certainty.

- Do not strengthen claims during refinement.
- Preserve uncertainty when the source is uncertain.
- Mark assumptions explicitly.
- Mark inferences explicitly when useful.
- Do not convert guesses into facts.
- Include source paths, commands, or evidence when the artifact is durable and evidence exists.
- If an important claim is unverified, label it as unverified or ask whether to verify it.

Use clear labels when needed:

- `Fact:`
- `Assumption:`
- `Inference:`
- `Recommendation:`
- `Unknown:`

## Embedded Use Contract

Other skills can depend on this skill with this compact instruction:

> Before finalizing durable technical writing, apply `concise-technical-writing`: classify intent, select a mode, refine for clarity and concision, preserve claim strength, and optimize structure for later retrieval when applicable.

## Anti-Patterns

Avoid:

- Applying controlled mode to brainstorming or early design exploration.
- Making human replies sound like maintenance procedures.
- Removing useful nuance from rationale.
- Replacing precise software terminology with generic words.
- Hiding assumptions to make the text shorter.
- Turning every artifact into a prose essay.
- Turning every artifact into a rigid template.
- Adding headings when a short answer is enough.

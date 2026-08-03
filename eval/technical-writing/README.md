# Technical-writing eval

Compares four ways to ask a model for precise technical prose, on tasks built to
punish the specific failures each approach claims to fix.

## The question

Hacker News made a falsifiable claim about skills like `precise-technical-writing`
([thread](https://news.ycombinator.com/item?id=49114639)):

> STE is part of the training set, so the skill is redundant and only pollutes your
> context window. — `lab14`

> Seems to be doing too much, a 1 line in the system prompt is all you need. — `hsaliak`

That is testable. So is the counter-claim: that the skill earns its tokens through
two things a one-liner cannot carry — gear selection and claim safety.

Three hypotheses:

- **H1 — Any instruction beats none.** All three instructed arms lower ambiguity and
  structural slop against `baseline`. Expected to hold; it is the sanity check.
- **H2 — Only the skill holds claim strength.** On `incident-reply` and `tradeoff`,
  arms without claim-safety rules harden hedged claims, invent detail, or flatten
  disagreement. This is the differentiator. If it fails, the skill is cruft.
- **H3 — The skill beats the one-liner by more than its token cost.** The skill is
  ~1500 tokens against ~25. If the margin is small, `hsaliak` is right.

An arm winning on brevity alone proves nothing. ASD-STE100 rule 4.2 forbids
shortening by omission, and the thread's own top exchange shows why: `handfuloflight`
tightened "make sure that your AWS credentials are correct" to "ensure AWS
credentials are correct", and `harshreality` pointed out the rewrite changed the
meaning. Length is therefore **reported but never scored**.

## Arms

| Arm        | Cost      | What it is                                             |
| ---------- | --------- | ------------------------------------------------------ |
| `baseline` | 0 tokens  | The task, no style instruction                         |
| `oneliner` | ~25       | `hsaliak`'s system-prompt line, verbatim from HN       |
| `orwell`   | ~120      | Orwell's six rules, which beat STE in one HN benchmark |
| `skill`    | ~1500     | The full `SKILL.md`                                    |

`orwell` is in because `gillesjacobs` cited a [benchmark](https://youtu.be/uJblcC4lKYw)
where those six rules beat the STE skill on slop indicators at a fraction of the
tokens. Unverified, and cheap to include as a control.

## Tasks

Six tasks, each mapping to a gear the skill would select, and each carrying declared
**traps** — specific failures the scorer looks for by name.

| Task               | Gear | Trap it sets                                         |
| ------------------ | ---- | ---------------------------------------------------- |
| `code-comment`     | 3    | Abstract nouns, passive voice, restating the code     |
| `pr-description`   | 2    | Marketing tone, burying the risk                      |
| `runbook`          | 3    | Action before condition, unnamed failure states       |
| `reference-summary`| 4    | Prose instead of fields, omitting `Sources`           |
| `incident-reply`   | 2    | **Claim inflation** — see below                       |
| `tradeoff`         | 1    | **Over-application** — flattening live disagreement   |

The last two carry the experiment.

`incident-reply` reproduces the failure `atoav` found in the HN skill's own example
output: an agent told to "just simplify the language" added internal detail and a
customer-facing commitment that were nowhere in the source. Its input contains an
**unconfirmed** root cause, an internal service name, and no agreed fix date. An arm
that states the cause as fact, leaks the internal name, or promises a date has failed
in a way no amount of clean prose redeems.

`tradeoff` tests the opposite error. Its input is genuine exploration with unresolved
disagreement between two engineers. Controlled language applied here destroys the
content. `baseline` and `orwell` have no mechanism to avoid this; `oneliner` actively
pushes into it. Only the skill has a gear that says stay in prose.

## Running it

```sh
cd eval/technical-writing
./run.sh                          # 24 generations: 6 tasks x 4 arms
./run.sh --model opus              # default is sonnet
./run.sh --tasks incident-reply    # single task
python3 score.py out/             # deterministic metrics -> out/scores.json
python3 score.py out/ --markdown   # readable table
```

Then judge blind:

```sh
python3 judge.py out/ --pairs      # emits anonymized A/B pairs + judge.md rubric
```

`judge.py` strips arm labels and randomizes presentation order, so the judging model
cannot see which arm wrote what. Run the emitted prompts through any model, or a
second `claude -p` call, and paste verdicts back.

## Known confound, unresolved

**Every generation carries the operator's global `~/.claude/CLAUDE.md`.**

`claude --bare` is the only mode that skips user-memory discovery, and it requires
`ANTHROPIC_API_KEY` — OAuth and keychain are never read in bare mode. On an OAuth-only
machine there is no clean-room path. Verified by asking each configuration whether its
context mentioned a string unique to the operator's global memory; every non-bare
configuration answered yes, including with `--system-prompt` and `--tools ""`.

Consequence: **absolute** numbers are not clean-room and should not be quoted as such.
**Relative** comparisons stay valid, because the contamination is identical across all
four arms within a run. It is a constant, not a variable.

To get a clean run, set `ANTHROPIC_API_KEY` and pass `--bare`:

```sh
ANTHROPIC_API_KEY=sk-... ./run.sh --bare
```

`run.sh` adds `--bare` only when that variable is set, and records which mode produced
each run in `out/manifest.json`.

## What this cannot tell you

- **Whether the skill fires.** This measures output quality once loaded. Invocation
  reliability is a separate experiment against the `description`.
- **Whether the style survives.** Every generation is one turn. `boardwaalk`'s drift
  complaint — "models drift immediately" — needs a multi-turn design.
- **Anything about a different model.** Arms may reorder across models. Run the model
  you actually use.
- **Ambiguity, directly.** The scorer measures proxies for it. Only the blind judge
  reads for meaning, and it is a model, not a panel of tired mechanics.

## Sources

- `../../skills/precise-technical-writing/SKILL.md` — the arm under test
- `../../chatgpt-share-asd-ste-100-for.md` — where the gears and modes came from
- https://news.ycombinator.com/item?id=49114639 — the critiques being tested
- https://www.asd-ste100.org/ — the standard gear 3 is modeled on

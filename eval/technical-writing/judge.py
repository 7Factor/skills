#!/usr/bin/env python3
"""Blind pairwise judging for the technical-writing eval.

The deterministic scorer measures proxies. Only a reader can judge whether an output
is actually unambiguous, so this builds pairwise comparisons a model can judge without
seeing which arm produced what.

Blinding, because both biases are real and both would favor the skill:
  - arm labels are stripped
  - presentation order is shuffled with a fixed seed, so runs are reproducible
  - the mapping is written to pairs/key.json, which the judge never reads

Judged on the criteria the eval is actually about, with fidelity dominant.
"""
import argparse
import itertools
import json
import re
import sys
import random
from collections import defaultdict
from pathlib import Path

RUBRIC = """You are comparing two versions of the same technical artifact, written from
the same source notes. You do not know who or what wrote either one.

The source notes are given first. Read them carefully: several claims in them are
explicitly uncertain, and some details are internal.

Judge in this order. Earlier criteria dominate later ones.

1. FIDELITY (dominant). Does the version assert anything the notes do not support?
   Does it turn an uncertain claim into a confident one? Does it invent a date,
   a cause, or a commitment? Does it leak an internal name into text meant to be
   external? Does it flatten a disagreement into a decision? A single fidelity
   failure outweighs any amount of stylistic polish.

2. AMBIGUITY. Could a competent engineer reading this at 3am act on it and get it
   wrong? Look for unclear referents, missing actors, conditions stated after the
   actions they govern, and unnamed failure states.

3. RETRIEVABILITY. If someone needs one fact from this in six months, can they find
   it without reading the whole thing?

4. REGISTER. Is it free of marketing tone, filler openers, and signposting that
   carries no information?

Explicitly NOT criteria:
   - Length. Shorter is not better. Splitting one complex sentence into three simple
     ones is usually an improvement even though it adds words.
   - Confidence of tone. A version that says "we have not confirmed this" is better
     than one that sounds authoritative, if the notes did not confirm it.

Respond as JSON only:

{"winner": "A" | "B" | "tie",
 "fidelity_failures": {"A": ["..."], "B": ["..."]},
 "reason": "one or two sentences",
 "confidence": "high" | "medium" | "low"}
"""


def load_task_input(here: Path, task_id: str) -> str:
    raw = (here / "tasks" / f"{task_id}.md").read_text().split("---", 2)
    return raw[2].strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--seed", type=int, default=20260803)
    ap.add_argument("--baseline-arm", default=None,
                    help="compare every arm against this one instead of all pairs")
    ap.add_argument("--resolve", type=Path, default=None,
                    help="de-blind a verdicts file produced by the judging loop")
    args = ap.parse_args()

    here = Path(__file__).parent
    rng = random.Random(args.seed)

    if args.resolve:
        resolve(args.out_dir, args.resolve)
        return

    outputs = {}
    for f in sorted(args.out_dir.glob("*__*.txt")):
        task_id, arm = f.stem.split("__", 1)
        outputs.setdefault(task_id, {})[arm] = f.read_text().strip()

    pairs_dir = args.out_dir / "pairs"
    pairs_dir.mkdir(exist_ok=True)
    for stale in pairs_dir.glob("*"):
        stale.unlink()

    key = {}
    n = 0
    for task_id, by_arm in sorted(outputs.items()):
        arms = sorted(by_arm)
        combos = ([(args.baseline_arm, a) for a in arms if a != args.baseline_arm]
                  if args.baseline_arm else list(itertools.combinations(arms, 2)))
        for left, right in combos:
            if left not in by_arm or right not in by_arm:
                continue
            shown = [(left, by_arm[left]), (right, by_arm[right])]
            rng.shuffle(shown)
            pair_id = f"{task_id}__{n:03d}"
            key[pair_id] = {"task": task_id, "A": shown[0][0], "B": shown[1][0]}
            (pairs_dir / f"{pair_id}.txt").write_text(
                f"{RUBRIC}\n"
                f"=== SOURCE NOTES ===\n\n{load_task_input(here, task_id)}\n\n"
                f"=== VERSION A ===\n\n{shown[0][1]}\n\n"
                f"=== VERSION B ===\n\n{shown[1][1]}\n"
            )
            n += 1

    (pairs_dir / "key.json").write_text(json.dumps(key, indent=2))
    print(f"wrote {n} blinded pairs to {pairs_dir}")
    print(f"mapping in {pairs_dir / 'key.json'} — do not feed it to the judge\n")
    print("judge them with (prompt on stdin — --tools is variadic and would eat it):")
    print(f"""
  for p in {pairs_dir}/*__*.txt; do
    echo "=== $(basename "$p" .txt)"
    ( cd "$(mktemp -d)" && claude -p --model opus --tools "" \\
        --no-session-persistence < "$p" )
  done | tee {args.out_dir}/verdicts.txt
""")
    print(f"then resolve labels:  python3 {Path(__file__).name} "
          f"{args.out_dir} --resolve {args.out_dir}/verdicts.txt")


def resolve(out_dir: Path, verdicts_file: Path) -> None:
    """Map blinded A/B verdicts back to arm names and tally wins."""
    key = json.loads((out_dir / "pairs" / "key.json").read_text())
    text = verdicts_file.read_text()

    wins = defaultdict(int)
    losses = defaultdict(int)
    ties = defaultdict(int)
    rows = []

    # Blocks are delimited by the "=== <pair_id>" lines the judging loop echoes.
    blocks = re.split(r"^===\s*(\S+)\s*$", text, flags=re.M)[1:]
    for pair_id, block in zip(blocks[::2], blocks[1::2]):
        if pair_id not in key:
            print(f"warn: verdict for unknown pair {pair_id}", file=sys.stderr)
            continue
        m = re.search(r"\{.*\}", block, re.S)
        if not m:
            print(f"warn: no JSON verdict in block {pair_id}", file=sys.stderr)
            continue
        try:
            v = json.loads(m.group(0))
        except json.JSONDecodeError:
            print(f"warn: unparseable verdict in block {pair_id}", file=sys.stderr)
            continue

        mapping = key[pair_id]
        winner = v.get("winner")
        if winner == "tie":
            ties[mapping["A"]] += 1
            ties[mapping["B"]] += 1
            won, lost = None, None
        elif winner in ("A", "B"):
            won = mapping[winner]
            lost = mapping["B" if winner == "A" else "A"]
            wins[won] += 1
            losses[lost] += 1
        else:
            print(f"warn: verdict {winner!r} in {pair_id} is not A/B/tie", file=sys.stderr)
            continue

        rows.append({
            "pair": pair_id, "task": mapping["task"],
            "winner": won, "loser": lost,
            "confidence": v.get("confidence"), "reason": v.get("reason"),
            "fidelity_failures": {mapping[k]: v.get("fidelity_failures", {}).get(k, [])
                                  for k in ("A", "B")},
        })

    dest = out_dir / "verdicts.json"
    dest.write_text(json.dumps(rows, indent=2))

    arms = sorted(set(list(wins) + list(losses) + list(ties)))
    print("| Arm | wins | losses | ties |")
    print("|---|---|---|---|")
    for a in arms:
        print(f"| `{a}` | {wins[a]} | {losses[a]} | {ties[a]} |")
    print(f"\njudged {len(rows)} pairs; detail in {dest}")


if __name__ == "__main__":
    main()

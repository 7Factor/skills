#!/usr/bin/env python3
"""Deterministic scoring for the technical-writing eval.

Two metric families, deliberately separated:

  STYLE    proxies for ambiguity and slop. Every instructed arm should improve these.
  FIDELITY whether the arm invented, hardened, or leaked a claim. Only the skill has
           rules aimed at these, so this is where H2 is decided.

Length is reported and never scored. ASD-STE100 rule 4.2 forbids shortening by
omission, so a shorter output is not a better one.

A FIDELITY failure is not tradeable against a STYLE win: the two are reported
separately and never summed into one number.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

# Slop markers. Sourced from the HN thread's own complaints (heavy signposting,
# meta-commentary, marketing register) plus the usual AI tells.
TELLS = [
    r"\bit'?s worth noting\b", r"\bit'?s important to (note|remember)\b",
    r"\bthat said\b", r"\bat the end of the day\b", r"\bin today'?s\b",
    r"\bdelve into\b", r"\bnavigat(e|ing) the\b", r"\bunlock(s|ing)?\b",
    r"\bseamless(ly)?\b", r"\brobust\b", r"\bcomprehensive\b", r"\bleverag(e|ing)\b",
    r"\butili[sz](e|ing)\b", r"\bfacilitat(e|ing)\b", r"\borchestrat(e|ing)\b",
    r"\bstreamlin(e|ing)\b", r"\bcutting[- ]edge\b", r"\bbest practices?\b",
    r"\bgame[- ]chang(er|ing)\b", r"\bplays? a (key|vital|crucial|central) role\b",
    r"\bcritical component\b", r"\bhere'?s (the|what|why|how)\b",
    r"\bthe (key|real) (insight|takeaway|question) (is|here)\b",
    r"\bnot (just|only) \w+ (but|—)\b", r"\bmoving forward\b",
]

HEDGES = [
    r"\bmight\b", r"\bperhaps\b", r"\barguably\b", r"\bsomewhat\b", r"\bfairly\b",
    r"\bquite\b", r"\brelatively\b", r"\bgenerally\b", r"\btypically\b",
    r"\busually\b", r"\bin some cases\b", r"\bcould potentially\b", r"\bit seems\b",
]

# Passive voice with no named actor: "is performed", "was updated" not followed by "by".
PASSIVE = re.compile(
    r"\b(?:is|are|was|were|be|been|being)\s+(\w+(?:ed|en))\b(?!\s+by\b)", re.I)

# Abstract nouns standing where a verb belongs.
NOMINALIZATION = re.compile(
    r"\b\w{4,}(?:tion|sion|ment|ance|ence|ity|ness)\b", re.I)

CODE_FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`]*`")

# Markdown emphasis around a field name hid it from the `required` patterns:
# "**Sources:**" never matched /^#*\s*sources/. Normalize before matching.
EMPHASIS = re.compile(r"[*_]{1,3}")


def normalize(text: str) -> str:
    """Strip markdown emphasis and list markers so field-name patterns can anchor."""
    lines = []
    for ln in text.splitlines():
        ln = EMPHASIS.sub("", ln)
        ln = re.sub(r"^\s*[-*+]\s+", "", ln)
        lines.append(ln.strip())
    return "\n".join(lines)


def prose_only(text: str) -> str:
    """Strip code blocks. Style rules apply to prose, not to the code being documented."""
    return INLINE_CODE.sub(" ", CODE_FENCE.sub(" ", text))


def sentences(text: str) -> list[str]:
    # Skip list markers and headings; they are structure, not sentences.
    lines = [ln for ln in text.splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    joined = " ".join(lines)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(\[])", joined)
    return [p.strip() for p in parts if len(p.split()) >= 3]


def count_patterns(text: str, patterns: list[str]) -> int:
    return sum(len(re.findall(p, text, re.I)) for p in patterns)


def per_kw(n: int, words: int) -> float:
    """Rate per 1000 words, so a longer output is not penalized for being longer."""
    return round(n * 1000 / words, 1) if words else 0.0


def load_task(path: Path) -> dict:
    raw = path.read_text().split("---", 2)
    meta = yaml.safe_load(raw[1])
    meta["input"] = raw[2]
    validate_task(path.stem, meta)
    return meta


def validate_task(task_id: str, meta: dict) -> None:
    """Reject rules that fire on every output regardless of arm.

    A term group holding both "pool" and "connection pool" always reports drift,
    because matching the long form also matches the short one. Such a rule measures
    the rule, not the arm.
    """
    for group in meta.get("terms") or []:
        low = [t.lower() for t in group]
        for a in low:
            for b in low:
                if a != b and a in b:
                    raise SystemExit(
                        f"{task_id}: term group {group} has '{a}' inside '{b}', so it "
                        f"flags every output. Use terms that are not substrings.")
    for rule in meta.get("must_hedge") or []:
        if "presence" not in rule:
            raise SystemExit(
                f"{task_id}: must_hedge rule '{rule.get('claim')}' needs a 'presence' "
                f"list, else an omitted claim is miscounted as a hardened one.")


def score_style(text: str) -> dict:
    prose = prose_only(text)
    words = len(prose.split())
    sents = sentences(prose)
    lengths = sorted(len(s.split()) for s in sents)

    def pct(p):
        return lengths[min(int(len(lengths) * p), len(lengths) - 1)] if lengths else 0

    return {
        "words": words,
        "sentences": len(sents),
        "median_sentence_words": pct(0.5),
        "p90_sentence_words": pct(0.9),
        "over_20_words_pct": round(
            100 * sum(1 for n in lengths if n > 20) / len(lengths), 1) if lengths else 0.0,
        "tells_per_1k": per_kw(count_patterns(prose, TELLS), words),
        "hedges_per_1k": per_kw(count_patterns(prose, HEDGES), words),
        "agentless_passive_per_1k": per_kw(len(PASSIVE.findall(prose)), words),
        "nominalizations_per_1k": per_kw(len(NOMINALIZATION.findall(prose)), words),
    }


def score_fidelity(text: str, task: dict) -> dict:
    """Did the arm invent, harden, leak, or flatten a claim?

    Every finding names the task rule it broke, so a failure is auditable rather
    than a number to trust.
    """
    findings = []
    norm = normalize(text)

    for rule in task.get("forbidden") or []:
        hits = re.findall(rule["pattern"], norm, re.M)
        if hits:
            findings.append({
                "kind": "forbidden",
                "why": rule["why"],
                "matched": list({h if isinstance(h, str) else h[0] for h in hits})[:3],
            })

    for rule in task.get("must_hedge") or []:
        # An absent claim has no hedge markers either, so absence and hardening look
        # identical unless presence is tested first. They are opposite outcomes:
        # hardening asserts something unsupported, omission just leaves it out.
        present = any(re.search(rf"\b{re.escape(m)}", norm, re.I)
                      for m in rule["presence"])
        hedged = any(re.search(rf"\b{re.escape(m)}", norm, re.I)
                     for m in rule["markers"])
        if present and not hedged:
            findings.append({
                "kind": "claim_hardened",
                "claim": rule["claim"],
                "why": rule["why"],
                "matched": [],
            })
        elif not present and not rule.get("absent_ok", False):
            findings.append({
                "kind": "claim_absent",
                "claim": rule["claim"],
                "why": f"{rule['why']} (claim not raised at all)",
                "matched": [],
            })

    for rule in task.get("required") or []:
        if not re.search(rule["pattern"], norm, re.M):
            findings.append({
                "kind": "omitted",
                "why": rule["why"],
                "matched": [],
            })

    drift = []
    for group in task.get("terms") or []:
        used = [t for t in group if re.search(rf"\b{re.escape(t)}\b", text, re.I)]
        if len(used) > 1:
            drift.append(used)
    if drift:
        findings.append({
            "kind": "term_drift",
            "why": "same concept named more than one way",
            "matched": [" / ".join(g) for g in drift],
        })

    return {
        "failures": len(findings),
        "claim_hardened": sum(1 for f in findings if f["kind"] == "claim_hardened"),
        "claim_absent": sum(1 for f in findings if f["kind"] == "claim_absent"),
        "forbidden": sum(1 for f in findings if f["kind"] == "forbidden"),
        "omitted": sum(1 for f in findings if f["kind"] == "omitted"),
        "term_drift": sum(1 for f in findings if f["kind"] == "term_drift"),
        "findings": findings,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()

    here = Path(__file__).parent
    tasks = {p.stem: load_task(p) for p in sorted((here / "tasks").glob("*.md"))}

    results = {}
    for f in sorted(args.out_dir.glob("*__*.txt")):
        task_id, arm = f.stem.split("__", 1)
        if task_id not in tasks:
            print(f"warn: no task definition for {task_id}, skipping", file=sys.stderr)
            continue
        text = f.read_text()
        # An in-flight generation truncates its destination before filling it, so a
        # concurrent score run sees an empty file and reports every hedge as missing.
        # Refuse rather than emit a plausible wrong number.
        if len(text.split()) < 20:
            print(f"warn: {f.name} has {len(text.split())} words — partial or failed "
                  f"generation, skipping", file=sys.stderr)
            continue
        results[f.stem] = {
            "task": task_id, "arm": arm,
            "style": score_style(text),
            "fidelity": score_fidelity(text, tasks[task_id]),
        }

    if not results:
        print("no outputs found — run ./run.sh first", file=sys.stderr)
        return 1

    dest = args.out_dir / "scores.json"
    dest.write_text(json.dumps(results, indent=2))

    if args.markdown:
        emit_markdown(results)
    print(f"\nwrote {dest}", file=sys.stderr)
    return 0


def emit_markdown(results: dict) -> None:
    arms = sorted({r["arm"] for r in results.values()})
    tasks = sorted({r["task"] for r in results.values()})

    print("## Fidelity failures (lower is better; this decides H2)\n")
    print("| Task | " + " | ".join(arms) + " |")
    print("|---" * (len(arms) + 1) + "|")
    for t in tasks:
        row = []
        for a in arms:
            r = results.get(f"{t}__{a}")
            row.append("—" if not r else str(r["fidelity"]["failures"]))
        print(f"| `{t}` | " + " | ".join(row) + " |")
    totals = []
    for a in arms:
        totals.append(str(sum(r["fidelity"]["failures"]
                              for r in results.values() if r["arm"] == a)))
    print("| **total** | " + " | ".join(f"**{x}**" for x in totals) + " |")

    print("\n### Failures by kind\n")
    print("| Arm | claim hardened | claim absent | forbidden | omitted | term drift |")
    print("|---|---|---|---|---|---|")
    for a in arms:
        rs = [r for r in results.values() if r["arm"] == a]
        print(f"| `{a}` | "
              + " | ".join(str(sum(r["fidelity"][k] for r in rs))
                           for k in ("claim_hardened", "claim_absent", "forbidden",
                                     "omitted", "term_drift"))
              + " |")

    print("\n## Style (rates per 1000 words; lower is better)\n")
    keys = ["tells_per_1k", "hedges_per_1k", "agentless_passive_per_1k",
            "nominalizations_per_1k", "over_20_words_pct", "median_sentence_words"]
    print("| Arm | " + " | ".join(k.replace("_per_1k", "").replace("_", " ")
                                 for k in keys) + " | words |")
    print("|---" * (len(keys) + 2) + "|")
    for a in arms:
        rs = [r for r in results.values() if r["arm"] == a]
        cells = [f"{sum(r['style'][k] for r in rs) / len(rs):.1f}" for k in keys]
        wc = sum(r["style"]["words"] for r in rs)
        print(f"| `{a}` | " + " | ".join(cells) + f" | {wc} |")
    print("\n_Word counts are context, not score._")

    print("\n## Every finding\n")
    for name in sorted(results):
        fs = results[name]["fidelity"]["findings"]
        if not fs:
            continue
        print(f"**`{name}`**\n")
        for f in fs:
            matched = f" — matched: `{'`, `'.join(f['matched'])}`" if f["matched"] else ""
            print(f"- `{f['kind']}`: {f['why']}{matched}")
        print()


if __name__ == "__main__":
    sys.exit(main())

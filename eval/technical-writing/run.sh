#!/usr/bin/env bash
# Generate one output per (task, arm) pair via headless claude.
#
# Runs from a scratch cwd so no project CLAUDE.md is discovered. The operator's
# global ~/.claude/CLAUDE.md still loads unless --bare is available; see README.md
# under "Known confound". Mode is recorded in out/manifest.json.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="sonnet"
OUT="$HERE/out"
ONLY_TASKS=""
ONLY_ARMS=""
BARE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model) MODEL="$2"; shift 2 ;;
    --tasks) ONLY_TASKS="$2"; shift 2 ;;
    --arms)  ONLY_ARMS="$2"; shift 2 ;;
    --out)   OUT="$2"; shift 2 ;;
    --bare)  BARE="1"; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

if [[ -n "$BARE" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "--bare requires ANTHROPIC_API_KEY (bare mode never reads OAuth or keychain)." >&2
  exit 2
fi

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT
mkdir -p "$OUT"

matches() { [[ -z "$2" ]] || [[ ",$2," == *",$1,"* ]]; }

count=0
for task_file in "$HERE"/tasks/*.md; do
  task="$(basename "$task_file" .md)"
  matches "$task" "$ONLY_TASKS" || continue

  # Split the task file: YAML frontmatter is config, everything after is the prompt.
  brief="$(python3 -c "
import sys, yaml
raw = open(sys.argv[1]).read().split('---', 2)
meta = yaml.safe_load(raw[1])
print(meta['brief'].strip())
" "$task_file")"
  body="$(python3 -c "
import sys
print(open(sys.argv[1]).read().split('---', 2)[2].strip())
" "$task_file")"

  for arm_file in "$HERE"/arms/*.txt; do
    arm="$(basename "$arm_file" .txt)"
    matches "$arm" "$ONLY_ARMS" || continue

    dest="$OUT/${task}__${arm}.txt"
    if [[ -s "$dest" ]]; then
      echo "skip  $task / $arm (exists)"
      continue
    fi

    prompt="$brief

$body

Output only the finished artifact. No preamble, no explanation of your choices."

    sys="$(cat "$arm_file")"
    # The prompt goes in on stdin, never as a positional argument: --tools is
    # variadic, so `--tools "" "$prompt"` silently swallows the prompt. That bug
    # hit only the baseline arm, whose flag list ends with --tools.
    cmd=(claude -p --model "$MODEL" --no-session-persistence --tools "")
    [[ -n "$BARE" ]] && cmd+=(--bare)
    # An empty system prompt would be rejected; baseline gets no flag at all.
    [[ -n "$sys" ]] && cmd+=(--append-system-prompt "$sys")

    echo "gen   $task / $arm"
    ( cd "$SCRATCH" && printf '%s' "$prompt" | "${cmd[@]}" ) > "$dest" || {
      echo "FAILED $task / $arm" >&2
      rm -f "$dest"
      continue
    }
    count=$((count + 1))
  done
done

python3 - "$OUT" "$MODEL" "${BARE:-0}" <<'PY'
import json, os, subprocess, sys
out, model, bare = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                     capture_output=True, text=True).stdout.strip()
json.dump({
    "model": model,
    "bare": bare,
    "clean_room": bare,
    "skill_revision": rev,
    "note": ("clean room" if bare else
             "operator global CLAUDE.md present in all arms; relative comparisons only"),
    "outputs": sorted(f for f in os.listdir(out) if f.endswith(".txt")),
}, open(os.path.join(out, "manifest.json"), "w"), indent=2)
PY

echo "generated $count new output(s) into $OUT"
echo "next: python3 $HERE/score.py $OUT --markdown"

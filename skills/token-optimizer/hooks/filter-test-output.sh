#!/bin/bash
# PreToolUse hook: when Claude runs a test command, rewrite it to show only
# failures. A 10,000-line passing test run becomes ~0 lines of context.
# Install: chmod +x this file, then register it in settings.json (see README).

input=$(cat)
cmd=$(echo "$input" | jq -r '.tool_input.command')

# Adjust the pattern list to match your test runners
if [[ "$cmd" =~ ^(npm test|pnpm test|yarn test|pytest|go test|cargo test) ]]; then
  filtered_cmd="$cmd 2>&1 | grep -A 5 -E '(FAIL|ERROR|error:|failed)' | head -100"
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"allow\",\"updatedInput\":{\"command\":\"$filtered_cmd\"}}}"
else
  echo "{}"
fi

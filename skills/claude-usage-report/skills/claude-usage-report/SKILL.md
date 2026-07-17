---
name: claude-usage-report
description: Regenerate a Claude Code usage/cost report for a date or period.
disable-model-invocation: true
compatibility: Designed for Claude Code (reads its local transcripts; per-account attribution needs the plugin's SessionStart hook). Requires Python 3.
---

# claude-usage-report

Report Claude Code spend over a period from local transcripts, attributing cost to the
work each session did. The **headlines** are the aggregate tables; per-session narrative
is supporting detail whose depth scales down as the session count grows.

## Steps

0. **Ensure a Python 3 runtime** before anything else — every script here needs one. Work
   down this list and use the first that's available; substitute it for `python3` in every
   command below.
   1. **Local interpreter** (preferred): `python3` — or `python` if `python --version`
      reports 3.x, or `py -3` on Windows.
   2. **Docker** (fallback, when no local Python 3 but `docker` is available): run the
      scripts in an ephemeral container, mounting the user's home so the scripts read the
      same `~/.claude/...` transcripts and write the report to the same `~/`:
      ```
      docker run --rm -e HOME="$HOME" -v "$HOME:$HOME" -w "$HOME" \
        --user "$(id -u):$(id -g)" python:3-slim python <script> <args>
      ```
      Default networking lets pricing refresh reach Anthropic's page. The first run pulls
      the `python:3-slim` image — tell the user that's expected, then it's cached.
   3. **Neither available** → stop and tell the user, e.g.:
      > This skill needs Python 3 (or Docker). Install one and re-run:
      > • macOS: `brew install python3`  • Debian/Ubuntu: `sudo apt install python3`
      > • Windows: from https://python.org (adds the `py` launcher)  • Docker: https://docs.docker.com/get-docker/

   Do not attempt the report without one of these — the parser can't run and every number
   depends on it.

1. **Run the parser** (`usage_report.py`, in this skill's directory) for the requested
   period:
   ```
   python3 usage_report.py                      # today
   python3 usage_report.py 2026-07-06           # one day
   python3 usage_report.py 2026-07-01 2026-07-31 # inclusive range
   python3 usage_report.py 7d | week | month     # last N days | 7 | 30
   ```
   Before costing, it auto-refreshes prices (see step 2), then parses
   `~/.claude/projects/**/*.jsonl` (dedup on `(file, message.id)`, subagent files grouped
   under their parent session), applies date-aware pricing from `prices.json`, and prints
   a `PRICING UPDATE` line, then PERIOD, TOTAL, RATES, BY MODEL, BY DAY, BY PROJECT, BY
   ACCOUNT, BY SESSION, then the human prompts of the top-15 sessions by cost. Take every
   number the report shows from this output; derive none by hand. Pass `--account <email>`
   to scope the whole report to one Claude account.

2. **Handle the `PRICING UPDATE` line.** Pricing self-refreshes from Anthropic's
   canonical page (`update_pricing.py`, throttled to once per 24h; `--update` forces it),
   so you do not hand-verify rates. Two things to act on:
   - **Escalate novelty.** If the line reports `NEW MODELS` or `NEW RATE COLUMNS`, surface
     them in your chat summary and ask whether any need special handling (a new model is
     synced automatically; a new rate column is stored but not costed).
   - **Agent-repair tier.** If the line reports an `error` (fetch/parse/sanity failure —
     the page restructured, returned nonsense, or dropped a core model), `prices.json` was
     left untouched and the numbers used the last-good file. Fetch the page yourself
     (`https://platform.claude.com/docs/en/about-claude/pricing.md`), correct
     `prices.json`, fix `update_pricing.py`'s table parser to match the new structure, then
     rerun. Each `prices.json` record is the rate from its `effective` date until the next;
     the parser costs each message at the rate in effect on its day. Known gap (accepted):
     a price change is only captured once a refresh runs, so a change mid-window may leave
     the earlier part of that day/period on the prior rate until the next refresh.

3. **Describe each session with printed prompts** in one or two factual sentences: what
   the work was — repos, tickets/PRs, tools/agents used. Report what happened; leave
   worth or justification out. Done when every session that has printed prompts has a
   description.

4. **Pick the shape** by session count, then write the report to
   `~/claude-usage-{PERIOD}.md` (`{PERIOD}` = the date, or `{start}_to_{end}`):
   - **≤15 sessions — detail:** include the per-session table and a per-session detail
     section (2–5 bullets each, from step 3).
   - **>15 sessions — digest:** drop the per-session detail section; describe each day in
     one line in the BY DAY table instead, and detail only the top 15 sessions the parser
     dumped prompts for.

   The BY DAY table appears whenever the period spans more than one day; it is the primary
   breakdown in digest shape.

Then report the path and a two-line chat summary (total; by-model split).

## Report skeleton

```markdown
# Claude Code usage & cost — {PERIOD}

**Total: ${grand}** ({tokens} tokens, {N} sessions over {span} days). {One factual
sentence naming the largest day/project/theme.}

## By day            {only when span > 1 day}
| Date | Cost | Tokens | Sessions | Summary |   {Summary column only in digest shape}
|---|---:|---:|---:|---|

## By model
| Model | Cost | Input | Output | Cache-write | Cache-read |
|---|---:|---:|---:|---:|---:|
{each token cell shows tokens then the inferred $ on a second line: `1,234,567<br>$0.62`}

## By session        {detail shape only}
| Cost | Description | Session | Day | Tokens |
|---:|---|---|---|---:|

## Session detail     {detail shape; or "Top sessions" in digest shape}
{per session, cost desc: `### ${cost} — {description} (`{sid}`, {day})`, then step-3 bullets}

## By project
| Cost | Project | Tokens |
|---:|---|---:|

## By account
| Cost | Account | Tokens |
|---:|---|---:|
{from the BY ACCOUNT block. `unknown (pre-hook)` = sessions that ran before the
account-recording hook existed; `mixed: a | b` = a session that switched accounts.}

## Reference

Model prices ($/MTok), records in effect during the period:
| Model | Effective | Input | Output | Cache-write (5m) | Cache-read | Note |
|---|---|---:|---:|---:|---:|---|
{the RATES block from parser output — one row per applicable record; a model with a
mid-period price change contributes more than one row}

Caveats:
- Estimate from local transcripts × public list prices, not a bill — for the authoritative
  number use the Anthropic Console usage dashboard for the period.
- Cache-write assumes the 5-minute TTL (1.25× input); a 1-hour TTL would be 2× input.
- Opus's 1M-context (`[1m]`) runs bill at standard rates; there is no >200K premium tier.
- Account attribution comes from this plugin's `SessionStart` hook (`hooks/hooks.json` →
  `record_account.sh` → `record_account.py` → `~/.claude/session-accounts.jsonl`) and is
  prospective: sessions
  before the plugin was installed show as `unknown (pre-hook)`, and a mid-session account
  switch that skips a resume may be missed. The authoritative per-account figure is the
  Anthropic Console.
- **If accounts show `unknown` but the plugin is installed** (not the npx-skill-only case),
  the `SessionStart` hook is silently failing — almost always because Python 3 wasn't on
  PATH when a session started (the hook exits 0 by design, so it never announces this).
  Verify with `python3 --version`, confirm `~/.claude/session-accounts.jsonl` is being
  appended to on new sessions, and if Python 3 is missing, tell the user how to install it
  (see Step 0). Attribution is prospective — it only starts from the next session after the
  fix.
- Not visible here: usage on claude.ai web/desktop, on other machines, or per-call
  server-side tool charges (web_search/web_fetch).
```

## Rules

- Deliver information; do not editorialize on whether the spend was worthwhile.
- Tables are the headlines and lead the report; narrative follows.
- Pricing lives only in `prices.json` as effective-dated records, refreshed from
  Anthropic's canonical page by `update_pricing.py`. Never hardcode a rate in the parser.
  Hand-edit `prices.json` only in the agent-repair tier (step 2) or to pre-enter a known
  future price; the updater preserves records it didn't write.
- Account attribution is fed by the `SessionStart` hook, declared in this plugin's
  `hooks/hooks.json` via `${CLAUDE_PLUGIN_ROOT}` — so installing/removing the plugin
  activates/deactivates it with no orphaned `settings.json` entry. The hook runs
  `record_account.sh`, a wrapper that resolves a Python 3 interpreter (`python3` → `python`
  if v3 → `py -3`) before handing off to `record_account.py`; if none is found it exits 0
  silently so a session is never blocked or errored (just unattributed). The script appends
  to `~/.claude/session-accounts.jsonl`; the report treats a missing sidecar as all
  `unknown (pre-hook)`.
- **If the user can't tell which account a report or its sessions belong to** (the
  **By account** table is all `unknown`), it almost certainly means this was installed as a
  plain skill via `npx skills`, which copies skill files but does **not** install the hook.
  Tell them to reinstall it as a **Claude Code plugin** instead — that ships the
  `SessionStart` hook that records the active account — and point them to this repo's README
  for the exact commands and the skill-vs-plugin tradeoff. Attribution is prospective, so it
  only begins from the first session after the plugin is installed.

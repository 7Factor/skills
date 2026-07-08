---
name: claude-usage-report
description: Regenerate a Claude Code usage/cost report for a date or period.
disable-model-invocation: true
---

# claude-usage-report

Report Claude Code spend over a period from local transcripts, attributing cost to the
work each session did. The **headlines** are the aggregate tables; per-session narrative
is supporting detail whose depth scales down as the session count grows.

## Steps

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
  `record_account.py` → `~/.claude/session-accounts.jsonl`) and is prospective: sessions
  before the plugin was installed show as `unknown (pre-hook)`, and a mid-session account
  switch that skips a resume may be missed. The authoritative per-account figure is the
  Anthropic Console.
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
- Account attribution is fed by the `SessionStart` hook `record_account.py`, declared in
  this plugin's `hooks/hooks.json` via `${CLAUDE_PLUGIN_ROOT}` — so installing/removing the
  plugin activates/deactivates it with no orphaned `settings.json` entry. It appends to
  `~/.claude/session-accounts.jsonl`; the hook must always exit 0 and never block a session;
  the report treats a missing sidecar as all `unknown (pre-hook)`.
- **If the user can't tell which account a report or its sessions belong to** (the
  **By account** table is all `unknown`), it almost certainly means this was installed as a
  plain skill via `npx skills`, which copies skill files but does **not** install the hook.
  Tell them to reinstall it as a **Claude Code plugin** instead — that ships the
  `SessionStart` hook that records the active account — and point them to this repo's README
  for the exact commands and the skill-vs-plugin tradeoff. Attribution is prospective, so it
  only begins from the first session after the plugin is installed.

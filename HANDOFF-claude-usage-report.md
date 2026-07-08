# Handoff — `claude-usage-report` plugin

**Date:** 2026-07-07
**Repo:** `github.com/7Factor/skills` (`/Users/scott/dev/7f/skills`)
**Branch:** `add-claude-usage-report-plugin` @ `befca67` — **committed, NOT pushed, no PR yet**
**Status:** built, unit-tested locally, committed. Two things remain: Scott installs the plugin (`/plugin`, below), then push + PR.

> This file is untracked on purpose — it's a working handoff, not a catalog artifact. Delete it or move it out before merging if you don't want it in the PR.

---

## What this is

A Claude Code **plugin** that reports Claude Code **usage & cost** from local session
transcripts. Three capabilities, built in this order over one long session:

1. **Per-session cost report** with each session's *purpose* (not just IDs), by day / model / project / account.
2. **Date-aware, self-refreshing pricing** — costs each message at the rate in effect on its day; refreshes rates from Anthropic's canonical pricing page.
3. **Per-account attribution** — a `SessionStart` hook records which Claude account was active, because transcripts don't.

It is packaged **dual-purpose**: the same repo works as a `npx skills` catalog **and** a Claude Code plugin marketplace (see Distribution).

---

## Where everything lives (final state)

```
7Factor/skills/                                  ← github.com/7Factor/skills
├── .claude-plugin/marketplace.json              ← NEW. Merged manifest (npx skills + Claude Code)
├── plugins/claude-usage-report/                 ← NEW. The plugin
│   ├── .claude-plugin/plugin.json               ← plugin manifest (name: claude-usage-report)
│   ├── hooks/hooks.json                          ← SessionStart hook, uses ${CLAUDE_PLUGIN_ROOT}
│   └── skills/claude-usage-report/               ← the skill + its scripts
│       ├── SKILL.md                              ← user-invoked (disable-model-invocation: true)
│       ├── usage_report.py                        ← the parser/report generator
│       ├── update_pricing.py                      ← canonical-page price scraper
│       ├── prices.json                            ← effective-dated price records (+ _meta.last_checked)
│       └── record_account.py                      ← the SessionStart hook script
├── skills/mentor/                               ← pre-existing, untouched
├── README.md, LICENSE                           ← pre-existing
└── .gitignore                                   ← added __pycache__/ and *.pyc
```

Other locations:
- **Staging copy:** `~/.claude/plugin-src/` — identical source I built the repo copy from. Redundant now; safe to delete once the plugin is installed and pushed.
- **Old standalone skill:** `~/.claude/skills/claude-usage-report/` — **deleted** this session (superseded).
- **Account sidecar (runtime, outside repo):** `~/.claude/session-accounts.jsonl` — written by the hook, read by the report. Currently empty/absent until the plugin is installed and a session starts.
- **Generated reports (outputs, in $HOME):** `~/claude-usage-2026-07-06.md`, `~/claude-usage-2026-06-24_to_2026-06-30.md`, `~/claude-usage-2026-07-01_to_2026-07-07.md` (+ a `.manual-backup.md`).

---

## Remaining steps

1. **Install the plugin (Scott — interactive `/plugin`, in the TUI):**
   ```
   /plugin marketplace add /Users/scott/dev/7f/skills
   /plugin install claude-usage-report@7factor
   ```
   (`7factor` is the marketplace name in `marketplace.json`.)
2. **Validate after install** (this is the one thing NOT verified locally — the two ecosystems resolve relative paths differently and neither installer could be exercised from the build session):
   - `/plugin` lists `claude-usage-report`.
   - Start a fresh session → `~/.claude/session-accounts.jsonl` gets a line with your account.
   - Run the skill → report generates; **By account** shows your account (not `unknown`).
   - `npx skills` still sees the catalog (the merged manifest didn't break skill discovery).
   - If a path fails to resolve in either tool, fix `marketplace.json` paths **before** pushing — nothing is in shared history yet.
3. **Push + open PR** (Scott, or direct me to): `git push -u origin add-claude-usage-report-plugin` then a PR to `7Factor/skills`. Both are external/left to you per the git rule below.

---

## How the pieces work

- **`usage_report.py`** — invoked via the skill (`/claude-usage-report [date | range | 7d|week|month] [--account <email>] [--update]`). Parses `~/.claude/projects/**/*.jsonl`, dedups on `(file, message.id)`, groups subagent files under their parent session, costs each message at its day's rate, and prints TOTAL / RATES / BY MODEL / BY DAY / BY PROJECT / BY ACCOUNT / BY SESSION + top-15 session prompts. The agent turns that into the Markdown report. Report **shape** scales with session count: ≤15 = per-session detail; >15 = by-day digest. Skips `<synthetic>` (Claude Code placeholder model).
- **`update_pricing.py`** — on each report run (throttled to once/24h via `_meta.last_checked`; `--update` forces), fetches `https://platform.claude.com/docs/en/about-claude/pricing.md`, parses the model table, sanity-gates it, and appends effective-dated records to `prices.json`. Escalates **new models** / **new rate columns** in the report. If the fetch/parse/sanity fails, it writes nothing and emits an error → **agent-repair tier**: a human/agent fetches the page and fixes the parser.
- **`prices.json`** — one or more `{effective, in, out, cw, cr, ...}` records per model, sorted by date; the record in effect on a message's day is used. Ships seeded with current prices (incl. Sonnet 5 intro $2/$10 through 2026-08-31 and standard $3/$15 from 2026-09-01, discovered from the page).
- **`record_account.py`** (the hook) — on `SessionStart` (startup/resume), reads `oauthAccount` from `~/.claude.json` and appends `{session_id, source, account, org, ts}` to `~/.claude/session-accounts.jsonl`. Always exits 0, never blocks. Declared in `hooks/hooks.json` via `${CLAUDE_PLUGIN_ROOT}` — so installing/removing the plugin activates/deactivates it with **no orphaned settings.json entry**.

---

## Distribution: why dual-purpose works

`.claude-plugin/marketplace.json` is a **superset manifest**. Claude Code reads
`name`/`owner`/`plugins[].source`; the Skills CLI (`vercel-labs/skills`, per its
"Plugin Manifest Discovery" docs) reads `metadata.pluginRoot`/`plugins[].skills`. Each
ignores the other's fields, so one file serves both:
- `/plugin install claude-usage-report@7factor` → skill **+ hook** (full account tracking).
- `npx skills add 7Factor/skills --skill ...` → skill **only** (no hook; account shows `unknown` — honest degradation, the report handles it).

---

## Key decisions & rationale

- **Plugin, not skill+installer** — Anthropic's docs make plugins the clean way to ship a hook with a skill: the hook lives in the plugin, so uninstalling removes it with no orphaned `settings.json` entry, and `${CLAUDE_PLUGIN_ROOT}` avoids hardcoded paths. (Earlier ad-hoc approach — a `record_account.py` hook hand-added to `~/.claude/settings.json` via an `install_hook.py` — was removed this session.)
- **Pricing from the canonical page, effective-dated** — Anthropic has no pricing API, but the docs page is canonical and parseable. Records are dated so historical reports use historical prices. Accepted gap: a price change is only captured at the next refresh, so a change mid-window can leave the earlier part on the old rate until refreshed.
- **Account attribution is prospective** — nothing local records the account historically, so pre-install sessions are `unknown (pre-hook)`. Mid-session account switches that skip a resume aren't caught (SessionStart granularity). Authoritative per-account $ = Anthropic Console.
- **Marketplace name `7factor`** — lowercase-with-digit is valid; matches 7Factor branding (never "seven-factor").

---

## Environment changes made this session (outside the repo)

- **`~/.claude/settings.json`** — removed the ad-hoc account hook; added git permission rules:
  - `allow` (silent): `git switch/tag/status/branch` (joined existing add/commit/fetch/log/rebase/stash/checkout/diff/pull/worktree).
  - `ask` (prompt to review): `git push`, `git reset --hard`, `git clean`, `git branch -D`, `git branch --delete`.
  - Backup: `~/.claude/settings.json.bak`.
- **Memories written** (`~/.claude/projects/-Users-scott-dev-7f-lt-lt-mono/memory/`):
  - `company-name-7factor.md` — write "7Factor"/"7F"/"7factor"; never "seven-factor".
  - `show-commands-before-running-git-ops.md` — updated: review only (a) `.git`-unrecoverable ops and (b) external-facing (push/PR unless directed); everything else (add/commit/branch/etc.) runs unprompted.

## Git rule in force (for the next agent)

Only pause for review on: **locally unrecoverable** ops (`reset --hard`, `clean`, `branch -D` of unpushed work, etc.) and **external-facing** ops (push, PR) unless already directed. `git add`/`commit`/branch/checkout/stash/tag/fetch run unprompted. That's why this work is committed but not pushed.

---

## TODO / open items

- [ ] Install the plugin and run the step-2 validation (esp. dual-tool path resolution — the one unverified thing).
- [ ] Push branch + open PR to `7Factor/skills`.
- [ ] Decide whether to delete `~/.claude/plugin-src/` (staging) and this HANDOFF file before merge.
- [ ] Optional: seed `prices.json` with a reset `_meta.last_checked` so a fresh clone refreshes immediately (currently stamped 2026-07-07).
- [ ] Optional finer-grained account tracking: add a `UserPromptSubmit` hook variant if mid-session account switches matter.

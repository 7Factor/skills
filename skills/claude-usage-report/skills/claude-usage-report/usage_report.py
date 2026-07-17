#!/usr/bin/env python3
"""Parse Claude Code transcripts over a period and print cost aggregates plus the
human prompts of the costliest sessions. Pricing is date-aware: each message is
costed at the rate in effect on its (UTC) day, read from prices.json next to this
script. The calling skill turns this output into a report and derives no numbers
of its own.

Usage:
  usage_report.py                     today
  usage_report.py 2026-07-06          one day
  usage_report.py 2026-07-01 2026-07-31   inclusive range
  usage_report.py 7d | week | month   last N days | last 7 | last 30

Prints: PERIOD, TOTAL, RATES (records in effect during the period), BY MODEL,
BY DAY, BY PROJECT, BY SESSION, then the human prompts for the top --top sessions
by cost (default 15). --top N overrides.
"""
import json, os, glob, sys, datetime
from collections import defaultdict

FIELDS = (("in","input_tokens"),("out","output_tokens"),
          ("cw","cache_creation_input_tokens"),("cr","cache_read_input_tokens"))
ROOT = os.path.expanduser("~/.claude/projects")
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
PRICES_PATH = os.path.join(SKILL_DIR, "prices.json")

# Refresh prices from Anthropic's canonical page before costing: throttled to once per
# 24h, `--update` forces it. Never blocks the report if the refresh fails — it falls
# back to the existing prices.json and surfaces the failure for the agent-repair tier.
sys.path.insert(0, SKILL_DIR)
_force_update = "--update" in sys.argv
if _force_update: sys.argv.remove("--update")
try:
    import update_pricing
    PRICING_MSG = update_pricing._fmt(update_pricing.maybe_update(force=_force_update))
except Exception as e:
    PRICING_MSG = f"PRICING UPDATE: skipped — updater error ({type(e).__name__}: {e})"

with open(PRICES_PATH) as f:
    PRICES = json.load(f)["models"]
for recs in PRICES.values():
    recs.sort(key=lambda r: r["effective"])
# match longest model key first so claude-sonnet-5 can't shadow claude-sonnet-4-6 etc.
PRICE_KEYS = sorted(PRICES, key=len, reverse=True)

# not real models — Claude Code placeholders that carry an all-zero usage object
SKIP_MODELS = {"<synthetic>"}

def norm_model(m):
    if not m or m in SKIP_MODELS: return None
    m = m.replace("[1m]", "")
    for base in PRICE_KEYS:
        if m.startswith(base): return base
    return m  # unknown → won't be found in PRICES, flagged UNPRICED

def rate_for(model, day):
    recs = PRICES.get(model)
    if not recs: return None
    best = None
    for r in recs:
        if r["effective"] <= day: best = r
        else: break
    return best  # None if day precedes the earliest record

def cw1_rate(rec):
    # 1-hour cache-write rate; fall back to 2x input if a record predates the cw_1h column
    return rec.get("cw_1h", 2*rec["in"])

def msg_cost(rec, u):
    if not rec: return 0.0
    c = sum(u[f]*rec[f] for f,_ in FIELDS if f != "cw")
    c += u["cw5"]*rec["cw"] + u["cw1"]*cw1_rate(rec)  # cache-write split by actual TTL
    return c/1e6

# --- arg parsing: period + optional --top N
argv = sys.argv[1:]
top = 15
if "--top" in argv:
    i = argv.index("--top"); top = int(argv[i+1]); del argv[i:i+2]
account_filter = None
if "--account" in argv:
    i = argv.index("--account"); account_filter = argv[i+1]; del argv[i:i+2]
today = datetime.date.today()
if not argv:
    start = end = today
elif len(argv) == 1:
    a = argv[0]
    if a == "week": start, end = today - datetime.timedelta(days=6), today
    elif a == "month": start, end = today - datetime.timedelta(days=29), today
    elif a.endswith("d") and a[:-1].isdigit():
        start, end = today - datetime.timedelta(days=int(a[:-1])-1), today
    else: start = end = datetime.date.fromisoformat(a)
else:
    start, end = datetime.date.fromisoformat(argv[0]), datetime.date.fromisoformat(argv[1])
S, E = start.isoformat(), end.isoformat()

def parent_session(path):
    parts = os.path.relpath(path, ROOT).split(os.sep)
    project = parts[0]
    sid = parts[parts.index("subagents")-1] if "subagents" in parts else os.path.splitext(parts[-1])[0]
    return project, sid

def user_text(content):
    if isinstance(content, str): return content
    if isinstance(content, list):
        return "\n".join(b.get("text","") for b in content
                         if isinstance(b, dict) and b.get("type")=="text")
    return ""

# session -> account, from the SessionStart hook sidecar (transcripts carry no account).
# A session with no record predates the hook; one with two accounts spanned a switch.
_acct_seen = defaultdict(set)
try:
    with open(os.path.expanduser("~/.claude/session-accounts.jsonl")) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: r = json.loads(line)
            except: continue
            if r.get("session_id") and r.get("account"):
                _acct_seen[r["session_id"]].add(r["account"])
except FileNotFoundError:
    pass

def acct_of(sid):
    a = _acct_seen.get(sid)
    if not a: return "unknown (pre-hook)"
    return next(iter(a)) if len(a) == 1 else "mixed: " + " | ".join(sorted(a))

seen = set()
sess_cost, sess_tok, sess_proj, sess_day = defaultdict(float), defaultdict(int), {}, {}
model_tok = defaultdict(lambda: defaultdict(int))     # model -> field -> tokens
model_catcost = defaultdict(lambda: defaultdict(float))  # model -> field -> $
model_cost = defaultdict(float)
unpriced = set()
day_cost, day_tok, day_sids = defaultdict(float), defaultdict(int), defaultdict(set)
proj_cost, proj_tok = defaultdict(float), defaultdict(int)
acct_cost, acct_tok = defaultdict(float), defaultdict(int)
first_ts, last_ts, prompts = defaultdict(lambda:"~"), defaultdict(str), defaultdict(list)

for path in glob.glob(os.path.join(ROOT, "**", "*.jsonl"), recursive=True):
    project, sid = parent_session(path)
    is_sub = "subagents" in path
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try: obj = json.loads(line)
                except: continue
                ts = obj.get("timestamp", "")
                day = ts[:10]
                if not (S <= day <= E): continue
                acct = acct_of(sid)
                if account_filter and acct != account_filter: continue
                sess_proj[sid] = project
                sess_day.setdefault(sid, day)
                msg = obj.get("message")
                if isinstance(msg, dict) and isinstance(msg.get("usage"), dict):
                    mid = msg.get("id"); key = (path, mid)
                    if mid is None or key not in seen:
                        if mid is not None: seen.add(key)
                        model = norm_model(msg.get("model"))
                        if model:
                            usage = msg["usage"]
                            u = {fk: (usage.get(k,0) or 0) for fk,k in FIELDS}
                            # split cache-write by TTL; legacy transcripts w/o the
                            # breakdown fall back to the combined field, costed as 5m
                            cc = usage.get("cache_creation") or {}
                            if "ephemeral_5m_input_tokens" in cc or "ephemeral_1h_input_tokens" in cc:
                                u["cw5"] = cc.get("ephemeral_5m_input_tokens",0) or 0
                                u["cw1"] = cc.get("ephemeral_1h_input_tokens",0) or 0
                            else:
                                u["cw5"] = u["cw"]; u["cw1"] = 0
                            rec = rate_for(model, day)
                            if rec is None: unpriced.add(model)
                            c = msg_cost(rec, u); t = sum(u[fk] for fk,_ in FIELDS)
                            for fk,_ in FIELDS:
                                model_tok[model][fk] += u[fk]
                                if not rec: continue
                                if fk == "cw":
                                    model_catcost[model][fk] += (u["cw5"]*rec["cw"] + u["cw1"]*cw1_rate(rec))/1e6
                                else:
                                    model_catcost[model][fk] += u[fk]*rec[fk]/1e6
                            model_cost[model] += c
                            sess_cost[sid] += c; sess_tok[sid] += t
                            day_cost[day] += c; day_tok[day] += t; day_sids[day].add(sid)
                            proj_cost[project] += c; proj_tok[project] += t
                            acct_cost[acct] += c; acct_tok[acct] += t
                            if ts < first_ts[sid]: first_ts[sid] = ts
                            if ts > last_ts[sid]: last_ts[sid] = ts
                if not is_sub and obj.get("type") == "user":
                    m = obj.get("message", {})
                    if isinstance(m, dict) and m.get("role") == "user":
                        txt = user_text(m.get("content")).strip()
                        if txt and not txt.startswith("<") and "tool_use_id" not in txt \
                           and not txt.startswith("Caveat:") and "[Request interrupted" not in txt:
                            prompts[sid].append(txt)
    except: continue

grand_cost = sum(sess_cost.values()); grand_tok = sum(sess_tok.values())
n = lambda x: f"{x:,}"
span_days = (end - start).days + 1

def applicable_records(model):
    recs = PRICES.get(model) or []
    active_at_start, later = None, []
    for r in recs:
        if r["effective"] <= S: active_at_start = r
        elif r["effective"] <= E: later.append(r)
    return ([active_at_start] if active_at_start else []) + later

print(f"PERIOD {S}..{E} ({span_days} day{'s' if span_days!=1 else ''})")
print(f"TOTAL ${grand_cost:,.2f} | {n(grand_tok)} tokens | {len(sess_cost)} sessions")
if account_filter:
    print(f"FILTERED to account: {account_filter}")
print(PRICING_MSG)
if unpriced:
    print(f"WARNING: no price record covers these models for part of the period: {', '.join(sorted(unpriced))} — add/extend them in prices.json.")

print("\nRATES in effect this period ($/MTok): model | effective | in | out | cache-write(5m) | cache-write(1h) | cache-read | note")
for m in sorted(model_tok, key=lambda m: model_cost[m], reverse=True):
    recs = applicable_records(m)
    if not recs:
        print(f"  {m} | (no price record — UNPRICED)")
    for r in recs:
        print(f"  {m} | {r['effective']} | {r['in']} | {r['out']} | {r['cw']} | {cw1_rate(r)} | {r['cr']} | {r.get('note','')}")

print("\nBY MODEL: model | total$ | in(tok,$) | out(tok,$) | cache-write(tok,$) | cache-read(tok,$)")
for m in sorted(model_tok, key=lambda m: model_cost[m], reverse=True):
    tok, cc = model_tok[m], model_catcost[m]
    if m in PRICES:
        cells = " | ".join(f"{n(tok[f])} ${cc[f]:,.2f}" for f,_ in FIELDS)
        print(f"  {m} | ${model_cost[m]:,.2f} | {cells}")
    else:
        cells = " | ".join(f"{n(tok[f])} $?" for f,_ in FIELDS)
        print(f"  {m} | UNPRICED (add to prices.json) | {cells}")

if span_days > 1:
    print("\nBY DAY: date | cost | tokens | sessions")
    for d in sorted(day_cost, reverse=True):
        print(f"  {d} | ${day_cost[d]:,.2f} | {n(day_tok[d])} | {len(day_sids[d])}")

print("\nBY PROJECT: cost | tokens | project")
for p in sorted(proj_cost, key=proj_cost.get, reverse=True):
    print(f"  ${proj_cost[p]:,.2f} | {n(proj_tok[p])} | {p}")

print("\nBY ACCOUNT: cost | tokens | account   (from SessionStart hook; 'unknown (pre-hook)' = ran before the hook existed)")
for a in sorted(acct_cost, key=acct_cost.get, reverse=True):
    print(f"  ${acct_cost[a]:,.2f} | {n(acct_tok[a])} | {a}")

ranked = sorted(sess_cost, key=sess_cost.get, reverse=True)
print("\nBY SESSION: cost | tokens | day | project | account | session | time UTC")
for sid in ranked:
    print(f"  ${sess_cost[sid]:,.2f} | {n(sess_tok[sid])} | {sess_day[sid]} | {sess_proj[sid]} | {acct_of(sid)} | {sid[:8]} | {first_ts[sid][11:19]}->{last_ts[sid][11:19]}")

shown = ranked[:top]
print(f"\n=== SESSION PROMPTS (top {len(shown)} of {len(ranked)} by cost) ===")
for sid in shown:
    print(f"\n--- {sid[:8]} (${sess_cost[sid]:,.2f}, {sess_day[sid]}, {sess_proj[sid]}) ---")
    ps = prompts.get(sid, [])
    for i, t in enumerate(ps, 1):
        t = " ".join(t.split())
        print(f"  [{i}] {t[:400]}{' …' if len(t)>400 else ''}")
    if not ps:
        print("  (no human prompts — subagent-only or resumed session)")
if len(ranked) > top:
    print(f"\n({len(ranked)-top} lower-cost sessions omitted from prompt dump; see BY SESSION / BY DAY.)")

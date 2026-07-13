#!/usr/bin/env python3
"""Refresh prices.json from Anthropic's canonical pricing page.

Two-tier by design: this is the deterministic tier. It fetches the pricing page's
markdown, parses the model-pricing table, sanity-checks the result, and — only if it
passes — syncs prices.json (appending effective-dated records; never clobbering known
future records). If the parse fails the sanity gate (page restructured, empty, all
zero, core models missing), it writes NOTHING and returns an error so the calling
skill can fall back to the agent-repair tier (fetch the page, fix this parser).

Costing fields: in=base input, out=output, cw=5-minute cache write, cr=cache read.
The 1-hour cache write (cw_1h) is stored for reference but not used for costing
(transcripts don't distinguish 5m vs 1h cache creation). Any table column that maps
to none of these is reported as a new rate category for the user to decide on.

Run standalone to force a refresh:  python3 update_pricing.py
Import and call maybe_update(force=False) for the throttled path.
"""
import json, os, re, urllib.request, datetime

PRICES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prices.json")
SOURCE_URL = "https://platform.claude.com/docs/en/about-claude/pricing.md"
THROTTLE_HOURS = 24

# header keyword (lowercased substring) -> our field. cw_1h is known-but-not-costed.
COLUMN_MAP = [
    ("base input", "in"), ("5m cache", "cw"), ("1h cache", "cw_1h"),
    ("cache hits", "cr"), ("cache read", "cr"), ("output", "out"),
]
COST_FIELDS = ("in", "out", "cw", "cr")
CORE_IDS = {"claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"}
MONTHS = {m: i for i, m in enumerate(
    ["january","february","march","april","may","june","july",
     "august","september","october","november","december"], 1)}


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")


def _price(cell):
    m = re.search(r"\$\s*([0-9]+(?:\.[0-9]+)?)", cell)
    return float(m.group(1)) if m else None


def _clean_id(display):
    s = re.sub(r"\[[^\]]*\]\([^)]*\)", "", display)   # drop markdown links
    s = re.sub(r"\([^)]*\)", "", s)                    # drop parentheticals
    s = re.split(r"\b(through|starting)\b", s)[0]       # drop date phrases
    s = s.replace("Claude", "").strip().lower()
    s = re.sub(r"[.\s]+", "-", s).strip("-")
    return "claude-" + s if s else None


def _future_effective(display):
    m = re.search(r"starting\s+([A-Za-z]+)\s+(\d+),?\s+(\d+)", display)
    if not m: return None
    mon = MONTHS.get(m.group(1).lower())
    if not mon: return None
    return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(2)):02d}"


def _parse_table(md):
    """Return (rows, unknown_columns). rows = list of (id, is_future, effective|None, rates)."""
    lines = md.splitlines()
    hdr_idx = None
    for i, l in enumerate(lines):
        low = l.lower()
        if l.lstrip().startswith("|") and "cache" in low and "output" in low and "input" in low:
            hdr_idx = i; break
    if hdr_idx is None:
        raise ValueError("model-pricing table header not found")
    headers = [c.strip() for c in lines[hdr_idx].strip().strip("|").split("|")]
    col_field, unknown = {}, []
    for j, h in enumerate(headers):
        hl = h.lower()
        if hl == "model" or j == 0:
            col_field[j] = "model"; continue
        field = next((f for kw, f in COLUMN_MAP if kw in hl), None)
        if field: col_field[j] = field
        else: unknown.append(h)
    rows = []
    for l in lines[hdr_idx + 2:]:
        if not l.lstrip().startswith("|"): break
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if len(cells) < len(headers): continue
        display = cells[0]
        mid = _clean_id(display)
        if not mid: continue
        rates = {}
        for j, f in col_field.items():
            if f == "model": continue
            v = _price(cells[j])
            if v is not None: rates[f] = v
        if "in" not in rates or "out" not in rates: continue
        eff = _future_effective(display)
        rows.append((mid, eff is not None, eff, rates))
    return rows, unknown


def _sanity(rows):
    ids = {r[0] for r in rows}
    if len(ids) < 5: return "parsed fewer than 5 models"
    missing = CORE_IDS - ids
    if missing: return f"core models missing: {', '.join(sorted(missing))}"
    for mid, _, _, rates in rows:
        for f in COST_FIELDS:
            if f in rates and not (0 < rates[f] < 1000):
                return f"{mid}.{f} out of range: {rates.get(f)}"
    return None


def _load():
    with open(PRICES_PATH) as f:
        return json.load(f)


def _save(doc):
    with open(PRICES_PATH, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")


def maybe_update(force=False, today=None):
    """Throttled refresh. Returns a summary dict the report relays to the user."""
    doc = _load()
    meta = doc.setdefault("_meta", {})
    today = today or datetime.date.today().isoformat()
    now = datetime.datetime.now()
    last = meta.get("last_checked")
    if not force and last:
        try:
            age_h = (now - datetime.datetime.fromisoformat(last)).total_seconds() / 3600
            if age_h < THROTTLE_HOURS:
                return {"checked": False, "reason": f"prices checked {age_h:.0f}h ago (<{THROTTLE_HOURS}h)"}
        except ValueError:
            pass
    try:
        rows, unknown = _parse_table(_fetch(SOURCE_URL))
    except Exception as e:
        return {"checked": False, "error": f"fetch/parse failed ({type(e).__name__}: {e}); "
                "prices.json untouched — agent-repair tier needed"}
    err = _sanity(rows)
    if err:
        return {"checked": False, "error": f"sanity check failed: {err}; prices.json untouched — "
                "agent-repair tier needed"}

    models = doc["models"]
    added, changed = [], []
    # group parsed rows by id: one current + optional future records
    by_id = {}
    for mid, is_future, eff, rates in rows:
        by_id.setdefault(mid, {"current": None, "future": []})
        if is_future: by_id[mid]["future"].append((eff, rates))
        else: by_id[mid]["current"] = rates

    for mid, info in by_id.items():
        recs = models.get(mid)
        cur = info["current"]
        if recs is None:
            first = dict(effective=today, **(cur or {}))
            models[mid] = [first] + [dict(effective=e, **r) for e, r in sorted(info["future"])]
            added.append((mid, cur or {}))
            recs = models[mid]
        elif cur is not None:
            in_effect = None
            for r in sorted(recs, key=lambda r: r["effective"]):
                if r["effective"] <= today: in_effect = r
            if in_effect is None or any(round(in_effect.get(f, -1), 4) != round(cur.get(f, -2), 4)
                                        for f in COST_FIELDS if f in cur):
                recs.append(dict(effective=today, **cur))
                changed.append((mid, cur))
        # future records straight from the page
        for e, r in info["future"]:
            if not any(x["effective"] == e for x in recs):
                recs.append(dict(effective=e, **r))
                changed.append((mid, {"effective": e, **r}))
        recs.sort(key=lambda r: r["effective"])

    meta["last_checked"] = now.isoformat(timespec="seconds")
    meta["source"] = SOURCE_URL
    _save(doc)
    return {"checked": True, "added": added, "changed": changed,
            "new_columns": unknown, "models_seen": sorted(by_id)}


def _fmt(s):
    if s.get("error"): return "PRICING UPDATE: " + s["error"]
    if not s.get("checked"): return "PRICING UPDATE: skipped — " + s.get("reason", "")
    parts = ["PRICING UPDATE: refreshed from source."]
    if s["added"]:
        parts.append("NEW MODELS synced (escalate — decide if any need special handling): "
                     + ", ".join(f"{m} (in ${r.get('in','?')}/out ${r.get('out','?')})" for m, r in s["added"]))
    if s["changed"]:
        parts.append("RATE CHANGES applied: " + ", ".join(m for m, _ in s["changed"]))
    if s["new_columns"]:
        parts.append("NEW RATE COLUMNS on the page not tracked here (escalate): "
                     + ", ".join(s["new_columns"]))
    if not (s["added"] or s["changed"] or s["new_columns"]):
        parts.append("No changes — prices.json already current.")
    return "\n".join(parts)


if __name__ == "__main__":
    print(_fmt(maybe_update(force=True)))

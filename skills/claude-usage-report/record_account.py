#!/usr/bin/env python3
"""Claude Code SessionStart hook — stamp the active account onto a sidecar log.

Transcripts don't record which Claude account produced them, so usage reports
can't tell accounts apart. This hook fires on session startup/resume/clear/compact,
reads the currently logged-in account from ~/.claude.json, and appends one line to
~/.claude/session-accounts.jsonl keyed by session_id. The report joins on that.

Prospective only: it tags sessions from install-time forward; it cannot label
history. Always exits 0 and swallows every error — a hook must never break a session.
"""
import sys, os, json, datetime

def main():
    try:
        raw = sys.stdin.read()
        ev = json.loads(raw) if raw.strip() else {}
    except Exception:
        ev = {}
    sid = ev.get("session_id")
    if not sid:
        return
    acct = {"account": None, "org": None, "account_uuid": None}
    try:
        d = json.load(open(os.path.expanduser("~/.claude.json")))
        oa = d.get("oauthAccount") or {}
        acct = {"account": oa.get("emailAddress"),
                "org": oa.get("organizationName"),
                "account_uuid": oa.get("accountUuid")}
    except Exception:
        pass
    rec = {"session_id": sid, "source": ev.get("source"), "cwd": ev.get("cwd"),
           **acct, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    try:
        with open(os.path.expanduser("~/.claude/session-accounts.jsonl"), "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass

if __name__ == "__main__":
    main()

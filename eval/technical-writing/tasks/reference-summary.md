---
id: reference-summary
gear: 4
brief: >
  Write the reference entry for this service in our architecture index. Another agent
  will read it to answer questions without reading the code.
terms:
  - ["dedupe table", "dedupe log", "sent log"]
forbidden:
  - pattern: "(?i)\\b(plays a (key|vital|central) role|is a critical component|serves as the backbone)\\b"
    why: prose padding in a lookup artifact
must_hedge:
  - claim: ownership_unknown
    presence: ["owner", "Platform", "Growth", "catalog", "team"]
    markers: ["unknown", "unclear", "not documented", "no owner", "unowned", "TBD",
              "unassigned", "disputed", "contested", "never accepted"]
    why: the input says ownership is disputed and undocumented
required:
  - pattern: "(?i)^#*\\s*sources?\\b"
    why: gear 4 requires a Sources field so the entry can be re-checked against the code
  - pattern: "(?i)(invariant|must always|guarantee)"
    why: the input contains an invariant, which is the highest-value field for an agent
---

## Input

Whatever anyone could remember about the service, collected in a thread:

```
NotificationDispatcher. Lives in services/notify/. Entry point is
Dispatcher.RunAsync in Dispatcher.cs.

It reads off the notifications topic and fans out to email (SendGrid), push (FCM),
and SMS (Twilio). Config for which channels are on per-tenant is in
NotifyOptions.cs, loaded from app config.

Depends on: IdentityService (to resolve a user id to contact details), TenantConfig
(channel toggles), and the three vendor SDKs.

Important thing nobody wrote down: it must never send the same notification twice
for the same (notification_id, channel) pair. There's a dedupe table,
notify_sent_log, and the whole design assumes that constraint holds. If you add a
channel you have to add it to the dedupe key or you get duplicate sends.

Failure modes: SendGrid 429s a lot, there's a backoff. FCM token expiry produces a
permanent failure that gets logged and dropped, deliberately. Twilio failures retry
3x then dead-letter to notify_dlq.

Who owns it: honestly unclear. It was the Platform team, then it moved to Growth
during the reorg, but Growth says they never accepted it. Nobody has updated the
service catalog.

Open question: nobody knows if the dedupe table is ever pruned. It's 400M rows.
```

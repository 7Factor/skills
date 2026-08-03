---
id: incident-reply
gear: 2
brief: >
  Write the customer-facing status update for this incident, for posting on our public
  status page. Use only what the internal notes support.
terms:
  # "ingest" is excluded deliberately: it appears inside the forbidden internal
  # hostname, so counting it here would double-charge the same mistake.
  - ["outage", "incident", "disruption"]
  - ["customer", "client", "user"]
forbidden:
  - pattern: "(?i)\\bkafka-ingest-3\\b"
    why: internal hostname, not for a public status page
  - pattern: "(?i)\\bLegacyBlobShim\\b"
    why: internal class name, not for a public status page
  - pattern: "(?i)root cause (is|was)\\b"
    why: states an unconfirmed cause as established fact
  - pattern: "(?i)(this week|by (monday|tuesday|wednesday|thursday|friday)|within \\d+ (hours|days)|by end of)"
    why: invents a delivery commitment the notes do not contain
  - pattern: "(?i)(no data (was )?lost|nothing was lost|all data (is|was) (safe|intact))"
    why: notes say the 41 records are still unaccounted for
  - pattern: "(?i)(we (deeply )?apologi[sz]e for the inconvenience|we sincerely apologi[sz]e)"
    why: boilerplate the notes do not ask for and gear 2 cuts as filler
must_hedge:
  # absent_ok on both: for a public status page, saying nothing about an unconfirmed
  # cause or about records the notes forbid calling lost is defensible restraint.
  # The failure being measured is raising the claim and stating it confidently.
  - claim: cause
    presence: ["cause", "reason", "shim", "retry", "offset", "trigger"]
    markers: ["likely", "appears", "suspect", "not confirmed", "unconfirmed", "possible",
              "may", "believe", "preliminary", "investigat", "determin", "identif",
              "not yet", "continue", "continuing"]
    absent_ok: true
    why: the notes mark the cause as unconfirmed
  - claim: missing_records
    presence: ["41", "unaccounted", "data loss", "lost", "missing"]
    markers: ["unaccounted", "still", "not yet", "investigat", "unresolved",
              "outstanding", "reconcil", "review"]
    absent_ok: true
    why: the 41 records are unresolved, not recovered
---

## Input

Internal incident notes, verbatim from the on-call channel:

```
2026-07-29 14:02 — alerts firing on upload failures, ~8% of POST /v2/upload returning 500
2026-07-29 14:20 — kafka-ingest-3 is the only broker showing the errors. Restarted it.
                   error rate drops to ~1% but doesn't clear.
2026-07-29 15:10 — sam thinks it's the LegacyBlobShim retry path double-acking and
                   dropping the offset. NOT CONFIRMED. we don't have the trace data to
                   prove it, the sampling was at 1% during the window.
2026-07-29 15:45 — rolled back to build 4471. error rate at 0% since 15:38.
2026-07-29 16:30 — reconciliation finds 41 upload records that we can't match to a
                   stored blob. could be the same bug, could be a reconciliation
                   artifact. still digging. do NOT tell anyone these are lost yet.
2026-07-30 09:15 — priya: we should fix the shim retry path but nobody has scoped it.
                   not on this sprint. no date.
2026-07-30 09:40 — 41 records still unaccounted for. reconciliation job rerun didn't
                   change the number.
```

Customers affected: uploads failing intermittently for roughly 100 minutes.

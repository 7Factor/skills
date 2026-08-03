# Known issues / backlog

## Day-bucketing uses UTC, not local timezone — undercounts late-evening sessions

`usage_report.py`'s BY DAY (and single-day-argument) logic buckets each message by the
UTC date of its timestamp. For a user in a negative-UTC-offset timezone (e.g. CDT,
UTC-5), any session that runs past ~7pm local time rolls into the *next* UTC calendar
date. The report then splits that one real evening session across two "day" buckets —
and if you query a single day (e.g. `usage_report.py 2026-07-20`), you only see the
pre-midnight-UTC half, silently undercounting that day's actual spend.

**Reproduced 2026-07-21**: querying `2026-07-20` alone showed session `b8c257de` (a CE-31
Jira/instrumentation review) at $3.27. Widening the query to `2026-07-20..2026-07-21`
showed the same session — which ran 22:09 UTC 07-20 through 02:20 UTC 07-21, i.e.
5:09pm–9:20pm CDT, entirely within local 07-20 — actually cost $9.08. Same story for
session `6cc3db71` ($0.44 vs. $1.70 full). Together that's ~$7 of same-local-day spend
that a single-day query hid.

**Fix**: bucket by local date instead of UTC. Simplest approach — accept a
`--tz`/config-driven UTC offset (or read the system local timezone) and convert each
message timestamp to local time before taking its date for BY DAY / single-day-argument
filtering. Also consider: the account-attribution and BY SESSION timestamp columns are
UTC-labeled and unambiguous as-is, so those probably don't need to change — only the
date-bucketing/filtering logic does.

## BY DAY table isn't ordered by date

`BY DAY` (and the report skeleton's "By day" table) currently prints in whatever order
the day-cost dict iterates, not chronologically. Sort ascending (or descending, pick one
and document it) by date before printing/writing the table.

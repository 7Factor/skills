---
id: runbook
gear: 3
brief: >
  Turn these notes into the runbook step for rotating the signing key. The reader is
  on-call at 3am and has not done this before.
terms:
  - ["verify set", "verify_kids", "verification list"]
  - ["revoke", "invalidate"]
forbidden:
  - pattern: "(?i)^\\s*\\d+\\..*\\bif (the|there|you)\\b.*,"
    why: condition placed after the action instead of before it
  - pattern: "(?i)\\b(simply|just|merely) (run|execute|click|do)\\b"
    why: minimizes a step that has a destructive failure mode
must_hedge: []
required:
  - pattern: "(?i)(do not|must not|never|before)"
    why: there is an ordering constraint whose violation logs out every user
  - pattern: "(?i)(rollback|roll back|revert|restore)"
    why: the notes contain a recovery path and a 3am reader needs it
---

## Input

Notes from the engineer who did it last time:

```
you get the new key from vault, path is secret/auth/signing, field is next_key.
it's already generated, the cron makes it monthly.

then you set it as the active key via the admin API, PUT /admin/keys/active with
the kid. THE OLD KEY HAS TO STAY IN THE VERIFY SET or every live session breaks —
there's a separate list, verify_kids, and the old kid must be in it for at least
24h because that's the token TTL. if you revoke the old kid immediately you log
out every user, which is what happened in April.

after 24h you remove the old kid from verify_kids.

if the PUT fails halfway you can end up with active_kid set but verify_kids not
updated. symptom is 401s on everything. fix is PUT the old kid back as active,
then retry.

the health endpoint /admin/keys/health shows both lists, check it after every step.
```

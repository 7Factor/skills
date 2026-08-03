---
id: pr-description
gear: 2
brief: >
  Write the pull request description for this change.
terms:
  - ["timeout", "deadline"]
forbidden:
  - pattern: "(?i)\\b(significantly|dramatically|greatly|massively) (improv|reduc|enhanc|boost)"
    why: unquantified intensifier where a number exists in the input
  - pattern: "(?i)\\b(robust|seamless|comprehensive|elegant|clean) (solution|implementation|approach|fix)\\b"
    why: marketing register
  - pattern: "(?i)this (PR|change) (introduces|brings) (a|an) (new|improved)\\b"
    why: filler opener
must_hedge:
  - claim: unverified_gain
    presence: ["40", "1.1", "p99", "faster", "improvement", "benchmark", "latency"]
    markers: ["local", "not measured", "unverified", "staging", "expect", "should",
              "have not", "no production", "laptop", "only", "unconfirmed"]
    why: the 40% figure came from a local benchmark and has not been measured in production
required:
  - pattern: "(?i)(migration|deploy|order|before|first|drain)"
    why: the change has a deploy-ordering hazard that a reviewer must be told about
---

## Input

What changed, from the author's own notes:

```
- swapped the per-request psycopg connection for a shared pool (pool size 20)
- added statement_timeout=5s, previously unbounded
- deleted the retry wrapper in db/legacy.py, the pool handles it now
- local benchmark: p99 on /reports went 1.9s -> 1.1s (about 40% better).
  I have NOT measured this in staging or prod. Just my laptop, 200 iterations.
- CAREFUL: the pool reads DB_POOL_SIZE from env. If you deploy this before the
  config change lands in the terraform repo, it defaults to 5 and reports will
  queue. The terraform PR is separate and has to go first.
- statement_timeout will now kill two known-slow admin queries that used to
  finish in ~8s. Those will start erroring. I think that's correct behavior but
  someone from the admin team should confirm.
```

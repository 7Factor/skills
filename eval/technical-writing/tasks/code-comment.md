---
id: code-comment
gear: 3
brief: >
  Write the doc comment for this function. The reader is an engineer who has to call it
  correctly and has not read its body.
terms:
  - ["stale entries", "orphaned entries", "dangling entries"]
  - ["entry", "record", "item"]
forbidden:
  - pattern: "(?i)\\b(utili[sz]e|leverage|facilitate|orchestrat)"
    why: abstract verb where a concrete one exists
  - pattern: "(?i)\\b(is|are|be) (performed|executed|carried out|utili[sz]ed)\\b"
    why: passive voice with no actor
  - pattern: "(?i)\\bthis (function|method) (is responsible for|serves to|aims to)\\b"
    why: filler opener
must_hedge: []
required:
  - pattern: "(?i)(raise|throw|error|exception|ValueError)"
    why: the function has a failure mode the caller must handle; gear 3 requires naming it
  - pattern: "(?i)(mutat|in place|modifi|changes the|removes from|deletes from)"
    why: the function mutates its argument, which is the one thing a caller must know
---

## Input

```python
def reconcile(cache, redis, *, ttl=None, dry_run=False):
    if ttl is not None and ttl <= 0:
        raise ValueError("ttl must be positive")
    live = set(redis.scan_iter(match="entry:*"))
    stale = [k for k in cache if f"entry:{k}" not in live]
    if dry_run:
        return stale
    for k in stale:
        del cache[k]
    for k in live - {f"entry:{k}" for k in cache}:
        cache[k.removeprefix("entry:")] = redis.get(k)
        if ttl:
            redis.expire(k, ttl)
    return stale
```

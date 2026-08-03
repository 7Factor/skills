---
id: tradeoff
gear: 1
brief: >
  Write up this design discussion for the team so someone joining next week understands
  where the thinking currently stands.
terms:
  - ["gateway", "proxy", "edge"]
forbidden:
  - pattern: "(?i)^#+ *(decision|we (will|have) (decided|chosen))"
    why: flattens a live disagreement into a decision that was never made
  - pattern: "(?i)\\bwe (will|have) (decided|chosen|selected|agreed)\\b"
    why: no decision was reached in the input
  - pattern: "(?i)\\b(the )?recommended (approach|option|path) is\\b"
    why: invents a recommendation neither engineer made
must_hedge:
  - claim: unresolved
    markers: ["unresolved", "disagree", "open", "not decided", "undecided", "no decision", "still", "yet to", "tension", "argument"]
    why: the discussion ended without agreement and that is the main fact
  - claim: cost_unknown
    markers: ["unknown", "unclear", "no numbers", "not measured", "guess", "estimate", "nobody", "not been"]
    why: the latency cost is explicitly unmeasured
required:
  - pattern: "(?i)\\b(mira|dev)\\b"
    why: attributing positions to the people holding them is what makes exploration readable
---

## Input

Notes from a whiteboard session. Nothing was decided.

```
Question: do we put the new billing API behind the existing APIM gateway, or give it
its own ingress?

Mira's position: APIM. We already pay for it, it already does the auth handoff, and
every other service is behind it. Standing up a second ingress means a second set of
WAF rules, a second cert rotation, a second thing that breaks at 3am. She's been burned
by exactly this at a previous job — two ingresses drifted apart over a year and nobody
noticed until an audit.

Dev's position: own ingress. APIM adds a hop we can't tune, and billing is the one
service where p99 actually shows up in a contract. He also points out APIM's policy
language is a pain to test and the billing team can't deploy a policy change without
going through the platform team, which is a two-week queue right now.

Where they agree: the two-week platform queue is the real problem and neither option
fixes it.

Where they got stuck: nobody has measured what the APIM hop actually costs. Dev thinks
it's 15-40ms. Mira thinks it's under 10ms. There is no number. Somebody could measure
it in an afternoon and nobody has.

Also raised and dropped: Kong (nobody wants to operate it), and putting billing behind
APIM but with a bypass route for the one latency-sensitive endpoint. That last one got
a "huh, maybe" from both of them and then the meeting ended.
```

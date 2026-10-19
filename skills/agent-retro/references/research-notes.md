# Research notes

Primary sources and compatibility notes, checked on 2026-10-19. Consult this file when checking external guidance or maintaining the skill.

## Guidance and its limits

These are primary sources from product builders and practitioners. Their workflow advice is not controlled evidence of universal productivity gains.

| Source | Contribution to the skill | Limit or adaptation |
| --- | --- | --- |
| Anthropic, [Claude Code best practices](https://code.claude.com/docs/en/best-practices), living documentation | Give the agent a way to verify results, supply relevant context, keep persistent instructions focused, and distinguish resumable work from unrelated tasks. | Small clear changes can skip planning. Reset thresholds are heuristics. Diagnose the loop and preserve decisions before recommending a new session. Independent review can produce unnecessary findings. |
| Anthropic, [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents), September 29, 2025 | Retrieve relevant context through references; use compaction, notes, or isolated research workers for sustained work. Workers can read extensive material while returning condensed findings to a coordinating agent. | A long context alone does not prove context caused a failure. Summaries may lose information, so preserve locators and verify decisive passages. Parallel work needs a useful division of responsibility. |
| Eric Provencher, OpenAI, [Rethinking skills and prompts](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra), September 11, 2026 | Revisit accumulated instructions, narrow skill triggers, load references conditionally, and define completion and decision boundaries clearly. | Model-specific observations should prompt a local experiment, not a permanent rule for every agent. Preserve necessary authorization boundaries. |
| Matt Pocock, [Skills repository](https://github.com/mattpocock/skills), living practitioner workflow | Reusable workflows can capture clarification, domain language, feedback, and focused implementation. His `retro` examines the agent's environment. | This skill reviews the person's collaboration across sessions. Broad interviewing and test-first preferences become options when the task warrants them. Verify installed skills before suggesting invocation. |
| Addy Osmani, [My LLM coding workflow going into 2026](https://addyosmani.com/blog/ai-coding-workflow/), January 4, 2026 | Favor understandable increments, source context, runtime feedback, review, and continued human understanding. | Detailed upfront specifications and frequent commits are workflow choices. Scale preparation to uncertainty and respect the person's authority over changes. |
| Simon Willison, [Red/green TDD](https://simonwillison.net/guides/agentic-engineering-patterns/red-green-tdd/), living guide | An observed failing test helps establish that the check can detect the behavior being changed. | Appropriate for relevant behavior changes. Other tasks may be better checked through existing tests, inspection, calculations, or source comparisons. |
| Simon Willison, [Interactive explanations](https://simonwillison.net/guides/agentic-engineering-patterns/interactive-explanations/), living guide | A concrete walkthrough or interactive model can help someone understand generated work when an abstract explanation fails. | Recommend the smallest explanation that resolves an observed gap. Learning questions are not evidence of poor prompting. |

## Portability decisions

The package uses only `name` and `description` frontmatter, plain instructions, and relative references from the [Agent Skills specification](https://agentskills.io/specification). It has no executable or connector dependency. The description supports natural-language requests for a retrospective; host-specific invocation controls are unnecessary.

[Claude Code's skills documentation](https://code.claude.com/docs/en/skills#using-skill-frontmatter-outside-claude-code) distinguishes standard fields from Claude Code extensions that can fail in other upload paths. [Claude's upload guide](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills) documents packaging the skill folder as a ZIP. [OpenAI's skills guide](https://learn.chatgpt.com/docs/build-skills) describes the shared skill format and differences between local loading and plugin distribution. The README also provides an instructions-and-transcripts fallback for hosts without native loading.

Format compatibility does not establish history access or prove behavioral reliability. Check actual host capabilities at runtime. Recheck official documentation when product-specific advice changes, and use the evaluation cases when changing this workflow.

[Claude Code's subagent documentation](https://code.claude.com/docs/en/sub-agents) describes separate worker contexts, tool access, and the cost of returning large summaries. Other hosts may expose different capabilities or none. Delegation is an optional reading strategy; targeted retrieval and compact notes remain available without it.

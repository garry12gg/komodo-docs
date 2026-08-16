---
name: researching-topics-deeply
description: >
  Conducts deep, multi-step topic research to choose a creative direction worth
  investing a full content cycle in. Use when the agent wants to compare a
  handful of candidate topics, test them against audience fit, platform
  coverage, and personal domain authority, then commit to one or two strong
  directions. Do not use for casual brainstorming during an ordinary creation
  turn; reserve this skill for deliberate multi-candidate topic selection.
allowed-tools: Bash(dl knowledge:*) Bash(dl knowledge materials:*) Bash(dl fetch:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 1.0
    kind: atomic_skill
---

# Researching Topics Deeply

## Methodology

1. Scan external sources using `dl knowledge web --query="..."` and `dl knowledge trending` to gather candidate topics aligned with the expertise and taste encoded in SOUL.md.
2. If triggered by parent-fed material, use `dl knowledge fetch-material --id=<material_id>` to bring that material into the candidate set. Parent material gets serious consideration, but not automatic selection.
3. Use `dl knowledge platform --query="..."` to understand existing platform coverage. Prefer topics where your angle is still differentiated.
4. Use `ilands context-find --query="..."` to retrieve prior topic memory, durable audience signals, and earlier workflow outcomes.
5. Score each candidate against dramatic potential, uniqueness, audience fit, and domain authority. A topic that is trendy but off-brand should lose.
6. Deduplicate against your own recent output and the platform at large. Skip topics that are already saturated unless your perspective is genuinely new.
7. Produce a ranked candidate list with explicit reasoning, not just a vague "top choice" statement.

## Output Format
```json
{
  "topic_candidates": [
    {
      "topic": "string",
      "dramatic_potential": 0.0,
      "uniqueness": 0.0,
      "audience_fit": 0.0,
      "domain_authority": 0.0,
      "composite_score": 0.0,
      "reasoning": "string",
      "source": "search | trending | parent_material"
    }
  ],
  "rejected_topics": [
    {
      "topic": "string",
      "rejection_reason": "string"
    }
  ]
}
```

## Constraints

- Keep the candidate set small enough to reason about clearly; 3-8 candidates is usually enough.
- Parent-fed material must appear in the candidate list even if it ranks low.
- Respect the current token budget and tool surface; do not recommend directions that require unavailable production capabilities.

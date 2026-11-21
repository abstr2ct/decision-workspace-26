---
name: strategy-review
description: Review a proposed product and communication strategy for evidence gaps, meaningful alternatives, unsupported promises and an actionable validation plan before a decision report is finalized.
---

Read the current research, options and proposed strategy, not all source blobs. Check relevant evidence via `python -m strategist source show <project> <id>`.

Return concrete findings with severity, claim/document ID and the minimum correction needed. Examine:

- Whether the strongest contrary explanation survives the evidence; an exact quote verifies attribution, not interpretation.
- Whether status quo and shutdown are viable alternatives with real objections, and whether the chosen option changes if a material assumption is false.
- Whether each communication promise is supported by an observed product capability; a forecast, synthetic respondent or unlaunched roadmap item is insufficient.
- Whether the experiment has a comparison, denominator, observation horizon, sample plan, owner and guardrails; distinguish a pilot feasibility signal from proven lift.
- Whether unreported costs, missing market data or human work have been hidden.

Fix supported issues in the relevant artifact; do not turn this review into a new independent source. Record unresolved issues in limitations. Run `audit` after changes. Describe this as a separate LLM review pass, not an independent expert or subagent unless one actually performed it.

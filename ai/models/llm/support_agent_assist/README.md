# Support Agent Assist Baseline

This is the first non-LMS model archetype implemented under Enterprise AI Platform.

It is intentionally deterministic. The goal is to establish reusable platform flow for support use cases before adding LLM/RAG dependencies:

```text
feature contract -> model IO contract -> baseline model -> tests
-> model card -> eval report -> artifact manifest -> evidence validation
```

## Scope

- Summarize a support case.
- Classify coarse intent.
- Produce a priority signal.
- Generate a retrieval query.
- Draft a safe response that always requires human review.

## Non-goals

- No direct external reply sending.
- No customer identity resolution.
- No LLM call.
- No vector search call.


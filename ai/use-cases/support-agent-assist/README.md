# Support Agent Assist Use Case

`support-agent-assist` proves that Enterprise AI Platform is reusable outside LMS.

## Problem

Support agents spend time reading long case histories, identifying intent, searching knowledge articles and drafting first replies. Enterprise support cannot let AI send external replies directly without human review and audit.

## Baseline Capability

The first implementation is a deterministic baseline, not an LLM:

- case summary
- coarse intent classification
- priority signal
- retrieval query for knowledge search
- suggested reply draft
- mandatory human review flag

## Future AI Path

```text
deterministic baseline
-> classifier baseline
-> embeddings/RAG knowledge retrieval
-> LLM suggested reply
-> HITL quality workflow
-> monitored/cost-controlled assistant
```

## Done For Baseline

- Feature contract exists.
- Model IO contract exists.
- Model code has unit tests.
- Model card exists.
- Evaluation report exists.
- Artifact manifest verifies source hash.
- Use case remains tenant-scoped and HITL-governed.


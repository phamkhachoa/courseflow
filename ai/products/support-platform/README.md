# Support Platform AI Product Onboarding

Support Platform is the first non-LMS candidate product onboarded to Enterprise AI Platform.

## Product Outcomes

| Outcome | AI modules |
|---|---|
| Faster first response | support agent assist, suggested reply draft |
| Better case routing | intent classification, priority classification |
| Lower SLA breach risk | support SLA risk prediction |
| Safer support automation | human-in-the-loop for external replies |
| Reusable knowledge retrieval | support knowledge vector collection |

## AI Use Cases

| Use case | Status | Notes |
|---|---|---|
| `support-agent-assist` | baseline implementation | deterministic baseline for summary, intent and draft response |
| `support-sla-risk` | proposed | supervised prediction from case lifecycle features |

## Integration Boundaries

- Support system remains owner of cases, comments, SLA state and customer communication.
- AI Platform owns model lifecycle, evidence, evaluation and serving contracts.
- Any externally visible reply must be reviewed by a support agent until governance policy changes.
- Case features must be tenant-scoped and scrubbed of secrets before model use.

## First Slice

Start with a deterministic support-agent-assist baseline:

1. Summarize the case.
2. Classify coarse intent.
3. Generate a safe internal draft.
4. Produce a retrieval query for future RAG.
5. Require human review for any external response.


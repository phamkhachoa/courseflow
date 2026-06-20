# Model Card: Support Agent Assist Baseline V1

## Identity

| Field | Value |
|---|---|
| Model ID | `support-agent-assist-baseline-v1` |
| Algorithm | deterministic rules baseline |
| Use case | `support-agent-assist` |
| Product | `support-platform` |
| Owner | `ai-platform` |
| Status | baseline implemented |

## Intended Use

Assist internal support agents by summarizing a case, classifying coarse intent, producing a priority signal, creating a retrieval query and drafting a safe response for human review.

## Not Intended For

- Sending external replies automatically.
- Replacing support agent judgment.
- Legal, billing adjustment or access revocation decisions.
- Cross-tenant retrieval or case matching.

## Inputs

| Input | Description |
|---|---|
| tenant ID | Tenant boundary |
| case ID | Support case identifier |
| subject | Case subject |
| latest message | Latest customer/support message |
| product area | Optional product routing context |
| priority | Optional declared priority |
| language | Optional language tag |

## Outputs

| Output | Description |
|---|---|
| summary | Short support case summary |
| intent | `billing`, `access`, `technical`, `account` or `general` |
| priority signal | `normal`, `medium` or `high` |
| retrieval query | Query string for future support knowledge retrieval |
| suggested reply | Internal draft requiring human review |
| confidence | Heuristic confidence score |
| reason codes | Transparent reasons for intent/priority/HITL |

## Governance

- `requires_human_review` is always true.
- External reply auto-send is forbidden by model IO contract.
- Tenant ID is required.
- Future LLM/RAG variants must prove prompt redaction, citation quality, cost control and hallucination/safety gates.

## Known Limitations

- Rule-based intent classification only.
- No multilingual semantic understanding.
- No knowledge retrieval yet.
- No LLM generation quality.
- No historical learning from support outcomes.

## Monitoring

Track draft acceptance rate, agent edits, intent correction rate, first response time, resolution time and safety incidents before LLM/RAG promotion.


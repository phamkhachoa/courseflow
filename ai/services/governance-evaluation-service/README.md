# Governance Evaluation Service

Policy-enforced service boundary for AI Platform governance, safety and evaluation gates.

The service answers release and promotion questions for LMS and non-LMS products through the same contract:

- Are required evaluation gates green?
- Is the promotion artifact fresh and maker-checker approved?
- Is rollback evidence present?
- Does the request require human review?
- Are direct identifiers, secrets or external auto-send attempts blocked?

## Routes

| Method | Path | Scope |
| --- | --- | --- |
| `POST` | `/v1/governance-evaluation/assess` | `internal:ai-platform:governance-evaluation:assess` |
| `GET` | `/v1/governance-evaluation/health` | `internal:ai-platform:governance-evaluation:ops` |
| `GET` | `/v1/governance-evaluation/metrics` | `internal:ai-platform:governance-evaluation:ops` |

## Example

```bash
PYTHONPATH=src:../../platform/src python3.11 -m courseflow_governance_evaluation_service \
  --ai-root ../.. \
  --principal-id service:support-platform-governance-evaluation \
  assess \
  --body-json '{"tenantId":"tenant-support","product":"support-platform","useCaseId":"support-agent-assist","promotionId":"support-agent-assist-baseline-approved","riskLevel":"high","asOf":"2026-06-17"}'
```

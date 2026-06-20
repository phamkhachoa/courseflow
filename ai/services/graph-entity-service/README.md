# Graph Entity Service

Policy-enforced runtime service for entity-link evidence derived from
`finance-payment-fraud-baseline-v1`.

The service promotes graph/entity-link behavior into a reusable AI Platform
service boundary for finance graph-risk triage while keeping payment decisions
inside human-reviewed workflows.

## Routes

| Method | Path | Scope |
|---|---|---|
| `POST` | `/v1/graph-entity/analyze` | `internal:ai-platform:graph-entity:analyze` |
| `GET` | `/v1/graph-entity/health` | `internal:ai-platform:graph-entity:ops` |
| `GET` | `/v1/graph-entity/metrics` | `internal:ai-platform:graph-entity:ops` |

## Guardrails

- Product, use-case and tenant grants come from
  `platform/governance/policies/graph-entity-access-policy.yaml`.
- Requests must use pseudonymous hashes; direct account, counterparty, device,
  customer, user, email or phone identifiers are rejected at the service boundary.
- The service returns entity-link evidence and graph review flags only.
- Automated adverse action remains forbidden.
- Payment scoring and payment-hold workflow decisions remain owned by
  `payment-fraud-service`.

## Local Commands

```bash
PYTHONPATH=src:../../platform/src python3.11 -m pytest
PYTHONPATH=src:../../platform/src python3.11 -m ruff check .
PYTHONPATH=src:../../platform/src python3.11 -m courseflow_graph_entity_service manifest
```

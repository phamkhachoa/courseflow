# Routing Policy Service

Policy-enforced runtime service for `operations-routing-policy-simulator-v1`.

The service promotes the deterministic routing policy simulator into a reusable
AI Platform service boundary for Enterprise Operations constrained routing and
offline policy evaluation.

## Routes

| Method | Path | Scope |
|---|---|---|
| `POST` | `/v1/routing-policy/recommend` | `internal:ai-platform:routing-policy:recommend` |
| `GET` | `/v1/routing-policy/health` | `internal:ai-platform:routing-policy:ops` |
| `GET` | `/v1/routing-policy/metrics` | `internal:ai-platform:routing-policy:ops` |

## Guardrails

- Product, use-case and tenant grants come from
  `platform/governance/policies/routing-policy-access-policy.yaml`.
- Direct agent, assignee, customer, learner, email or phone identifiers are
  rejected at the service boundary.
- Constraint violations require human review.
- Online policy activation remains forbidden; this is a simulator and offline
  decision-support boundary.
- Safe exploration budget remains bounded to the simulator contract.

## Local Commands

```bash
PYTHONPATH=src:../../platform/src python3.11 -m pytest
PYTHONPATH=src:../../platform/src python3.11 -m ruff check .
PYTHONPATH=src:../../platform/src python3.11 -m courseflow_routing_policy_service manifest
```

# Causal Uplift Service

Policy-enforced runtime service for `causal-uplift-baseline-v1`.

The service promotes the deterministic treatment/control uplift baseline into a
reusable AI Platform service boundary for LMS intervention effectiveness and
enterprise experimentation review.

## Routes

| Method | Path | Scope |
|---|---|---|
| `POST` | `/v1/causal-uplift/evaluate` | `internal:ai-platform:causal-uplift:evaluate` |
| `GET` | `/v1/causal-uplift/health` | `internal:ai-platform:causal-uplift:ops` |
| `GET` | `/v1/causal-uplift/metrics` | `internal:ai-platform:causal-uplift:ops` |

## Guardrails

- Product, use-case and tenant grants come from
  `platform/governance/policies/causal-uplift-access-policy.yaml`.
- Requests must use aggregate experiment snapshots; direct learner, customer,
  participant, email or phone identifiers are rejected at the service boundary.
- High-impact and guardrail-risk outcomes require human review.
- Automated rollout remains forbidden; the service provides decision-support
  evidence for review, not automatic experiment activation.
- The baseline stays deterministic until a covariate-adjusted uplift estimator
  and experiment registry integration are separately approved.

## Local Commands

```bash
PYTHONPATH=src:../../platform/src python3.11 -m pytest
PYTHONPATH=src:../../platform/src python3.11 -m ruff check .
PYTHONPATH=src:../../platform/src python3.11 -m courseflow_causal_uplift_service manifest
```

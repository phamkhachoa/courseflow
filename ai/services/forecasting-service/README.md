# Forecasting Service

Policy-enforced runtime service for `operations-demand-forecast-baseline-v1`.

The service promotes the deterministic demand forecast baseline into a reusable
AI Platform service boundary for enterprise operations planning and future LMS
cohort capacity planning.

## Routes

| Method | Path | Scope |
|---|---|---|
| `POST` | `/v1/forecasting/demand/score` | `internal:ai-platform:forecasting:score` |
| `GET` | `/v1/forecasting/health` | `internal:ai-platform:forecasting:ops` |
| `GET` | `/v1/forecasting/metrics` | `internal:ai-platform:forecasting:ops` |

## Guardrails

- Product, use-case and tenant grants come from
  `platform/governance/policies/forecasting-access-policy.yaml`.
- Direct employee, customer, learner, student, email or phone identifiers are
  rejected at the service boundary.
- High demand, incident and material capacity-shortfall forecasts require human
  review before staffing or SLA-impacting action.
- Automated capacity changes remain forbidden.

## Local Commands

```bash
PYTHONPATH=src:../../platform/src python3.11 -m pytest
PYTHONPATH=src:../../platform/src python3.11 -m ruff check .
PYTHONPATH=src:../../platform/src python3.11 -m courseflow_forecasting_service manifest
```

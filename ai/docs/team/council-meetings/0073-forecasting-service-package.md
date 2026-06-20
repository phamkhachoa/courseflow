# 0073 - Forecasting Service Package

Date: 2026-06-17
Owner: AI Platform Council

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Create `services/forecasting-service` as the AI Platform service boundary for
bounded demand forecasting and capacity planning.

This promotes `operations-demand-forecast-baseline-v1` from runtime library to
a service-integrated baseline for Enterprise Operations planning and future LMS
cohort capacity planning. Probabilistic forecasting, causal intervention
estimation and live staffing feedback loops remain separate promotion work.

## Accepted Scope

- Serve demand forecasting through `POST /v1/forecasting/demand/score`.
- Enforce product, use-case and tenant grants from
  `platform/governance/policies/forecasting-access-policy.yaml`.
- Grant Enterprise Operations demand forecasting and LMS cohort planning through
  the same platform boundary.
- Reject direct employee, customer, learner, student, email and phone
  identifiers.
- Set `requiresHumanReview=true` for high demand, incident and material
  capacity-shortfall scenarios.
- Keep automated capacity changes forbidden.
- Expose health and tenant-safe score, error, direct-identifier rejection,
  capacity-shortfall and HITL metrics.

## Deliberate Non-Scope

- Probabilistic prediction intervals are not implemented yet.
- Trained time-series models are not promoted yet.
- Causal intervention lift estimation and live staffing feedback loops are not
  production-connected yet.
- Automated staffing or capacity changes remain forbidden.

## Evidence

- Service package: `services/forecasting-service/service.yaml`
- Platform runtime: `platform/src/courseflow_ai_platform/forecasting_service.py`
- Access policy: `platform/governance/policies/forecasting-access-policy.yaml`
- Service tests: `services/forecasting-service/tests/test_service_contract.py`
- Platform tests: `platform/tests/test_forecasting_service.py`
- Quality gate: `platform/evaluation/reports/operations-demand-forecast-v1-eval.yaml`

## Acceptance Criteria

- Forecasting/planning module moves from runtime library to service-integrated
  baseline.
- Enterprise Operations and LMS planning use cases reference the shared platform
  service boundary.
- Direct person/contact identifiers are rejected at the service boundary.
- Capacity-impacting forecasts require human review before staffing or SLA
  action.

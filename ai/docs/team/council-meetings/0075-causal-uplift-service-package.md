# 0075 Causal Uplift Service Package

Date: 2026-06-17

## Participants

| Role | Focus |
| --- | --- |
| SA AI Platform | Shared experimentation service boundary and runtime roadmap |
| SA AI Engineer | Causal uplift runtime adapter, contract tests and metrics |
| PO/BA | LMS intervention and enterprise experimentation acceptance criteria |
| Governance Reviewer | Aggregate-only privacy, HITL rollout review and guardrail stops |

## Decision

Promote `causal-uplift-baseline-v1` from a reusable runtime library to a
service-integrated baseline through `causal-uplift-service`.
The service evaluates aggregate treatment/control uplift snapshots for LMS
intervention effectiveness and AI Platform enterprise experimentation review.

## Scope

| Area | Decision |
| --- | --- |
| Products | `lms-courseflow`, `ai-platform` |
| Use cases | `lms-intervention-effectiveness`, `enterprise-experimentation-uplift` |
| Service route | `POST /v1/causal-uplift/evaluate` |
| Runtime | Deterministic two-proportion uplift baseline |
| Access | Tenant, product, use-case and scope grants from `causal-uplift-access-policy.yaml` |
| Privacy | Aggregate experiment snapshots only; direct participant, learner, customer, user and contact identifiers are rejected |
| Safety | High-impact and guardrail-risk outputs require human review |
| Activation | Automated rollout remains forbidden |

## Non-Scope

- No online experiment allocator.
- No automatic learner, customer or product rollout action.
- No raw user-level event, learner profile or customer profile processing.
- No covariate-adjusted uplift estimator in this slice.

## Evidence

| Artifact | Path |
| --- | --- |
| Service package | `services/causal-uplift-service/service.yaml` |
| Platform runtime | `platform/src/courseflow_ai_platform/causal_uplift_service.py` |
| Access policy | `platform/governance/policies/causal-uplift-access-policy.yaml` |
| Contract tests | `services/causal-uplift-service/tests/test_service_contract.py` |
| Platform tests | `platform/tests/test_causal_uplift_service.py` |
| Feature contract | `contracts/features/causal-experiment-features.v1.yaml` |
| Model IO contract | `contracts/models/causal-uplift-model-io.v1.yaml` |
| Evaluation report | `platform/evaluation/reports/causal-uplift-v1-eval.yaml` |
| Coverage taxonomy | `platform/coverage/business-capability-coverage.yaml` |
| AI capability taxonomy | `platform/coverage/ai-capability-taxonomy.yaml` |

## Acceptance

- The service enforces tenant, product, use-case and scope grants before
  evaluation.
- Direct identity fields are rejected before model execution.
- High-impact and guardrail-risk outputs are surfaced in metrics and kept under
  human review.
- The runtime roadmap no longer counts causal experimentation as a runtime gap.
- Experiment registry integration, randomization audit, sample-ratio checks and
  covariate-adjusted uplift remain separate roadmap items.

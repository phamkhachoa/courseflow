# 0071 - Sequence Risk Service Package

Date: 2026-06-17
Owner: AI Platform Council

## Decision

Create `services/sequence-risk-service` as the AI Platform service boundary for
bounded recurrent sequence-risk scoring.

This promotes `sequence-risk-baseline-v1` from runtime library to
service-integrated baseline for LMS at-risk prediction and knowledge-tracing
workflows while keeping future trainable PyTorch/ONNX sequence models as a
separate promotion path.

## Accepted Scope

- Serve sequence risk scoring through `POST /v1/sequence-risk/score`.
- Enforce product, use-case and tenant grants from
  `platform/governance/policies/sequence-risk-access-policy.yaml`.
- Accept only pseudonymous subject hashes and bounded event sequences.
- Reject direct learner, student, user and email identifiers.
- Set `requiresHumanReview=true` for medium and high risk interventions.
- Expose health and tenant-safe score, error, direct-identifier rejection and
  human-review metrics.

## Deliberate Non-Scope

- Trainable sequence model artifacts are not promoted yet.
- Intervention feedback-loop metrics are not production-connected yet.
- Automated adverse learner actions remain forbidden.

## Evidence

- Service package: `services/sequence-risk-service/service.yaml`
- Platform runtime: `platform/src/courseflow_ai_platform/sequence_risk_service.py`
- Access policy: `platform/governance/policies/sequence-risk-access-policy.yaml`
- Service tests: `services/sequence-risk-service/tests/test_service_contract.py`
- Platform tests: `platform/tests/test_sequence_risk_service.py`
- Quality gate: `platform/evaluation/reports/sequence-risk-baseline-v1-eval.yaml`

## Acceptance Criteria

- Deep-learning sequence module moves from runtime library to service-integrated
  baseline.
- LMS use cases call the shared platform service rather than model code.
- Direct learner identifiers are rejected at the service boundary.
- Medium/high risk scores require human review before intervention.

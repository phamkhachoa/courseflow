# Model Card: Sequence Risk Baseline V1

## Identity

| Field | Value |
|---|---|
| Model ID | `sequence-risk-baseline-v1` |
| Algorithm | deterministic recurrent sequence scorer |
| Use case | `lms-at-risk-prediction` |
| Product | `lms-courseflow` |
| Owner | `ai-platform` |
| Status | runtime library baseline |

## Intended Use

Score learner-course sequences for early at-risk triage. This baseline gives the
AI Platform a tested sequence-model runtime shape before a trainable
PyTorch/ONNX artifact is introduced.

## Not Intended For

- Automated adverse learner decisions.
- Final intervention assignment without human review.
- Cross-tenant sequence comparison.
- Replacing a trained risk model after sufficient governed data exists.
- High-stakes education decisions without product and governance approval.

## Inputs

| Input | Description |
|---|---|
| tenant ID | Tenant boundary for the learner sequence |
| learner principal hash | Pseudonymous learner identifier |
| course ID | Course context |
| feature snapshot timestamp | Feature snapshot boundary |
| sequence events | Ordered engagement, assessment, inactivity and deadline signals |

## Outputs

| Output | Description |
|---|---|
| risk score | Bounded probability-like score |
| risk band | `low`, `medium` or `high` |
| reason codes | Explainable sequence risk reasons |
| recommended actions | Human-reviewed intervention suggestions |
| hidden state | Rounded recurrent state for audit/debug only |

## Runtime Method

The runtime library uses a small fixed-weight recurrent scoring function. It
processes events chronologically, combines event weights, recency, assessment
score and engagement minutes, then maps the final hidden state to a bounded risk
score.

This is a deterministic sequence runtime baseline. It proves the model IO,
evaluation and governance path for deep-learning sequence modules, but it is not
a trained deep-learning model.

## Governance

- Tenant ID and learner principal hash are required.
- Output is advisory only; automated adverse action is forbidden.
- Recommended actions require a product or advisor workflow before execution.
- Future trainable variants must bind to governed DP Gold snapshots and compare
  against this baseline.

## Known Limitations

- Fixed weights are hand-authored.
- No learned embeddings or trainable recurrent/transformer parameters.
- No production service integration yet.
- No feedback-loop learning from intervention outcomes yet.
- Golden dataset is intentionally small and contract-oriented.

## Monitoring

Track risk band distribution, intervention acceptance, false positive review
rate, course completion lift, feature freshness, model age and tenant isolation
before any shadow or active promotion.

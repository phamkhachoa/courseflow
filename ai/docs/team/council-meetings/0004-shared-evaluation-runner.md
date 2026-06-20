# AI Platform Product Council 0004

Date: 2026-06-16

## Topic

Move from static evaluation reports to executable evaluation runners.

## Decision

Enterprise AI Platform must support executable golden-set evaluation. The first implemented runner evaluates `support-agent-assist-baseline-v1` against a support golden dataset.

## Why

Static evaluation reports are useful evidence, but enterprise gates need repeatable execution. A model should be able to prove that its current source artifact still passes the expected baseline quality gate.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Support golden dataset | `platform/evaluation/datasets/support-agent-assist-golden.yaml` |
| Shared evaluation runner | `platform/src/courseflow_ai_platform/evaluation.py` |
| Evaluation tests | `platform/tests/test_evaluation.py` |
| Updated support eval report | `platform/evaluation/reports/support-agent-assist-baseline-v1-eval.yaml` |

## Gate Policy

For support-agent-assist baseline:

- intent accuracy must meet the dataset threshold.
- priority accuracy must meet the dataset threshold.
- every output must require human review.
- retrieval queries must include required expected terms.

## Next Actions

1. Generalize evaluation runner registry for additional model families.
2. Add RAG retrieval eval for support knowledge.
3. Add prompt redaction tests before LLM adapter.
4. Add LMS recommendation offline Recall@K/NDCG runner.


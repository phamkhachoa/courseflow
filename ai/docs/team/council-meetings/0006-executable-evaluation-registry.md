# AI Platform Product Council 0006

Date: 2026-06-16

## Topic

Move evaluation execution from one hard-coded support runner to a reusable platform evaluation registry.

## Decision

Create `platform/evaluation/registry.yaml` and make the CLI run all required evaluations from that registry. Add an executable offline ranking evaluator for the existing LMS item-CF recommendation baseline so both LMS and non-LMS model evidence have runnable quality gates.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Evaluation registry | `platform/evaluation/registry.yaml` |
| Recommendation golden dataset | `platform/evaluation/datasets/recommendation-item-cf-golden.yaml` |
| Shared evaluation runner | `platform/src/courseflow_ai_platform/evaluation.py` |
| Evaluation tests | `platform/tests/test_evaluation.py` |
| Recommendation eval report update | `platform/evaluation/reports/recommendation-item-cf-v1-eval.yaml` |

## Product Impact

| Product | Evaluation now executable |
|---|---|
| LMS CourseFlow | `recommendation-item-cf-v1` Recall@K, NDCG@K and catalog coverage |
| Support Platform | `support-agent-assist-baseline-v1` intent, priority, HITL and retrieval query coverage |

## Engineering Rule

Every model promoted beyond proposal must have a registry row with runner, dataset, report, product, use case and required/pass policy. The CLI must fail if any required evaluation fails.

## Next Actions

1. Add a generic eval-result schema so reports can be generated from runner output.
2. Bind recommender eval to governed `dp` gold snapshots when those snapshots are stable.
3. Add embedding/hybrid retrievers that beat the lexical retrieval baseline.
4. Add prompt redaction and cost gates before LLM adapter implementation.

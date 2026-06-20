# AI Pipelines

`pipelines/` chứa orchestration cho training, evaluation, batch scoring và feature materialization. Đây là nơi nối `dp` datasets, model archetypes và runtime services.

## Structure

```text
pipelines/
  training/          Train model candidates from governed data
  evaluation/        Run offline, safety and regression evals
  batch-scoring/     Generate scores/read models for product consumption
  materialization/   Move dp features into offline/online AI feature stores
```

## First Pipeline Candidates

| Pipeline | Source | Output |
|---|---|---|
| `recommendation_baseline_train` | recsys interactions | item-CF model candidate |
| `course_embedding_index` | course/lesson content | vector collection |
| `learner_risk_baseline_train` | learner activity + gradebook | at-risk candidate |
| `rag_tutor_eval` | golden Q&A set | groundedness/relevance report |
| `auto_grading_eval` | rubric + instructor-graded submissions | agreement report |

## Operating Rule

Pipelines should write evaluation evidence before any model is registered as a candidate.


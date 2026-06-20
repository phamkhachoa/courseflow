# Council 0057: Causal Experimentation Module

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer

## Decision

Add `causal-experimentation` as an optional extended enterprise module beyond
the required classical-to-RL AI spectrum. The module proves that the AI Platform
can answer intervention and rollout questions, not only prediction or generation
questions.

## Delivered Evidence

| Evidence | Path |
| --- | --- |
| Runtime library | `models/causal/causal_uplift_baseline/causal_uplift_baseline.py` |
| Feature contract | `contracts/features/causal-experiment-features.v1.yaml` |
| Model IO contract | `contracts/models/causal-uplift-model-io.v1.yaml` |
| Golden dataset | `platform/evaluation/datasets/causal-uplift-golden.yaml` |
| Evaluation report | `platform/evaluation/reports/causal-uplift-v1-eval.yaml` |
| Artifact manifest | `platform/artifacts/manifests/causal-uplift-baseline-v1.yaml` |
| Model card | `platform/model-registry/model-cards/causal-uplift-baseline-v1.md` |

## Product Fit

| Product | Reuse |
| --- | --- |
| LMS CourseFlow | Measure learning intervention lift before rollout |
| Enterprise Commerce | Review personalization or ranking experiments |
| Enterprise Operations | Stop routing/capacity policy experiments when guardrails regress |
| AI Platform | Provide one reusable uplift and guardrail review gate |

## Guardrails

- Aggregate assignment/outcome snapshots are required; raw user IDs are not
  allowed in the feature contract.
- High-impact learner or customer decisions require human review.
- Guardrail regression returns a stop/redesign recommendation.
- Online activation still requires shadow review and governed experiment
  assignment evidence.

## Current State

The AI Platform now catalogs 14 AI modules: 8 required spectrum modules and 6
extended enterprise modules. `causal-experimentation` is an executable
runtime-library baseline, not yet a hosted experimentation service.

## Next Step

Host the causal uplift runtime behind the model-serving facade and connect it to
a governed experiment assignment snapshot source.

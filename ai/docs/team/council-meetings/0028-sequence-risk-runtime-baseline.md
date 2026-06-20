# 0028 Sequence Risk Runtime Baseline

Date: 2026-06-17

## Decision

Promote `deep-learning-sequence-models` from registry-only roadmap coverage to
an executable runtime-library baseline through `sequence-risk-baseline-v1`.

## Why

The AI Platform must cover the full requested spectrum honestly: classical ML,
deep learning, NLP/transformers, GenAI/LLM, RAG, CV, speech and RL. Deep
learning needed more than taxonomy coverage, so the team added a tested
sequence-risk runtime shape for LMS at-risk prediction.

## Evidence

| Artifact | Path |
| --- | --- |
| Runtime library | `models/deep_learning/sequence_risk_baseline/sequence_risk_baseline.py` |
| Model IO contract | `contracts/models/sequence-risk-model-io.v1.yaml` |
| Golden dataset | `platform/evaluation/datasets/sequence-risk-baseline-golden.yaml` |
| Evaluation report | `platform/evaluation/reports/sequence-risk-baseline-v1-eval.yaml` |
| Model card | `platform/model-registry/model-cards/sequence-risk-baseline-v1.md` |
| Artifact manifest | `platform/artifacts/manifests/sequence-risk-baseline-v1.yaml` |

## Current Baseline

| Scope | Value |
| --- | --- |
| Model ID | `sequence-risk-baseline-v1` |
| Product | `lms-courseflow` |
| Use case | `lms-at-risk-prediction` |
| Runtime status | `runtime_library` |
| Coverage status | `executable_gate` |
| Required eval status | passed |

## Guardrail

This is a deterministic recurrent scoring baseline, not a trained PyTorch or
ONNX model. It proves the model IO, evaluation, governance and artifact path so
future trainable sequence models have a measurable baseline to beat.

## Product Impact

| Role | Outcome |
| --- | --- |
| PO/BA | Can move LMS at-risk prediction into solution design with explicit KPIs |
| SA AI Platform | Can distinguish runtime library readiness from hosted serving readiness |
| SA AI Engineer | Has a tested sequence-model contract gate before trainable DL |
| Governance Reviewer | Keeps learner-risk output advisory and human-reviewed |

## Next Moves

1. Bind the baseline to governed DP Gold learner activity snapshots.
2. Add a trainable sequence model artifact and compare it against this baseline.
3. Host or service-integrate the runtime library only after serving SLA and
   human-review workflow are accepted.

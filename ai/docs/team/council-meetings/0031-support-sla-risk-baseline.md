# 0031 Support SLA Risk Baseline

Date: 2026-06-17

## Decision

Add `support-sla-risk-baseline-v1` as a deterministic classical/tabular runtime
library for the `support-sla-risk` use case.

## Why

The AI Platform must prove it is not only an LMS platform and not only an LLM
assistant platform. Support needs an explainable operational-risk model path
with feature contract, model IO contract, golden evaluation, model card,
artifact manifest and solution-blueprint readiness.

## Evidence

| Artifact | Path |
| --- | --- |
| Runtime library | `models/classical/support_sla_risk_baseline/support_sla_risk_baseline.py` |
| Model IO contract | `contracts/models/support-sla-risk-model-io.v1.yaml` |
| Golden dataset | `platform/evaluation/datasets/support-sla-risk-golden.yaml` |
| Evaluation report | `platform/evaluation/reports/support-sla-risk-v1-eval.yaml` |
| Model card | `platform/model-registry/model-cards/support-sla-risk-baseline-v1.md` |
| Artifact manifest | `platform/artifacts/manifests/support-sla-risk-baseline-v1.yaml` |

## Current Baseline

| Scope | Value |
| --- | --- |
| Model ID | `support-sla-risk-baseline-v1` |
| Product | `support-platform` |
| Use case | `support-sla-risk` |
| Runtime status | `runtime_library` |
| Coverage status | `implemented_baseline` through classical ML coverage |
| Required eval status | passed |
| Solution request | `support-sla-risk-discovery` ready for solution design |

## Guardrail

This is a deterministic explainable baseline, not a trained gradient-boosted or
neural classifier. Its outputs are advisory; supervisor escalation requires
human review, and production promotion still needs governed support-case
snapshots and false-positive monitoring.

## Product Impact

| Role | Outcome |
| --- | --- |
| PO/BA | Can move support SLA risk into solution design with accepted KPIs |
| SA AI Platform | Can show non-LMS classical ML reuse beyond recommendation |
| SA AI Engineer | Has a tested tabular baseline to beat with trained classifiers |
| Governance Reviewer | Keeps escalation advisory and human-reviewed |
| Admin/Ops | Sees one fewer evaluation-strategy blocker in the cockpit |

## Next Moves

1. Publish solution architecture for `support-sla-risk-discovery`.
2. Bind the baseline to governed support-case snapshots.
3. Compare against a trained tabular classifier before shadow workflow
   activation.

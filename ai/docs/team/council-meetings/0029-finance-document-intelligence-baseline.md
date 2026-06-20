# 0029 Finance Document Intelligence Baseline

Date: 2026-06-17

## Decision

Add `finance-document-intelligence-baseline-v1` as a bounded OCR-token runtime
library for the `computer-vision-document-ai` module.

## Why

The AI Platform needs non-LMS proof that document AI can use the same lifecycle
as LMS and support: feature contract, model IO contract, golden evaluation,
model card, artifact manifest and promotion intake. Raw document/image
processing remains privacy-gated, so the baseline operates only on bounded OCR
tokens and forces human review for raw financial PII signals.

## Evidence

| Artifact | Path |
| --- | --- |
| Runtime library | `models/multimodal/document_intelligence_baseline/document_intelligence_baseline.py` |
| Model IO contract | `contracts/models/finance-document-intelligence-model-io.v1.yaml` |
| Golden dataset | `platform/evaluation/datasets/finance-document-intelligence-golden.yaml` |
| Evaluation report | `platform/evaluation/reports/finance-document-intelligence-v1-eval.yaml` |
| Model card | `platform/model-registry/model-cards/finance-document-intelligence-baseline-v1.md` |
| Artifact manifest | `platform/artifacts/manifests/finance-document-intelligence-baseline-v1.yaml` |

## Current Baseline

| Scope | Value |
| --- | --- |
| Model ID | `finance-document-intelligence-baseline-v1` |
| Product | `billing-finance` |
| Use case | `finance-document-intelligence` |
| Runtime status | `runtime_library` |
| Coverage status | `privacy_gated` |
| Required eval status | passed |

## Guardrail

This is not an OCR, layout or computer vision model over raw pixels. It proves
the OCR-token model IO, extraction, evidence and privacy guardrail path while
keeping raw document/image processing blocked until privacy review is complete.

## Product Impact

| Role | Outcome |
| --- | --- |
| PO/BA | Can show a concrete non-LMS finance baseline with measurable extraction gates |
| SA AI Platform | Can keep CV/document runtime maturity separate from raw-media approval |
| SA AI Engineer | Has a deterministic baseline to beat with OCR/layout models later |
| Governance Reviewer | Keeps tax IDs, bank accounts and financial adjustments human-reviewed |

## Next Moves

1. Complete document AI privacy review for raw OCR/layout processing.
2. Bind the baseline to governed finance document snapshots.
3. Add OCR/layout model artifacts only after privacy approval and compare them
   against this baseline.

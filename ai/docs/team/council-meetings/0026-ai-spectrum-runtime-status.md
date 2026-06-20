# 0026 AI Spectrum Runtime Status

Date: 2026-06-17

## Decision

Extend the AI Business Capability Coverage registry with `runtime_status`.
Coverage status answers whether a module is implemented, executable, roadmap,
privacy-gated or simulator-gated. Runtime status answers how real the current
runtime path is.

## Why

The platform covers the requested spectrum from classical ML to deep learning,
NLP/transformers, GenAI/LLM, RAG, CV, speech and RL, plus recommender,
anomaly/fraud/risk, forecasting, graph/knowledge and governance modules.
However, enterprise stakeholders must not confuse registry coverage with full
runtime implementation.

## Runtime Statuses

| Runtime status | Meaning |
| --- | --- |
| `service_integrated` | Runtime path is integrated into an existing service |
| `runtime_library` | Reusable runtime library exists |
| `shadow_artifact` | Artifact and evaluation path exist for shadow use |
| `tooling` | Validator, safety, evaluation or deterministic tooling exists |
| `registry_only` | Module is registered as roadmap or gated without runtime artifact yet |
| `production_ready` | Reserved for modules with production serving evidence |

## Current Runtime Coverage

| Runtime status | Count |
| --- | ---: |
| `service_integrated` | 3 |
| `runtime_library` | 8 |
| `shadow_artifact` | 1 |
| `tooling` | 2 |
| `registry_only` | 0 |
| `production_ready` | 0 |

## Product Impact

| Role | Outcome |
| --- | --- |
| PO/BA | Can present coverage honestly without overclaiming runtime readiness |
| SA AI Platform | Can separate platform roadmap from executable/runtime surface |
| SA AI Engineer | Can prioritize service integration, privacy review and production hardening for runtime gaps |
| Governance Reviewer | Can keep privacy-gated and simulator-gated work from being activated too early |

## Next Moves

1. Host or service-integrate the sequence-risk, finance payment fraud, speech quality and operations demand forecast
   runtime libraries when product serving SLAs are accepted.
2. Complete document AI privacy review before raw document/image processing or shadow promotion.
3. Complete audio privacy review before raw ASR, diarization or speaker processing.
4. Host or service-integrate the operations-routing simulator before any shadow decision policy activation.

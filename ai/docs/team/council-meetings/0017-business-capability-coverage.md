# AI Platform Product Council 0017

Date: 2026-06-16

## Topic

Prove that the AI Platform covers the full enterprise AI spectrum, not only the
current LMS recommendation baseline.

## Decision

Create `platform/coverage/business-capability-coverage.yaml` as the product-facing
coverage contract. The report maps each AI module to model families, LMS use
cases, non-LMS enterprise use cases, evidence artifacts, evaluation gates and a
clear coverage status.

The platform now validates coverage for:

- Classical ML
- Deep learning and sequence models
- NLP and transformers
- GenAI and LLM assistants
- RAG, retrieval and vector search
- Computer vision and document AI
- Speech and audio AI
- RL, bandits and decision optimization
- Recommender systems, anomaly/fraud, forecasting, graph/knowledge and governance

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Coverage registry | `platform/coverage/business-capability-coverage.yaml` |
| Coverage validator | `platform/src/courseflow_ai_platform/coverage_taxonomy.py` |
| Coverage tests | `platform/tests/test_coverage_taxonomy.py` |
| CLI regression test | `platform/tests/test_cli.py` |
| Product/use-case expansion | `products/registry.yaml`, `use-cases/registry.yaml` |
| Capability registry update | `platform/capabilities/registry.yaml` |

## Runtime Guarantees

| Guarantee | Behavior |
|---|---|
| Full spectrum coverage | Required taxonomy areas must exist in the coverage report |
| LMS plus enterprise mapping | Every module must map to at least one LMS and one non-LMS use case |
| Real evidence links | Every referenced artifact path must exist |
| Gate-backed active modules | Implemented/executable modules must reference evaluation gates |
| Honest maturity | Roadmap, privacy-gated and simulator-required modules are explicit |

## Product Impact

| Product | Use |
|---|---|
| AI Platform | Business-friendly coverage report for platform scope and gaps |
| LMS CourseFlow | AI Mentor roadmap now spans recommendation, RAG, DL, CV/speech and RL |
| Support Platform | Agent assist, SLA risk and speech QA share the same coverage model |
| Billing/Finance | Anomaly, fraud, reconciliation and document intelligence are named use cases |
| Enterprise Operations | Forecasting, visual inspection and routing optimization are onboarded |

## Next Actions

1. Add runtime adapters and eval datasets for CV/speech before leaving privacy-gated status.
2. Host or service-integrate the operations-routing simulator before shadow policy activation.
3. Add trainable deep-learning model artifacts for sequence prediction and knowledge tracing.

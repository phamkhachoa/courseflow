# AI Model Archetypes

`models/` là nơi đặt archetype model khi bắt đầu implementation thật. Mỗi model nên có cùng hình dạng để dễ học, dễ test và dễ đưa qua lifecycle platform.

## Standard Model Folder

```text
models/<family>/<model-name>/
  README.md
  contract.yaml
  model_card.md
  train.py
  predict.py
  evaluate.py
  tests/
```

## Families

| Folder | Purpose | LMS examples |
|---|---|---|
| `classical/` | Baseline and explainable ML | item-CF, XGBoost dropout, logistic risk |
| `anomaly_fraud/` | Fraud, anomaly and entity-link risk baselines | payment fraud scoring, access outlier triage |
| `forecasting/` | Time-series forecasting and planning simulation | cohort demand, staffing and capacity forecast |
| `causal/` | Experimentation, uplift and intervention effectiveness | learning nudges, A/B test review, rollout guardrails |
| `embeddings/` | Representation and vector retrieval | course semantic search, cold-start |
| `deep_learning/` | Neural sequence and recommender models | two-tower, SASRec, DKT, SAKT |
| `llm/` | Prompted or fine-tuned GenAI modules | auto-grading, tutor, quiz generation |
| `bandit_rl/` | Policy learning and adaptive decisions | next best learning action |
| `speech/` | Transcript-segment speech/audio baselines | lecture transcript QA, support call quality |
| `multimodal/` | ASR/CV and media AI | video transcript, OCR/proctoring optional |

## Promotion Rule

Do not create runtime API code here. Model code graduates to `services/` only after its feature contract, model IO contract, quality gate and serving SLA are accepted.

## Implemented Baselines

| Model | Product | Purpose |
|---|---|---|
| `llm/support_agent_assist` | support-platform | Deterministic baseline for summary, intent, retrieval query and HITL reply draft |
| `classical/support_sla_risk_baseline` | support-platform | Deterministic classical SLA breach risk baseline with reason codes |
| `anomaly_fraud/payment_fraud_baseline` | billing-finance | Deterministic payment fraud risk baseline with reason codes and entity-link evidence |
| `forecasting/demand_forecast_baseline` | enterprise-operations | Deterministic workload forecasting and capacity planning baseline |
| `causal/causal_uplift_baseline` | ai-platform | Deterministic treatment/control uplift and experiment guardrail baseline |
| `deep_learning/sequence_risk_baseline` | lms-courseflow | Deterministic recurrent sequence-risk runtime baseline for at-risk prediction |
| `multimodal/document_intelligence_baseline` | billing-finance | Deterministic OCR-token document intelligence baseline with privacy guardrail |
| `speech/audio_quality_baseline` | support-platform and lms-courseflow | Deterministic transcript-segment speech quality baseline with privacy guardrail |
| `bandit_rl/routing_policy_simulator` | enterprise-operations | Deterministic constrained routing simulator and offline policy baseline |

# Sequence Risk Baseline

Deterministic recurrent runtime baseline for `lms-at-risk-prediction`.

This module gives the AI Platform a first executable sequence-model shape:

```text
learner sequence events
-> fixed recurrent scorer
-> risk score, risk band, reason codes, recommended actions
```

It is intentionally lightweight and dependency-free. It is not a trained
PyTorch/ONNX model. Its job is to prove the runtime contract, evaluation gate,
model card and artifact manifest path for future deep-learning sequence models.

Evidence:

- Model IO contract: `contracts/models/sequence-risk-model-io.v1.yaml`
- Model card: `platform/model-registry/model-cards/sequence-risk-baseline-v1.md`
- Golden dataset: `platform/evaluation/datasets/sequence-risk-baseline-golden.yaml`
- Eval report: `platform/evaluation/reports/sequence-risk-baseline-v1-eval.yaml`
- Artifact manifest: `platform/artifacts/manifests/sequence-risk-baseline-v1.yaml`

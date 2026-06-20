# Routing Policy Simulator

Deterministic simulator and offline policy baseline for
`operations-routing-optimization`.

This module gives the AI Platform a first executable RL/bandit decisioning
shape:

```text
work item context + queue state
-> constrained policy scoring
-> assigned queue, expected SLA success, baseline lift, exploration budget
```

It is intentionally dependency-free and is not an online RL learner. Its job is
to prove the simulator, offline policy evaluation, safety constraints, model
card and artifact manifest path before any policy is promoted to shadow or
online activation.

Evidence:

- Model IO contract: `contracts/models/operations-routing-policy-model-io.v1.yaml`
- Model card: `platform/model-registry/model-cards/operations-routing-policy-simulator-v1.md`
- Golden dataset: `platform/evaluation/datasets/operations-routing-policy-golden.yaml`
- Eval report: `platform/evaluation/reports/operations-routing-policy-v1-eval.yaml`
- Artifact manifest: `platform/artifacts/manifests/operations-routing-policy-simulator-v1.yaml`

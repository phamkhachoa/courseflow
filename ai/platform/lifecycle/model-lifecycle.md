# Model Lifecycle

All AI modules in `ai/` must use one shared lifecycle so the platform remains learnable and operable.

## Lifecycle Stages

1. Use-case intake
   - Define product problem, user, business KPI and risk.
   - Register the use case in `use-cases/registry.yaml`.

2. Data and feature contract
   - Define source, owner, freshness, PII class, training/serving parity and retention.
   - Store contract under `contracts/features/`.

3. Experiment
   - Build baseline first.
   - Record dataset version, algorithm, hyperparameters and metrics.

4. Train
   - Produce a bounded artifact.
   - Store training run metadata and lineage.

5. Evaluate
   - Compare against baseline.
   - Run product metric, safety metric and regression eval.
   - Write an evaluation report and model card.

6. Register
   - Create model version as `candidate`.
   - Attach metrics, artifact manifest, model card, evaluation report, feature contract and model IO contract.

7. Approve
   - Maker requests activation.
   - Checker approves or rejects.
   - High-risk modules require human-in-the-loop policy review.

8. Activate
   - Promote one active version per model contract.
   - Keep rollback path to last healthy model.

9. Serve
   - Use internal auth scopes.
   - Return bounded output with reason code, confidence and fallback metadata.

10. Monitor
    - Track latency, error, model age, fallback, drift, cost and quality feedback.
    - Trigger retrain or rollback when gates are violated.

## Required Statuses

```text
draft -> candidate -> approved -> active -> deprecated
                    -> rejected
active -> rollback_candidate -> active
```

## Baseline Rule

No advanced model can replace a baseline unless it passes the configured quality gate. For recommendation, `IMPLICIT_ITEM_CF_V1` is the current baseline.

## Evidence Rule

No model can become a platform candidate without:

- artifact manifest under `platform/artifacts/manifests/`
- model card under `platform/model-registry/model-cards/`
- evaluation report under `platform/evaluation/reports/`
- checksum verification for source or binary artifacts
- feature and model IO contract links

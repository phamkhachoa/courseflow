# Audio Quality Baseline

Deterministic transcript-segment runtime baseline for support and LMS speech/audio use cases.

This module does not process raw audio. It accepts bounded transcript segments
that have already crossed the product privacy boundary, then predicts support
intent, quality band, compliance risk, evidence terms and human-review flags.

```text
redacted transcript segments
-> deterministic speech/audio quality baseline
-> intent, quality, compliance risk, review flags
```

Evidence:

- Model IO contract: `contracts/models/speech-quality-model-io.v1.yaml`
- Feature contract: `contracts/features/speech-audio-features.v1.yaml`
- Model card: `platform/model-registry/model-cards/speech-quality-baseline-v1.md`
- Golden dataset: `platform/evaluation/datasets/speech-quality-golden.yaml`
- Eval report: `platform/evaluation/reports/speech-quality-v1-eval.yaml`
- Artifact manifest: `platform/artifacts/manifests/speech-quality-baseline-v1.yaml`

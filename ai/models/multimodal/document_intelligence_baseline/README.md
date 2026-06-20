# Document Intelligence Baseline

Deterministic OCR-token runtime baseline for `finance-document-intelligence`.

This module does not process raw images or PDFs. It accepts bounded OCR tokens
that have already crossed the product privacy boundary, then extracts document
type, basic financial fields, evidence terms and human-review signals.

```text
redacted OCR tokens
-> deterministic document intelligence baseline
-> document type, extracted fields, evidence terms, review flags
```

Evidence:

- Model IO contract: `contracts/models/finance-document-intelligence-model-io.v1.yaml`
- Model card: `platform/model-registry/model-cards/finance-document-intelligence-baseline-v1.md`
- Golden dataset: `platform/evaluation/datasets/finance-document-intelligence-golden.yaml`
- Eval report: `platform/evaluation/reports/finance-document-intelligence-v1-eval.yaml`
- Artifact manifest: `platform/artifacts/manifests/finance-document-intelligence-baseline-v1.yaml`

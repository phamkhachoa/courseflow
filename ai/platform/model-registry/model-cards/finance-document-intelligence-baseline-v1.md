# Model Card: Finance Document Intelligence Baseline V1

## Identity

| Field | Value |
|---|---|
| Model ID | `finance-document-intelligence-baseline-v1` |
| Algorithm | deterministic OCR-token document intelligence |
| Use case | `finance-document-intelligence` |
| Product | `billing-finance` |
| Owner | `ai-platform` |
| Status | runtime library baseline |

## Intended Use

Extract basic document type, invoice/receipt fields, evidence terms and
human-review flags from bounded OCR tokens for finance document triage.

## Not Intended For

- Raw image or PDF OCR without privacy approval.
- Automatic financial adjustments or payments.
- Extracting raw tax IDs, bank accounts or payment credentials.
- Replacing finance reviewer judgment.
- Cross-tenant document matching.

## Inputs

| Input | Description |
|---|---|
| tenant ID | Tenant boundary |
| document ID | Product document identifier |
| document checksum | Immutable source checksum |
| MIME type | PDF or image MIME |
| document language | Language tag |
| vendor hint | Optional governed vendor master signal |
| OCR tokens | Bounded redacted tokens with page and optional bbox |

## Outputs

| Output | Description |
|---|---|
| document type | `invoice`, `receipt` or `unknown` |
| extracted fields | Non-sensitive vendor/document/date/amount/currency fields |
| confidence | Heuristic confidence score |
| reason codes | Transparent extraction, privacy and review signals |
| evidence terms | Token text snippets supporting the extraction |
| human-review flag | Required for raw financial PII or incomplete/low-confidence extraction |

## Runtime Method

The runtime library uses deterministic token heuristics over OCR text. It
classifies invoices and receipts, extracts document numbers, totals, currency
and dates, detects raw financial PII patterns, then routes risky or incomplete
cases to human review.

This is a document-intelligence runtime baseline. It proves the model IO,
evaluation and governance path for document AI, but it is not an OCR, layout or
computer vision model over raw pixels.

## Governance

- Tenant ID and document checksum are required.
- Raw document/image processing remains privacy gated.
- Raw tax IDs, bank accounts and payment credentials are not allowed as output
  fields.
- Financial adjustment human review is required.
- Future OCR/layout variants must bind to governed document snapshots and pass
  privacy review before promotion.

## Known Limitations

- Rule-based field extraction only.
- No OCR, layout understanding or table extraction.
- No vendor disambiguation beyond supplied hints.
- No production service integration yet.
- Golden dataset is small and contract-oriented.

## Monitoring

Track field correction rate, human-review rate, raw-PII detection rate, document
type drift, extraction latency, document checksum coverage and reviewer override
rate before shadow or active promotion.

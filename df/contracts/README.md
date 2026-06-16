# Data Contracts

This folder owns enterprise data platform contracts. Contracts are the API of data. They define the
shape, compatibility policy, product ownership, domain ownership, privacy classification, residency,
consumer contract and quality SLO for events and data products.

Initial contract types:

- `event-envelope.v1.schema.json`: mandatory envelope for events entering the platform.
- `data-product-contract.template.yaml`: template for Bronze, Silver and Gold datasets.

## Rules

- Every ingested event must carry a stable `eventId`, `eventType`, `eventVersion`, `productId`,
  `sourceService`, `occurredAt`, `tenantId` or mapped product organization key, and correlation
  metadata.
- Every topic and data product must declare `product`, `domainOwner`, `dataSteward`,
  `dataResidency`, access personas and consumer contract metadata.
- `product` must match an onboarded product under `products/`; `domain` must be an enterprise data
  domain from `domains/registry.yaml`.
- Breaking schema changes require a new major version.
- Additive compatible changes may use a minor version only when consumers can ignore the new fields.
- PII classification is required before data reaches Silver or Gold.
- PII contracts must declare subject-erasure metadata through `subjectKeys` objects. Topic contracts
  point to payload paths such as `$.payload.learnerIdHash`; data products point to physical columns
  such as `learner_id_hash`.
- Bronze PII datasets with `raw_payload` must tag that column as PII and use
  `rawPayloadPolicy=SECURE_RAW_PAYLOAD_WITH_SUBJECT_ERASURE`.
- Silver and Gold products without raw payloads must use `rawPayloadPolicy=NO_RAW_PAYLOAD`; non-PII
  raw event products must use `rawPayloadPolicy=NON_PERSONAL_RAW_PAYLOAD`.
- Gold data products must declare owner, SLA, quality checks and downstream consumers.

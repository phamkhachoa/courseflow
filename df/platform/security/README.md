# Data Security Platform

Security policies protect person, organization, payment, incentive, assessment, customer and product
data across the analytical estate.

## Required Controls

- Tenant and organization row-level isolation.
- PII classification before Silver/Gold publication.
- Hashing/tokenization for person identifiers used by ML.
- Column masking for self-service BI.
- Data access audit with user/service identity.
- Retention and right-to-erasure workflow.
- Cryptographically verified external evidence attestations for production release gates.

## Evidence Attestation Trust

Production-like release gates accept external evidence only through `external_evidence_attestation.v1`
documents signed by a trusted key. Trusted public keys live in
`platform/security/evidence-trust-keys.yaml` and declare key owner, status, algorithm, validity
window, allowed environments, allowed evidence kinds, allowed producers and allowed subject URI
prefixes.

The current offline verifier supports Ed25519. The signing payload is canonical JSON of the
attestation with the `signature` field omitted. Private keys must live outside this repository,
typically in KMS or a CI/CD signing service; the repository stores only public verification keys.

Operators can verify an attestation before attaching it to release evidence:

```bash
PYTHONPATH=src python -m enterprise_df.cli attestation-verify \
  --root . \
  --input build/evidence/schema-registry.attestation.json \
  --evidence-kind schema_registry \
  --environment prod \
  --release-id prod-ml-feature-001
```

## Local Access Policy Evidence

`enterprise-df access-policy-check` creates a machine-readable `access_policy_check.v1` report from a
data product contract and optional snapshot metadata.

```bash
PYTHONPATH=src python -m enterprise_df.cli access-policy-check \
  --root . \
  --data-product gold.recsys_interactions \
  --output build/evidence/access-policy.json \
  --release-id local-recsys-001
```

The report checks:

- Row-level org isolation requires an `org_id` column.
- PII data products require `tenantIsolation=REQUIRED`.
- PII columns must be tagged.
- Direct identifier columns are blocked from approved Silver/Gold serving contracts.
- Access personas must be known to the platform.
- Consumer contract and access policy must be declared for audit correlation.

Production releases must attach a durable access-policy report URI and hash to the release evidence.

## Local Access Grant Evidence

`enterprise-df access-grant-check` creates a machine-readable `access_grant_evidence.v1` report for
approved grants, maker-checker approvals, expiry, review cadence and runtime allow/deny decisions.

```bash
PYTHONPATH=src python -m enterprise_df.cli access-grant-check \
  --root . \
  --data-product gold.recsys_interactions \
  --output build/evidence/access-grant.json \
  --release-id local-recsys-001
```

The report checks:

- Required non-platform personas have active grants.
- Grants include catalog request, business purpose, owner approval, steward approval, expiry and review cadence.
- Requester, owner approver and steward approver are separated.
- Grant duration and review cadence stay within the referenced consumer contract controls.
- Runtime audit decisions match expected allow, unauthorized deny and cross-org deny behavior.

## Local Retention And Erasure Evidence

`enterprise-df retention-check` creates a machine-readable `retention_erasure_evidence.v1` report for a
data product snapshot.

```bash
PYTHONPATH=src python -m enterprise_df.cli retention-check \
  --root . \
  --data-product gold.recsys_interactions \
  --output build/evidence/retention.json \
  --release-id local-recsys-001
```

For production-like environments, pass a retention job evidence document:

```bash
PYTHONPATH=src python -m enterprise_df.cli retention-check \
  --root . \
  --data-product gold.recsys_interactions \
  --environment prod \
  --output build/evidence/retention.json \
  --release-id prod-recsys-001 \
  --evidence-input build/evidence/retention-job-evidence.json
```

Without `--evidence-input`, production-like reports fail `production_retention_evidence_input_required`.
Local/dev may still use synthetic evidence for development flow.

The report checks:

- The contract resolves to an active retention policy.
- `retentionDays` is within policy min/max bounds.
- PII erasure support is enabled when policy requires it.
- Subject keys, erasure mode, legal-hold policy and raw-payload policy align with the referenced
  retention policy.
- Expired-record scan, subject-key coverage, erasure replay, residual-subject scan and legal-hold
  evidence are present and passing.

`retention_erasure_job_evidence.v1` inputs must identify the producer, valid generated time, data
product and matching release/snapshot/table/hash metadata. When the report builder knows those
metadata values, the input must match them exactly. Evidence values include `job_run_id`,
`expired_record_count`, `coverage_percent`, `replay_passed`, `residual_match_count` and
`active_legal_hold_count`.

End-to-end release workflows can generate the report from job evidence directly:

```bash
PYTHONPATH=src python -m enterprise_df.cli run-use-case \
  --root . \
  --use-case-id ml-feature-governance \
  --input samples/recommendation/tracking.jsonl \
  --output-dir /tmp/enterprise-df/ml-feature-governance-prod \
  --release-id prod-ml-feature-001 \
  --environment prod \
  --retention-evidence-input build/evidence/retention-job-evidence.json
```

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
PYTHONPATH=src python -m enterprise_dp.cli attestation-verify \
  --root . \
  --input build/evidence/schema-registry.attestation.json \
  --evidence-kind schema_registry \
  --environment prod \
  --release-id prod-ml-feature-001
```

## Local Access Policy Evidence

`enterprise-dp access-policy-check` creates a machine-readable `access_policy_check.v1` report from a
data product contract and optional snapshot metadata.

```bash
PYTHONPATH=src python -m enterprise_dp.cli access-policy-check \
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

`enterprise-dp access-grant-check` creates a machine-readable `access_grant_evidence.v1` report for
approved grants, maker-checker approvals, expiry, review cadence and runtime allow/deny decisions.

```bash
PYTHONPATH=src python -m enterprise_dp.cli access-grant-check \
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

## Local Runtime Security Smoke

`enterprise-dp trino-runtime-security-smoke` creates `trino_runtime_security_smoke_report.v1` from
the local Trino/Iceberg/MinIO runtime. It uses Trino file-based access control and explicit Trino CLI
`--user` identities to prove runtime authorization decisions against the governed finance Gold table.

```bash
cd dp
make trino-runtime-security-smoke
```

The report checks:

- Trino is restarted with the local access-control files mounted and hashed in the report.
- `dp_allowed` is bound to the query identity and can `SELECT` the governed Iceberg table.
- `dp_allowed` is still read-only and cannot `INSERT`.
- `dp_denied` cannot `SELECT` the governed table.
- An unknown user is default-denied.
- A security probe table enforces row-level filtering and column masking.
- A local structured audit sink records expected allow/deny/filter/mask decisions.

This is local runtime authorization evidence, not production authentication or centralized policy
operations. Production signoff still requires OIDC/Keycloak or service identity enforcement,
production PDP integration and secret rotation evidence.

## OPA Policy Decision Smoke

`enterprise-dp policy-decision-smoke` creates `policy_decision_smoke_report.v1` from a real local OPA
server. It loads a Rego policy and proves policy decisions that are intentionally separate from
Trino's file-based enforcement smoke.

```bash
cd dp
make policy-decision-smoke
```

The report checks:

- OPA HTTP decision API is reachable.
- Finance Gold select is allowed for a reader role and denied by default for an unauthorized subject.
- The decision response carries row-filter and column-mask directives.
- Policy-admin approval requires maker-checker separation, reason and evidence.
- Self-approval and missing-evidence approval are denied.
- A structured policy-decision audit sink is written.

This proves a local OPA PDP and policy-admin maker-checker path. It is not production OIDC/Keycloak,
HA OPA/Ranger deployment, signed bundle distribution, SIEM export or production secret rotation.

## OIDC Auth Smoke

`enterprise-dp oidc-auth-smoke` creates `oidc_auth_smoke_report.v1` from a local OIDC-compatible
issuer and JWKS. It proves authentication boundary behavior that is intentionally separate from
Trino authorization and OPA policy decisions.

```bash
cd dp
make oidc-auth-smoke
```

The report checks:

- A JWKS RS256 public key is published with a stable `kid`.
- A valid access token is accepted only when issuer, audience, expiry and required role match.
- Missing token, wrong audience, issuer mismatch, expired token, unknown `kid`, tampered signature and
  missing required role are denied.
- A structured authn audit sink is written with token hashes and without raw access tokens or private
  keys.

This proves local OIDC/JWKS validation evidence for the runtime boundary. It is not enterprise
Keycloak realm deployment, IdP group sync, managed IdP HA, JWKS rotation from a managed provider,
SIEM export or production secret rotation.

## Secret Rotation Smoke

`enterprise-dp secret-rotation-smoke` creates `secret_rotation_smoke_report.v1` from a local
encrypted versioned secret store. It proves secret lifecycle behavior and Dagster secret injection
evidence without pretending to be a managed production secret platform.

```bash
cd dp
make secret-rotation-smoke
```

The report checks:

- Four runtime surfaces receive service-identity-scoped secret records.
- Secret versions rotate from v1 to v2.
- Active consumers read v2, old v1 reads are denied after revoke, unauthorized identity reads are
  denied and missing-secret reads fail closed.
- The Dagster orchestration boundary receives a service identity plus secret handle/version/hash, with
  the actual value redacted.
- Audit events include run id, service identity, secret name, version, decision and hash, without
  plaintext secret values.

This proves local secret rotation workflow and orchestrator service-identity injection. It is not
managed secret-manager HA, cloud KMS/HSM custody, workload identity federation, CSI/ESO injection,
automatic rotation scheduling, cross-region replication, SIEM export or production secret rotation
signoff.

## Secret Rotation Operations Report

`enterprise-dp secret-rotation-ops-report` creates `secret_rotation_ops_report.v1` from managed
secret-manager/KMS runtime evidence. This is the production-like gate for secret custody and
rotation; local smoke evidence remains supporting evidence only.

```bash
PYTHONPATH=src python -m enterprise_dp.cli secret-rotation-ops-report \
  --root . \
  --environment prod \
  --evidence build/evidence/managed-secret-rotation-evidence.json \
  --output build/evidence/secret-rotation-ops-prod.json
```

The report checks:

- The attached evidence is `managed_secret_rotation_evidence.v1`, fresh, passed and environment
  matched.
- Every P0 runtime service in `platform/runtime/topology.yaml` has an external secret handle,
  service identity, active version, KMS key id/hash, rotation policy and latest rotation timestamp.
- Managed secret-manager HA, workload identity federation, KMS/HSM custody, rotation policy,
  old-version deny, unauthorized-identity deny, missing-secret deny and redacted orchestrator
  injection are all proven.
- Plaintext secret material is absent from service rows, orchestrator evidence and audit evidence.
- Audit events are exported to a SIEM sink with zero failed events.
- External attestation is attached and signature/subject checks pass.
- Production reports require cross-region replication and backup/restore evidence.

The production review pack removes `production_secret_rotation`,
`production_cloud_kms_key_rotation`, `cloud_kms_or_hsm_key_custody`,
`managed_secret_manager_ha`, `workload_identity_federation_to_cloud`,
`automatic_rotation_scheduler`, `cross_region_secret_replication` and `siem_audit_export` only when
a staging/prod `secret_rotation_ops_report.v1` passes the strict release gate.

## Access Grant Operations Report

`enterprise-dp access-grant-ops-report` creates a registry-wide `access_grant_ops_report.v1` for
support, security and data governance operations.

```bash
PYTHONPATH=src python -m enterprise_dp.cli access-grant-ops-report \
  --root . \
  --output build/evidence/access-grant-ops.json \
  --environment prod \
  --generated-at 2026-06-16T12:00:00Z
```

The report creates a decision board with `page_now`, `review_queue` and `expiring_grants`. P0 issues
fail the report, including expired active grants, missing data products, missing approvals,
maker-checker conflicts, missing required evidence, missing organization scope and PII export
exceptions. P1/P2 issues remain visible for review cadence, overlong grants, redistribution
exceptions and expiry warnings.

## Local Retention And Erasure Evidence

`enterprise-dp retention-check` creates a machine-readable `retention_erasure_evidence.v1` report for a
data product snapshot.

```bash
PYTHONPATH=src python -m enterprise_dp.cli retention-check \
  --root . \
  --data-product gold.recsys_interactions \
  --output build/evidence/retention.json \
  --release-id local-recsys-001
```

For production-like environments, pass a retention job evidence document:

```bash
PYTHONPATH=src python -m enterprise_dp.cli retention-check \
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
PYTHONPATH=src python -m enterprise_dp.cli run-use-case \
  --root . \
  --use-case-id ml-feature-governance \
  --input samples/recommendation/tracking.jsonl \
  --output-dir /tmp/enterprise-dp/ml-feature-governance-prod \
  --release-id prod-ml-feature-001 \
  --environment prod \
  --retention-evidence-input build/evidence/retention-job-evidence.json
```

# Runtime Evidence Contracts

Runtime readiness evidence is machine-readable JSON produced by CI/CD, IaC tooling, SRE checks or
release governance jobs. These artifacts are inputs to `enterprise-df runtime-readiness-check`.

The platform uses evidence artifacts instead of parsing human text logs. OpenTofu/Terraform plan and
state JSON should be normalized into these contracts before production signoff.

## Common Fields

Every evidence artifact must include:

| Field | Meaning |
|---|---|
| `artifact_type` | One of the runtime evidence artifact types below. |
| `schema_version` | Integer contract version, currently `1`. |
| `evidence_id` | Stable id for audit and replay. |
| `environment` | `local`, `staging` or `prod`. Must match the readiness target. |
| `profile_id` | IaC profile from `platform/runtime/iac-modules.yaml`. |
| `evidence_kind` | Machine kind: `iac_plan`, `iac_apply`, `drift_check`, `backup_restore`, `dr_exercise` or `service_health`. |
| `source_kind` | `ci_tool_output`, `external_attestation` or `synthetic_fixture`. Synthetic fixtures cannot pass staging/prod readiness. |
| `status` | Must be `passed` for readiness. Other values are audit evidence but do not pass the gate. |
| `generated_at` | UTC timestamp when the artifact was produced. |
| `valid_until` | UTC expiry time. Expired evidence cannot pass readiness. |
| `issuer` | Object with `tool`, `tool_version` and `ci_run_id`. |
| `git_sha` | Source commit that produced the runtime artifact. |
| `artifact_uri` | Durable storage URI for the original evidence. |
| `artifact_sha256` | Hash of the original artifact. |
| `command` and `exit_code` | Command that produced the evidence and its exit code. Exit code must be `0` for readiness. |
| `redacted` | Must be `true`; evidence must not contain runtime secrets. |

## Artifact Types

| Artifact Type | Required For | Key Payload |
|---|---|---|
| `runtime_iac_plan_evidence.v1` | Staging/prod | `plan.status`, `plan.plan_hash`, `plan.destructive_change_count`, `service_matrix`. |
| `runtime_iac_apply_evidence.v1` | Staging/prod | `apply.status`, `apply.applied_plan_hash`, `apply.state_hash`, `deployed_services`. |
| `runtime_iac_drift_report.v1` | Staging/prod | `drift.status`, `drift.drifted_resource_count`, service coverage. |
| `runtime_backup_evidence.v1` | Staging/prod stateful services | `backups[]` with `service_id`, `status`, `restore_tested`. |
| `runtime_service_health_evidence.v1` | Staging/prod | `checks[]` with `service_id` and `status`. |
| `runtime_dr_evidence.v1` | Production | `exercise.status`, `rto_minutes`, `rpo_minutes`, `covered_services`. |

## Readiness Rules

- Staging can pass when plan/apply/drift/backup/health evidence is valid and covers every required
  P0 runtime service.
- Production requires every staging gate plus DR exercise coverage for every required P0 runtime
  service and no destructive IaC plan changes.
- Local readiness remains developer preflight only and cannot be used for production signoff.
- Skeleton IaC files and environment manifests are topology evidence, not deployment evidence.

## Pack Generator

Use `runtime-evidence-pack` to create a normalized artifact pack and manifest:

```bash
PYTHONPATH=src python -m enterprise_df.cli runtime-evidence-pack \
  --root . \
  --environment staging \
  --source-kind ci_tool_output \
  --git-sha 0123456789abcdef0123456789abcdef01234567 \
  --ci-run-id ci-123 \
  --artifact-base-uri s3://runtime-evidence/staging/ci-123 \
  --output-dir build/runtime/staging-evidence
```

For `prod`, pass `--change-request-id` and include DR evidence. The generator includes DR evidence
by default for `prod`.

When `source_kind` is `synthetic_fixture`, staging/prod packs are written as contract examples but
return a failing CLI status and use `status: blocked`; they are intentionally not production
readiness evidence.

## IaC JSON Normalizer

Use `runtime-evidence-normalize-iac` when CI/CD already produced OpenTofu/Terraform machine JSON:

```bash
tofu plan -out=tfplan
tofu show -json tfplan > build/runtime/tfplan.json
tofu show -json terraform.tfstate > build/runtime/tfstate.json

PYTHONPATH=src python -m enterprise_df.cli runtime-evidence-normalize-iac \
  --root . \
  --environment staging \
  --plan-json build/runtime/tfplan.json \
  --state-json build/runtime/tfstate.json \
  --health-checks build/runtime/health-checks.json \
  --backup-checks build/runtime/backup-checks.json \
  --git-sha 0123456789abcdef0123456789abcdef01234567 \
  --ci-run-id ci-123 \
  --issuer-tool opentofu \
  --issuer-tool-version 1.10.0 \
  --artifact-base-uri s3://runtime-evidence/staging/ci-123 \
  --output-dir build/runtime/staging-evidence
```

The normalizer only copies allowlisted metadata into evidence artifacts: resource addresses,
actions, counts, hashes and service coverage. It must not copy raw state values, planned values,
before/after payloads, outputs or sensitive values.

Resource-to-service mapping comes from `platform/runtime/iac-modules.yaml` by default. Use
`--resource-map` for provider layouts where runtime resources do not live under predictable module
addresses.

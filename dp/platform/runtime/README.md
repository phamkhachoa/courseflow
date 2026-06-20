# Platform Runtime and IaC

`platform/runtime/` is the runtime-as-code boundary for the group enterprise data platform. It
declares the shared control plane, data plane and serving plane services that every enterprise
product should use instead of creating bespoke analytics infrastructure.

The current maturity target for this folder is `L1`: validated as code with topology, environment
bindings and IaC profile metadata. It does not claim that staging or production infrastructure has
been applied yet.

## Files

| Path | Purpose |
|---|---|
| `topology.yaml` | Product-agnostic runtime topology across local, staging and production. |
| `iac-modules.yaml` | IaC profile and module registry for local compose and future OpenTofu/Terraform modules. |
| `local/docker-compose.yaml` | Local developer skeleton for required P0 data plane services. |
| `local-event-backbone-smoke.md` | Optional Redpanda/rpk round-trip smoke before local data-plane execution. |
| `local-data-plane-smoke.md` | CI smoke gate for the first executable source -> Bronze -> Silver/Gold -> query data flow. |
| `iac/staging/main.tf` | Staging OpenTofu/Terraform skeleton. |
| `iac/prod/main.tf` | Production OpenTofu/Terraform skeleton. |
| `evidence/README.md` | Machine-readable runtime evidence contract for plan/apply/drift/backup/DR/health gates. |

## Phase Guardrails

- P0 requires Kafka/outbox/CDC, schema registry, object storage, Iceberg, Spark/dbt, orchestration,
  quality, Trino-compatible SQL and observability.
- Dremio is declared as a conditional P1/P2 semantic lakehouse candidate.
- TiDB + TiFlash is declared as a P3+ operational HTAP option for product-specific needs, not a
  lakehouse foundation.
- Staging and production remain `not_ready` until real IaC plan/apply, secrets, service identity and
  DR evidence are attached.

Generate a runtime readiness report:

```bash
PYTHONPATH=src python -m enterprise_dp.cli runtime-readiness-check \
  --root . \
  --environment local \
  --output build/runtime/local-readiness.json
```

Run the executable local data-plane smoke:

```bash
make data-plane-smoke
```

Run the optional live event-backbone smoke when Docker is available:

```bash
make event-backbone-smoke
make production-review-pack EVENT_BACKBONE_SMOKE_REPORT=build/event-backbone-smoke/event-backbone-smoke-report.json
```

Production-like readiness must include evidence artifacts:

```bash
PYTHONPATH=src python -m enterprise_dp.cli runtime-readiness-check \
  --root . \
  --environment staging \
  --iac-plan build/runtime/staging-plan.json \
  --iac-apply build/runtime/staging-apply.json \
  --drift-report build/runtime/staging-drift.json \
  --backup-report build/runtime/staging-backup.json \
  --health-report build/runtime/staging-health.json \
  --output build/runtime/staging-readiness.json
```

Production adds `--dr-report` and must have no destructive IaC plan changes.

Attach production-like runtime evidence to the partner review pack:

```bash
PYTHONPATH=src python -m enterprise_dp.cli production-review-pack \
  --root . \
  --environment staging \
  --output-dir build/production-review-pack \
  --runtime-readiness-report build/runtime/staging-readiness.json
```

The review pack can also build the readiness report from raw evidence paths:

```bash
PYTHONPATH=src python -m enterprise_dp.cli production-review-pack \
  --root . \
  --environment prod \
  --output-dir build/production-review-pack \
  --runtime-iac-plan build/runtime/prod-plan.json \
  --runtime-iac-apply build/runtime/prod-apply.json \
  --runtime-drift-report build/runtime/prod-drift.json \
  --runtime-backup-report build/runtime/prod-backup.json \
  --runtime-health-report build/runtime/prod-health.json \
  --runtime-dr-report build/runtime/prod-dr.json
```

`platform-runtime-iac` is removed from the production-review backlog only for staging/prod
`production_like_ready` evidence with full P0 service coverage, clean drift, passing backup/health
checks and production DR evidence. Local or synthetic evidence remains review-only.

Create a normalized evidence pack:

```bash
PYTHONPATH=src python -m enterprise_dp.cli runtime-evidence-pack \
  --root . \
  --environment staging \
  --source-kind ci_tool_output \
  --git-sha 0123456789abcdef0123456789abcdef01234567 \
  --ci-run-id ci-123 \
  --artifact-base-uri s3://runtime-evidence/staging/ci-123 \
  --output-dir build/runtime/staging-evidence
```

`synthetic_fixture` packs are useful for contract review only. They cannot pass staging or production
readiness gates.

Normalize OpenTofu/Terraform machine JSON:

```bash
PYTHONPATH=src python -m enterprise_dp.cli runtime-evidence-normalize-iac \
  --root . \
  --environment staging \
  --plan-json build/runtime/tfplan.json \
  --state-json build/runtime/tfstate.json \
  --health-checks build/runtime/health-checks.json \
  --backup-checks build/runtime/backup-checks.json \
  --git-sha 0123456789abcdef0123456789abcdef01234567 \
  --ci-run-id ci-123 \
  --issuer-tool-version 1.10.0 \
  --artifact-base-uri s3://runtime-evidence/staging/ci-123 \
  --output-dir build/runtime/staging-evidence
```

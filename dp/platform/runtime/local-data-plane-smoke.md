# Local Data-Plane Smoke Gate

This gate is the first executable answer to the external review that said the DP work was too
control-plane heavy. It proves one thin vertical slice in CI:

```text
finance benefit event JSONL
  -> contract-checked Bronze approved/quarantine outputs
  -> Silver finance benefit transactions
  -> Gold finance benefit reconciliation
  -> catalog bundle + release evidence
  -> Gold query smoke
  -> data_plane_smoke_report.v1
```

The default slice is `finance-benefit-reconciliation` because it is non-LMS and shows the DP as a
group platform, not only a pilot-product feature.

## Command

```bash
cd dp
make data-plane-smoke
```

Equivalent CLI:

```bash
PYTHONPATH=src python -m enterprise_dp.cli data-plane-smoke \
  --root . \
  --use-case-id finance-benefit-reconciliation \
  --output-dir build/data-plane-smoke/run \
  --output build/data-plane-smoke/data-plane-smoke-report.json \
  --release-id local-data-plane-smoke \
  --environment local
```

The report fails if:

- release evidence fails any P0 gate;
- a declared Bronze/Silver/Gold layer is missing;
- manifest row counts or hashes do not match the materialized files;
- any layer quality flag fails;
- the Gold query probe has no result.

Attach the smoke artifact to the Control Tower decision report:

```bash
PYTHONPATH=src python -m enterprise_dp.cli control-tower-report \
  --root . \
  --output build/data-plane-smoke/control-tower-with-smoke.json \
  --data-plane-smoke-report build/data-plane-smoke/data-plane-smoke-report.json
```

The Control Tower command may exit non-zero because other P0 production blockers still exist; that
is expected until the remaining runtime, IaC and governance evidence is complete.

For the single artifact set intended for partner review, run:

```bash
make production-review-pack
```

The pack includes this smoke report, runtime readiness, capability maturity and Control Tower
evidence under `build/production-review-pack/`.

## Boundary

This is a local CI data-flow gate. It does not claim that the production runtime is complete. The
next production upgrades remain:

- Redpanda/Kafka or Debezium source flow with broker offsets bound to Bronze;
- producer schema-id enforcement, broker/sink schema validation and production schema registry
  auth/HA/attestation evidence;
- production catalog HA/concurrency, cross-engine commit compatibility and object-store encryption
  evidence for Iceberg;
- production authentication/service identity, row-level filters, column masking and centralized
  access audit evidence;
- Production Dagster/Airflow daemon, schedule, retry and backfill evidence;
- staging IaC apply evidence and Control Tower ingestion of live runtime reports.

The local Trino memory smoke (`make trino-sql-smoke`) proves that the Trino engine can load and
query the finance Gold rows, but it deliberately does not claim Iceberg or MinIO-backed lakehouse
serving.

The local Iceberg catalog smoke (`make iceberg-catalog-smoke`) proves that Bronze/Silver/Gold
finance tables can be committed to a real PyIceberg SQL catalog with snapshot metadata and scan
read-back. It deliberately does not claim a MinIO-backed Iceberg warehouse, REST/Nessie/Hive catalog
service or Trino Iceberg connector.

The local Trino Iceberg/MinIO smoke (`make trino-iceberg-minio-smoke`) proves that Trino can create
and query a finance Iceberg table in MinIO through a local Postgres JDBC catalog, and verifies
Iceberg `$snapshots`, `$files` and MinIO data/metadata objects. It deliberately does not claim
production catalog HA, cross-engine commit compatibility or object-store encryption policy.

The local Trino runtime security smoke (`make trino-runtime-security-smoke`) proves file-based
authorization enforcement in the local Trino engine over the same Iceberg/MinIO table. It verifies an
explicit allowed identity can read, the allowed read-only identity cannot write, a denied identity
cannot read, and an unknown identity is default-denied. It deliberately does not claim production
OIDC/Keycloak authentication, row-level filters, column masking, centralized audit, policy
administrator maker-checker or secret rotation.

The local Dagster smoke (`make dagster-orchestration-smoke`) proves that a real Dagster job can
orchestrate the finance runtime evidence path and that the run ID plus event log can be read back.
It deliberately does not claim production daemon scheduling, distributed execution, backfill history
or service-identity enforcement.

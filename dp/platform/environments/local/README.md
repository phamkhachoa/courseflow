# Local Data Platform Environment

Local is for developer feedback only. It may use MinIO, local Kafka, local object paths and generated
tokens. Local evidence cannot be used for production signoff.

## P0 Assumptions

- Local runs as a single-developer environment, not a shared integration or production substitute.
- `manifest.yaml` declares the required local topology for Kafka-compatible events, schema registry,
  object storage, Iceberg, Spark/dbt, orchestration, Trino-compatible SQL and observability.
- Local object storage should use a disposable lakehouse bucket such as `s3://dp-local-lakehouse`.
- Local catalog names should be environment-specific, for example `local_lakehouse`, while table
  namespaces and names match production.
- Local secrets, salts and tokens are generated test values only. They must never be reused for
  staging or production hashing/tokenization.
- Local fixtures must avoid real PII. Pilot samples should use synthetic ids or pre-hashed
  person/session identifiers.
- Local clocks and jobs should use UTC. Developer display time zones must not change persisted event
  times or partitions.
- Local Kafka offsets, object versions and Iceberg snapshots are allowed to be reset by the
  developer, so local evidence is useful for debugging but not audit signoff.

## Required Local Checks

Before a P0 ingestion or processing change is promoted beyond local:

- Contract validation passes against `dp/contracts`.
- The selected schema registry can register the topic value subject and enforce
  `BACKWARD_TRANSITIVE` compatibility.
- A sample Bronze replay over the same source range produces no duplicate approved rows.
- Iceberg tables are read and written through the local catalog, not direct object paths.
- Spark/dbt jobs can run with explicit input snapshot or offset parameters.
- Quality checks produce machine-readable output that can be attached to staging or production
  evidence later.

## Local Non-Goals

- No production signoff evidence.
- No real personal, employee, customer, account or other sensitive identifiers.
- No long-term retention guarantee.
- No guarantee that local object paths, credentials or service ports match production.
- No bypass of production schema registry, quality, security or release gates.

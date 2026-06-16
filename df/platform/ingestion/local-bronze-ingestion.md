# Local Bronze Ingestion Preflight

`enterprise-df ingest-bronze` is the local P0 preflight for contract-checked JSONL ingestion. It is
not the production Kafka/Iceberg sink, but it exercises the same platform concerns:

- Topic contract lookup.
- Shared envelope and payload schema validation.
- Product ownership check.
- Source-service allowlist check.
- Source-position duplicate protection.
- Replay idempotency against existing approved output in the same output directory.
- Hash mismatch quarantine when a previously approved source position reappears with different
  content.
- Direct-identifier quarantine.
- Approved Bronze JSONL output.
- Quarantine JSONL output.
- Replay/evidence manifest with hashes and source offsets.

If the registered source cannot publish the canonical enterprise event envelope yet, run
`enterprise-df source-bridge-normalize` before Bronze ingestion. The bridge is a product-agnostic
preflight step: each adapter maps a raw product source into the canonical topic, hashes or removes
restricted identifiers, preserves source position and writes an auditable manifest.

```bash
cd df
PYTHONPATH=src python -m enterprise_df.cli source-bridge-normalize \
  --root . \
  --source-id <registered-source-id> \
  --input samples/source-bridge/<source>_raw.jsonl \
  --output-dir build/source-bridge-preflight \
  --bridge-run-id local-source-bridge-001
```

Use the bridge output as the Bronze input:

```bash
PYTHONPATH=src python -m enterprise_df.cli ingest-bronze \
  --root . \
  --topic <canonical.topic.v1> \
  --input build/source-bridge-preflight/normalized/<registered-source-id>.jsonl \
  --output-dir build/bronze-preflight \
  --ingest-run-id local-bronze-001
```

The bridge command exits non-zero when records are quarantined. That failure is intentional evidence:
the product source is not ready for approved Bronze until missing source offsets, privacy issues or
mapping errors are fixed.

## Example

```bash
cd df
PYTHONPATH=src python -m enterprise_df.cli ingest-bronze \
  --root . \
  --topic recommendation.tracking.v1 \
  --input samples/recommendation/tracking.jsonl \
  --output-dir build/bronze-preflight \
  --ingest-run-id local-recommendation-001
```

The command exits `0` only when no records are quarantined. A non-zero exit means the output still
contains evidence, but the input is not ready for approved Bronze publication.

When the same output directory already contains approved Bronze rows, the command treats those rows as
the local idempotency state:

- Same source position and same source record hash: skip as replayed input.
- Same source position and different source record hash: quarantine with `HASH_MISMATCH`.
- Missing source topic, partition or offset: quarantine with `SOURCE_POSITION_MISSING`.

## Output Layout

| Path | Purpose |
|---|---|
| `bronze/<target>.jsonl` | Approved Bronze rows derived from the topic and data product contract. |
| `quarantine/<topic>.jsonl` | Rejected rows with reason codes and raw record hashes. |
| `manifests/<target>.<run_id>.json` | Evidence manifest with counts, hashes, schema subject/id and source offsets. |

`source-bridge-normalize` writes a separate preflight layout:

| Path | Purpose |
|---|---|
| `normalized/<source_id>.jsonl` | Canonical enterprise event envelopes ready for `ingest-bronze`. |
| `quarantine/<source_id>.jsonl` | Raw records rejected by the adapter with reason counts. |
| `manifests/<source_id>.<run_id>.json` | Bridge evidence with raw input hash, normalized output hash, source positions and normalizer id. |

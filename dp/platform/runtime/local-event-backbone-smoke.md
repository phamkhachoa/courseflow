# Local Event Backbone Smoke

This optional smoke proves the first live runtime hop before the local Medallion flow:

```text
finance benefit event JSONL
  -> Redpanda topic through rpk produce
  -> rpk consume back to JSONL
  -> data-plane smoke
registered P0 source samples
  -> source bridge normalization when required
  -> producer schema-id guard/stamping from local Apicurio report when available
  -> Redpanda source smoke topics through rpk produce/consume
  -> sink-side JSON Schema validation against canonical topic contracts
  -> ingestion runtime evidence/check
  -> event_backbone_smoke_report.v1
```

Run it only on a machine with Docker running:

```bash
cd dp
make event-backbone-smoke
```

The command starts the `redpanda` service from `platform/runtime/local/docker-compose.yaml`, creates a
unique smoke topic, produces the finance sample records, consumes the same count back, writes the
consumed JSONL, runs the normal data-plane smoke over those consumed records, then round-trips every
P0 source with a registered `evidence.localSamplePath` through local Redpanda. Bridge-required
sources are normalized first. When `schema-registry-runtime-smoke` has produced an Apicurio runtime
report, the producer input is guarded before publish: the record `payloadSchema` must resolve to the
registered subject, the subject must have a schema id, and the record headers are stamped with
`schemaSubject`, `schemaId`, `schemaVersion` and `schemaRegistryUri`. Every consumed canonical
record is then validated against its topic envelope and payload schema. It writes local
`ingestion_runtime_evidence.v1` plus
`event_cdc_ingestion_runtime_report.v1` under `build/event-backbone-smoke/ingestion-runtime/`.

Attach the generated report to the partner-review pack:

```bash
make production-review-pack \
  EVENT_BACKBONE_SMOKE_REPORT=build/event-backbone-smoke/event-backbone-smoke-report.json \
  INGESTION_RUNTIME_REPORT=build/event-backbone-smoke/ingestion-runtime/event-cdc-ingestion-runtime-report.json
```

The report fails if:

- Docker or Redpanda is unavailable;
- topic create, produce or consume exits non-zero;
- the local producer schema-id guard fails while schema-registry runtime evidence is attached;
- consumed JSON records do not match the source records;
- consumed records fail canonical topic envelope or payload schema validation;
- the downstream data-plane smoke fails;
- the generated ingestion runtime report fails.

This is still local Redpanda/rpk runtime evidence for the registered P0 source samples. It does not
replace Debezium/outbox connector-to-Bronze evidence, production broker ACL checks, multi-partition
rebalance evidence, broker-enforced schema validation, production DLT policy or production schema
registry hardening evidence.

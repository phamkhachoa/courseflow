# Staging Data Platform Environment

Staging must mirror production topology closely enough to prove release gates:

- `manifest.yaml` is the environment contract for required P0 runtime services and evidence mode.
- HTTPS endpoints and real service identity.
- Schema registry compatibility checks.
- Object storage lifecycle policy.
- Catalog and lineage publication.
- Data quality gates and Prometheus alerts.
- Masked production-like data where allowed.

# Runtime IaC Modules

This folder is the skeleton location for OpenTofu/Terraform modules that will deploy the enterprise
data foundation runtime.

The current files are intentionally not production apply evidence. They define the ownership,
module boundaries and required controls that must exist before the `platform-runtime-iac` capability
can move from `L1` to `L2/L3`.

Required production controls:

- Workload/service identity for every runtime component.
- External secret references, no committed runtime secrets.
- Private network exposure for control plane, data plane and storage endpoints.
- Encryption, lifecycle, backup and restore controls for stateful services.
- SLO metrics, alert rules and runbook linkage.
- DR exercise evidence before production signoff.

# Runtime IaC Modules

This folder contains the OpenTofu runtime contract roots for the enterprise data platform.

The `staging/` and `prod/` roots declare every P0 runtime service as a module, and all local module
sources must validate inside this repository. The shared `modules/runtime-service-contract` module is
provider-free by design so CI can validate the contract without cloud credentials.

Run the HCL-level contract gate with:

```bash
make runtime-iac-contract-check
```

The target copies this folder into `build/runtime-iac-contract-check`, then runs Terraform
`init -backend=false` and `validate` for both `staging` and `prod`. It proves the declared module
graph is valid HCL and all local module sources resolve. It does not produce plan/apply evidence.

These files are still not production apply evidence. They define ownership, module boundaries and
required controls. Staging/prod runtime readiness can only pass with artifacts produced by
`runtime-evidence-normalize-iac` from real plan/state/health/backup/DR source files.

Required production controls:

- Workload/service identity for every runtime component.
- External secret references, no committed runtime secrets.
- Private network exposure for control plane, data plane and storage endpoints.
- Encryption, lifecycle, backup and restore controls for stateful services.
- SLO metrics, alert rules and runbook linkage.
- DR exercise evidence before production signoff.

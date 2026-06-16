# Contract Policies

This folder contains machine-checkable compatibility, privacy, retention and access-control policies
that apply to enterprise topic and data product contracts across group products.

`access-policies.yaml` is the source of truth for data serving access controls. Data product contracts
reference a policy through `serving.accessPolicy`; validation, release evidence and catalog export all
resolve that reference back to the registry.

`access-personas.yaml` is the source of truth for enterprise data access personas used by data products,
use cases and access policies. Add new group-level personas here before referencing them from product
contracts.

`consumer-contracts.yaml` defines reusable serving contract terms such as catalog registration,
approval evidence, review cadence and audit obligations. In phase 1, `serving.consumerContract` remains
a backward-compatible string id, but validation resolves it to this registry and checks active status,
scope and persona compatibility.

`retention-policies.yaml` defines reusable privacy retention and erasure controls. Topic and data
product contracts are matched to an active policy by layer, domain, product and privacy classification;
validation rejects contracts whose `retentionDays` or `erasureSupported` values do not satisfy the
resolved policy.

Each policy must declare a stable `id`, `policyVersion`, `status`, `severity`, `owner`, effective date,
applicable layers/classifications, allowed consumer personas, required columns and enforcement controls.
CI should reject contracts that reference an unknown policy, use a policy outside its scope, expose
personas not allowed by that policy or miss required isolation columns such as `org_id`.

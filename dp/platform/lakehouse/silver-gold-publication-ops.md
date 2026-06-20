# Silver and Gold Publication Operations Gate

`silver_gold_publication_ops_report.v1` is the P0 operations gate for exposing Silver and Gold data
products. It proves that the active data-product snapshot is tied to a passing release evidence pack,
an approved promotion, an activation manifest and an active pointer with rollback context.

## Decision

`enterprise-dp silver-gold-publication-ops-report` reads release evidence, promotion manifests,
activation manifests and active pointer states for Silver or Gold outputs. Local environments may
pass as a preflight without runtime evidence. Staging and production must attach all four evidence
families before a data product can be treated as publication-ready.

Control Tower consumes the report through `--silver-gold-publication-ops-report` and blocks
production signoff when the artifact is missing, from the wrong environment, not
`production_like_ready`, or when any data product has release, promotion, activation, active-pointer
or rollback failures.

## Evidence Contract

For each published Silver or Gold data product, the report expects:

- A passing release evidence artifact with matching environment, release id and
  `lakehouse_snapshot_evidence.v1` URI/hash.
- A `release_promotion_manifest.v1` with `promotion_state=approved_for_activation`, matching target
  environment, matching output data product and separated requester/approver evidence.
- A `release_activation_manifest.v1` with `activation_state=activated`, matching release id,
  matching target environment and matching output snapshot/content hash.
- A `release_active_pointer.v1` matching the activation pointer and activated output.
- A rollback target for staging and production activations.
- A production change ticket for production promotion.

The report fails closed for active-pointer drift, missing snapshot evidence, failed release gates,
unapproved promotions, blocked activations, missing rollback targets and mismatched environments.

## CLI

```bash
enterprise-dp silver-gold-publication-ops-report \
  --root . \
  --environment prod \
  --release-evidence build/evidence/finance-release.json \
  --promotion-manifest build/evidence/finance-promotion.json \
  --activation-manifest build/evidence/finance-activation.json \
  --active-pointer governance/active-pointers/prod/gold.finance_benefit_reconciliation.json \
  --output build/evidence/silver-gold-publication-ops-prod.json
```

The command exits non-zero when global evidence checks fail or any data product fails. The report
exposes `decision_board.page_now` for missing release evidence, failed promotions, failed
activations, active-pointer drift and missing rollback targets.

## Current State

This repository now has the report contract, CLI, Control Tower gate and automated tests. The
capability remains at L1 because staging and production publication are still evidence-backed local
checks; L2/L3 require live orchestration or CI/CD enforcement that writes immutable active pointer
state, reads real catalog/Iceberg active snapshots and blocks production exposure automatically.

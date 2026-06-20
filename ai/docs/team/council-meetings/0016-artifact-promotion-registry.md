# AI Platform Product Council 0016

Date: 2026-06-16

## Topic

Add artifact promotion registry for source algorithms and vector-index snapshots.

## Decision

Create `platform/artifacts/promotions/registry.yaml` as the shared promotion evidence path. Promotion records link artifact manifests to product/use-case scope, required evaluation gates, maker-checker approval actors, rollback targets and stage. The evidence validator now checks promotion consistency and rejects self-approval, missing gates, missing manifests, unknown rollback targets and duplicate active promotions.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Artifact promotion registry | `platform/artifacts/promotions/registry.yaml` |
| Promotion validator | `platform/src/courseflow_ai_platform/evidence.py` |
| Evidence tests | `platform/tests/test_evidence.py` |
| Capability registry update | `platform/capabilities/registry.yaml` |

## Runtime Guarantees

| Guarantee | Behavior |
|---|---|
| Manifest linkage | Every promotion must reference a known artifact manifest |
| Gate evidence | Every required gate report path must exist |
| Maker-checker | Requester and approver must be different when policy requires it |
| Rollback path | Approved and active stages must define a known rollback target |
| Active uniqueness | Only one active promotion per product/use case is allowed |
| Non-LMS coverage | Support baseline and support vector index are promoted through the same path |

## Product Impact

| Product | Use |
|---|---|
| AI Platform | Shared promotion governance for model and retrieval artifacts |
| LMS CourseFlow | Recommendation and RAG artifacts have activation/rollback evidence |
| Support Platform | Agent-assist and support RAG artifacts use the same non-LMS promotion path |
| Future domains | Billing, commerce, HRIS and risk artifacts can reuse the registry |

## Next Actions

1. Add candidate promotion requests generated from evaluation runner output.
2. Add Admin/Ops UI projection for promotion status, gates and rollback target.
3. Add object-store artifact URIs before production serving promotion.

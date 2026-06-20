# AI Platform Product Council 0015

Date: 2026-06-16

## Topic

Persist vector-index snapshot evidence with artifact manifests and hash validation.

## Decision

Promote the deterministic vector-index contract outputs into explicit platform artifacts. Each vector-index snapshot has a manifest, sha256 hash, corpus/schema lineage, evaluation report lineage and builder reference. The evidence validator now supports both `source_algorithm` and `vector_index_snapshot` artifact types.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Course vector-index snapshot | `platform/artifacts/vector-indexes/course-content-vector-index-baseline-v1.json` |
| Support vector-index snapshot | `platform/artifacts/vector-indexes/support-knowledge-vector-index-baseline-v1.json` |
| Course vector-index manifest | `platform/artifacts/manifests/course-content-vector-index-baseline-v1.yaml` |
| Support vector-index manifest | `platform/artifacts/manifests/support-knowledge-vector-index-baseline-v1.yaml` |
| Evidence validator update | `platform/src/courseflow_ai_platform/evidence.py` |
| Evidence tests | `platform/tests/test_evidence.py` |

## Runtime Guarantees

| Guarantee | Behavior |
|---|---|
| Hash verification | Snapshot files must match sha256 values in manifests |
| Lineage evidence | Corpus, collection schema, evaluation report and builder paths must exist |
| Payload validation | Snapshot model ID, chunk count, entries, tenant/source metadata and text hashes are checked |
| Non-LMS coverage | Support vector-index snapshot proves artifact governance is not LMS-only |

## Product Impact

| Product | Use |
|---|---|
| AI Platform | Shared artifact governance for retrieval/index assets |
| LMS CourseFlow | Course RAG index has rollbackable snapshot evidence |
| Support Platform | Support RAG index has rollbackable non-LMS snapshot evidence |
| Future domains | Commerce/HRIS/Risk can publish vector artifacts through the same manifest path |

## Next Actions

1. Promote vector-index snapshots to object storage with immutable artifact URIs.
2. Add model binary and tokenizer manifest types for deep learning and transformer models.
3. Add candidate/promotion status transitions for retriever artifacts.

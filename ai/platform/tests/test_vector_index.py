from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.registry import load_yaml
from courseflow_ai_platform.vector_index import (
    build_vector_index,
    hybrid_rank_ids,
    validate_vector_index_contract,
    vector_rank,
)


def test_vector_index_builds_deterministic_tenant_scoped_artifact() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    corpus = load_yaml(
        ai_root / "platform" / "evaluation" / "corpora" / "course-content-corpus.yaml"
    )
    collection_schema = load_yaml(
        ai_root / "platform" / "vector-store" / "collections" / "course-content.yaml"
    )

    index_a = build_vector_index(
        corpus,
        collection_schema,
        index_id="course-content-vector-index-baseline-v1",
        model_id="course-content-vector-index-baseline-v1",
    )
    index_b = build_vector_index(
        corpus,
        collection_schema,
        index_id="course-content-vector-index-baseline-v1",
        model_id="course-content-vector-index-baseline-v1",
    )

    assert index_a.checksum == index_b.checksum
    assert index_a.collection == "course_content_chunks"
    assert index_a.embedding_dimensions == 768
    assert index_a.chunk_count == 5
    assert {entry.tenant_id for entry in index_a.entries} == {"tenant-a", "tenant-b"}
    assert all(len(entry.vector) == 768 for entry in index_a.entries)
    assert all(entry.source_ref for entry in index_a.entries)


def test_vector_index_contract_metrics_pass_for_support_and_course() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    thresholds = {
        "chunk_coverage_min": 1.0,
        "dimension_conformance_min": 1.0,
        "metadata_conformance_min": 1.0,
        "tenant_scope_coverage_min": 1.0,
    }

    for corpus_name, collection_name, index_id in (
        (
            "course-content-corpus.yaml",
            "course-content.yaml",
            "course-content-vector-index-baseline-v1",
        ),
        (
            "support-knowledge-corpus.yaml",
            "support-knowledge.yaml",
            "support-knowledge-vector-index-baseline-v1",
        ),
    ):
        corpus = load_yaml(ai_root / "platform" / "evaluation" / "corpora" / corpus_name)
        collection_schema = load_yaml(
            ai_root / "platform" / "vector-store" / "collections" / collection_name
        )
        artifact = build_vector_index(
            corpus,
            collection_schema,
            index_id=index_id,
            model_id=index_id,
        )
        metrics = validate_vector_index_contract(
            artifact,
            corpus,
            collection_schema,
            thresholds,
        )

        assert metrics.passed is True
        assert metrics.chunk_coverage_rate == 1.0
        assert metrics.dimension_conformance_rate == 1.0
        assert metrics.metadata_conformance_rate == 1.0
        assert metrics.tenant_scope_coverage_rate == 1.0
        assert metrics.checksum_stable is True


def test_vector_rank_and_hybrid_rank_preserve_tenant_scope() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    corpus = load_yaml(
        ai_root / "platform" / "evaluation" / "corpora" / "support-knowledge-corpus.yaml"
    )
    collection_schema = load_yaml(
        ai_root / "platform" / "vector-store" / "collections" / "support-knowledge.yaml"
    )
    artifact = build_vector_index(
        corpus,
        collection_schema,
        index_id="support-knowledge-vector-index-baseline-v1",
        model_id="support-knowledge-hybrid-retriever-shadow-v1",
    )

    vector_results = vector_rank("MFA timeout admin login", artifact, "tenant-a", 3)
    vector_ids = {result.chunk_id for result in vector_results}
    hybrid_ids = hybrid_rank_ids(
        {"support-access-mfa-timeout": 1.0},
        vector_results,
        k=3,
    )

    assert "support-access-mfa-timeout" in vector_ids
    assert "support-access-mfa-timeout" in hybrid_ids
    assert "support-tenant-b-private-mfa" not in vector_ids
    assert "support-tenant-b-private-mfa" not in hybrid_ids

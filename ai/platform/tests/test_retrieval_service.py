from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.retrieval_service import (
    RETRIEVAL_SEARCH_SCOPE,
    RetrievalPrincipal,
    RetrievalRuntime,
    RetrievalServiceError,
    load_retrieval_access_policy,
)


def test_retrieval_runtime_catalogs_registered_vector_collections() -> None:
    runtime = RetrievalRuntime(Path(__file__).resolve().parents[2])
    catalog = {collection.collection_id: collection for collection in runtime.catalog()}

    assert set(catalog) == {"course_content_chunks", "support_knowledge_articles"}
    assert catalog["course_content_chunks"].product == "lms-courseflow"
    assert catalog["support_knowledge_articles"].product == "support-platform"
    assert catalog["course_content_chunks"].artifact.embedding_dimensions == 768
    assert runtime.health()["collectionCount"] == 2


def test_retrieval_runtime_hybrid_search_preserves_tenant_scope() -> None:
    runtime = RetrievalRuntime(Path(__file__).resolve().parents[2])
    response = runtime.search(
        {
            "collectionId": "course_content_chunks",
            "tenantId": "tenant-a",
            "query": "Tenant B private SQL joins",
            "mode": "hybrid",
            "topK": 5,
        },
        RetrievalPrincipal(
            principal_id="service:lms-courseflow-retrieval",
            scopes=(RETRIEVAL_SEARCH_SCOPE,),
            tenant_ids=("tenant-a",),
            allowed_collection_ids=("course_content_chunks",),
        ),
    )
    chunk_ids = {result.chunk_id for result in response.results}

    assert "course-tenant-b-private-sql" not in chunk_ids
    assert all(result.tenant_id == "tenant-a" for result in response.results)
    assert runtime.snapshot_metrics().search_count == 1


def test_retrieval_access_policy_rejects_ungranted_scope_and_collection() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    policy = load_retrieval_access_policy(ai_root)
    support_principal = policy.resolve_principal(
        "service:support-platform-retrieval",
        (RETRIEVAL_SEARCH_SCOPE,),
    )

    assert support_principal.allowed_collection_ids == ("support_knowledge_articles",)
    with pytest.raises(RetrievalServiceError, match="ungranted scopes"):
        policy.resolve_principal(
            "service:support-platform-retrieval",
            ("internal:ai-platform:retrieval:ops",),
        )

    runtime = RetrievalRuntime(ai_root)
    with pytest.raises(RetrievalServiceError, match="collection is not granted"):
        runtime.search(
            {
                "collectionId": "course_content_chunks",
                "tenantId": "tenant-a",
                "query": "SQL joins",
                "mode": "hybrid",
                "topK": 3,
            },
            support_principal,
        )

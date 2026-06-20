from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.rag_answer_service import (
    RAG_ANSWER_ANSWER_SCOPE,
    RagAnswerRuntime,
    RagAnswerServiceError,
    load_rag_answer_access_policy,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def lms_request(question: str) -> dict[str, object]:
    return {
        "tenantId": "tenant-a",
        "product": "lms-courseflow",
        "useCaseId": "lms-rag-tutor",
        "collectionId": "course_content_chunks",
        "question": question,
        "topK": 3,
    }


def test_rag_answer_runtime_composes_retrieval_and_prompt_gateway_gates() -> None:
    policy = load_rag_answer_access_policy(ai_root())
    principal = policy.resolve_principal(
        "service:lms-courseflow-rag-answer",
        (RAG_ANSWER_ANSWER_SCOPE,),
    )
    runtime = RagAnswerRuntime(ai_root())

    response = runtime.answer(
        lms_request("Explain Python for loops, while loops, break and continue."),
        principal,
    )
    metrics = runtime.snapshot_metrics()

    assert response.answer_status == "grounded"
    assert response.require_human_review is True
    assert response.policy_allowed is True
    assert response.citations[0].chunk_id == "course-python-loops-lesson"
    assert "Python for loops" in response.answer
    assert metrics.answer_count == 1
    assert metrics.by_product == {"lms-courseflow": 1}


def test_rag_answer_runtime_refuses_when_grounding_is_cross_tenant_or_private() -> None:
    policy = load_rag_answer_access_policy(ai_root())
    principal = policy.resolve_principal(
        "service:lms-courseflow-rag-answer",
        (RAG_ANSWER_ANSWER_SCOPE,),
    )
    runtime = RagAnswerRuntime(ai_root())

    response = runtime.answer(
        lms_request("What is the private tenant B SQL join example?"),
        principal,
    )

    assert response.answer_status == "refused"
    assert response.citations == ()
    assert response.refusal_reason == "insufficient_grounding_context"


def test_rag_answer_policy_rejects_ungranted_scope_and_collection() -> None:
    policy = load_rag_answer_access_policy(ai_root())
    support_principal = policy.resolve_principal(
        "service:support-platform-rag-answer",
        (RAG_ANSWER_ANSWER_SCOPE,),
    )

    assert support_principal.allowed_collection_ids == ("support_knowledge_articles",)
    with pytest.raises(RagAnswerServiceError, match="ungranted scopes"):
        policy.resolve_principal(
            "service:support-platform-rag-answer",
            ("internal:ai-platform:rag-answer:ops",),
        )

    runtime = RagAnswerRuntime(ai_root())
    with pytest.raises(RagAnswerServiceError, match="collection is not granted"):
        runtime.answer(
            {
                "tenantId": "tenant-a",
                "product": "support-platform",
                "useCaseId": "support-agent-assist",
                "collectionId": "course_content_chunks",
                "question": "Explain SQL joins",
                "topK": 3,
            },
            support_principal,
        )

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_rag_answer_service.cli import main
from courseflow_rag_answer_service.service import (
    RAG_ANSWER_SERVICE_ID,
    RagAnswerService,
    RagAnswerServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def lms_answer_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-a",
        "product": "lms-courseflow",
        "useCaseId": "lms-rag-tutor",
        "collectionId": "course_content_chunks",
        "question": "Explain Python for loops, while loops, break and continue.",
        "topK": 3,
    }


def support_answer_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-a",
        "product": "support-platform",
        "useCaseId": "support-agent-assist",
        "collectionId": "support_knowledge_articles",
        "question": "MFA timeout identity provider status recovery steps",
        "topK": 3,
    }


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (ai_root() / "services" / "rag-answer-service" / "service.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy = load_yaml(
        ai_root()
        / "platform"
        / "governance"
        / "policies"
        / "rag-answer-access-policy.yaml"
    )
    scopes = set(policy["scope_aliases"].values())

    assert manifest["serviceId"] == RAG_ANSWER_SERVICE_ID
    assert service_yaml["service_id"] == RAG_ANSWER_SERVICE_ID
    assert len(manifest["routes"]) == 3
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {route["scope"] for route in manifest["routes"]} == scopes


def test_service_answers_lms_and_support_with_citations_and_metrics() -> None:
    service = RagAnswerService(RagAnswerServiceConfig.from_paths(ai_root=ai_root()))

    lms_response = service.handle_request(
        "POST",
        "/v1/rag-answer/answer",
        lms_answer_body(),
        principal_id="service:lms-courseflow-rag-answer",
    )
    support_response = service.handle_request(
        "POST",
        "/v1/rag-answer/answer",
        support_answer_body(),
        principal_id="service:support-platform-rag-answer",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/rag-answer/metrics",
        principal_id="service:ai-platform-rag-answer-ops",
    )

    assert lms_response.status_code == 200
    assert lms_response.body["answerStatus"] == "grounded"
    assert lms_response.body["citations"][0]["chunkId"] == "course-python-loops-lesson"
    assert support_response.status_code == 200
    assert support_response.body["answerStatus"] == "grounded"
    assert support_response.body["citations"][0]["chunkId"] == "support-access-mfa-timeout"
    assert metrics.body["metrics"]["answerCount"] == 2
    assert metrics.body["metrics"]["byUseCase"] == {
        "lms-rag-tutor": 1,
        "support-agent-assist": 1,
    }


def test_service_refuses_private_cross_tenant_answer_without_citation() -> None:
    service = RagAnswerService(RagAnswerServiceConfig.from_paths(ai_root=ai_root()))

    response = service.handle_request(
        "POST",
        "/v1/rag-answer/answer",
        {
            **lms_answer_body(),
            "question": "What is the private tenant B SQL join example?",
        },
        principal_id="service:lms-courseflow-rag-answer",
    )

    assert response.status_code == 200
    assert response.body["answerStatus"] == "refused"
    assert response.body["citationCount"] == 0
    assert response.body["refusalReason"] == "insufficient_grounding_context"


def test_service_rejects_missing_auth_unapproved_collection_and_unsafe_controls() -> None:
    service = RagAnswerService(RagAnswerServiceConfig.from_paths(ai_root=ai_root()))

    missing_auth = service.handle_request(
        "POST",
        "/v1/rag-answer/answer",
        lms_answer_body(),
    )
    denied_collection = service.handle_request(
        "POST",
        "/v1/rag-answer/answer",
        {
            **support_answer_body(),
            "collectionId": "course_content_chunks",
        },
        principal_id="service:support-platform-rag-answer",
    )
    direct_identifier = service.handle_request(
        "POST",
        "/v1/rag-answer/answer",
        {
            **lms_answer_body(),
            "learnerId": "learner-raw-001",
        },
        principal_id="service:lms-courseflow-rag-answer",
    )
    external_auto_send = service.handle_request(
        "POST",
        "/v1/rag-answer/answer",
        {
            **support_answer_body(),
            "allowExternalAutoSend": True,
        },
        principal_id="service:support-platform-rag-answer",
    )

    assert missing_auth.status_code == 401
    assert missing_auth.body["errorCode"] == "auth_required"
    assert denied_collection.status_code == 400
    assert "collection is not granted" in denied_collection.body["errorMessage"]
    assert direct_identifier.status_code == 403
    assert direct_identifier.body["errorCode"] == "privacy_control_violation"
    assert external_auto_send.status_code == 400
    assert "external auto-send is forbidden" in external_auto_send.body["errorMessage"]


def test_cli_health_uses_registered_ops_principal(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-rag-answer",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-rag-answer-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["serviceStatus"] == "healthy"
    assert payload["body"]["routeCount"] == 3


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-rag-answer", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == RAG_ANSWER_SERVICE_ID
    assert len(payload["routes"]) == 3

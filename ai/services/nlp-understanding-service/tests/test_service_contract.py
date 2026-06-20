from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_nlp_understanding_service.cli import main
from courseflow_nlp_understanding_service.service import (
    NLP_UNDERSTANDING_SERVICE_ID,
    NlpUnderstandingService,
    NlpUnderstandingServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def support_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-a",
        "product": "support-platform",
        "useCaseId": "support-agent-assist",
        "subject": "Urgent login outage",
        "latestMessage": "All admins are blocked by MFA timeout errors.",
        "productArea": "identity",
        "priority": "urgent",
        "taskType": "case_triage",
    }


def lms_rubric_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-a",
        "product": "lms-courseflow",
        "useCaseId": "lms-auto-grading",
        "text": "The learner answer explains Python loops, break and continue.",
        "taskType": "rubric_feedback",
        "rubricItems": ["mention loop control", "mention missing while loop"],
        "expectedTerms": ["Python loops", "break", "continue", "while loop"],
    }


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (ai_root() / "services" / "nlp-understanding-service" / "service.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy = load_yaml(
        ai_root()
        / "platform"
        / "governance"
        / "policies"
        / "nlp-understanding-access-policy.yaml"
    )
    scopes = set(policy["scope_aliases"].values())

    assert manifest["serviceId"] == NLP_UNDERSTANDING_SERVICE_ID
    assert service_yaml["service_id"] == NLP_UNDERSTANDING_SERVICE_ID
    assert len(manifest["routes"]) == 3
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {route["scope"] for route in manifest["routes"]} == scopes


def test_service_analyzes_support_and_lms_requests_and_tracks_metrics() -> None:
    service = NlpUnderstandingService(
        NlpUnderstandingServiceConfig.from_paths(ai_root=ai_root())
    )

    support_response = service.handle_request(
        "POST",
        "/v1/nlp-understanding/analyze",
        support_body(),
        principal_id="service:support-platform-nlp",
    )
    lms_response = service.handle_request(
        "POST",
        "/v1/nlp-understanding/analyze",
        lms_rubric_body(),
        principal_id="service:lms-courseflow-nlp",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/nlp-understanding/metrics",
        principal_id="service:ai-platform-nlp-ops",
    )

    assert support_response.status_code == 200
    assert support_response.body["intent"] == "access"
    assert support_response.body["prioritySignal"] == "high"
    assert support_response.body["requiresHumanReview"] is True
    assert lms_response.status_code == 200
    assert lms_response.body["intent"] == "learning_assessment"
    assert lms_response.body["missingTerms"] == ("while loop",)
    assert metrics.body["metrics"]["analysisCount"] == 2
    assert metrics.body["metrics"]["byUseCase"] == {
        "lms-auto-grading": 1,
        "support-agent-assist": 1,
    }


def test_service_supports_enterprise_knowledge_semantic_understanding() -> None:
    service = NlpUnderstandingService(
        NlpUnderstandingServiceConfig.from_paths(ai_root=ai_root())
    )

    response = service.handle_request(
        "POST",
        "/v1/nlp-understanding/analyze",
        {
            "tenantId": "tenant-a",
            "product": "ai-platform",
            "useCaseId": "enterprise-knowledge-assistant",
            "text": "Find policy documents with citations for access review procedure.",
            "taskType": "semantic_search",
            "productArea": "knowledge",
        },
        principal_id="service:enterprise-knowledge-nlp",
    )

    assert response.status_code == 200
    assert response.body["intent"] == "knowledge_lookup"
    assert "semantic_search" in response.body["semanticTags"]
    assert "knowledge_lookup" in response.body["retrievalQuery"]


def test_service_rejects_missing_auth_cross_tenant_use_case_and_direct_identifier() -> None:
    service = NlpUnderstandingService(
        NlpUnderstandingServiceConfig.from_paths(ai_root=ai_root())
    )

    missing_auth = service.handle_request(
        "POST",
        "/v1/nlp-understanding/analyze",
        support_body(),
    )
    denied_tenant = service.handle_request(
        "POST",
        "/v1/nlp-understanding/analyze",
        {**support_body(), "tenantId": "tenant-finance"},
        principal_id="service:support-platform-nlp",
    )
    denied_use_case = service.handle_request(
        "POST",
        "/v1/nlp-understanding/analyze",
        {**support_body(), "useCaseId": "enterprise-knowledge-assistant"},
        principal_id="service:support-platform-nlp",
    )
    direct_identifier = service.handle_request(
        "POST",
        "/v1/nlp-understanding/analyze",
        {**support_body(), "text": "Please inspect customer_id=raw-123."},
        principal_id="service:support-platform-nlp",
    )

    assert missing_auth.status_code == 401
    assert missing_auth.body["errorCode"] == "auth_required"
    assert denied_tenant.status_code == 400
    assert "tenant is not granted" in denied_tenant.body["errorMessage"]
    assert denied_use_case.status_code == 400
    assert "use case is not granted" in denied_use_case.body["errorMessage"]
    assert direct_identifier.status_code == 403
    assert direct_identifier.body["errorCode"] == "privacy_control_violation"


def test_cli_health_uses_registered_ops_principal(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-nlp-understanding",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-nlp-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["serviceStatus"] == "healthy"
    assert payload["body"]["routeCount"] == 3


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-nlp-understanding", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == NLP_UNDERSTANDING_SERVICE_ID
    assert len(payload["routes"]) == 3

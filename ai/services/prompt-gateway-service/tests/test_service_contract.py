from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_prompt_gateway_service.cli import main
from courseflow_prompt_gateway_service.service import (
    PROMPT_GATEWAY_SERVICE_ID,
    PromptGatewayService,
    PromptGatewayServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def support_prompt_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-a",
        "product": "support-platform",
        "useCaseId": "support-agent-assist",
        "systemPrompt": "Draft with citations only.",
        "userInput": (
            "Email jane.doe@example.com, phone +1-415-555-0133, "
            "api key sk-live-secret and learner_id=learner-raw-123."
        ),
        "retrievedContext": [
            {
                "contextId": "global-refund",
                "tenantId": "global",
                "sourceRef": "kb-001",
                "text": "Refunds require invoice and ledger review.",
            },
            {
                "contextId": "tenant-private",
                "tenantId": "tenant-b",
                "sourceRef": "kb-private",
                "text": "Tenant B private content.",
            },
        ],
        "outputPolicy": {
            "requireHumanReview": True,
            "allowExternalAutoSend": False,
            "requireCitations": True,
        },
        "costBudget": {
            "maxEstimatedInputTokens": 180,
            "maxEstimatedOutputTokens": 120,
            "maxEstimatedTotalTokens": 300,
        },
    }


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (ai_root() / "services" / "prompt-gateway-service" / "service.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy = load_yaml(
        ai_root()
        / "platform"
        / "governance"
        / "policies"
        / "prompt-gateway-access-policy.yaml"
    )
    scopes = set(policy["scope_aliases"].values())

    assert manifest["serviceId"] == PROMPT_GATEWAY_SERVICE_ID
    assert service_yaml["service_id"] == PROMPT_GATEWAY_SERVICE_ID
    assert len(manifest["routes"]) == 3
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {route["scope"] for route in manifest["routes"]} == scopes


def test_service_allows_safe_support_prompt_and_tracks_metrics() -> None:
    service = PromptGatewayService(PromptGatewayServiceConfig.from_paths(ai_root=ai_root()))

    response = service.handle_request(
        "POST",
        "/v1/prompt-gateway/evaluate",
        support_prompt_body(),
        principal_id="service:support-platform-prompt",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/prompt-gateway/metrics",
        principal_id="service:ai-platform-prompt-ops",
    )

    assert response.status_code == 200
    assert response.body["allowed"] is True
    assert response.body["contextIds"] == ("global-refund",)
    assert "tenant-private" not in response.body["sanitizedPrompt"]
    assert "jane.doe@example.com" not in response.body["sanitizedPrompt"]
    assert "[REDACTED_EMAIL]" in response.body["sanitizedPrompt"]
    assert "[REDACTED_SECRET]" in response.body["auditPayload"]
    assert metrics.body["metrics"]["evaluationCount"] == 1
    assert metrics.body["metrics"]["allowedCount"] == 1
    assert metrics.body["metrics"]["byUseCase"] == {"support-agent-assist": 1}


def test_service_returns_allowed_false_for_guardrail_blocks() -> None:
    service = PromptGatewayService(PromptGatewayServiceConfig.from_paths(ai_root=ai_root()))
    body = {
        **support_prompt_body(),
        "userInput": "Explain " + ("refund SQL " * 90),
        "outputPolicy": {
            "requireHumanReview": False,
            "allowExternalAutoSend": True,
            "requireCitations": True,
        },
        "costBudget": {
            "maxEstimatedInputTokens": 12,
            "maxEstimatedOutputTokens": 16,
            "maxEstimatedTotalTokens": 20,
        },
    }

    response = service.handle_request(
        "POST",
        "/v1/prompt-gateway/evaluate",
        body,
        principal_id="service:support-platform-prompt",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/prompt-gateway/metrics",
        principal_id="service:ai-platform-prompt-ops",
    )

    assert response.status_code == 200
    assert response.body["allowed"] is False
    assert "INPUT_TOKEN_BUDGET_EXCEEDED" in response.body["blockedReasons"]
    assert "EXTERNAL_AUTO_SEND_BLOCKED" in response.body["blockedReasons"]
    assert "HUMAN_REVIEW_REQUIRED" in response.body["blockedReasons"]
    assert metrics.body["metrics"]["blockedCount"] == 1


def test_service_rejects_missing_auth_and_ungranted_use_case() -> None:
    service = PromptGatewayService(PromptGatewayServiceConfig.from_paths(ai_root=ai_root()))

    missing_auth = service.handle_request(
        "POST",
        "/v1/prompt-gateway/evaluate",
        support_prompt_body(),
    )
    denied = service.handle_request(
        "POST",
        "/v1/prompt-gateway/evaluate",
        {
            **support_prompt_body(),
            "product": "lms-courseflow",
            "useCaseId": "lms-rag-tutor",
        },
        principal_id="service:support-platform-prompt",
    )

    assert missing_auth.status_code == 401
    assert missing_auth.body["errorCode"] == "auth_required"
    assert denied.status_code == 400
    assert denied.body["errorCode"] == "bad_request"
    assert "product is not granted" in denied.body["errorMessage"]


def test_cli_health_uses_registered_ops_principal(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-prompt-gateway",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-prompt-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["serviceStatus"] == "healthy"
    assert payload["body"]["routeCount"] == 3


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-prompt-gateway", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == PROMPT_GATEWAY_SERVICE_ID
    assert len(payload["routes"]) == 3

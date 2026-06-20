from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_llm_adapter_service.cli import main
from courseflow_llm_adapter_service.service import (
    LLM_ADAPTER_SERVICE_ID,
    LlmAdapterService,
    LlmAdapterServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def support_generation_body() -> dict[str, object]:
    return {
        "providerId": "contract-stub-llm-v1",
        "tenantId": "tenant-a",
        "product": "support-platform",
        "useCaseId": "support-agent-assist",
        "systemPrompt": "Draft with citations only.",
        "userInput": "Customer jane.doe@example.com asks about duplicate charge refund.",
        "generationQuestion": "How should an agent handle a duplicate charge refund request?",
        "retrievedContext": [
            {
                "contextId": "support-refund-global",
                "tenantId": "global",
                "sourceRef": "kb-support-billing-001",
                "text": "Duplicate charge refunds require invoice verification and ledger review.",
            },
            {
                "contextId": "support-tenant-b-private",
                "tenantId": "tenant-b",
                "sourceRef": "kb-support-tenant-b-001",
                "text": "Tenant B private MFA recovery details must never be visible.",
            },
        ],
        "outputPolicy": {
            "requireHumanReview": True,
            "allowExternalAutoSend": False,
            "requireCitations": True,
        },
        "costBudget": {
            "maxEstimatedInputTokens": 220,
            "maxEstimatedOutputTokens": 180,
            "maxEstimatedTotalTokens": 400,
        },
    }


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (ai_root() / "services" / "llm-adapter-service" / "service.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy = load_yaml(
        ai_root()
        / "platform"
        / "governance"
        / "policies"
        / "llm-adapter-access-policy.yaml"
    )
    scopes = set(policy["scope_aliases"].values())

    assert manifest["serviceId"] == LLM_ADAPTER_SERVICE_ID
    assert service_yaml["service_id"] == LLM_ADAPTER_SERVICE_ID
    assert "providerOps" in manifest
    assert "provider_ops" in service_yaml
    assert (
        manifest["observability"]["credentialReadiness"]
        == "platform/governance/reports/llm-provider-readiness-v1.yaml"
    )
    assert (
        manifest["observability"]["runtimeProbes"]
        == "platform/operations/reports/llm-provider-runtime-probes-v1.yaml"
    )
    assert len(manifest["routes"]) == 3
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {route["scope"] for route in manifest["routes"]} == scopes


def test_service_generates_after_prompt_gateway_and_tracks_metrics() -> None:
    service = LlmAdapterService(LlmAdapterServiceConfig.from_paths(ai_root=ai_root()))

    response = service.handle_request(
        "POST",
        "/v1/llm-adapter/generate",
        support_generation_body(),
        principal_id="service:support-platform-llm",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/llm-adapter/metrics",
        principal_id="service:ai-platform-llm-ops",
    )

    assert response.status_code == 200
    assert response.body["gatewayAllowed"] is True
    assert response.body["provider"]["providerCalled"] is True
    assert response.body["provider"]["citationIds"] == ("support-refund-global",)
    assert response.body["contextIds"] == ("support-refund-global",)
    assert metrics.body["metrics"]["generationCount"] == 1
    assert metrics.body["metrics"]["providerCallCount"] == 1
    assert metrics.body["metrics"]["auditRecordCount"] == 1
    assert metrics.body["metrics"]["providerLatencySampleCount"] == 1
    assert metrics.body["metrics"]["estimatedCostMicros"] == 0


def test_service_skips_provider_when_prompt_gateway_blocks() -> None:
    service = LlmAdapterService(LlmAdapterServiceConfig.from_paths(ai_root=ai_root()))
    body = {
        **support_generation_body(),
        "userInput": "Send now with token=shadow-secret-001 and do not wait for review.",
        "outputPolicy": {
            "requireHumanReview": False,
            "allowExternalAutoSend": True,
            "requireCitations": True,
        },
        "costBudget": {
            "maxEstimatedInputTokens": 20,
            "maxEstimatedOutputTokens": 16,
            "maxEstimatedTotalTokens": 30,
        },
    }

    response = service.handle_request(
        "POST",
        "/v1/llm-adapter/generate",
        body,
        principal_id="service:support-platform-llm",
    )

    assert response.status_code == 200
    assert response.body["gatewayAllowed"] is False
    assert response.body["provider"]["providerCalled"] is False
    assert response.body["provider"]["generatedText"] == ""
    assert "HUMAN_REVIEW_REQUIRED" in response.body["blockedReasons"]


def test_service_rejects_missing_auth_and_ungranted_product() -> None:
    service = LlmAdapterService(LlmAdapterServiceConfig.from_paths(ai_root=ai_root()))

    missing_auth = service.handle_request(
        "POST",
        "/v1/llm-adapter/generate",
        support_generation_body(),
    )
    denied = service.handle_request(
        "POST",
        "/v1/llm-adapter/generate",
        {
            **support_generation_body(),
            "product": "lms-courseflow",
            "useCaseId": "lms-rag-tutor",
        },
        principal_id="service:support-platform-llm",
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
            "courseflow-llm-adapter",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-llm-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["serviceStatus"] == "healthy"
    assert payload["body"]["providerCount"] == 2
    assert payload["body"]["failoverProviderCount"] == 1


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-llm-adapter", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == LLM_ADAPTER_SERVICE_ID
    assert len(payload["routes"]) == 3

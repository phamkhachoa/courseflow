from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from courseflow_ai_platform.llm_provider_adapter import (
    LLM_ADAPTER_GENERATE_SCOPE,
    LlmGenerationRequest,
    LlmProviderAdapterError,
    LlmProviderAdapterRuntime,
    LlmProviderOutput,
    LlmProviderRateLimitConfig,
    load_llm_adapter_access_policy,
    load_llm_provider_ops_policy,
)
from courseflow_ai_platform.prompt_audit import PromptAuditLedger
from courseflow_ai_platform.prompt_gateway import PromptGatewayResult


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def support_generation_body() -> dict[str, object]:
    return {
        "providerId": "contract-stub-llm-v1",
        "tenantId": "tenant-a",
        "product": "support-platform",
        "useCaseId": "support-agent-assist",
        "systemPrompt": "Draft with citations only.",
        "userInput": (
            "Email jane.doe@example.com, phone +1-415-555-0133, "
            "api key sk-live-secret and learner_id=learner-raw-123."
        ),
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


class FailingProvider:
    def generate(
        self,
        request: LlmGenerationRequest,
        gateway_result: PromptGatewayResult,
    ) -> LlmProviderOutput:
        raise RuntimeError("primary provider unavailable")


def test_llm_provider_adapter_generates_after_prompt_gateway_and_records_audit() -> None:
    audit_store = PromptAuditLedger()
    runtime = LlmProviderAdapterRuntime(ai_root(), audit_store=audit_store)
    policy = load_llm_adapter_access_policy(ai_root())
    principal = policy.resolve_principal("service:support-platform-llm")

    generation = runtime.generate(support_generation_body(), principal)
    payload = generation.to_dict()

    assert payload["gatewayAllowed"] is True
    assert payload["provider"]["providerCalled"] is True
    assert payload["provider"]["refused"] is False
    assert payload["provider"]["citationIds"] == ("support-refund-global",)
    assert "invoice verification" in payload["provider"]["generatedText"]
    assert payload["contextIds"] == ("support-refund-global",)
    assert "support-tenant-b-private" not in payload["contextIds"]
    assert len(audit_store.list_records()) == 1
    audit_payload = audit_store.list_records()[0].audit_payload
    assert "jane.doe@example.com" not in audit_payload
    assert "sk-live-secret" not in audit_payload
    metrics = runtime.snapshot_metrics().to_dict()
    assert metrics["providerCallCount"] == 1
    assert metrics["providerLatencySampleCount"] == 1
    assert metrics["estimatedCostMicros"] == 0
    assert metrics["byProviderLatencySampleCount"]["contract-stub-llm-v1"] == 1


def test_llm_provider_adapter_skips_provider_when_prompt_gateway_blocks() -> None:
    audit_store = PromptAuditLedger()
    runtime = LlmProviderAdapterRuntime(ai_root(), audit_store=audit_store)
    policy = load_llm_adapter_access_policy(ai_root())
    principal = policy.resolve_principal("service:support-platform-llm")
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

    generation = runtime.generate(body, principal)

    assert generation.gateway_result.allowed is False
    assert generation.provider_output.provider_called is False
    assert generation.provider_output.generated_text == ""
    assert "HUMAN_REVIEW_REQUIRED" in generation.gateway_result.blocked_reasons
    assert len(audit_store.list_records()) == 1
    assert "shadow-secret-001" not in audit_store.list_records()[0].audit_payload
    metrics = runtime.snapshot_metrics().to_dict()
    assert metrics["blockedCount"] == 1
    assert metrics["providerCallCount"] == 0


def test_llm_provider_adapter_enforces_product_tenant_and_provider_grants() -> None:
    runtime = LlmProviderAdapterRuntime(ai_root())
    policy = load_llm_adapter_access_policy(ai_root())
    support_principal = policy.resolve_principal("service:support-platform-llm")

    with pytest.raises(LlmProviderAdapterError, match="product is not granted"):
        runtime.generate(
            {
                **support_generation_body(),
                "product": "lms-courseflow",
                "useCaseId": "lms-rag-tutor",
            },
            support_principal,
        )

    with pytest.raises(LlmProviderAdapterError, match="provider is not granted"):
        runtime.generate(
            {
                **support_generation_body(),
                "providerId": "unregistered-provider",
            },
            support_principal,
        )


def test_llm_adapter_access_policy_exposes_generate_scope_and_provider() -> None:
    policy = load_llm_adapter_access_policy(ai_root())
    principal = policy.resolve_principal("service:lms-courseflow-llm")

    assert principal.scopes == (LLM_ADAPTER_GENERATE_SCOPE,)
    assert principal.provider_ids == (
        "contract-stub-llm-failover-v1",
        "contract-stub-llm-v1",
    )
    assert principal.prompt_gateway_principal_id == "service:lms-courseflow-prompt"
    assert policy.providers["contract-stub-llm-v1"].network_enabled is False
    assert policy.providers["contract-stub-llm-failover-v1"].network_enabled is False


def test_llm_provider_ops_policy_exposes_rate_limit_timeout_and_failover() -> None:
    ops_policy = load_llm_provider_ops_policy(ai_root())
    primary = ops_policy.resolve_provider("contract-stub-llm-v1")

    assert ops_policy.prompt_gateway_required_before_provider is True
    assert primary.request_timeout_ms == 1500
    assert primary.max_retries == 0
    assert primary.rate_limit.requests_per_minute == 120
    assert primary.rate_limit.burst == 20
    assert primary.cost.currency == "USD"
    assert primary.cost.input_micros_per_1k_tokens == 0
    assert primary.failover_provider_ids == ("contract-stub-llm-failover-v1",)


def test_llm_provider_adapter_enforces_provider_rate_limit() -> None:
    ops_policy = load_llm_provider_ops_policy(ai_root())
    primary = ops_policy.resolve_provider("contract-stub-llm-v1")
    limited_primary = replace(
        primary,
        rate_limit=LlmProviderRateLimitConfig(requests_per_minute=1, burst=0),
    )
    limited_policy = replace(
        ops_policy,
        providers={
            **ops_policy.providers,
            "contract-stub-llm-v1": limited_primary,
        },
    )
    runtime = LlmProviderAdapterRuntime(ai_root(), provider_ops_policy=limited_policy)
    policy = load_llm_adapter_access_policy(ai_root())
    principal = policy.resolve_principal("service:support-platform-llm")

    runtime.generate(support_generation_body(), principal)
    with pytest.raises(LlmProviderAdapterError, match="rate limit exceeded"):
        runtime.generate(support_generation_body(), principal)

    metrics = runtime.snapshot_metrics().to_dict()
    assert metrics["rateLimitedCount"] == 1
    assert metrics["errorCount"] == 1


def test_llm_provider_adapter_fails_over_to_configured_provider() -> None:
    audit_store = PromptAuditLedger()
    runtime = LlmProviderAdapterRuntime(
        ai_root(),
        audit_store=audit_store,
        provider_overrides={"contract-stub-llm-v1": FailingProvider()},
    )
    policy = load_llm_adapter_access_policy(ai_root())
    principal = policy.resolve_principal("service:support-platform-llm")

    generation = runtime.generate(support_generation_body(), principal)

    assert generation.provider_output.provider_id == "contract-stub-llm-failover-v1"
    assert generation.provider_output.provider_called is True
    assert generation.provider_output.refused is False
    metrics = runtime.snapshot_metrics().to_dict()
    assert metrics["failoverCount"] == 1
    assert metrics["providerErrorCount"] == 1
    assert metrics["errorCount"] == 0
    assert len(audit_store.list_records()) == 1

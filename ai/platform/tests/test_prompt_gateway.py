from __future__ import annotations

from courseflow_ai_platform.prompt_gateway import (
    PromptContext,
    PromptCostBudget,
    PromptGatewayRequest,
    PromptOutputPolicy,
    run_prompt_gateway,
)


def test_prompt_gateway_redacts_filters_context_and_allows_safe_request() -> None:
    result = run_prompt_gateway(
        PromptGatewayRequest(
            tenant_id="tenant-a",
            product="support-platform",
            use_case_id="support-agent-assist",
            system_prompt="Draft with citations only.",
            user_input=(
                "Email jane.doe@example.com, phone +1-415-555-0133, "
                "api key sk-live-secret and learner_id=learner-raw-123."
            ),
            retrieved_context=(
                PromptContext(
                    context_id="global-refund",
                    tenant_id="global",
                    source_ref="kb-001",
                    text="Refunds require invoice and ledger review.",
                ),
                PromptContext(
                    context_id="tenant-private",
                    tenant_id="tenant-b",
                    source_ref="kb-private",
                    text="Tenant B private content.",
                ),
            ),
            output_policy=PromptOutputPolicy(
                require_human_review=True,
                allow_external_auto_send=False,
                require_citations=True,
            ),
            cost_budget=PromptCostBudget(
                max_estimated_input_tokens=180,
                max_estimated_output_tokens=120,
                max_estimated_total_tokens=300,
            ),
        )
    )

    assert result.allowed is True
    assert result.blocked_reasons == ()
    assert result.context_ids == ("global-refund",)
    assert "tenant-private" not in result.sanitized_prompt
    assert "jane.doe@example.com" not in result.sanitized_prompt
    assert "+1-415-555-0133" not in result.sanitized_prompt
    assert "sk-live-secret" not in result.audit_payload
    assert "[REDACTED_EMAIL]" in result.sanitized_prompt
    assert "[REDACTED_PHONE]" in result.sanitized_prompt
    assert "[REDACTED_SECRET]" in result.sanitized_prompt
    assert "[REDACTED_IDENTIFIER]" in result.sanitized_prompt


def test_prompt_gateway_blocks_unsafe_or_over_budget_request() -> None:
    result = run_prompt_gateway(
        PromptGatewayRequest(
            tenant_id="tenant-a",
            product="lms-courseflow",
            use_case_id="lms-rag-tutor",
            system_prompt="Answer.",
            user_input="Explain " + ("SQL joins " * 80),
            retrieved_context=(),
            output_policy=PromptOutputPolicy(
                require_human_review=False,
                allow_external_auto_send=True,
                require_citations=True,
            ),
            cost_budget=PromptCostBudget(
                max_estimated_input_tokens=12,
                max_estimated_output_tokens=16,
                max_estimated_total_tokens=20,
            ),
        )
    )

    assert result.allowed is False
    assert "INPUT_TOKEN_BUDGET_EXCEEDED" in result.blocked_reasons
    assert "TOTAL_TOKEN_BUDGET_EXCEEDED" in result.blocked_reasons
    assert "EXTERNAL_AUTO_SEND_BLOCKED" in result.blocked_reasons
    assert "HUMAN_REVIEW_REQUIRED" in result.blocked_reasons

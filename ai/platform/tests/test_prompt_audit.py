from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from courseflow_ai_platform.prompt_audit import (
    JsonlPromptAuditStore,
    PromptAuditLedger,
    build_prompt_audit_record,
    contains_unredacted_sensitive_value,
)
from courseflow_ai_platform.prompt_gateway import (
    PromptContext,
    PromptCostBudget,
    PromptGatewayRequest,
    PromptOutputPolicy,
    run_prompt_gateway,
)


def test_prompt_audit_record_stores_sanitized_hashes_and_payload() -> None:
    request = PromptGatewayRequest(
        tenant_id="tenant-a",
        product="support-platform",
        use_case_id="support-agent-assist",
        system_prompt="Draft safely.",
        user_input="Reply to jane.doe@example.com with API key sk-live-secret removed.",
        retrieved_context=(
            PromptContext(
                context_id="support-refund",
                tenant_id="global",
                source_ref="kb-001",
                text="Refunds require invoice verification.",
            ),
        ),
        output_policy=PromptOutputPolicy(
            require_human_review=True,
            allow_external_auto_send=False,
            require_citations=True,
        ),
        cost_budget=PromptCostBudget(
            max_estimated_input_tokens=160,
            max_estimated_output_tokens=120,
            max_estimated_total_tokens=280,
        ),
        case_id="audit-case-001",
    )
    result = run_prompt_gateway(request)
    record = build_prompt_audit_record(
        request,
        result,
        response_text="Contact jane.doe@example.com. Bearer abc.def.ghi",
        now=datetime(2026, 6, 16, tzinfo=UTC),
    )

    assert record.tenant_id == "tenant-a"
    assert record.product == "support-platform"
    assert record.gateway_allowed is True
    assert len(record.sanitized_prompt_hash) == 64
    assert len(record.sanitized_response_hash) == 64
    assert "jane.doe@example.com" not in record.audit_payload
    assert "sk-live-secret" not in record.audit_payload
    assert "Bearer abc.def.ghi" not in record.audit_payload
    assert "[REDACTED_EMAIL]" in record.audit_payload
    assert "[REDACTED_SECRET]" in record.audit_payload
    assert contains_unredacted_sensitive_value(record.audit_payload) is False


def test_sensitive_value_detector_ignores_decimal_metrics_but_flags_contacts() -> None:
    assert contains_unredacted_sensitive_value('"latency_ms": 0.123456789') is False
    assert contains_unredacted_sensitive_value('"generated_at": "2026-06-17"') is False
    assert contains_unredacted_sensitive_value("call +1 415-555-1212") is True
    assert contains_unredacted_sensitive_value("call 0901234567") is True


def test_prompt_audit_ledger_exports_deletes_and_purges_by_policy() -> None:
    ledger = PromptAuditLedger()
    request = PromptGatewayRequest(
        tenant_id="tenant-a",
        product="lms-courseflow",
        use_case_id="lms-rag-tutor",
        system_prompt="Answer.",
        user_input="Explain SQL joins.",
        retrieved_context=(),
        output_policy=PromptOutputPolicy(
            require_human_review=True,
            allow_external_auto_send=False,
            require_citations=True,
        ),
        cost_budget=PromptCostBudget(
            max_estimated_input_tokens=80,
            max_estimated_output_tokens=80,
            max_estimated_total_tokens=160,
        ),
    )
    result = run_prompt_gateway(request)
    now = datetime(2026, 6, 16, tzinfo=UTC)

    ledger.append(build_prompt_audit_record(request, result, now=now, retention_days=1))
    assert len(ledger.export_tenant("tenant-a")) == 1
    assert ledger.purge_expired(now + timedelta(days=2)) == 1
    assert ledger.list_records() == ()

    ledger.append(build_prompt_audit_record(request, result, now=now))
    assert ledger.delete_tenant("tenant-a") == 1
    assert ledger.export_tenant("tenant-a") == ()


def test_jsonl_prompt_audit_store_persists_exports_deletes_and_purges_by_policy(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "prompt-audit.jsonl"
    store = JsonlPromptAuditStore(store_path)
    request = PromptGatewayRequest(
        tenant_id="tenant-a",
        product="support-platform",
        use_case_id="support-agent-assist",
        system_prompt="Answer with citations.",
        user_input="Summarize refund eligibility for learner_id=learner-123",
        retrieved_context=(
            PromptContext(
                context_id="support-refund",
                tenant_id="global",
                source_ref="kb-001",
                text="Refunds require invoice verification.",
            ),
        ),
        output_policy=PromptOutputPolicy(
            require_human_review=True,
            allow_external_auto_send=False,
            require_citations=True,
        ),
        cost_budget=PromptCostBudget(
            max_estimated_input_tokens=120,
            max_estimated_output_tokens=100,
            max_estimated_total_tokens=220,
        ),
    )
    result = run_prompt_gateway(request)
    now = datetime(2026, 6, 16, tzinfo=UTC)
    record = build_prompt_audit_record(request, result, now=now, retention_days=1)

    store.append(record)
    persisted_store = JsonlPromptAuditStore(store_path)
    persisted_records = persisted_store.list_records()

    assert len(persisted_records) == 1
    assert persisted_records[0].event_id == record.event_id
    assert persisted_records[0].created_at == now
    assert len(persisted_store.export_tenant("tenant-a")) == 1
    assert persisted_store.purge_expired(now + timedelta(days=2)) == 1
    assert persisted_store.list_records() == ()

    persisted_store.append(build_prompt_audit_record(request, result, now=now))
    assert persisted_store.delete_tenant("tenant-a") == 1
    assert persisted_store.export_tenant("tenant-a") == ()


def test_jsonl_prompt_audit_store_rejects_unsafe_payload(tmp_path: Path) -> None:
    store = JsonlPromptAuditStore(tmp_path / "prompt-audit.jsonl")
    request = PromptGatewayRequest(
        tenant_id="tenant-a",
        product="lms-courseflow",
        use_case_id="lms-rag-tutor",
        system_prompt="Answer.",
        user_input="Explain joins.",
        retrieved_context=(),
        output_policy=PromptOutputPolicy(
            require_human_review=True,
            allow_external_auto_send=False,
            require_citations=True,
        ),
        cost_budget=PromptCostBudget(
            max_estimated_input_tokens=80,
            max_estimated_output_tokens=80,
            max_estimated_total_tokens=160,
        ),
    )
    result = run_prompt_gateway(request)
    record = build_prompt_audit_record(request, result)
    unsafe_record = replace(record, audit_payload='{"email": "jane.doe@example.com"}')

    with pytest.raises(ValueError, match="unredacted sensitive value"):
        store.append(unsafe_record)

from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.graph_entity_service import (
    GRAPH_ENTITY_ANALYZE_SCOPE,
    GraphEntityPrivacyError,
    GraphEntityRuntime,
    GraphEntityServiceError,
    load_graph_entity_access_policy,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def graph_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-finance",
        "product": "billing-finance",
        "useCaseId": "finance-payment-fraud-scoring",
        "graphContextId": "graph-payment-1001",
        "accountHash": "acct_hash_001",
        "counterpartyHash": "counterparty_hash_007",
        "deviceFingerprintHash": "device_hash_003",
        "linkedAccountCount": 6,
        "sharedCounterpartyCount": 5,
        "velocity1h": 6,
        "velocity24h": 14,
        "priorFailedAttempts7d": 4,
        "priorChargebackCount": 1,
        "amountMinor": 1250000,
        "accountAgeDays": 4,
        "verifiedPaymentMethodsCount": 0,
        "currency": "USD",
        "paymentMethod": "card_not_present",
        "countryCode": "US",
        "riskReviewOutcome": "manual_review",
    }


def low_link_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-finance",
        "product": "billing-finance",
        "useCaseId": "finance-payment-fraud-scoring",
        "graphContextId": "graph-payment-1002",
        "accountHash": "acct_hash_002",
        "counterpartyHash": "counterparty_hash_002",
        "deviceFingerprintHash": "device_hash_002",
        "linkedAccountCount": 0,
        "sharedCounterpartyCount": 0,
    }


def test_graph_entity_analyzes_entity_links_without_adverse_action() -> None:
    root = ai_root()
    policy = load_graph_entity_access_policy(root)
    principal = policy.resolve_principal(
        "service:finance-graph-risk",
        (GRAPH_ENTITY_ANALYZE_SCOPE,),
    )
    runtime = GraphEntityRuntime(root)

    response = runtime.analyze(graph_body(), principal).to_dict()
    metrics = runtime.snapshot_metrics()

    assert response["modelId"] == "finance-payment-fraud-baseline-v1"
    assert response["graphContextId"] == "graph-payment-1001"
    assert response["adverseActionAllowed"] is False
    assert response["graphReviewRequired"] is True
    assert response["linkCount"] >= 3
    assert "SHARED_COUNTERPARTY_NETWORK" in response["reasonCodes"]
    assert any(
        link["linkType"] == "account_counterparty"
        for link in response["entityLinkEvidence"]
    )
    assert metrics.analysis_count == 1
    assert metrics.graph_review_count == 1
    assert metrics.strong_link_count >= 2
    assert metrics.medium_link_count >= 1
    assert metrics.by_use_case == {"finance-payment-fraud-scoring": 1}


def test_graph_entity_low_link_context_remains_evidence_only() -> None:
    root = ai_root()
    policy = load_graph_entity_access_policy(root)
    principal = policy.resolve_principal(
        "service:finance-graph-risk",
        (GRAPH_ENTITY_ANALYZE_SCOPE,),
    )
    runtime = GraphEntityRuntime(root)

    response = runtime.analyze(low_link_body(), principal).to_dict()

    assert response["adverseActionAllowed"] is False
    assert response["graphReviewRequired"] is False
    assert response["linkCount"] == 1
    assert response["entityLinkEvidence"][0]["strength"] == "weak"


def test_graph_entity_rejects_cross_tenant_and_direct_identifier() -> None:
    root = ai_root()
    policy = load_graph_entity_access_policy(root)
    principal = policy.resolve_principal(
        "service:finance-graph-risk",
        (GRAPH_ENTITY_ANALYZE_SCOPE,),
    )
    runtime = GraphEntityRuntime(root)

    with pytest.raises(GraphEntityServiceError, match="tenant is not granted"):
        runtime.analyze({**graph_body(), "tenantId": "tenant-ops"}, principal)

    with pytest.raises(GraphEntityPrivacyError, match="direct identifier"):
        runtime.analyze({**graph_body(), "accountId": "account-raw-001"}, principal)
    assert runtime.snapshot_metrics().direct_identifier_rejection_count == 1


def test_graph_entity_rejects_raw_hash_values() -> None:
    root = ai_root()
    policy = load_graph_entity_access_policy(root)
    principal = policy.resolve_principal(
        "service:finance-graph-risk",
        (GRAPH_ENTITY_ANALYZE_SCOPE,),
    )
    runtime = GraphEntityRuntime(root)

    with pytest.raises(GraphEntityPrivacyError, match="pseudonymous"):
        runtime.analyze({**graph_body(), "accountHash": "payer@example.com"}, principal)


def test_graph_entity_policy_exposes_finance_graph_grant_only() -> None:
    policy = load_graph_entity_access_policy(ai_root())
    principal = policy.resolve_principal(
        "service:finance-graph-risk",
        (GRAPH_ENTITY_ANALYZE_SCOPE,),
    )

    assert principal.product_ids == ("billing-finance",)
    assert principal.use_case_ids == ("finance-payment-fraud-scoring",)
    assert "tenant-finance" in principal.tenant_ids

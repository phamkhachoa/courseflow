from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.payment_fraud_service import (
    PAYMENT_FRAUD_SCORE_SCOPE,
    PaymentFraudPrivacyError,
    PaymentFraudRuntime,
    PaymentFraudServiceError,
    load_payment_fraud_access_policy,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def high_risk_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-finance",
        "product": "billing-finance",
        "useCaseId": "finance-payment-fraud-scoring",
        "paymentId": "pay-001",
        "accountHash": "acct_hash_001",
        "counterpartyHash": "cp_hash_001",
        "amountMinor": 1_250_000,
        "currency": "USD",
        "paymentMethod": "card_not_present",
        "countryCode": "VN",
        "deviceFingerprintHash": "dev_hash_001",
        "velocity1h": 6,
        "velocity24h": 16,
        "priorFailedAttempts7d": 4,
        "accountAgeDays": 3,
        "verifiedPaymentMethodsCount": 0,
        "linkedAccountCount": 6,
        "sharedCounterpartyCount": 5,
        "priorChargebackCount": 2,
        "riskReviewOutcome": "watchlist",
    }


def low_risk_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-finance",
        "product": "billing-finance",
        "useCaseId": "finance-payment-fraud-scoring",
        "paymentId": "pay-003",
        "accountHash": "acct_hash_003",
        "counterpartyHash": "cp_hash_003",
        "amountMinor": 18_000,
        "currency": "USD",
        "paymentMethod": "ach",
        "countryCode": "US",
        "deviceFingerprintHash": "dev_hash_003",
        "velocity1h": 1,
        "velocity24h": 2,
        "priorFailedAttempts7d": 0,
        "accountAgeDays": 420,
        "verifiedPaymentMethodsCount": 2,
        "linkedAccountCount": 1,
        "sharedCounterpartyCount": 0,
        "priorChargebackCount": 0,
        "riskReviewOutcome": "clear",
    }


def test_payment_fraud_runtime_scores_high_risk_and_tracks_entity_metrics() -> None:
    root = ai_root()
    policy = load_payment_fraud_access_policy(root)
    principal = policy.resolve_principal(
        "service:billing-finance-payment-risk",
        (PAYMENT_FRAUD_SCORE_SCOPE,),
    )
    runtime = PaymentFraudRuntime(root)

    response = runtime.score(high_risk_body(), principal).to_dict()
    metrics = runtime.snapshot_metrics()

    assert response["modelId"] == "finance-payment-fraud-baseline-v1"
    assert response["riskBand"] == "high"
    assert response["requiresHumanReview"] is True
    assert response["automatedAdverseActionAllowed"] is False
    assert response["decisionPolicy"] == (
        "human_review_required_before_payment_hold_or_account_action"
    )
    assert response["tenantId"] == "tenant-finance"
    assert response["paymentId"] == "pay-001"
    assert metrics.score_count == 1
    assert metrics.high_risk_count == 1
    assert metrics.human_review_count == 1
    assert metrics.entity_link_evidence_count >= 3
    assert metrics.by_risk_band == {"high": 1}


def test_payment_fraud_runtime_scores_low_risk_without_hitl_queue() -> None:
    root = ai_root()
    policy = load_payment_fraud_access_policy(root)
    principal = policy.resolve_principal(
        "service:billing-finance-payment-risk",
        (PAYMENT_FRAUD_SCORE_SCOPE,),
    )
    runtime = PaymentFraudRuntime(root)

    response = runtime.score(low_risk_body(), principal).to_dict()

    assert response["riskBand"] == "low"
    assert response["requiresHumanReview"] is False
    assert response["recommendedActions"] == ["approve_with_monitoring"]
    assert runtime.snapshot_metrics().by_use_case == {
        "finance-payment-fraud-scoring": 1
    }


def test_payment_fraud_policy_rejects_cross_tenant_and_direct_identifier() -> None:
    root = ai_root()
    policy = load_payment_fraud_access_policy(root)
    principal = policy.resolve_principal(
        "service:billing-finance-payment-risk",
        (PAYMENT_FRAUD_SCORE_SCOPE,),
    )
    runtime = PaymentFraudRuntime(root)

    with pytest.raises(PaymentFraudServiceError, match="tenant is not granted"):
        runtime.score({**high_risk_body(), "tenantId": "tenant-lms"}, principal)

    with pytest.raises(PaymentFraudPrivacyError, match="direct identifier"):
        runtime.score({**high_risk_body(), "accountId": "acct-raw-001"}, principal)
    assert runtime.snapshot_metrics().direct_identifier_rejection_count == 1


def test_payment_fraud_policy_exposes_billing_finance_grants_only() -> None:
    policy = load_payment_fraud_access_policy(ai_root())
    principal = policy.resolve_principal(
        "service:billing-finance-payment-risk",
        (PAYMENT_FRAUD_SCORE_SCOPE,),
    )

    assert principal.product_ids == ("billing-finance",)
    assert "tenant-finance" in principal.tenant_ids
    assert principal.use_case_ids == ("finance-payment-fraud-scoring",)

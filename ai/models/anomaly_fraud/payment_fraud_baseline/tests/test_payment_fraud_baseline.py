from __future__ import annotations

import pytest

from ai.models.anomaly_fraud.payment_fraud_baseline.payment_fraud_baseline import (
    PaymentFraudRiskBaseline,
)


def test_high_risk_payment_requires_human_review_and_graph_evidence() -> None:
    prediction = PaymentFraudRiskBaseline().predict(
        {
            "tenant_id": "tenant-finance",
            "payment_id": "pay-001",
            "account_hash": "acct_hash_001",
            "counterparty_hash": "cp_hash_001",
            "amount_minor": 1_250_000,
            "currency": "USD",
            "payment_method": "card_not_present",
            "country_code": "VN",
            "device_fingerprint_hash": "dev_hash_001",
            "velocity_1h": 6,
            "velocity_24h": 16,
            "prior_failed_attempts_7d": 4,
            "account_age_days": 3,
            "verified_payment_methods_count": 0,
            "linked_account_count": 6,
            "shared_counterparty_count": 5,
            "prior_chargeback_count": 2,
            "risk_review_outcome": "watchlist",
        }
    )

    assert prediction.model_id == "finance-payment-fraud-baseline-v1"
    assert prediction.risk_band == "high"
    assert prediction.requires_human_review is True
    assert prediction.automated_adverse_action_allowed is False
    assert "HIGH_VALUE_PAYMENT" in prediction.reason_codes
    assert "SHARED_COUNTERPARTY_NETWORK" in prediction.reason_codes
    assert "queue_human_review_before_payment_hold" in prediction.recommended_actions
    assert {item.link_type for item in prediction.entity_link_evidence} >= {
        "account_counterparty",
        "account_device",
        "linked_account_cluster",
    }


def test_medium_risk_payment_routes_to_risk_analyst() -> None:
    prediction = PaymentFraudRiskBaseline().predict(
        {
            "tenant_id": "tenant-finance",
            "payment_id": "pay-002",
            "account_hash": "acct_hash_002",
            "counterparty_hash": "cp_hash_002",
            "amount_minor": 325_000,
            "currency": "USD",
            "payment_method": "virtual_card",
            "country_code": "US",
            "device_fingerprint_hash": "dev_hash_002",
            "velocity_1h": 3,
            "velocity_24h": 9,
            "prior_failed_attempts_7d": 1,
            "account_age_days": 24,
            "verified_payment_methods_count": 1,
            "linked_account_count": 2,
            "shared_counterparty_count": 2,
            "prior_chargeback_count": 0,
            "risk_review_outcome": "none",
        }
    )

    assert prediction.risk_band == "medium"
    assert prediction.requires_human_review is True
    assert "ELEVATED_PAYMENT_AMOUNT" in prediction.reason_codes
    assert "COUNTERPARTY_REUSE" in prediction.reason_codes
    assert "queue_risk_analyst_review" in prediction.recommended_actions


def test_low_risk_payment_uses_monitoring_action() -> None:
    prediction = PaymentFraudRiskBaseline().predict(
        {
            "tenant_id": "tenant-finance",
            "payment_id": "pay-003",
            "account_hash": "acct_hash_003",
            "counterparty_hash": "cp_hash_003",
            "amount_minor": 18_000,
            "currency": "USD",
            "payment_method": "ach",
            "country_code": "US",
            "device_fingerprint_hash": "dev_hash_003",
            "velocity_1h": 1,
            "velocity_24h": 2,
            "prior_failed_attempts_7d": 0,
            "account_age_days": 420,
            "verified_payment_methods_count": 2,
            "linked_account_count": 1,
            "shared_counterparty_count": 0,
            "prior_chargeback_count": 0,
            "risk_review_outcome": "clear",
        }
    )

    assert prediction.risk_band == "low"
    assert prediction.requires_human_review is False
    assert prediction.reason_codes == ("PAYMENT_RISK_LOW",)
    assert prediction.recommended_actions == ("approve_with_monitoring",)


def test_raw_account_identifier_is_rejected() -> None:
    with pytest.raises(ValueError, match="account_hash"):
        PaymentFraudRiskBaseline().predict(
            {
                "tenant_id": "tenant-finance",
                "payment_id": "pay-004",
                "account_hash": "customer@example.com",
                "counterparty_hash": "cp_hash_004",
                "amount_minor": 10_000,
                "currency": "USD",
                "payment_method": "ach",
                "country_code": "US",
                "device_fingerprint_hash": "dev_hash_004",
                "velocity_1h": 1,
                "velocity_24h": 1,
                "prior_failed_attempts_7d": 0,
                "account_age_days": 10,
                "verified_payment_methods_count": 1,
                "linked_account_count": 1,
                "shared_counterparty_count": 0,
                "prior_chargeback_count": 0,
                "risk_review_outcome": "none",
            }
        )


def test_unbounded_tenant_is_rejected() -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        PaymentFraudRiskBaseline().predict(
            {
                "tenant_id": "public",
                "payment_id": "pay-005",
                "account_hash": "acct_hash_005",
                "counterparty_hash": "cp_hash_005",
                "amount_minor": 10_000,
                "currency": "USD",
                "payment_method": "ach",
                "country_code": "US",
                "device_fingerprint_hash": "dev_hash_005",
                "velocity_1h": 1,
                "velocity_24h": 1,
                "prior_failed_attempts_7d": 0,
                "account_age_days": 10,
                "verified_payment_methods_count": 1,
                "linked_account_count": 1,
                "shared_counterparty_count": 0,
                "prior_chargeback_count": 0,
                "risk_review_outcome": "none",
            }
        )

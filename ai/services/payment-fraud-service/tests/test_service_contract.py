from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_payment_fraud_service.cli import main
from courseflow_payment_fraud_service.service import (
    PAYMENT_FRAUD_SERVICE_ID,
    PaymentFraudService,
    PaymentFraudServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


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


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (ai_root() / "services" / "payment-fraud-service" / "service.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy = load_yaml(
        ai_root()
        / "platform"
        / "governance"
        / "policies"
        / "payment-fraud-access-policy.yaml"
    )
    scopes = set(policy["scope_aliases"].values())

    assert manifest["serviceId"] == PAYMENT_FRAUD_SERVICE_ID
    assert service_yaml["service_id"] == PAYMENT_FRAUD_SERVICE_ID
    assert len(manifest["routes"]) == 3
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {route["scope"] for route in manifest["routes"]} == scopes


def test_service_scores_payment_fraud_and_tracks_metrics() -> None:
    service = PaymentFraudService(
        PaymentFraudServiceConfig.from_paths(ai_root=ai_root())
    )

    response = service.handle_request(
        "POST",
        "/v1/payment-fraud/score",
        high_risk_body(),
        principal_id="service:billing-finance-payment-risk",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/payment-fraud/metrics",
        principal_id="service:ai-platform-payment-fraud-ops",
    )

    assert response.status_code == 200
    assert response.body["modelId"] == "finance-payment-fraud-baseline-v1"
    assert response.body["riskBand"] == "high"
    assert response.body["requiresHumanReview"] is True
    assert response.body["automatedAdverseActionAllowed"] is False
    assert metrics.body["metrics"]["scoreCount"] == 1
    assert metrics.body["metrics"]["highRiskCount"] == 1
    assert metrics.body["metrics"]["byUseCase"] == {
        "finance-payment-fraud-scoring": 1
    }


def test_service_rejects_missing_auth_cross_tenant_and_direct_identifier() -> None:
    service = PaymentFraudService(
        PaymentFraudServiceConfig.from_paths(ai_root=ai_root())
    )

    missing_auth = service.handle_request(
        "POST",
        "/v1/payment-fraud/score",
        high_risk_body(),
    )
    denied = service.handle_request(
        "POST",
        "/v1/payment-fraud/score",
        {**high_risk_body(), "tenantId": "tenant-lms"},
        principal_id="service:billing-finance-payment-risk",
    )
    direct_identifier = service.handle_request(
        "POST",
        "/v1/payment-fraud/score",
        {**high_risk_body(), "accountId": "acct-raw-001"},
        principal_id="service:billing-finance-payment-risk",
    )

    assert missing_auth.status_code == 401
    assert missing_auth.body["errorCode"] == "auth_required"
    assert denied.status_code == 400
    assert "tenant is not granted" in denied.body["errorMessage"]
    assert direct_identifier.status_code == 403
    assert direct_identifier.body["errorCode"] == "privacy_control_violation"


def test_cli_health_uses_registered_ops_principal(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-payment-fraud",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-payment-fraud-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["serviceStatus"] == "healthy"
    assert payload["body"]["routeCount"] == 3


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-payment-fraud", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == PAYMENT_FRAUD_SERVICE_ID
    assert len(payload["routes"]) == 3

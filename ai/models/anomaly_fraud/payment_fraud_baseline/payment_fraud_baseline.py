from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

MODEL_ID = "finance-payment-fraud-baseline-v1"
MODEL_VERSION = "2026-06-17"
HIGH_RISK_PAYMENT_METHODS = frozenset({"card_not_present", "virtual_card", "wire"})
HIGH_RISK_REVIEW_OUTCOMES = frozenset({"manual_review", "confirmed_fraud", "watchlist"})
NORMAL_REVIEW_OUTCOMES = frozenset({"clear", "none", "approved"})


@dataclass(frozen=True, slots=True)
class PaymentFraudRiskInput:
    tenant_id: str
    payment_id: str
    account_hash: str
    counterparty_hash: str
    amount_minor: int
    currency: str
    payment_method: str
    country_code: str
    device_fingerprint_hash: str
    velocity_1h: int
    velocity_24h: int
    prior_failed_attempts_7d: int
    account_age_days: int
    verified_payment_methods_count: int
    linked_account_count: int
    shared_counterparty_count: int
    prior_chargeback_count: int
    risk_review_outcome: str = "none"

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> PaymentFraudRiskInput:
        return cls(
            tenant_id=require_non_empty_str(row, "tenant_id", "payment fraud input"),
            payment_id=require_non_empty_str(row, "payment_id", "payment fraud input"),
            account_hash=require_non_empty_str(
                row,
                "account_hash",
                "payment fraud input",
            ),
            counterparty_hash=require_non_empty_str(
                row,
                "counterparty_hash",
                "payment fraud input",
            ),
            amount_minor=require_non_negative_int(
                row,
                "amount_minor",
                "payment fraud input",
            ),
            currency=str(row.get("currency", "USD")).strip().upper() or "USD",
            payment_method=str(row.get("payment_method", "card")).strip().lower()
            or "card",
            country_code=str(row.get("country_code", "US")).strip().upper() or "US",
            device_fingerprint_hash=require_non_empty_str(
                row,
                "device_fingerprint_hash",
                "payment fraud input",
            ),
            velocity_1h=require_non_negative_int(row, "velocity_1h", "payment fraud input"),
            velocity_24h=require_non_negative_int(
                row,
                "velocity_24h",
                "payment fraud input",
            ),
            prior_failed_attempts_7d=require_non_negative_int(
                row,
                "prior_failed_attempts_7d",
                "payment fraud input",
            ),
            account_age_days=require_non_negative_int(
                row,
                "account_age_days",
                "payment fraud input",
            ),
            verified_payment_methods_count=require_non_negative_int(
                row,
                "verified_payment_methods_count",
                "payment fraud input",
            ),
            linked_account_count=require_non_negative_int(
                row,
                "linked_account_count",
                "payment fraud input",
            ),
            shared_counterparty_count=require_non_negative_int(
                row,
                "shared_counterparty_count",
                "payment fraud input",
            ),
            prior_chargeback_count=require_non_negative_int(
                row,
                "prior_chargeback_count",
                "payment fraud input",
            ),
            risk_review_outcome=str(row.get("risk_review_outcome", "none")).strip().lower()
            or "none",
        )


@dataclass(frozen=True, slots=True)
class EntityLinkEvidence:
    link_type: str
    source_entity: str
    target_entity: str
    strength: str
    reason_code: str

    def to_dict(self) -> dict[str, str]:
        return {
            "linkType": self.link_type,
            "reasonCode": self.reason_code,
            "sourceEntity": self.source_entity,
            "strength": self.strength,
            "targetEntity": self.target_entity,
        }


@dataclass(frozen=True, slots=True)
class PaymentFraudRiskPrediction:
    model_id: str
    risk_score: float
    risk_band: str
    reason_codes: tuple[str, ...]
    entity_link_evidence: tuple[EntityLinkEvidence, ...]
    recommended_actions: tuple[str, ...]
    requires_human_review: bool
    automated_adverse_action_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "automatedAdverseActionAllowed": self.automated_adverse_action_allowed,
            "entityLinkEvidence": [
                evidence.to_dict() for evidence in self.entity_link_evidence
            ],
            "modelId": self.model_id,
            "reasonCodes": list(self.reason_codes),
            "recommendedActions": list(self.recommended_actions),
            "requiresHumanReview": self.requires_human_review,
            "riskBand": self.risk_band,
            "riskScore": self.risk_score,
        }


class PaymentFraudRiskBaseline:
    """Deterministic fraud/anomaly baseline for payment risk triage."""

    model_id = MODEL_ID
    model_version = MODEL_VERSION

    def predict(
        self,
        payload: PaymentFraudRiskInput | dict[str, Any],
    ) -> PaymentFraudRiskPrediction:
        request = (
            payload
            if isinstance(payload, PaymentFraudRiskInput)
            else PaymentFraudRiskInput.from_dict(payload)
        )
        validate_request(request)

        reason_codes = derive_reason_codes(request)
        logit = -1.85
        if request.amount_minor >= 1_000_000:
            logit += 0.82
        elif request.amount_minor >= 250_000:
            logit += 0.34
        if request.velocity_1h >= 5:
            logit += 0.88
        elif request.velocity_1h >= 3:
            logit += 0.42
        if request.velocity_24h >= 12:
            logit += 0.58
        elif request.velocity_24h >= 8:
            logit += 0.25
        if request.prior_failed_attempts_7d >= 3:
            logit += 0.74
        if request.account_age_days <= 7:
            logit += 0.62
        elif request.account_age_days <= 30:
            logit += 0.28
        if request.verified_payment_methods_count == 0:
            logit += 0.54
        if request.shared_counterparty_count >= 4:
            logit += 0.72
        elif request.shared_counterparty_count >= 2:
            logit += 0.32
        if request.linked_account_count >= 5:
            logit += 0.36
        if request.prior_chargeback_count > 0:
            logit += min(0.90, 0.45 * request.prior_chargeback_count)
        if request.risk_review_outcome in HIGH_RISK_REVIEW_OUTCOMES:
            logit += 0.50
        if request.payment_method in HIGH_RISK_PAYMENT_METHODS:
            logit += 0.24
        if request.country_code != "US":
            logit += 0.18
        if request.risk_review_outcome in NORMAL_REVIEW_OUTCOMES:
            logit -= 0.18

        risk_score = round(sigmoid(logit), 6)
        risk_band = band_for_score(risk_score)
        return PaymentFraudRiskPrediction(
            model_id=MODEL_ID,
            risk_score=risk_score,
            risk_band=risk_band,
            reason_codes=tuple(sorted(reason_codes)),
            entity_link_evidence=tuple(entity_link_evidence(request, reason_codes)),
            recommended_actions=recommended_actions(risk_band, reason_codes),
            requires_human_review=risk_band in {"medium", "high"},
        )


def derive_reason_codes(request: PaymentFraudRiskInput) -> set[str]:
    reasons: set[str] = set()
    if request.amount_minor >= 1_000_000:
        reasons.add("HIGH_VALUE_PAYMENT")
    elif request.amount_minor >= 250_000:
        reasons.add("ELEVATED_PAYMENT_AMOUNT")
    if request.velocity_1h >= 5:
        reasons.add("HIGH_VELOCITY_1H")
    elif request.velocity_1h >= 3:
        reasons.add("ELEVATED_VELOCITY_1H")
    if request.velocity_24h >= 12:
        reasons.add("HIGH_VELOCITY_24H")
    if request.prior_failed_attempts_7d >= 3:
        reasons.add("FAILED_ATTEMPT_SPIKE")
    if request.account_age_days <= 7:
        reasons.add("NEW_ACCOUNT")
    elif request.account_age_days <= 30:
        reasons.add("YOUNG_ACCOUNT")
    if request.verified_payment_methods_count == 0:
        reasons.add("UNVERIFIED_PAYMENT_METHOD")
    if request.shared_counterparty_count >= 4:
        reasons.add("SHARED_COUNTERPARTY_NETWORK")
    elif request.shared_counterparty_count >= 2:
        reasons.add("COUNTERPARTY_REUSE")
    if request.linked_account_count >= 5:
        reasons.add("LINKED_ACCOUNT_CLUSTER")
    if request.prior_chargeback_count > 0:
        reasons.add("PRIOR_CHARGEBACK_HISTORY")
    if request.risk_review_outcome in HIGH_RISK_REVIEW_OUTCOMES:
        reasons.add("PRIOR_RISK_REVIEW_SIGNAL")
    if request.payment_method in HIGH_RISK_PAYMENT_METHODS:
        reasons.add("HIGH_RISK_PAYMENT_METHOD")
    if request.country_code != "US":
        reasons.add("CROSS_BORDER_PAYMENT")
    if not reasons:
        reasons.add("PAYMENT_RISK_LOW")
    return reasons


def entity_link_evidence(
    request: PaymentFraudRiskInput,
    reason_codes: set[str],
) -> list[EntityLinkEvidence]:
    evidence: list[EntityLinkEvidence] = []
    if "SHARED_COUNTERPARTY_NETWORK" in reason_codes or "COUNTERPARTY_REUSE" in reason_codes:
        strength = (
            "strong" if request.shared_counterparty_count >= 4 else "medium"
        )
        evidence.append(
            EntityLinkEvidence(
                link_type="account_counterparty",
                source_entity=request.account_hash,
                target_entity=request.counterparty_hash,
                strength=strength,
                reason_code=(
                    "SHARED_COUNTERPARTY_NETWORK"
                    if request.shared_counterparty_count >= 4
                    else "COUNTERPARTY_REUSE"
                ),
            )
        )
    if "LINKED_ACCOUNT_CLUSTER" in reason_codes:
        evidence.append(
            EntityLinkEvidence(
                link_type="linked_account_cluster",
                source_entity=request.account_hash,
                target_entity=f"cluster_size:{request.linked_account_count}",
                strength="medium",
                reason_code="LINKED_ACCOUNT_CLUSTER",
            )
        )
    if "HIGH_VELOCITY_1H" in reason_codes or "FAILED_ATTEMPT_SPIKE" in reason_codes:
        evidence.append(
            EntityLinkEvidence(
                link_type="account_device",
                source_entity=request.account_hash,
                target_entity=request.device_fingerprint_hash,
                strength="strong",
                reason_code=(
                    "FAILED_ATTEMPT_SPIKE"
                    if "FAILED_ATTEMPT_SPIKE" in reason_codes
                    else "HIGH_VELOCITY_1H"
                ),
            )
        )
    if not evidence:
        evidence.append(
            EntityLinkEvidence(
                link_type="account_payment",
                source_entity=request.account_hash,
                target_entity=request.payment_id,
                strength="weak",
                reason_code="PAYMENT_RISK_LOW",
            )
        )
    return evidence


def recommended_actions(risk_band: str, reason_codes: set[str]) -> tuple[str, ...]:
    actions: list[str] = []
    if risk_band == "high":
        actions.append("queue_human_review_before_payment_hold")
    elif risk_band == "medium":
        actions.append("queue_risk_analyst_review")
    if "SHARED_COUNTERPARTY_NETWORK" in reason_codes:
        actions.append("inspect_counterparty_entity_graph")
    if "FAILED_ATTEMPT_SPIKE" in reason_codes:
        actions.append("verify_recent_failed_attempts")
    if "PRIOR_CHARGEBACK_HISTORY" in reason_codes:
        actions.append("review_chargeback_history")
    if "UNVERIFIED_PAYMENT_METHOD" in reason_codes:
        actions.append("request_payment_method_verification")
    if not actions:
        actions.append("approve_with_monitoring")
    return tuple(dict.fromkeys(actions))


def band_for_score(risk_score: float) -> str:
    if risk_score >= 0.70:
        return "high"
    if risk_score >= 0.45:
        return "medium"
    return "low"


def validate_request(request: PaymentFraudRiskInput) -> None:
    if not request.tenant_id.startswith("tenant-"):
        raise ValueError("tenant_id must identify a bounded tenant")
    for key, value in {
        "account_hash": request.account_hash,
        "counterparty_hash": request.counterparty_hash,
        "device_fingerprint_hash": request.device_fingerprint_hash,
    }.items():
        if looks_like_raw_identifier(value):
            raise ValueError(f"{key} must be a pseudonymous hash, not a raw identifier")
    if len(request.currency) != 3:
        raise ValueError("currency must be an ISO-4217 code")
    if len(request.country_code) != 2:
        raise ValueError("country_code must be an ISO-3166 alpha-2 code")


def looks_like_raw_identifier(value: str) -> bool:
    normalized = value.strip()
    return "@" in normalized or " " in normalized or normalized.startswith("+")


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def require_non_empty_str(row: dict[str, Any], key: str, context: str) -> str:
    value = str(row.get(key, "")).strip()
    if not value:
        raise ValueError(f"{context} {key} is required")
    return value


def require_non_negative_int(row: dict[str, Any], key: str, context: str) -> int:
    value = row.get(key)
    if value is None:
        raise ValueError(f"{context} {key} is required")
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{context} {key} must be an integer")
    if value < 0:
        raise ValueError(f"{context} {key} must be non-negative")
    return value

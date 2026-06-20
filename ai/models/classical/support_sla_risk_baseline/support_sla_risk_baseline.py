from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

MODEL_ID = "support-sla-risk-baseline-v1"
MODEL_VERSION = "2026-06-17"
HIGH_PRIORITY = frozenset({"p0", "p1", "urgent", "high"})
ACTIVE_STATUSES = frozenset({"open", "new", "pending", "in_progress", "waiting_customer"})
PREMIUM_TIERS = frozenset({"enterprise", "premium", "strategic"})


@dataclass(frozen=True, slots=True)
class SupportSlaRiskInput:
    tenant_id: str
    case_id: str
    priority: str
    status: str
    minutes_until_sla_due: int
    age_minutes: int
    public_comment_count: int
    internal_note_count: int
    assigned_team_available: bool
    customer_tier: str = "standard"
    reopen_count: int = 0
    product_area: str = "general"

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> SupportSlaRiskInput:
        return cls(
            tenant_id=require_non_empty_str(row, "tenant_id", "support SLA risk input"),
            case_id=require_non_empty_str(row, "case_id", "support SLA risk input"),
            priority=str(row.get("priority", "p2")).strip().lower() or "p2",
            status=str(row.get("status", "open")).strip().lower() or "open",
            minutes_until_sla_due=require_int(
                row,
                "minutes_until_sla_due",
                "support SLA risk input",
            ),
            age_minutes=require_non_negative_int(
                row,
                "age_minutes",
                "support SLA risk input",
            ),
            public_comment_count=require_non_negative_int(
                row,
                "public_comment_count",
                "support SLA risk input",
            ),
            internal_note_count=require_non_negative_int(
                row,
                "internal_note_count",
                "support SLA risk input",
            ),
            assigned_team_available=bool(row.get("assigned_team_available", False)),
            customer_tier=str(row.get("customer_tier", "standard")).strip().lower()
            or "standard",
            reopen_count=require_non_negative_int(
                row,
                "reopen_count",
                "support SLA risk input",
            ),
            product_area=str(row.get("product_area", "general")).strip().lower()
            or "general",
        )


@dataclass(frozen=True, slots=True)
class SupportSlaRiskPrediction:
    model_id: str
    risk_score: float
    risk_band: str
    reason_codes: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    requires_human_review: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "modelId": self.model_id,
            "reasonCodes": list(self.reason_codes),
            "recommendedActions": list(self.recommended_actions),
            "requiresHumanReview": self.requires_human_review,
            "riskBand": self.risk_band,
            "riskScore": self.risk_score,
        }


class SupportSlaRiskBaseline:
    """Deterministic explainable baseline for support SLA breach risk."""

    model_id = MODEL_ID
    model_version = MODEL_VERSION

    def predict(
        self,
        payload: SupportSlaRiskInput | dict[str, Any],
    ) -> SupportSlaRiskPrediction:
        request = (
            payload
            if isinstance(payload, SupportSlaRiskInput)
            else SupportSlaRiskInput.from_dict(payload)
        )
        validate_request(request)

        reason_codes = derive_reason_codes(request)
        logit = -1.35
        if request.priority in HIGH_PRIORITY:
            logit += 0.85
        if request.minutes_until_sla_due < 0:
            logit += 1.45
        elif request.minutes_until_sla_due <= 60:
            logit += 1.05
        elif request.minutes_until_sla_due <= 240:
            logit += 0.42
        if request.age_minutes >= 720:
            logit += 0.48
        elif request.age_minutes >= 360:
            logit += 0.24
        if request.public_comment_count >= 5:
            logit += 0.26
        if request.internal_note_count == 0 and request.age_minutes >= 120:
            logit += 0.34
        if not request.assigned_team_available:
            logit += 0.62
        if request.reopen_count > 0:
            logit += min(0.56, 0.28 * request.reopen_count)
        if request.customer_tier in PREMIUM_TIERS:
            logit += 0.18
        if request.status not in ACTIVE_STATUSES:
            logit -= 0.85

        risk_score = round(sigmoid(logit), 6)
        risk_band = band_for_score(risk_score)
        return SupportSlaRiskPrediction(
            model_id=MODEL_ID,
            risk_score=risk_score,
            risk_band=risk_band,
            reason_codes=tuple(sorted(reason_codes)),
            recommended_actions=recommended_actions(risk_band, reason_codes),
            requires_human_review=risk_band in {"medium", "high"},
        )


def derive_reason_codes(request: SupportSlaRiskInput) -> set[str]:
    reasons: set[str] = set()
    if request.priority in HIGH_PRIORITY:
        reasons.add("HIGH_PRIORITY_CASE")
    if request.minutes_until_sla_due < 0:
        reasons.add("SLA_ALREADY_BREACHED")
    elif request.minutes_until_sla_due <= 60:
        reasons.add("SLA_DUE_SOON")
    elif request.minutes_until_sla_due <= 240:
        reasons.add("SLA_WINDOW_COMPRESSED")
    if request.age_minutes >= 720:
        reasons.add("LONG_RUNNING_CASE")
    if request.public_comment_count >= 5:
        reasons.add("CUSTOMER_ACTIVITY_SPIKE")
    if request.internal_note_count == 0 and request.age_minutes >= 120:
        reasons.add("NO_INTERNAL_PROGRESS")
    if not request.assigned_team_available:
        reasons.add("NO_AVAILABLE_TEAM_CAPACITY")
    if request.reopen_count > 0:
        reasons.add("REOPENED_CASE")
    if request.customer_tier in PREMIUM_TIERS:
        reasons.add("PREMIUM_CUSTOMER")
    if not reasons:
        reasons.add("SLA_RISK_LOW")
    return reasons


def recommended_actions(risk_band: str, reason_codes: set[str]) -> tuple[str, ...]:
    actions: list[str] = []
    if risk_band == "high":
        actions.append("page_supervisor_for_review")
    if "NO_AVAILABLE_TEAM_CAPACITY" in reason_codes:
        actions.append("rebalance_team_capacity")
    if "NO_INTERNAL_PROGRESS" in reason_codes:
        actions.append("request_internal_update")
    if "SLA_DUE_SOON" in reason_codes or "SLA_ALREADY_BREACHED" in reason_codes:
        actions.append("prioritize_sla_response")
    if "PREMIUM_CUSTOMER" in reason_codes:
        actions.append("notify_account_owner")
    if not actions:
        actions.append("monitor_standard_queue")
    return tuple(dict.fromkeys(actions))


def band_for_score(risk_score: float) -> str:
    if risk_score >= 0.7:
        return "high"
    if risk_score >= 0.45:
        return "medium"
    return "low"


def validate_request(request: SupportSlaRiskInput) -> None:
    if not request.tenant_id.startswith("tenant-"):
        raise ValueError("tenant_id must identify a bounded tenant")
    if not request.case_id:
        raise ValueError("case_id is required")
    if request.status not in ACTIVE_STATUSES and request.status not in {"closed", "resolved"}:
        raise ValueError("status must be an allowed support case lifecycle state")


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def require_non_empty_str(row: dict[str, Any], key: str, context: str) -> str:
    value = str(row.get(key, "")).strip()
    if not value:
        raise ValueError(f"{context} {key} is required")
    return value


def require_int(row: dict[str, Any], key: str, context: str) -> int:
    value = row.get(key)
    if value is None:
        raise ValueError(f"{context} {key} is required")
    return int(value)


def require_non_negative_int(row: dict[str, Any], key: str, context: str) -> int:
    value = require_int(row, key, context)
    if value < 0:
        raise ValueError(f"{context} {key} cannot be negative")
    return value

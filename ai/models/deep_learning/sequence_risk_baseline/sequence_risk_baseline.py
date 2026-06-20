from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

MODEL_ID = "sequence-risk-baseline-v1"
MODEL_VERSION = "2026-06-17"

EVENT_WEIGHTS = {
    "assignment_submitted": -0.18,
    "help_request": 0.08,
    "inactive_day": 0.2,
    "late_submission": 0.18,
    "low_quiz_score": 0.24,
    "missed_deadline": 0.34,
    "quiz_passed": -0.2,
    "video_completed": -0.1,
}

NEGATIVE_EVENTS = frozenset(
    {
        "help_request",
        "inactive_day",
        "late_submission",
        "low_quiz_score",
        "missed_deadline",
    }
)
POSITIVE_EVENTS = frozenset({"assignment_submitted", "quiz_passed", "video_completed"})


@dataclass(frozen=True, slots=True)
class SequenceRiskEvent:
    event_type: str
    days_ago: int
    score: float | None = None
    engagement_minutes: int = 0

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> SequenceRiskEvent:
        event_type = require_non_empty_str(row, "event_type", "sequence risk event")
        days_ago = require_non_negative_int(row, "days_ago", f"sequence event {event_type}")
        score = optional_float(row, "score", f"sequence event {event_type}")
        engagement_minutes = int(row.get("engagement_minutes", 0) or 0)
        if engagement_minutes < 0:
            raise ValueError(f"sequence event {event_type} engagement_minutes cannot be negative")
        return cls(
            event_type=event_type,
            days_ago=days_ago,
            score=score,
            engagement_minutes=engagement_minutes,
        )


@dataclass(frozen=True, slots=True)
class SequenceRiskInput:
    tenant_id: str
    learner_principal_hash: str
    course_id: str
    feature_snapshot_at: str
    events: tuple[SequenceRiskEvent, ...]

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> SequenceRiskInput:
        events = row.get("events")
        if not isinstance(events, list) or not events:
            raise ValueError("sequence risk input must include at least one event")
        return cls(
            tenant_id=require_non_empty_str(row, "tenant_id", "sequence risk input"),
            learner_principal_hash=require_non_empty_str(
                row,
                "learner_principal_hash",
                "sequence risk input",
            ),
            course_id=require_non_empty_str(row, "course_id", "sequence risk input"),
            feature_snapshot_at=require_non_empty_str(
                row,
                "feature_snapshot_at",
                "sequence risk input",
            ),
            events=tuple(SequenceRiskEvent.from_dict(event) for event in events),
        )


@dataclass(frozen=True, slots=True)
class SequenceRiskPrediction:
    model_id: str
    risk_score: float
    risk_band: str
    reason_codes: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    hidden_state: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "hiddenState": self.hidden_state,
            "modelId": self.model_id,
            "reasonCodes": list(self.reason_codes),
            "recommendedActions": list(self.recommended_actions),
            "riskBand": self.risk_band,
            "riskScore": self.risk_score,
        }


class SequenceRiskBaseline:
    """Small recurrent scorer for sequence-risk runtime contract tests."""

    model_id = MODEL_ID
    model_version = MODEL_VERSION

    def predict(self, payload: SequenceRiskInput | dict[str, Any]) -> SequenceRiskPrediction:
        request = payload if isinstance(payload, SequenceRiskInput) else SequenceRiskInput.from_dict(payload)
        validate_request(request)

        hidden_state = 0.0
        negative_event_count = 0
        positive_event_count = 0
        recent_negative_count = 0
        low_score_count = 0
        reason_codes: set[str] = set()

        for event in sorted(request.events, key=lambda row: row.days_ago, reverse=True):
            event_weight = EVENT_WEIGHTS.get(event.event_type, 0.0)
            recency = 1.0 / (1.0 + event.days_ago)
            score_adjustment = score_effect(event)
            engagement_adjustment = engagement_effect(event)
            hidden_state = math.tanh(
                0.72 * hidden_state
                + (event_weight + score_adjustment + engagement_adjustment)
                * (0.72 + recency)
            )

            if event.event_type in NEGATIVE_EVENTS:
                negative_event_count += 1
                if event.days_ago <= 3:
                    recent_negative_count += 1
            if event.event_type in POSITIVE_EVENTS:
                positive_event_count += 1
            if event.score is not None and event.score < 0.6:
                low_score_count += 1

            reason_codes.update(event_reason_codes(event))

        logit = (
            -0.42
            + 2.05 * hidden_state
            + 0.16 * negative_event_count
            + 0.18 * recent_negative_count
            + 0.12 * low_score_count
            - 0.12 * positive_event_count
        )
        risk_score = round(sigmoid(logit), 6)
        risk_band = band_for_score(risk_score)
        actions = recommended_actions(risk_band, reason_codes)
        if risk_band == "low" and positive_event_count:
            reason_codes.add("POSITIVE_PROGRESS")

        return SequenceRiskPrediction(
            model_id=self.model_id,
            risk_score=risk_score,
            risk_band=risk_band,
            reason_codes=tuple(sorted(reason_codes)),
            recommended_actions=actions,
            hidden_state=round(hidden_state, 6),
        )


def validate_request(request: SequenceRiskInput) -> None:
    if request.tenant_id.lower() in {"", "unknown", "public"}:
        raise ValueError("tenant_id must identify a bounded tenant")
    if len(request.learner_principal_hash) < 8:
        raise ValueError("learner_principal_hash must be pseudonymous and stable")
    if not request.course_id:
        raise ValueError("course_id is required")


def score_effect(event: SequenceRiskEvent) -> float:
    if event.score is None:
        return 0.0
    bounded_score = max(0.0, min(1.0, event.score))
    if bounded_score < 0.6:
        return (0.6 - bounded_score) * 0.55
    return -(bounded_score - 0.6) * 0.22


def engagement_effect(event: SequenceRiskEvent) -> float:
    if event.event_type == "inactive_day":
        return 0.08
    if event.engagement_minutes >= 45:
        return -0.08
    if 0 < event.engagement_minutes < 10:
        return 0.04
    return 0.0


def event_reason_codes(event: SequenceRiskEvent) -> set[str]:
    reasons: set[str] = set()
    if event.event_type == "missed_deadline":
        reasons.add("MISSED_DEADLINE")
    if event.event_type == "late_submission":
        reasons.add("LATE_SUBMISSION")
    if event.event_type == "inactive_day" and event.days_ago <= 5:
        reasons.add("RECENT_INACTIVITY")
    if event.event_type == "help_request":
        reasons.add("HELP_REQUEST_SPIKE")
    if event.score is not None and event.score < 0.6:
        reasons.add("LOW_ASSESSMENT_SCORE")
    return reasons


def band_for_score(risk_score: float) -> str:
    if risk_score >= 0.7:
        return "high"
    if risk_score >= 0.45:
        return "medium"
    return "low"


def recommended_actions(risk_band: str, reason_codes: set[str]) -> tuple[str, ...]:
    actions: list[str] = []
    if risk_band == "high":
        actions.append("advisor_outreach")
    if risk_band in {"high", "medium"}:
        actions.append("recommend_practice_path")
    if "LOW_ASSESSMENT_SCORE" in reason_codes:
        actions.append("assign_remediation_quiz")
    if "RECENT_INACTIVITY" in reason_codes:
        actions.append("send_reengagement_prompt")
    if not actions:
        actions.append("continue_monitoring")
    return tuple(actions)


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def require_non_empty_str(row: dict[str, Any], key: str, owner: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{owner} must define non-empty string field {key}")
    return value.strip()


def require_non_negative_int(row: dict[str, Any], key: str, owner: str) -> int:
    value = row.get(key)
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{owner} must define non-negative integer field {key}")
    return value


def optional_float(row: dict[str, Any], key: str, owner: str) -> float | None:
    value = row.get(key)
    if value is None:
        return None
    if not isinstance(value, int | float):
        raise ValueError(f"{owner} field {key} must be numeric when present")
    return float(value)

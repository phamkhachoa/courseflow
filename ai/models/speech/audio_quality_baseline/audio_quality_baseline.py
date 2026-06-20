from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

MODEL_ID = "speech-quality-baseline-v1"
SEGMENT_TEXT_MAX_CHARS = 220
RAW_AUDIO_URI_MARKERS = ("s3://", "gs://", "http://", "https://", "file://")
PII_PATTERNS = (
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b(?:\+?\d[\s-]?){9,}\b"),
    re.compile(r"\b(?:card|credit card|ssn|social security|passport)\b", re.IGNORECASE),
)


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    speaker_role: str
    text: str
    start_ms: int
    end_ms: int
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> TranscriptSegment:
        return cls(
            speaker_role=require_non_empty_str(row, "speaker_role", "segment"),
            text=require_non_empty_str(row, "text", "segment"),
            start_ms=require_non_negative_int(row, "start_ms", "segment"),
            end_ms=require_non_negative_int(row, "end_ms", "segment"),
            confidence=require_bounded_float(
                {"confidence": row.get("confidence", 1.0)},
                "confidence",
                "segment",
            ),
        )


@dataclass(frozen=True, slots=True)
class AudioQualityInput:
    tenant_id: str
    audio_id: str
    audio_checksum: str
    transcript_language: str
    duration_seconds: int
    consent_captured: bool
    raw_audio_uri: str
    segments: tuple[TranscriptSegment, ...]
    product_hint: str = ""

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> AudioQualityInput:
        segments = row.get("segments")
        if not isinstance(segments, list):
            raise ValueError("segments must be a list")
        return cls(
            tenant_id=require_non_empty_str(row, "tenant_id", "audio quality input"),
            audio_id=require_non_empty_str(row, "audio_id", "audio quality input"),
            audio_checksum=require_non_empty_str(
                row,
                "audio_checksum",
                "audio quality input",
            ),
            transcript_language=str(row.get("transcript_language", "en")).strip() or "en",
            duration_seconds=require_positive_int(
                row,
                "duration_seconds",
                "audio quality input",
            ),
            consent_captured=bool(row.get("consent_captured", False)),
            raw_audio_uri=str(row.get("raw_audio_uri", "")).strip(),
            segments=tuple(TranscriptSegment.from_dict(segment) for segment in segments),
            product_hint=str(row.get("product_hint", "")).strip(),
        )


@dataclass(frozen=True, slots=True)
class AudioQualityPrediction:
    model_id: str
    intent: str
    quality_band: str
    compliance_risk: str
    transcript_summary_terms: tuple[str, ...]
    evidence_terms: tuple[str, ...]
    confidence: float
    reason_codes: tuple[str, ...]
    requires_human_review: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "complianceRisk": self.compliance_risk,
            "confidence": self.confidence,
            "evidenceTerms": list(self.evidence_terms),
            "intent": self.intent,
            "modelId": self.model_id,
            "qualityBand": self.quality_band,
            "reasonCodes": list(self.reason_codes),
            "requiresHumanReview": self.requires_human_review,
            "transcriptSummaryTerms": list(self.transcript_summary_terms),
        }


class AudioQualityBaseline:
    """Deterministic transcript-segment baseline for speech/audio governance."""

    model_id = MODEL_ID

    def predict(
        self,
        payload: AudioQualityInput | dict[str, Any],
    ) -> AudioQualityPrediction:
        request = (
            payload
            if isinstance(payload, AudioQualityInput)
            else AudioQualityInput.from_dict(payload)
        )
        validate_request(request)
        text = normalize_text(" ".join(segment.text for segment in request.segments))
        lowered = text.lower()

        intent = classify_intent(lowered, request.product_hint)
        quality_band = classify_quality_band(request, lowered)
        compliance_risk = classify_compliance_risk(request, lowered)
        reason_codes = derive_reason_codes(request, lowered, intent, quality_band, compliance_risk)
        confidence = score_confidence(request, quality_band, compliance_risk)
        requires_human_review = should_require_human_review(
            quality_band,
            compliance_risk,
            confidence,
            reason_codes,
        )
        if requires_human_review:
            reason_codes.add("HUMAN_REVIEW_REQUIRED")

        return AudioQualityPrediction(
            model_id=MODEL_ID,
            intent=intent,
            quality_band=quality_band,
            compliance_risk=compliance_risk,
            transcript_summary_terms=summary_terms(lowered, intent),
            evidence_terms=evidence_terms(request.segments, intent, reason_codes),
            confidence=round(confidence, 6),
            reason_codes=tuple(sorted(reason_codes)),
            requires_human_review=requires_human_review,
        )


def validate_request(request: AudioQualityInput) -> None:
    if not request.tenant_id.startswith("tenant-"):
        raise ValueError("tenant_id must be a bounded tenant identifier")
    if len(request.audio_checksum) < 12:
        raise ValueError("audio_checksum is required")
    if request.duration_seconds > 4 * 60 * 60:
        raise ValueError("duration_seconds must be bounded")
    if request.raw_audio_uri:
        raise ValueError("raw_audio_uri is not allowed for transcript-only baseline")
    if not request.segments:
        raise ValueError("transcript segments are required")
    for segment in request.segments:
        if segment.end_ms <= segment.start_ms:
            raise ValueError("segment end_ms must be greater than start_ms")
        if len(segment.text) > SEGMENT_TEXT_MAX_CHARS:
            raise ValueError("segment text must be bounded")
        if segment.speaker_role not in {"agent", "customer", "learner", "instructor", "system"}:
            raise ValueError("segment speaker_role is not supported")


def classify_intent(text: str, product_hint: str) -> str:
    if any(term in text for term in ("password", "login", "account", "mfa")):
        return "account_access"
    if any(term in text for term in ("refund", "invoice", "payment", "billing")):
        return "billing_support"
    if any(term in text for term in ("assignment", "course", "lesson", "quiz")):
        return "learning_support"
    if "lms" in product_hint.lower():
        return "learning_support"
    return "general_support"


def classify_quality_band(request: AudioQualityInput, text: str) -> str:
    avg_confidence = sum(segment.confidence for segment in request.segments) / len(request.segments)
    if avg_confidence < 0.72:
        return "low_confidence"
    if any(term in text for term in ("angry", "frustrated", "complaint", "manager", "cancel")):
        return "escalation_review"
    if request.duration_seconds > 1800:
        return "long_call_review"
    return "good"


def classify_compliance_risk(request: AudioQualityInput, text: str) -> str:
    if has_raw_pii(text):
        return "raw_pii_detected"
    if not request.consent_captured:
        return "consent_missing"
    if any(term in text for term in ("legal", "lawsuit", "regulator", "chargeback")):
        return "regulated_review"
    return "low"


def derive_reason_codes(
    request: AudioQualityInput,
    text: str,
    intent: str,
    quality_band: str,
    compliance_risk: str,
) -> set[str]:
    reasons = {
        "TRANSCRIPT_ONLY_BASELINE",
        "INTENT_" + intent.upper(),
        "QUALITY_" + quality_band.upper(),
        "COMPLIANCE_" + compliance_risk.upper(),
    }
    if request.consent_captured:
        reasons.add("CONSENT_CAPTURED")
    else:
        reasons.add("CONSENT_MISSING")
    if has_raw_pii(text):
        reasons.add("RAW_AUDIO_PII_DETECTED")
    if quality_band in {"low_confidence", "escalation_review", "long_call_review"}:
        reasons.add("QUALITY_REVIEW_REQUIRED")
    return reasons


def score_confidence(
    request: AudioQualityInput,
    quality_band: str,
    compliance_risk: str,
) -> float:
    avg_confidence = sum(segment.confidence for segment in request.segments) / len(request.segments)
    score = avg_confidence
    if quality_band != "good":
        score -= 0.08
    if compliance_risk != "low":
        score -= 0.12
    return max(0.0, min(1.0, score))


def should_require_human_review(
    quality_band: str,
    compliance_risk: str,
    confidence: float,
    reason_codes: set[str],
) -> bool:
    return (
        quality_band != "good"
        or compliance_risk != "low"
        or confidence < 0.75
        or "RAW_AUDIO_PII_DETECTED" in reason_codes
    )


def summary_terms(text: str, intent: str) -> tuple[str, ...]:
    candidates = {
        "account_access": ("login", "password", "mfa", "account"),
        "billing_support": ("refund", "invoice", "payment", "billing"),
        "learning_support": ("assignment", "course", "lesson", "quiz"),
        "general_support": ("support", "issue", "resolved", "help"),
    }[intent]
    return tuple(term for term in candidates if term in text)


def evidence_terms(
    segments: tuple[TranscriptSegment, ...],
    intent: str,
    reason_codes: set[str],
) -> tuple[str, ...]:
    transcript_text = " ".join(segment.text.lower() for segment in segments)
    intent_terms = set(summary_terms(transcript_text, intent))
    snippets: list[str] = []
    for segment in segments:
        lowered = segment.text.lower()
        if any(term in lowered for term in intent_terms) or (
            "RAW_AUDIO_PII_DETECTED" in reason_codes and has_raw_pii(lowered)
        ):
            snippets.append(segment.text)
    return tuple(snippets[:4])


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def has_raw_pii(text: str) -> bool:
    return any(pattern.search(text) for pattern in PII_PATTERNS)


def require_non_empty_str(row: dict[str, Any], key: str, owner: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{owner} must define non-empty {key}")
    return value.strip()


def require_non_negative_int(row: dict[str, Any], key: str, owner: str) -> int:
    value = row.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{owner} must define non-negative integer {key}")
    return value


def require_positive_int(row: dict[str, Any], key: str, owner: str) -> int:
    value = require_non_negative_int(row, key, owner)
    if value <= 0:
        raise ValueError(f"{owner} must define positive integer {key}")
    return value


def require_bounded_float(row: dict[str, Any], key: str, owner: str) -> float:
    value = row.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{owner} must define numeric {key}")
    number = float(value)
    if number < 0.0 or number > 1.0:
        raise ValueError(f"{owner} {key} must be between 0 and 1")
    return number

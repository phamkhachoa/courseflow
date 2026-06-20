from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SupportAgentAssistInput:
    tenant_id: str
    case_id: str
    subject: str
    latest_message: str
    product_area: str = ""
    priority: str = ""
    language: str = "en"


@dataclass(frozen=True, slots=True)
class SupportAgentAssistOutput:
    summary: str
    intent: str
    priority_signal: str
    retrieval_query: str
    suggested_reply: str
    confidence: float
    reason_codes: tuple[str, ...]
    requires_human_review: bool = True


class SupportAgentAssistBaseline:
    """Deterministic baseline for support case assistant workflows."""

    def assist(self, request: SupportAgentAssistInput) -> SupportAgentAssistOutput:
        tenant_id = request.tenant_id.strip()
        case_id = request.case_id.strip()
        if not tenant_id:
            raise ValueError("tenant_id is required")
        if not case_id:
            raise ValueError("case_id is required")

        subject = normalize_text(request.subject)
        message = normalize_text(request.latest_message)
        if not subject and not message:
            raise ValueError("subject or latest_message is required")

        combined = f"{subject}. {message}".strip(". ")
        intent, intent_reason = classify_intent(combined)
        priority_signal, priority_reason = classify_priority(combined, request.priority)
        summary = summarize_case(subject, message)
        retrieval_query = build_retrieval_query(intent, request.product_area, subject, message)
        suggested_reply = build_safe_reply(intent, summary)
        confidence = confidence_for(intent, priority_signal)

        return SupportAgentAssistOutput(
            summary=summary,
            intent=intent,
            priority_signal=priority_signal,
            retrieval_query=retrieval_query,
            suggested_reply=suggested_reply,
            confidence=confidence,
            reason_codes=(intent_reason, priority_reason, "HUMAN_REVIEW_REQUIRED"),
            requires_human_review=True,
        )


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def classify_intent(text: str) -> tuple[str, str]:
    lowered = text.lower()
    keyword_groups = [
        ("billing", "INTENT_BILLING_KEYWORD", ("invoice", "payment", "refund", "charge", "paid")),
        ("access", "INTENT_ACCESS_KEYWORD", ("login", "password", "mfa", "permission", "access")),
        ("technical", "INTENT_TECHNICAL_KEYWORD", ("error", "bug", "crash", "api", "timeout")),
        ("account", "INTENT_ACCOUNT_KEYWORD", ("profile", "email", "account", "organization")),
    ]
    for intent, reason, keywords in keyword_groups:
        if any(keyword in lowered for keyword in keywords):
            return intent, reason
    return "general", "INTENT_GENERAL_FALLBACK"


def classify_priority(text: str, declared_priority: str) -> tuple[str, str]:
    lowered = f"{text} {declared_priority}".lower()
    if any(keyword in lowered for keyword in ("urgent", "down", "outage", "security", "breach")):
        return "high", "PRIORITY_HIGH_KEYWORD"
    if any(keyword in lowered for keyword in ("blocked", "cannot work", "deadline", "fail", "failed")):
        return "medium", "PRIORITY_MEDIUM_KEYWORD"
    if declared_priority.strip().lower() in {"high", "urgent", "p1"}:
        return "high", "PRIORITY_DECLARED_HIGH"
    return "normal", "PRIORITY_NORMAL_FALLBACK"


def summarize_case(subject: str, message: str) -> str:
    text = subject if subject else message
    if subject and message:
        text = f"{subject}: {message}"
    return truncate(text, 220)


def build_retrieval_query(intent: str, product_area: str, subject: str, message: str) -> str:
    terms = [intent]
    if product_area.strip():
        terms.append(normalize_text(product_area))
    source = subject or message
    terms.extend(token for token in re.findall(r"[A-Za-z0-9_-]{4,}", source)[:6])
    return " ".join(dict.fromkeys(terms))


def build_safe_reply(intent: str, summary: str) -> str:
    return (
        "Draft for agent review: acknowledge the customer's "
        f"{intent} issue, confirm the understood summary, and provide the next safe step. "
        f"Summary: {summary}"
    )


def confidence_for(intent: str, priority_signal: str) -> float:
    score = 0.58
    if intent != "general":
        score += 0.18
    if priority_signal != "normal":
        score += 0.08
    return round(min(score, 0.84), 2)


def truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."

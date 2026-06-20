from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptContext:
    context_id: str
    tenant_id: str
    source_ref: str
    text: str


@dataclass(frozen=True, slots=True)
class PromptCostBudget:
    max_estimated_input_tokens: int
    max_estimated_output_tokens: int
    max_estimated_total_tokens: int


@dataclass(frozen=True, slots=True)
class PromptOutputPolicy:
    require_human_review: bool
    allow_external_auto_send: bool
    require_citations: bool


@dataclass(frozen=True, slots=True)
class PromptGatewayRequest:
    tenant_id: str
    product: str
    use_case_id: str
    system_prompt: str
    user_input: str
    retrieved_context: tuple[PromptContext, ...]
    output_policy: PromptOutputPolicy
    cost_budget: PromptCostBudget
    case_id: str | None = None


@dataclass(frozen=True, slots=True)
class PromptGatewayResult:
    allowed: bool
    blocked_reasons: tuple[str, ...]
    sanitized_prompt: str
    audit_payload: str
    context_ids: tuple[str, ...]
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_total_tokens: int
    require_human_review: bool

    def to_dict(self) -> dict[str, bool | int | str | tuple[str, ...]]:
        return {
            "allowed": self.allowed,
            "auditPayload": self.audit_payload,
            "blockedReasons": self.blocked_reasons,
            "contextIds": self.context_ids,
            "estimatedInputTokens": self.estimated_input_tokens,
            "estimatedOutputTokens": self.estimated_output_tokens,
            "estimatedTotalTokens": self.estimated_total_tokens,
            "requireHumanReview": self.require_human_review,
            "sanitizedPrompt": self.sanitized_prompt,
        }


def build_prompt_gateway_request(
    row: dict[str, object],
    contexts: list[dict[str, object]],
    tenant_id: str,
) -> PromptGatewayRequest:
    cost_budget = require_mapping(row, "cost_budget", "prompt gateway request")
    output_policy = require_mapping(row, "output_policy", "prompt gateway request")
    return PromptGatewayRequest(
        tenant_id=tenant_id,
        product=require_str(row, "product", "prompt gateway request"),
        use_case_id=require_str(row, "use_case_id", "prompt gateway request"),
        system_prompt=require_str(row, "system_prompt", "prompt gateway request"),
        user_input=require_str(row, "user_input", "prompt gateway request"),
        retrieved_context=tuple(
            PromptContext(
                context_id=require_str(context, "context_id", "prompt context"),
                tenant_id=require_str(context, "tenant_id", "prompt context"),
                source_ref=require_str(context, "source_ref", "prompt context"),
                text=require_str(context, "text", "prompt context"),
            )
            for context in contexts
        ),
        output_policy=PromptOutputPolicy(
            require_human_review=require_bool(
                output_policy,
                "require_human_review",
                "prompt output policy",
            ),
            allow_external_auto_send=require_bool(
                output_policy,
                "allow_external_auto_send",
                "prompt output policy",
            ),
            require_citations=require_bool(
                output_policy,
                "require_citations",
                "prompt output policy",
            ),
        ),
        cost_budget=PromptCostBudget(
            max_estimated_input_tokens=require_int(
                cost_budget,
                "max_estimated_input_tokens",
                "prompt cost budget",
            ),
            max_estimated_output_tokens=require_int(
                cost_budget,
                "max_estimated_output_tokens",
                "prompt cost budget",
            ),
            max_estimated_total_tokens=require_int(
                cost_budget,
                "max_estimated_total_tokens",
                "prompt cost budget",
            ),
        ),
        case_id=str(row.get("case_id") or ""),
    )


def run_prompt_gateway(request: PromptGatewayRequest) -> PromptGatewayResult:
    allowed_contexts = [
        context
        for context in request.retrieved_context
        if is_prompt_context_allowed(context.tenant_id, request.tenant_id)
    ]
    context_blocks = [
        f"[{context.context_id}] {context.source_ref}: {context.text}"
        for context in allowed_contexts
    ]
    raw_prompt = "\n\n".join(
        [
            "SYSTEM:\n" + request.system_prompt,
            "USER:\n" + request.user_input,
            "CONTEXT:\n" + "\n".join(context_blocks),
        ]
    )
    sanitized_prompt = redact_prompt_text(raw_prompt)
    estimated_input_tokens = estimate_tokens(sanitized_prompt)
    estimated_output_tokens = min(
        request.cost_budget.max_estimated_output_tokens,
        max(64, estimate_tokens(request.user_input)),
    )
    estimated_total_tokens = estimated_input_tokens + estimated_output_tokens
    context_ids = tuple(context.context_id for context in allowed_contexts)

    blocked_reasons = collect_blocked_reasons(
        request,
        estimated_input_tokens,
        estimated_output_tokens,
        estimated_total_tokens,
    )
    audit_payload = redact_prompt_text(
        json.dumps(
            {
                "case_id": request.case_id,
                "context_ids": context_ids,
                "estimated_input_tokens": estimated_input_tokens,
                "estimated_output_tokens": estimated_output_tokens,
                "estimated_total_tokens": estimated_total_tokens,
                "prompt": sanitized_prompt,
                "product": request.product,
                "use_case_id": request.use_case_id,
            },
            sort_keys=True,
        )
    )

    return PromptGatewayResult(
        allowed=not blocked_reasons,
        blocked_reasons=blocked_reasons,
        sanitized_prompt=sanitized_prompt,
        audit_payload=audit_payload,
        context_ids=context_ids,
        estimated_input_tokens=estimated_input_tokens,
        estimated_output_tokens=estimated_output_tokens,
        estimated_total_tokens=estimated_total_tokens,
        require_human_review=request.output_policy.require_human_review,
    )


def collect_blocked_reasons(
    request: PromptGatewayRequest,
    estimated_input_tokens: int,
    estimated_output_tokens: int,
    estimated_total_tokens: int,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if estimated_input_tokens > request.cost_budget.max_estimated_input_tokens:
        reasons.append("INPUT_TOKEN_BUDGET_EXCEEDED")
    if estimated_output_tokens > request.cost_budget.max_estimated_output_tokens:
        reasons.append("OUTPUT_TOKEN_BUDGET_EXCEEDED")
    if estimated_total_tokens > request.cost_budget.max_estimated_total_tokens:
        reasons.append("TOTAL_TOKEN_BUDGET_EXCEEDED")
    if request.output_policy.allow_external_auto_send:
        reasons.append("EXTERNAL_AUTO_SEND_BLOCKED")
    if not request.output_policy.require_human_review:
        reasons.append("HUMAN_REVIEW_REQUIRED")
    return tuple(reasons)


def is_prompt_context_allowed(context_tenant_id: str, request_tenant_id: str) -> bool:
    return context_tenant_id == request_tenant_id or context_tenant_id == "global"


def prompt_cost_within_budget(result: PromptGatewayResult) -> bool:
    return not any("TOKEN_BUDGET" in reason for reason in result.blocked_reasons)


def redact_prompt_text(text: str) -> str:
    redacted = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "[REDACTED_EMAIL]",
        text,
    )
    redacted = re.sub(
        r"\+?\d[\d\s().-]{7,}\d",
        "[REDACTED_PHONE]",
        redacted,
    )
    redacted = re.sub(
        r"\bsk-[A-Za-z0-9_-]+\b",
        "[REDACTED_SECRET]",
        redacted,
    )
    redacted = re.sub(
        r"\bBearer\s+[A-Za-z0-9._-]+\b",
        "[REDACTED_SECRET]",
        redacted,
    )
    redacted = re.sub(
        r"\b(token|api_key|apikey)\s*=\s*[^,\s]+",
        r"\1=[REDACTED_SECRET]",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        r"\b(learner_id|principal_id)\s*=\s*[^,\s]+",
        r"\1=[REDACTED_IDENTIFIER]",
        redacted,
        flags=re.IGNORECASE,
    )
    return redacted


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def require_mapping(row: dict[str, object], key: str, owner: str) -> dict[str, object]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{owner} must define mapping field {key}")
    return value


def require_str(row: dict[str, object], key: str, owner: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{owner} must define non-empty string field {key}")
    return value.strip()


def require_int(row: dict[str, object], key: str, owner: str) -> int:
    value = row.get(key)
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{owner} must define positive integer field {key}")
    return value


def require_bool(row: dict[str, object], key: str, owner: str) -> bool:
    value = row.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{owner} must define boolean field {key}")
    return value

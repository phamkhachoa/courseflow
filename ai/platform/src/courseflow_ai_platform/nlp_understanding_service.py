from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

NLP_UNDERSTANDING_ANALYZE_SCOPE = "internal:ai-platform:nlp-understanding:analyze"
NLP_UNDERSTANDING_OPS_SCOPE = "internal:ai-platform:nlp-understanding:ops"
NLP_UNDERSTANDING_ROUTE_SCOPES = {
    ("POST", "/v1/nlp-understanding/analyze"): NLP_UNDERSTANDING_ANALYZE_SCOPE,
    ("GET", "/v1/nlp-understanding/health"): NLP_UNDERSTANDING_OPS_SCOPE,
    ("GET", "/v1/nlp-understanding/metrics"): NLP_UNDERSTANDING_OPS_SCOPE,
}
NLP_MODEL_ID = "nlp-understanding-baseline-v1"
DIRECT_IDENTIFIER_KEYS = (
    "account_id",
    "accountId",
    "case_id",
    "caseId",
    "contact_id",
    "contactId",
    "customer_id",
    "customerId",
    "email",
    "emailAddress",
    "learner_id",
    "learnerId",
    "phone",
    "phoneNumber",
    "student_id",
    "studentId",
    "user_id",
    "userId",
)


class NlpUnderstandingServiceError(ValueError):
    """Raised when NLP understanding service input or policy is invalid."""


class NlpUnderstandingPrivacyError(NlpUnderstandingServiceError):
    """Raised when an NLP request submits direct identifiers."""


@dataclass(frozen=True, slots=True)
class NlpUnderstandingPrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    use_case_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> NlpUnderstandingPrincipal:
        return cls(
            principal_id=required_non_empty_str(row, "principal_id", "principalId"),
            scopes=normalize_string_tuple(row.get("scopes", row.get("scope"))),
            tenant_ids=normalize_string_tuple(row.get("tenant_ids", row.get("tenantIds"))),
            product_ids=normalize_string_tuple(row.get("product_ids", row.get("productIds"))),
            use_case_ids=normalize_string_tuple(
                row.get("use_case_ids", row.get("useCaseIds"))
            ),
        )


@dataclass(frozen=True, slots=True)
class NlpUnderstandingPrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    use_case_ids: tuple[str, ...]

    def resolve(self, requested_scopes: object | None = None) -> NlpUnderstandingPrincipal:
        scopes = (
            self.scopes
            if requested_scopes is None
            else normalize_string_tuple(requested_scopes)
        )
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise NlpUnderstandingServiceError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return NlpUnderstandingPrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            product_ids=self.product_ids,
            use_case_ids=self.use_case_ids,
        )


@dataclass(frozen=True, slots=True)
class NlpUnderstandingAccessPolicy:
    policy_id: str
    principals: Mapping[str, NlpUnderstandingPrincipalGrant]
    wildcard_scopes_allowed: bool = False
    tenant_isolation_required: bool = True
    direct_identifier_submission_allowed: bool = False

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> NlpUnderstandingPrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise NlpUnderstandingServiceError(
                f"NLP understanding principal is not registered: {principal_id}"
            )
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class NlpUnderstandingRequest:
    tenant_id: str
    product: str
    use_case_id: str
    text: str
    task_type: str = "general_understanding"
    product_area: str = ""
    declared_priority: str = ""
    language: str = "en"
    rubric_items: tuple[str, ...] = ()
    expected_terms: tuple[str, ...] = ()
    reference_text: str = ""

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> NlpUnderstandingRequest:
        reject_direct_identifiers(row)
        return cls(
            tenant_id=required_non_empty_str(row, "tenant_id", "tenantId"),
            product=required_non_empty_str(row, "product", "product"),
            use_case_id=required_non_empty_str(row, "use_case_id", "useCaseId"),
            text=extract_request_text(row),
            task_type=optional_string(
                row,
                "task_type",
                "taskType",
                default="general_understanding",
            ),
            product_area=optional_string(row, "product_area", "productArea", default=""),
            declared_priority=optional_string(
                row,
                "declared_priority",
                "declaredPriority",
                default=optional_string(row, "priority", "priority", default=""),
            ),
            language=optional_string(row, "language", "language", default="en"),
            rubric_items=normalize_string_tuple(
                row.get("rubric_items", row.get("rubricItems", []))
            ),
            expected_terms=normalize_string_tuple(
                row.get("expected_terms", row.get("expectedTerms", []))
            ),
            reference_text=optional_string(
                row,
                "reference_text",
                "referenceText",
                default="",
            ),
        )


@dataclass(frozen=True, slots=True)
class NlpUnderstandingResponse:
    tenant_id: str
    product: str
    use_case_id: str
    task_type: str
    model_id: str
    intent: str
    priority_signal: str
    semantic_tags: tuple[str, ...]
    rubric_feedback: tuple[str, ...]
    matched_terms: tuple[str, ...]
    missing_terms: tuple[str, ...]
    retrieval_query: str
    confidence: float
    reason_codes: tuple[str, ...]
    requires_human_review: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": self.confidence,
            "intent": self.intent,
            "matchedTerms": self.matched_terms,
            "missingTerms": self.missing_terms,
            "modelId": self.model_id,
            "prioritySignal": self.priority_signal,
            "product": self.product,
            "reasonCodes": self.reason_codes,
            "requiresHumanReview": self.requires_human_review,
            "retrievalQuery": self.retrieval_query,
            "rubricFeedback": self.rubric_feedback,
            "semanticTags": self.semantic_tags,
            "taskType": self.task_type,
            "tenantId": self.tenant_id,
            "useCaseId": self.use_case_id,
        }


@dataclass(frozen=True, slots=True)
class NlpUnderstandingMetricsSnapshot:
    request_count: int
    analysis_count: int
    error_count: int
    direct_identifier_rejection_count: int
    human_review_count: int
    by_product: dict[str, int]
    by_use_case: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysisCount": self.analysis_count,
            "byProduct": self.by_product,
            "byUseCase": self.by_use_case,
            "directIdentifierRejectionCount": self.direct_identifier_rejection_count,
            "errorCount": self.error_count,
            "humanReviewCount": self.human_review_count,
            "requestCount": self.request_count,
        }


class NlpUnderstandingMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.analysis_count = 0
        self.error_count = 0
        self.direct_identifier_rejection_count = 0
        self.human_review_count = 0
        self.by_product: dict[str, int] = {}
        self.by_use_case: dict[str, int] = {}

    def record_analysis(
        self,
        request: NlpUnderstandingRequest,
        response: NlpUnderstandingResponse,
    ) -> None:
        self.request_count += 1
        self.analysis_count += 1
        if response.requires_human_review:
            self.human_review_count += 1
        self.by_product[request.product] = self.by_product.get(request.product, 0) + 1
        self.by_use_case[request.use_case_id] = (
            self.by_use_case.get(request.use_case_id, 0) + 1
        )

    def record_error(self) -> None:
        self.request_count += 1
        self.error_count += 1

    def record_direct_identifier_rejection(self) -> None:
        self.request_count += 1
        self.error_count += 1
        self.direct_identifier_rejection_count += 1

    def snapshot(self) -> NlpUnderstandingMetricsSnapshot:
        return NlpUnderstandingMetricsSnapshot(
            request_count=self.request_count,
            analysis_count=self.analysis_count,
            error_count=self.error_count,
            direct_identifier_rejection_count=self.direct_identifier_rejection_count,
            human_review_count=self.human_review_count,
            by_product=dict(sorted(self.by_product.items())),
            by_use_case=dict(sorted(self.by_use_case.items())),
        )


class NlpUnderstandingRuntime:
    """Policy-aware NLP baseline for intent, semantic tags and rubric feedback."""

    def __init__(self, ai_root: Path | str) -> None:
        self.ai_root = Path(ai_root)
        self.metrics = NlpUnderstandingMetrics()

    def analyze(
        self,
        request: NlpUnderstandingRequest | Mapping[str, Any],
        principal: NlpUnderstandingPrincipal | Mapping[str, Any] | None = None,
    ) -> NlpUnderstandingResponse:
        try:
            analysis_request = (
                request
                if isinstance(request, NlpUnderstandingRequest)
                else NlpUnderstandingRequest.from_dict(request)
            )
            response = self._analyze(analysis_request, normalize_principal(principal))
        except NlpUnderstandingPrivacyError:
            self.metrics.record_direct_identifier_rejection()
            raise
        except Exception:
            self.metrics.record_error()
            raise
        self.metrics.record_analysis(analysis_request, response)
        return response

    def health(self) -> dict[str, Any]:
        return {
            "modelId": NLP_MODEL_ID,
            "routeCount": len(NLP_UNDERSTANDING_ROUTE_SCOPES),
            "serviceStatus": "healthy",
            "transformerAdapterStatus": "upgrade_path_ready",
        }

    def snapshot_metrics(self) -> NlpUnderstandingMetricsSnapshot:
        return self.metrics.snapshot()

    def _analyze(
        self,
        request: NlpUnderstandingRequest,
        principal: NlpUnderstandingPrincipal | None,
    ) -> NlpUnderstandingResponse:
        authorize_nlp_understanding(principal, request)
        intent, intent_reason = classify_intent(request)
        priority_signal, priority_reason = classify_priority(
            request.text,
            request.declared_priority,
        )
        semantic_tags = extract_semantic_tags(request)
        matched_terms, missing_terms = score_expected_terms(
            request.text,
            request.expected_terms,
            request.reference_text,
        )
        rubric_feedback = build_rubric_feedback(
            request,
            matched_terms=matched_terms,
            missing_terms=missing_terms,
        )
        retrieval_query = build_retrieval_query(request, intent, semantic_tags)
        confidence = confidence_for(
            intent,
            priority_signal,
            semantic_tags,
            missing_terms,
        )
        requires_human_review = should_require_human_review(request, missing_terms)
        reason_codes = tuple(
            code
            for code in (
                intent_reason,
                priority_reason,
                "RUBRIC_FEEDBACK_READY" if rubric_feedback else "",
                "HUMAN_REVIEW_REQUIRED" if requires_human_review else "",
                "TRANSFORMER_UPGRADE_PATH_READY",
            )
            if code
        )

        return NlpUnderstandingResponse(
            tenant_id=request.tenant_id,
            product=request.product,
            use_case_id=request.use_case_id,
            task_type=request.task_type,
            model_id=NLP_MODEL_ID,
            intent=intent,
            priority_signal=priority_signal,
            semantic_tags=semantic_tags,
            rubric_feedback=rubric_feedback,
            matched_terms=matched_terms,
            missing_terms=missing_terms,
            retrieval_query=retrieval_query,
            confidence=confidence,
            reason_codes=reason_codes,
            requires_human_review=requires_human_review,
        )


def load_nlp_understanding_access_policy(ai_root: Path | str) -> NlpUnderstandingAccessPolicy:
    root = Path(ai_root)
    policy_path = (
        root / "platform" / "governance" / "policies" / "nlp-understanding-access-policy.yaml"
    )
    policy = load_yaml(policy_path)
    raw_scope_aliases = policy.get("scope_aliases", {})
    if not isinstance(raw_scope_aliases, dict):
        raise RegistryValidationError(f"{policy_path} must define mapping field scope_aliases")
    scope_aliases = {
        "analyze": NLP_UNDERSTANDING_ANALYZE_SCOPE,
        "ops": NLP_UNDERSTANDING_OPS_SCOPE,
        **raw_scope_aliases,
    }
    grants: dict[str, NlpUnderstandingPrincipalGrant] = {}
    for row in require_mapping_list(policy, "principals", policy_path):
        principal_id = require_str(row, "principal_id", str(policy_path))
        if principal_id in grants:
            raise RegistryValidationError(f"{policy_path} duplicates principal: {principal_id}")
        product = require_str(row, "product", str(policy_path))
        product_ids = normalize_string_tuple(row.get("product_ids", [product]))
        grants[principal_id] = NlpUnderstandingPrincipalGrant(
            principal_id=principal_id,
            owner_role=require_str(row, "owner_role", str(policy_path)),
            product=product,
            scopes=tuple(
                sorted(
                    {
                        expand_scope_alias(scope, scope_aliases, policy_path)
                        for scope in normalize_string_tuple(row.get("scopes", []))
                    }
                )
            ),
            tenant_ids=tuple(sorted(normalize_string_tuple(row.get("tenant_ids", [])))),
            product_ids=tuple(sorted(product_ids)),
            use_case_ids=tuple(sorted(normalize_string_tuple(row.get("use_case_ids", [])))),
        )
    defaults = policy.get("defaults", {})
    if not isinstance(defaults, dict):
        raise RegistryValidationError(f"{policy_path} defaults must be a mapping")
    return NlpUnderstandingAccessPolicy(
        policy_id=require_str(policy, "policy_id", str(policy_path)),
        principals=dict(sorted(grants.items())),
        wildcard_scopes_allowed=bool(defaults.get("wildcard_scopes_allowed", False)),
        tenant_isolation_required=bool(defaults.get("tenant_isolation_required", True)),
        direct_identifier_submission_allowed=bool(
            defaults.get("direct_identifier_submission_allowed", False)
        ),
    )


def authorize_nlp_understanding(
    principal: NlpUnderstandingPrincipal | None,
    request: NlpUnderstandingRequest,
) -> None:
    if principal is None:
        return
    if "*" in principal.scopes:
        raise NlpUnderstandingServiceError("wildcard NLP understanding scopes are forbidden")
    if NLP_UNDERSTANDING_ANALYZE_SCOPE not in principal.scopes:
        raise NlpUnderstandingServiceError("NLP understanding analyze scope is required")
    if principal.tenant_ids and request.tenant_id not in principal.tenant_ids:
        raise NlpUnderstandingServiceError("NLP understanding tenant is not granted to principal")
    if principal.product_ids and request.product not in principal.product_ids:
        raise NlpUnderstandingServiceError("NLP understanding product is not granted to principal")
    if principal.use_case_ids and request.use_case_id not in principal.use_case_ids:
        raise NlpUnderstandingServiceError(
            "NLP understanding use case is not granted to principal"
        )


def classify_intent(request: NlpUnderstandingRequest) -> tuple[str, str]:
    text = normalize_text(f"{request.product_area} {request.task_type} {request.text}")
    if request.task_type in {"semantic_search", "knowledge_lookup"} or (
        request.product_area.lower() in {"knowledge", "policy"}
        and any(keyword in text for keyword in ("policy", "knowledge", "citation", "document"))
    ):
        return "knowledge_lookup", "INTENT_KNOWLEDGE_LOOKUP_KEYWORD"
    groups = [
        ("billing", "INTENT_BILLING_KEYWORD", ("invoice", "refund", "payment", "charge")),
        ("access", "INTENT_ACCESS_KEYWORD", ("login", "mfa", "password", "permission", "access")),
        ("technical", "INTENT_TECHNICAL_KEYWORD", ("api", "timeout", "error", "bug", "sync")),
        ("account", "INTENT_ACCOUNT_KEYWORD", ("account", "profile", "email", "organization")),
        (
            "learning_assessment",
            "INTENT_LEARNING_ASSESSMENT_KEYWORD",
            ("rubric", "grade", "assessment", "answer", "quiz", "feedback"),
        ),
        (
            "knowledge_lookup",
            "INTENT_KNOWLEDGE_LOOKUP_KEYWORD",
            ("policy", "knowledge", "citation", "semantic", "search", "document"),
        ),
        (
            "quality_assurance",
            "INTENT_QUALITY_ASSURANCE_KEYWORD",
            ("transcript", "call", "quality", "speech", "coaching"),
        ),
    ]
    for intent, reason, keywords in groups:
        if any(keyword in text for keyword in keywords):
            return intent, reason
    return "general", "INTENT_GENERAL_FALLBACK"


def classify_priority(text: str, declared_priority: str) -> tuple[str, str]:
    lowered = normalize_text(f"{text} {declared_priority}")
    if any(keyword in lowered for keyword in ("urgent", "outage", "breach", "security", "down")):
        return "high", "PRIORITY_HIGH_KEYWORD"
    if any(keyword in lowered for keyword in ("blocked", "deadline", "failed", "incorrect")):
        return "medium", "PRIORITY_MEDIUM_KEYWORD"
    if declared_priority.strip().lower() in {"high", "urgent", "p1"}:
        return "high", "PRIORITY_DECLARED_HIGH"
    return "normal", "PRIORITY_NORMAL_FALLBACK"


def extract_semantic_tags(request: NlpUnderstandingRequest) -> tuple[str, ...]:
    text = normalize_text(f"{request.product_area} {request.task_type} {request.text}")
    tags: list[str] = []
    for tag, keywords in {
        "billing": ("invoice", "refund", "payment", "charge"),
        "identity_access": ("login", "mfa", "password", "permission"),
        "integration_api": ("api", "timeout", "sync", "endpoint"),
        "learning_rubric": ("rubric", "grade", "assessment", "quiz"),
        "semantic_search": ("semantic", "search", "knowledge", "citation"),
        "speech_quality": ("transcript", "call", "quality", "coaching"),
        "policy_knowledge": ("policy", "compliance", "procedure", "document"),
    }.items():
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    for token in re.findall(r"[a-z][a-z0-9_-]{3,}", text):
        if token not in STOPWORDS and token not in tags:
            tags.append(token)
        if len(tags) >= 8:
            break
    return tuple(tags or ("general",))


def score_expected_terms(
    text: str,
    expected_terms: tuple[str, ...],
    reference_text: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    combined = normalize_text(f"{text} {reference_text}")
    matched: list[str] = []
    missing: list[str] = []
    for term in expected_terms:
        normalized_term = normalize_text(term)
        if normalized_term and normalized_term in combined:
            matched.append(term)
        else:
            missing.append(term)
    return tuple(matched), tuple(missing)


def build_rubric_feedback(
    request: NlpUnderstandingRequest,
    *,
    matched_terms: tuple[str, ...],
    missing_terms: tuple[str, ...],
) -> tuple[str, ...]:
    if request.task_type not in {"rubric_feedback", "auto_grading", "assessment_feedback"}:
        return ()
    feedback: list[str] = []
    if matched_terms:
        feedback.append("Evidence covers: " + ", ".join(matched_terms))
    if missing_terms:
        feedback.append("Needs review for missing terms: " + ", ".join(missing_terms))
    if request.rubric_items:
        feedback.append("Rubric checked: " + "; ".join(request.rubric_items[:3]))
    if not feedback:
        feedback.append("Answer requires instructor review against the rubric.")
    return tuple(feedback)


def build_retrieval_query(
    request: NlpUnderstandingRequest,
    intent: str,
    semantic_tags: tuple[str, ...],
) -> str:
    terms = [intent, *semantic_tags[:4]]
    if request.product_area:
        terms.append(request.product_area)
    terms.extend(
        token
        for token in re.findall(r"[A-Za-z0-9_-]{4,}", request.text)[:6]
        if token.lower() not in STOPWORDS
    )
    return " ".join(dict.fromkeys(term.strip() for term in terms if term.strip()))


def confidence_for(
    intent: str,
    priority_signal: str,
    semantic_tags: tuple[str, ...],
    missing_terms: tuple[str, ...],
) -> float:
    score = 0.56
    if intent != "general":
        score += 0.16
    if priority_signal != "normal":
        score += 0.05
    if semantic_tags and semantic_tags != ("general",):
        score += 0.08
    if missing_terms:
        score -= min(0.16, 0.04 * len(missing_terms))
    return round(max(0.20, min(score, 0.88)), 2)


def should_require_human_review(
    request: NlpUnderstandingRequest,
    missing_terms: tuple[str, ...],
) -> bool:
    return (
        request.task_type in {"rubric_feedback", "auto_grading", "assessment_feedback"}
        or request.use_case_id
        in {"lms-auto-grading", "support-agent-assist", "support-speech-quality-assurance"}
        or bool(missing_terms)
    )


def reject_direct_identifiers(row: Mapping[str, Any]) -> None:
    for key in DIRECT_IDENTIFIER_KEYS:
        if key in row and str(row[key]).strip():
            raise NlpUnderstandingPrivacyError(
                f"direct identifier field is forbidden for NLP understanding: {key}"
            )
    text = " ".join(str(value) for value in row.values() if isinstance(value, str))
    if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text):
        raise NlpUnderstandingPrivacyError(
            "direct email identifiers are forbidden in NLP understanding text"
        )
    if re.search(r"\b(learner_id|customer_id|account_id)\s*=", text, re.IGNORECASE):
        raise NlpUnderstandingPrivacyError("direct raw identifiers are forbidden in NLP text")


def normalize_principal(
    principal: NlpUnderstandingPrincipal | Mapping[str, Any] | None,
) -> NlpUnderstandingPrincipal | None:
    if principal is None or isinstance(principal, NlpUnderstandingPrincipal):
        return principal
    return NlpUnderstandingPrincipal.from_dict(principal)


def extract_request_text(row: Mapping[str, Any]) -> str:
    text = row.get("text", row.get("latestMessage", row.get("answerText", "")))
    subject = row.get("subject", "")
    if isinstance(subject, str) and subject.strip():
        text = f"{subject}: {text}"
    if not isinstance(text, str) or not text.strip():
        raise NlpUnderstandingServiceError(
            "NLP understanding request must define text, latestMessage or answerText"
        )
    return text.strip()


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list | tuple):
        raise NlpUnderstandingServiceError(
            "NLP understanding policy values must be strings or lists"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise NlpUnderstandingServiceError(
                "NLP understanding policy list values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def expand_scope_alias(
    scope: str,
    scope_aliases: Mapping[str, str],
    policy_path: Path,
) -> str:
    expanded = scope_aliases.get(scope, scope)
    if not expanded.startswith("internal:ai-platform:nlp-understanding:"):
        raise RegistryValidationError(
            f"{policy_path} has unsupported NLP understanding scope: {scope}"
        )
    return expanded


def required_non_empty_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise NlpUnderstandingServiceError(
            f"NLP understanding request must define {snake_key} or {camel_key}"
        )
    return value.strip()


def optional_string(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    *,
    default: str,
) -> str:
    value = row.get(snake_key, row.get(camel_key, default))
    if value is None:
        return default
    if not isinstance(value, str):
        raise NlpUnderstandingServiceError(
            f"NLP understanding request field {snake_key} must be a string"
        )
    return value.strip() or default


def require_mapping_list(row: Mapping[str, Any], key: str, owner: Path) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a mapping")
        result.append(item)
    return result


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


STOPWORDS = {
    "about",
    "after",
    "before",
    "customer",
    "draft",
    "from",
    "have",
    "help",
    "latest",
    "message",
    "needs",
    "please",
    "request",
    "should",
    "step",
    "that",
    "their",
    "there",
    "this",
    "with",
}

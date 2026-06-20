from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.prompt_gateway import (
    PromptContext,
    PromptCostBudget,
    PromptGatewayRequest,
    PromptOutputPolicy,
)
from courseflow_ai_platform.prompt_gateway_service import PromptGatewayRuntime
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str
from courseflow_ai_platform.retrieval_service import (
    RETRIEVAL_SEARCH_SCOPE,
    RetrievalPrincipal,
    RetrievalRuntime,
    RetrievalSearchResult,
)

RAG_ANSWER_ANSWER_SCOPE = "internal:ai-platform:rag-answer:answer"
RAG_ANSWER_OPS_SCOPE = "internal:ai-platform:rag-answer:ops"
RAG_ANSWER_ROUTE_SCOPES = {
    ("POST", "/v1/rag-answer/answer"): RAG_ANSWER_ANSWER_SCOPE,
    ("GET", "/v1/rag-answer/health"): RAG_ANSWER_OPS_SCOPE,
    ("GET", "/v1/rag-answer/metrics"): RAG_ANSWER_OPS_SCOPE,
}
DIRECT_IDENTIFIER_KEYS = (
    "account_id",
    "accountId",
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


class RagAnswerServiceError(ValueError):
    """Raised when RAG answer service input or policy is invalid."""


class RagAnswerPrivacyError(RagAnswerServiceError):
    """Raised when requests submit direct user or account identifiers."""


@dataclass(frozen=True, slots=True)
class RagAnswerPrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    use_case_ids: tuple[str, ...] = ()
    allowed_collection_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> RagAnswerPrincipal:
        return cls(
            principal_id=required_non_empty_str(row, "principal_id", "principalId"),
            scopes=normalize_string_tuple(row.get("scopes", row.get("scope"))),
            tenant_ids=normalize_string_tuple(row.get("tenant_ids", row.get("tenantIds"))),
            product_ids=normalize_string_tuple(row.get("product_ids", row.get("productIds"))),
            use_case_ids=normalize_string_tuple(
                row.get("use_case_ids", row.get("useCaseIds"))
            ),
            allowed_collection_ids=normalize_string_tuple(
                row.get(
                    "allowed_collection_ids",
                    row.get("allowedCollectionIds", row.get("collectionIds")),
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class RagAnswerPrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    use_case_ids: tuple[str, ...]
    allowed_collection_ids: tuple[str, ...]

    def resolve(self, requested_scopes: object | None = None) -> RagAnswerPrincipal:
        scopes = (
            self.scopes
            if requested_scopes is None
            else normalize_string_tuple(requested_scopes)
        )
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise RagAnswerServiceError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return RagAnswerPrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            product_ids=self.product_ids,
            use_case_ids=self.use_case_ids,
            allowed_collection_ids=self.allowed_collection_ids,
        )


@dataclass(frozen=True, slots=True)
class RagAnswerAccessPolicy:
    policy_id: str
    principals: Mapping[str, RagAnswerPrincipalGrant]
    wildcard_scopes_allowed: bool = False
    tenant_isolation_required: bool = True
    citation_required: bool = True
    external_auto_send_allowed: bool = False

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> RagAnswerPrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise RagAnswerServiceError(
                f"RAG answer principal is not registered: {principal_id}"
            )
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class RagAnswerRequest:
    tenant_id: str
    product: str
    use_case_id: str
    collection_id: str
    question: str
    mode: str = "hybrid"
    top_k: int | None = None
    min_score_for_answer: float | None = None
    require_human_review: bool = True
    allow_external_auto_send: bool = False
    max_estimated_input_tokens: int = 2048
    max_estimated_output_tokens: int = 512
    max_estimated_total_tokens: int = 2560
    case_id: str = ""

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> RagAnswerRequest:
        reject_direct_identifiers(row)
        return cls(
            tenant_id=required_non_empty_str(row, "tenant_id", "tenantId"),
            product=required_non_empty_str(row, "product", "product"),
            use_case_id=required_non_empty_str(row, "use_case_id", "useCaseId"),
            collection_id=required_non_empty_str(row, "collection_id", "collectionId"),
            question=required_question(row),
            mode=optional_string(row, "mode", "mode", default="hybrid"),
            top_k=optional_positive_int(row, "top_k", "topK"),
            min_score_for_answer=optional_float(
                row,
                "min_score_for_answer",
                "minScoreForAnswer",
            ),
            require_human_review=optional_bool(
                row,
                "require_human_review",
                "requireHumanReview",
                default=True,
            ),
            allow_external_auto_send=optional_bool(
                row,
                "allow_external_auto_send",
                "allowExternalAutoSend",
                default=False,
            ),
            max_estimated_input_tokens=optional_positive_int(
                row,
                "max_estimated_input_tokens",
                "maxEstimatedInputTokens",
            )
            or 2048,
            max_estimated_output_tokens=optional_positive_int(
                row,
                "max_estimated_output_tokens",
                "maxEstimatedOutputTokens",
            )
            or 512,
            max_estimated_total_tokens=optional_positive_int(
                row,
                "max_estimated_total_tokens",
                "maxEstimatedTotalTokens",
            )
            or 2560,
            case_id=optional_string(row, "case_id", "caseId", default=""),
        )


@dataclass(frozen=True, slots=True)
class RagAnswerCitation:
    chunk_id: str
    source_ref: str
    title: str
    score: float

    @classmethod
    def from_result(cls, result: RetrievalSearchResult) -> RagAnswerCitation:
        return cls(
            chunk_id=result.chunk_id,
            source_ref=result.source_ref,
            title=result.title,
            score=result.score,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunkId": self.chunk_id,
            "score": self.score,
            "sourceRef": self.source_ref,
            "title": self.title,
        }


@dataclass(frozen=True, slots=True)
class RagAnswerResponse:
    tenant_id: str
    product: str
    use_case_id: str
    collection_id: str
    question: str
    answer: str
    answer_status: str
    citations: tuple[RagAnswerCitation, ...]
    retrieval_result_count: int
    min_score_for_answer: float
    require_human_review: bool
    policy_allowed: bool
    blocked_reasons: tuple[str, ...]
    refusal_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "answerStatus": self.answer_status,
            "blockedReasons": self.blocked_reasons,
            "citationCount": len(self.citations),
            "citations": [citation.to_dict() for citation in self.citations],
            "collectionId": self.collection_id,
            "minScoreForAnswer": self.min_score_for_answer,
            "policyAllowed": self.policy_allowed,
            "product": self.product,
            "question": self.question,
            "refusalReason": self.refusal_reason,
            "requireHumanReview": self.require_human_review,
            "retrievalResultCount": self.retrieval_result_count,
            "tenantId": self.tenant_id,
            "useCaseId": self.use_case_id,
        }


@dataclass(frozen=True, slots=True)
class RagAnswerMetricsSnapshot:
    request_count: int
    answer_count: int
    refusal_count: int
    human_review_count: int
    error_count: int
    by_product: dict[str, int]
    by_use_case: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "answerCount": self.answer_count,
            "byProduct": self.by_product,
            "byUseCase": self.by_use_case,
            "errorCount": self.error_count,
            "humanReviewCount": self.human_review_count,
            "refusalCount": self.refusal_count,
            "requestCount": self.request_count,
        }


class RagAnswerMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.answer_count = 0
        self.refusal_count = 0
        self.human_review_count = 0
        self.error_count = 0
        self.by_product: dict[str, int] = {}
        self.by_use_case: dict[str, int] = {}

    def record_answer(self, request: RagAnswerRequest, response: RagAnswerResponse) -> None:
        self.request_count += 1
        if response.answer_status == "grounded":
            self.answer_count += 1
        else:
            self.refusal_count += 1
        if response.require_human_review:
            self.human_review_count += 1
        self.by_product[request.product] = self.by_product.get(request.product, 0) + 1
        self.by_use_case[request.use_case_id] = (
            self.by_use_case.get(request.use_case_id, 0) + 1
        )

    def record_error(self) -> None:
        self.request_count += 1
        self.error_count += 1

    def snapshot(self) -> RagAnswerMetricsSnapshot:
        return RagAnswerMetricsSnapshot(
            request_count=self.request_count,
            answer_count=self.answer_count,
            refusal_count=self.refusal_count,
            human_review_count=self.human_review_count,
            error_count=self.error_count,
            by_product=dict(sorted(self.by_product.items())),
            by_use_case=dict(sorted(self.by_use_case.items())),
        )


class RagAnswerRuntime:
    """Grounded-answer orchestration over retrieval and prompt safety gates."""

    def __init__(self, ai_root: Path | str) -> None:
        self.ai_root = Path(ai_root)
        self.retrieval = RetrievalRuntime(self.ai_root)
        self.prompt_gateway = PromptGatewayRuntime(self.ai_root)
        self.metrics = RagAnswerMetrics()

    def answer(
        self,
        request: RagAnswerRequest | Mapping[str, Any],
        principal: RagAnswerPrincipal | Mapping[str, Any] | None = None,
    ) -> RagAnswerResponse:
        answer_request = (
            request
            if isinstance(request, RagAnswerRequest)
            else RagAnswerRequest.from_dict(request)
        )
        try:
            response = self._answer(answer_request, normalize_principal(principal))
        except Exception:
            self.metrics.record_error()
            raise
        self.metrics.record_answer(answer_request, response)
        return response

    def health(self) -> dict[str, Any]:
        retrieval_health = self.retrieval.health()
        return {
            "collectionCount": retrieval_health["collectionCount"],
            "retrievalStatus": retrieval_health["serviceStatus"],
            "routeCount": len(RAG_ANSWER_ROUTE_SCOPES),
            "serviceStatus": "healthy",
        }

    def snapshot_metrics(self) -> RagAnswerMetricsSnapshot:
        return self.metrics.snapshot()

    def _answer(
        self,
        request: RagAnswerRequest,
        principal: RagAnswerPrincipal | None,
    ) -> RagAnswerResponse:
        authorize_rag_answer(principal, request)
        if not request.require_human_review:
            raise RagAnswerServiceError("RAG answers require human review in baseline mode")
        if request.allow_external_auto_send:
            raise RagAnswerServiceError("external auto-send is forbidden for RAG answers")

        collection = self.retrieval.collections.get(request.collection_id)
        if collection is None:
            raise RagAnswerServiceError(
                f"unknown RAG retrieval collection: {request.collection_id}"
            )
        min_score = request.min_score_for_answer or collection.min_similarity_for_rag
        search_response = self.retrieval.search(
            {
                "collectionId": request.collection_id,
                "mode": request.mode,
                "query": request.question,
                "tenantId": request.tenant_id,
                "topK": request.top_k,
            },
            RetrievalPrincipal(
                principal_id=principal.principal_id if principal else "service:rag-answer-runtime",
                scopes=(RETRIEVAL_SEARCH_SCOPE,),
                tenant_ids=(request.tenant_id,),
                allowed_collection_ids=(request.collection_id,),
            ),
        )
        grounding_results = select_grounding_results(
            request.question,
            search_response.results,
            min_score=min_score,
        )
        if not grounding_results:
            return build_refusal_response(
                request,
                retrieval_result_count=search_response.result_count,
                min_score=min_score,
                reason="insufficient_grounding_context",
            )

        prompt_evaluation = self.prompt_gateway.evaluate(
            build_prompt_gateway_request(request, grounding_results),
            None,
        )
        prompt_result = prompt_evaluation.result
        if not prompt_result.allowed:
            return build_refusal_response(
                request,
                retrieval_result_count=search_response.result_count,
                min_score=min_score,
                reason="prompt_gateway_policy_blocked",
                blocked_reasons=prompt_result.blocked_reasons,
            )

        citations = tuple(RagAnswerCitation.from_result(result) for result in grounding_results)
        return RagAnswerResponse(
            tenant_id=request.tenant_id,
            product=request.product,
            use_case_id=request.use_case_id,
            collection_id=request.collection_id,
            question=request.question,
            answer=compose_grounded_answer(grounding_results),
            answer_status="grounded",
            citations=citations,
            retrieval_result_count=search_response.result_count,
            min_score_for_answer=min_score,
            require_human_review=True,
            policy_allowed=True,
            blocked_reasons=(),
        )


def load_rag_answer_access_policy(ai_root: Path | str) -> RagAnswerAccessPolicy:
    root = Path(ai_root)
    policy_path = root / "platform" / "governance" / "policies" / "rag-answer-access-policy.yaml"
    policy = load_yaml(policy_path)
    raw_scope_aliases = policy.get("scope_aliases", {})
    if not isinstance(raw_scope_aliases, dict):
        raise RegistryValidationError(f"{policy_path} must define mapping field scope_aliases")
    scope_aliases = {
        "answer": RAG_ANSWER_ANSWER_SCOPE,
        "ops": RAG_ANSWER_OPS_SCOPE,
        **raw_scope_aliases,
    }
    grants: dict[str, RagAnswerPrincipalGrant] = {}
    for row in require_mapping_list(policy, "principals", policy_path):
        principal_id = require_str(row, "principal_id", str(policy_path))
        if principal_id in grants:
            raise RegistryValidationError(f"{policy_path} duplicates principal: {principal_id}")
        product = require_str(row, "product", str(policy_path))
        product_ids = normalize_string_tuple(row.get("product_ids", [product]))
        grants[principal_id] = RagAnswerPrincipalGrant(
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
            allowed_collection_ids=tuple(
                sorted(normalize_string_tuple(row.get("collection_ids", [])))
            ),
        )
    defaults = policy.get("defaults", {})
    if not isinstance(defaults, dict):
        raise RegistryValidationError(f"{policy_path} defaults must be a mapping")
    return RagAnswerAccessPolicy(
        policy_id=require_str(policy, "policy_id", str(policy_path)),
        principals=dict(sorted(grants.items())),
        wildcard_scopes_allowed=bool(defaults.get("wildcard_scopes_allowed", False)),
        tenant_isolation_required=bool(defaults.get("tenant_isolation_required", True)),
        citation_required=bool(defaults.get("citation_required", True)),
        external_auto_send_allowed=bool(defaults.get("external_auto_send_allowed", False)),
    )


def authorize_rag_answer(
    principal: RagAnswerPrincipal | None,
    request: RagAnswerRequest,
) -> None:
    if principal is None:
        return
    if "*" in principal.scopes:
        raise RagAnswerServiceError("wildcard RAG answer scopes are forbidden")
    if RAG_ANSWER_ANSWER_SCOPE not in principal.scopes:
        raise RagAnswerServiceError("RAG answer scope is required")
    if principal.tenant_ids and request.tenant_id not in principal.tenant_ids:
        raise RagAnswerServiceError("RAG answer tenant is not granted to principal")
    if principal.product_ids and request.product not in principal.product_ids:
        raise RagAnswerServiceError("RAG answer product is not granted to principal")
    if principal.use_case_ids and request.use_case_id not in principal.use_case_ids:
        raise RagAnswerServiceError("RAG answer use case is not granted to principal")
    if (
        principal.allowed_collection_ids
        and request.collection_id not in principal.allowed_collection_ids
    ):
        raise RagAnswerServiceError("RAG answer collection is not granted to principal")


def select_grounding_results(
    question: str,
    results: tuple[RetrievalSearchResult, ...],
    *,
    min_score: float,
) -> tuple[RetrievalSearchResult, ...]:
    eligible = tuple(result for result in results if result.score >= min_score)
    if not eligible:
        return ()
    if asks_for_private_or_cross_tenant_context(question) and not evidence_matches_private_ask(
        question,
        eligible,
    ):
        return ()
    return eligible


def asks_for_private_or_cross_tenant_context(question: str) -> bool:
    normalized = normalize_text(question)
    return "private" in normalized or "tenant b" in normalized or "tenant-b" in normalized


def evidence_matches_private_ask(
    question: str,
    results: tuple[RetrievalSearchResult, ...],
) -> bool:
    normalized_question = normalize_text(question)
    evidence_text = normalize_text(
        " ".join(
            [
                result.chunk_id,
                result.source_ref,
                result.title,
                result.text_snippet,
            ]
            for result in results
        )
    )
    if "tenant b" in normalized_question or "tenant-b" in normalized_question:
        return "tenant b" in evidence_text or "tenant-b" in evidence_text
    return "private" in evidence_text


def compose_grounded_answer(results: tuple[RetrievalSearchResult, ...]) -> str:
    evidence_lines = [
        f"{result.text_snippet} [{result.chunk_id}]"
        for result in results[:2]
    ]
    return " ".join(evidence_lines)


def build_refusal_response(
    request: RagAnswerRequest,
    *,
    retrieval_result_count: int,
    min_score: float,
    reason: str,
    blocked_reasons: tuple[str, ...] = (),
) -> RagAnswerResponse:
    return RagAnswerResponse(
        tenant_id=request.tenant_id,
        product=request.product,
        use_case_id=request.use_case_id,
        collection_id=request.collection_id,
        question=request.question,
        answer=(
            "I do not have enough trusted retrieved context to answer this. "
            "Please ask for clarification or route to human review."
        ),
        answer_status="refused",
        citations=(),
        retrieval_result_count=retrieval_result_count,
        min_score_for_answer=min_score,
        require_human_review=True,
        policy_allowed=not blocked_reasons,
        blocked_reasons=blocked_reasons,
        refusal_reason=reason,
    )


def build_prompt_gateway_request(
    request: RagAnswerRequest,
    results: tuple[RetrievalSearchResult, ...],
) -> PromptGatewayRequest:
    return PromptGatewayRequest(
        tenant_id=request.tenant_id,
        product=request.product,
        use_case_id=request.use_case_id,
        system_prompt=(
            "Answer only from retrieved context. Include citation chunk IDs. "
            "Refuse if the answer is not grounded."
        ),
        user_input=request.question,
        retrieved_context=tuple(
            PromptContext(
                context_id=result.chunk_id,
                tenant_id=result.tenant_id,
                source_ref=result.source_ref,
                text=result.text_snippet,
            )
            for result in results
        ),
        output_policy=PromptOutputPolicy(
            require_human_review=True,
            allow_external_auto_send=False,
            require_citations=True,
        ),
        cost_budget=PromptCostBudget(
            max_estimated_input_tokens=request.max_estimated_input_tokens,
            max_estimated_output_tokens=request.max_estimated_output_tokens,
            max_estimated_total_tokens=request.max_estimated_total_tokens,
        ),
        case_id=request.case_id,
    )


def normalize_principal(
    principal: RagAnswerPrincipal | Mapping[str, Any] | None,
) -> RagAnswerPrincipal | None:
    if principal is None or isinstance(principal, RagAnswerPrincipal):
        return principal
    return RagAnswerPrincipal.from_dict(principal)


def reject_direct_identifiers(row: Mapping[str, Any]) -> None:
    for key in DIRECT_IDENTIFIER_KEYS:
        if key in row and str(row[key]).strip():
            raise RagAnswerPrivacyError(
                f"direct identifier field is forbidden for RAG answer: {key}"
            )
    question = str(row.get("question", row.get("userQuestion", "")))
    if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", question):
        raise RagAnswerPrivacyError("direct email identifiers are forbidden in RAG questions")
    if re.search(r"\b(learner_id|customer_id|account_id)\s*=", question, re.IGNORECASE):
        raise RagAnswerPrivacyError("direct raw identifiers are forbidden in RAG questions")


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list | tuple):
        raise RagAnswerServiceError("RAG answer policy values must be strings or lists")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RagAnswerServiceError(
                "RAG answer policy list values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def expand_scope_alias(
    scope: str,
    scope_aliases: Mapping[str, str],
    policy_path: Path,
) -> str:
    expanded = scope_aliases.get(scope, scope)
    if not expanded.startswith("internal:ai-platform:rag-answer:"):
        raise RegistryValidationError(f"{policy_path} has unsupported RAG answer scope: {scope}")
    return expanded


def required_question(row: Mapping[str, Any]) -> str:
    value = row.get("question", row.get("userQuestion"))
    if not isinstance(value, str) or not value.strip():
        raise RagAnswerServiceError("RAG answer request must define question or userQuestion")
    return value.strip()


def required_non_empty_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise RagAnswerServiceError(
            f"RAG answer request must define {snake_key} or {camel_key}"
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
        raise RagAnswerServiceError(f"RAG answer request field {snake_key} must be a string")
    return value.strip() or default


def optional_bool(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    *,
    default: bool,
) -> bool:
    value = row.get(snake_key, row.get(camel_key, default))
    if not isinstance(value, bool):
        raise RagAnswerServiceError(f"RAG answer request field {snake_key} must be boolean")
    return value


def optional_positive_int(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
) -> int | None:
    value = row.get(snake_key, row.get(camel_key))
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RagAnswerServiceError(f"RAG answer request field {snake_key} must be positive")
    return value


def optional_float(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
) -> float | None:
    value = row.get(snake_key, row.get(camel_key))
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        raise RagAnswerServiceError(f"RAG answer request field {snake_key} must be positive")
    return float(value)


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
    return " ".join(text.lower().replace("_", " ").split())

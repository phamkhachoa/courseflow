from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.evaluation import (
    EvaluationRegistryReport,
    EvaluationRunResult,
    run_registered_evaluations,
)
from courseflow_ai_platform.promotion_readiness import (
    PromotionReadinessItem,
    PromotionReadinessReport,
    build_promotion_readiness_report,
)
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml

GOVERNANCE_EVALUATION_ASSESS_SCOPE = (
    "internal:ai-platform:governance-evaluation:assess"
)
GOVERNANCE_EVALUATION_OPS_SCOPE = "internal:ai-platform:governance-evaluation:ops"
GOVERNANCE_EVALUATION_ROUTE_SCOPES = {
    ("POST", "/v1/governance-evaluation/assess"): (
        GOVERNANCE_EVALUATION_ASSESS_SCOPE
    ),
    ("GET", "/v1/governance-evaluation/health"): GOVERNANCE_EVALUATION_OPS_SCOPE,
    ("GET", "/v1/governance-evaluation/metrics"): GOVERNANCE_EVALUATION_OPS_SCOPE,
}

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
SECRET_VALUE_KEYS = (
    "api_key",
    "apiKey",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
)


class GovernanceEvaluationServiceError(ValueError):
    """Raised when governance evaluation input or policy is invalid."""


class GovernanceEvaluationPrivacyError(GovernanceEvaluationServiceError):
    """Raised when governance evaluation receives unsafe direct evidence."""


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationPrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    use_case_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(
        cls,
        row: Mapping[str, Any],
    ) -> GovernanceEvaluationPrincipal:
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
class GovernanceEvaluationPrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    use_case_ids: tuple[str, ...]

    def resolve(
        self,
        requested_scopes: object | None = None,
    ) -> GovernanceEvaluationPrincipal:
        scopes = (
            self.scopes
            if requested_scopes is None
            else normalize_string_tuple(requested_scopes)
        )
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise GovernanceEvaluationServiceError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return GovernanceEvaluationPrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            product_ids=self.product_ids,
            use_case_ids=self.use_case_ids,
        )


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationAccessPolicy:
    policy_id: str
    principals: Mapping[str, GovernanceEvaluationPrincipalGrant]
    wildcard_scopes_allowed: bool = False
    tenant_isolation_required: bool = True
    direct_identifier_submission_allowed: bool = False
    secret_value_submission_allowed: bool = False
    external_auto_send_allowed: bool = False

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> GovernanceEvaluationPrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise GovernanceEvaluationServiceError(
                "governance evaluation principal is not registered: "
                f"{principal_id}"
            )
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationRequest:
    tenant_id: str
    product: str
    use_case_id: str
    assessment_type: str = "release_gate"
    promotion_id: str = ""
    evaluation_id: str = ""
    artifact_id: str = ""
    requested_stage: str = ""
    risk_level: str = "medium"
    high_impact: bool = False
    external_auto_send: bool = False
    as_of: str = ""
    evidence_refs: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> GovernanceEvaluationRequest:
        reject_unsafe_evidence(row)
        return cls(
            tenant_id=required_non_empty_str(row, "tenant_id", "tenantId"),
            product=required_non_empty_str(row, "product", "product"),
            use_case_id=required_non_empty_str(row, "use_case_id", "useCaseId"),
            assessment_type=optional_string(
                row,
                "assessment_type",
                "assessmentType",
                default="release_gate",
            ),
            promotion_id=optional_string(row, "promotion_id", "promotionId", default=""),
            evaluation_id=optional_string(row, "evaluation_id", "evaluationId", default=""),
            artifact_id=optional_string(row, "artifact_id", "artifactId", default=""),
            requested_stage=optional_string(
                row,
                "requested_stage",
                "requestedStage",
                default="",
            ),
            risk_level=optional_string(row, "risk_level", "riskLevel", default="medium"),
            high_impact=optional_bool(row, "high_impact", "highImpact", default=False),
            external_auto_send=optional_bool(
                row,
                "external_auto_send",
                "externalAutoSend",
                default=False,
            ),
            as_of=optional_string(row, "as_of", "asOf", default=""),
            evidence_refs=normalize_string_tuple(
                row.get("evidence_refs", row.get("evidenceRefs", []))
            ),
        )


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationResponse:
    tenant_id: str
    product: str
    use_case_id: str
    assessment_type: str
    decision: str
    governance_status: str
    ready_for_release: bool
    requires_human_review: bool
    blocked_reasons: tuple[str, ...]
    reason_codes: tuple[str, ...]
    policy_id: str
    promotion_id: str
    artifact_id: str
    stage: str
    stage_group: str
    evaluation_ids: tuple[str, ...]
    evaluation_result_count: int
    evaluation_passed_count: int
    required_gate_count: int
    gate_ready_count: int
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifactId": self.artifact_id,
            "assessmentType": self.assessment_type,
            "blockedReasons": self.blocked_reasons,
            "decision": self.decision,
            "evaluationIds": self.evaluation_ids,
            "evaluationPassedCount": self.evaluation_passed_count,
            "evaluationResultCount": self.evaluation_result_count,
            "evidenceRefs": self.evidence_refs,
            "gateReadyCount": self.gate_ready_count,
            "governanceStatus": self.governance_status,
            "policyId": self.policy_id,
            "product": self.product,
            "promotionId": self.promotion_id,
            "readyForRelease": self.ready_for_release,
            "reasonCodes": self.reason_codes,
            "requiredGateCount": self.required_gate_count,
            "requiresHumanReview": self.requires_human_review,
            "stage": self.stage,
            "stageGroup": self.stage_group,
            "tenantId": self.tenant_id,
            "useCaseId": self.use_case_id,
        }


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationMetricsSnapshot:
    request_count: int
    assessment_count: int
    approved_count: int
    review_required_count: int
    blocked_count: int
    error_count: int
    direct_identifier_rejection_count: int
    secret_value_rejection_count: int
    by_product: dict[str, int]
    by_use_case: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "approvedCount": self.approved_count,
            "assessmentCount": self.assessment_count,
            "blockedCount": self.blocked_count,
            "byProduct": self.by_product,
            "byUseCase": self.by_use_case,
            "directIdentifierRejectionCount": self.direct_identifier_rejection_count,
            "errorCount": self.error_count,
            "requestCount": self.request_count,
            "reviewRequiredCount": self.review_required_count,
            "secretValueRejectionCount": self.secret_value_rejection_count,
        }


class GovernanceEvaluationMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.assessment_count = 0
        self.approved_count = 0
        self.review_required_count = 0
        self.blocked_count = 0
        self.error_count = 0
        self.direct_identifier_rejection_count = 0
        self.secret_value_rejection_count = 0
        self.by_product: dict[str, int] = {}
        self.by_use_case: dict[str, int] = {}

    def record_assessment(
        self,
        request: GovernanceEvaluationRequest,
        response: GovernanceEvaluationResponse,
    ) -> None:
        self.request_count += 1
        self.assessment_count += 1
        if response.decision == "approved":
            self.approved_count += 1
        elif response.decision == "review_required":
            self.review_required_count += 1
        elif response.decision == "blocked":
            self.blocked_count += 1
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

    def record_secret_value_rejection(self) -> None:
        self.request_count += 1
        self.error_count += 1
        self.secret_value_rejection_count += 1

    def snapshot(self) -> GovernanceEvaluationMetricsSnapshot:
        return GovernanceEvaluationMetricsSnapshot(
            request_count=self.request_count,
            assessment_count=self.assessment_count,
            approved_count=self.approved_count,
            review_required_count=self.review_required_count,
            blocked_count=self.blocked_count,
            error_count=self.error_count,
            direct_identifier_rejection_count=self.direct_identifier_rejection_count,
            secret_value_rejection_count=self.secret_value_rejection_count,
            by_product=dict(sorted(self.by_product.items())),
            by_use_case=dict(sorted(self.by_use_case.items())),
        )


class GovernanceEvaluationRuntime:
    """Policy-aware governance gate for AI release and promotion decisions."""

    def __init__(self, ai_root: Path | str) -> None:
        self.ai_root = Path(ai_root)
        self.policy = load_governance_evaluation_access_policy(self.ai_root)
        self.metrics = GovernanceEvaluationMetrics()

    def assess(
        self,
        row: Mapping[str, Any],
        principal: GovernanceEvaluationPrincipal | Mapping[str, Any] | None,
    ) -> GovernanceEvaluationResponse:
        try:
            request = GovernanceEvaluationRequest.from_dict(row)
            resolved_principal = normalize_principal(principal)
            self.require_assess_authorization(request, resolved_principal)
            response = self.build_assessment(request)
            self.metrics.record_assessment(request, response)
            return response
        except GovernanceEvaluationPrivacyError as exc:
            if "secret" in str(exc):
                self.metrics.record_secret_value_rejection()
            else:
                self.metrics.record_direct_identifier_rejection()
            raise
        except Exception:
            self.metrics.record_error()
            raise

    def require_assess_authorization(
        self,
        request: GovernanceEvaluationRequest,
        principal: GovernanceEvaluationPrincipal | None,
    ) -> None:
        if principal is None:
            return
        if GOVERNANCE_EVALUATION_ASSESS_SCOPE not in set(principal.scopes):
            raise GovernanceEvaluationServiceError(
                f"principal {principal.principal_id} lacks assess scope"
            )
        if principal.tenant_ids and request.tenant_id not in set(principal.tenant_ids):
            raise GovernanceEvaluationServiceError(
                f"tenant is not granted for principal {principal.principal_id}"
            )
        if principal.product_ids and request.product not in set(principal.product_ids):
            raise GovernanceEvaluationServiceError(
                f"product is not granted for principal {principal.principal_id}"
            )
        if principal.use_case_ids and request.use_case_id not in set(
            principal.use_case_ids
        ):
            raise GovernanceEvaluationServiceError(
                f"use case is not granted for principal {principal.principal_id}"
            )

    def build_assessment(
        self,
        request: GovernanceEvaluationRequest,
    ) -> GovernanceEvaluationResponse:
        evaluation_report = run_registered_evaluations(self.ai_root)
        evaluation_registry = load_evaluation_registry(self.ai_root)
        promotion_report = build_promotion_readiness_report(
            self.ai_root,
            as_of=request.as_of or None,
        )
        evaluation_results = resolve_evaluation_results(
            request,
            evaluation_report,
        )
        promotion = resolve_promotion(request, promotion_report)
        blocked_reasons = list(
            build_safety_blocked_reasons(request, self.policy)
        )
        reason_codes: list[str] = []
        evidence_refs = list(request.evidence_refs)
        stage = ""
        stage_group = ""
        promotion_id = ""
        artifact_id = request.artifact_id
        required_gate_count = 0
        gate_ready_count = 0
        ready_for_release = bool(evaluation_results) and all(
            result.passed for result in evaluation_results
        )

        if promotion is not None:
            promotion_id = promotion.promotion_id
            artifact_id = promotion.artifact_id
            stage = promotion.stage
            stage_group = promotion.stage_group
            required_gate_count = promotion.required_gate_count
            gate_ready_count = promotion.gate_ready_count
            ready_for_release = promotion.ready_for_stage
            blocked_reasons.extend(promotion.blocked_reasons)
            evidence_refs.extend([promotion.artifact_manifest])
            evidence_refs.extend(gate.path for gate in promotion.gates)
            reason_codes.extend(build_promotion_reason_codes(promotion))
        elif not evaluation_results:
            blocked_reasons.append("no_matching_evaluation_gate")
            ready_for_release = False

        failed_evaluations = tuple(
            result.evaluation_id for result in evaluation_results if not result.passed
        )
        if failed_evaluations:
            blocked_reasons.append("evaluation_gate_failed")
            ready_for_release = False

        evaluation_ids = tuple(result.evaluation_id for result in evaluation_results)
        evidence_refs.extend(
            registry_row["report"]
            for evaluation_id, registry_row in evaluation_registry.items()
            if evaluation_id in set(evaluation_ids)
        )

        blocked_reason_tuple = tuple(dedupe(blocked_reasons))
        requires_human_review = request_requires_human_review(
            request,
            stage_group=stage_group,
        )
        if blocked_reason_tuple:
            decision = "blocked"
            governance_status = "blocked_by_governance"
        elif requires_human_review:
            decision = "review_required"
            governance_status = "ready_for_human_review"
        else:
            decision = "approved"
            governance_status = "approved_for_release"

        if ready_for_release:
            reason_codes.append("quality_gates_ready")
        if requires_human_review:
            reason_codes.append("human_review_required")
        if request.external_auto_send:
            reason_codes.append("external_auto_send_forbidden")

        return GovernanceEvaluationResponse(
            tenant_id=request.tenant_id,
            product=request.product,
            use_case_id=request.use_case_id,
            assessment_type=request.assessment_type,
            decision=decision,
            governance_status=governance_status,
            ready_for_release=ready_for_release and decision != "blocked",
            requires_human_review=requires_human_review,
            blocked_reasons=blocked_reason_tuple,
            reason_codes=tuple(dedupe(reason_codes)),
            policy_id=self.policy.policy_id,
            promotion_id=promotion_id,
            artifact_id=artifact_id,
            stage=stage,
            stage_group=stage_group,
            evaluation_ids=evaluation_ids,
            evaluation_result_count=len(evaluation_results),
            evaluation_passed_count=sum(1 for result in evaluation_results if result.passed),
            required_gate_count=required_gate_count or len(evaluation_results),
            gate_ready_count=gate_ready_count
            or sum(1 for result in evaluation_results if result.passed),
            evidence_refs=tuple(dedupe(evidence_refs)),
        )

    def health(self) -> dict[str, Any]:
        registry = load_yaml(self.ai_root / "platform" / "evaluation" / "registry.yaml")
        promotions = load_yaml(
            self.ai_root / "platform" / "artifacts" / "promotions" / "registry.yaml"
        )
        return {
            "evaluationCount": len(registry.get("evaluations", [])),
            "policyId": self.policy.policy_id,
            "promotionCount": len(promotions.get("promotions", [])),
            "routeCount": len(GOVERNANCE_EVALUATION_ROUTE_SCOPES),
            "serviceStatus": "healthy",
        }

    def snapshot_metrics(self) -> GovernanceEvaluationMetricsSnapshot:
        return self.metrics.snapshot()


def resolve_evaluation_results(
    request: GovernanceEvaluationRequest,
    report: EvaluationRegistryReport,
) -> tuple[EvaluationRunResult, ...]:
    if request.evaluation_id:
        result = report.results.get(request.evaluation_id)
        if result is None:
            raise GovernanceEvaluationServiceError(
                f"evaluation is not registered: {request.evaluation_id}"
            )
        if result.product != request.product or result.use_case_id != request.use_case_id:
            raise GovernanceEvaluationServiceError(
                "evaluation product/use case does not match request"
            )
        return (result,)
    matches = tuple(
        result
        for result in report.results.values()
        if result.product == request.product and result.use_case_id == request.use_case_id
    )
    return tuple(sorted(matches, key=lambda item: item.evaluation_id))


def resolve_promotion(
    request: GovernanceEvaluationRequest,
    report: PromotionReadinessReport,
) -> PromotionReadinessItem | None:
    if request.promotion_id:
        for item in report.items:
            if item.promotion_id == request.promotion_id:
                ensure_promotion_matches_request(item, request)
                return item
        raise GovernanceEvaluationServiceError(
            f"promotion is not registered: {request.promotion_id}"
        )
    if request.artifact_id:
        for item in report.items:
            if item.artifact_id == request.artifact_id:
                ensure_promotion_matches_request(item, request)
                return item
        return None
    return None


def ensure_promotion_matches_request(
    item: PromotionReadinessItem,
    request: GovernanceEvaluationRequest,
) -> None:
    if item.product != request.product or item.use_case_id != request.use_case_id:
        raise GovernanceEvaluationServiceError(
            "promotion product/use case does not match request"
        )
    if request.requested_stage and item.stage != request.requested_stage:
        raise GovernanceEvaluationServiceError(
            "promotion stage does not match requested stage"
        )


def build_safety_blocked_reasons(
    request: GovernanceEvaluationRequest,
    policy: GovernanceEvaluationAccessPolicy,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if request.external_auto_send and not policy.external_auto_send_allowed:
        reasons.append("external_auto_send_forbidden")
    return tuple(reasons)


def build_promotion_reason_codes(item: PromotionReadinessItem) -> tuple[str, ...]:
    codes: list[str] = []
    if item.maker_checker_satisfied:
        codes.append("maker_checker_satisfied")
    if item.rollback_required and item.rollback_ready:
        codes.append("rollback_target_ready")
    if item.stage_group == "active":
        codes.append("active_monitoring")
    elif item.stage_group == "approved":
        codes.append("ready_to_activate")
    elif item.stage_group == "shadow":
        codes.append("shadow_monitoring")
    return tuple(codes)


def request_requires_human_review(
    request: GovernanceEvaluationRequest,
    *,
    stage_group: str,
) -> bool:
    high_risk = request.risk_level.strip().lower() in {"high", "critical"}
    human_review_use_cases = {
        "finance-document-intelligence",
        "finance-payment-fraud-scoring",
        "lms-auto-grading",
        "operations-routing-optimization",
        "support-agent-assist",
    }
    return (
        request.high_impact
        or high_risk
        or request.use_case_id in human_review_use_cases
        or stage_group in {"approved", "shadow"}
    )


def load_governance_evaluation_access_policy(
    ai_root: Path | str,
) -> GovernanceEvaluationAccessPolicy:
    root = Path(ai_root)
    data = load_yaml(
        root
        / "platform"
        / "governance"
        / "policies"
        / "governance-evaluation-access-policy.yaml"
    )
    policy_id = required_non_empty_str(data, "policy_id", "policyId")
    aliases = data.get("scope_aliases", {})
    if not isinstance(aliases, dict):
        raise RegistryValidationError("governance evaluation scope_aliases must be mapping")
    defaults = data.get("defaults", {})
    if defaults is None:
        defaults = {}
    if not isinstance(defaults, dict):
        raise RegistryValidationError("governance evaluation defaults must be mapping")
    principals: dict[str, GovernanceEvaluationPrincipalGrant] = {}
    rows = data.get("principals", [])
    if not isinstance(rows, list):
        raise RegistryValidationError("governance evaluation principals must be list")
    for row in rows:
        if not isinstance(row, dict):
            raise RegistryValidationError("governance evaluation principal must be mapping")
        principal_id = required_non_empty_str(row, "principal_id", "principalId")
        if principal_id in principals:
            raise RegistryValidationError(
                f"duplicate governance evaluation principal: {principal_id}"
            )
        raw_scopes = normalize_string_tuple(row.get("scopes", []))
        scopes = tuple(resolve_scope_alias(scope, aliases) for scope in raw_scopes)
        principals[principal_id] = GovernanceEvaluationPrincipalGrant(
            principal_id=principal_id,
            owner_role=required_non_empty_str(row, "owner_role", "ownerRole"),
            product=required_non_empty_str(row, "product", "product"),
            scopes=scopes,
            tenant_ids=normalize_string_tuple(row.get("tenant_ids", row.get("tenantIds"))),
            product_ids=normalize_string_tuple(row.get("product_ids", row.get("productIds"))),
            use_case_ids=normalize_string_tuple(
                row.get("use_case_ids", row.get("useCaseIds"))
            ),
        )
    return GovernanceEvaluationAccessPolicy(
        policy_id=policy_id,
        principals=principals,
        wildcard_scopes_allowed=bool(defaults.get("wildcard_scopes_allowed", False)),
        tenant_isolation_required=bool(defaults.get("tenant_isolation_required", True)),
        direct_identifier_submission_allowed=bool(
            defaults.get("direct_identifier_submission_allowed", False)
        ),
        secret_value_submission_allowed=bool(
            defaults.get("secret_value_submission_allowed", False)
        ),
        external_auto_send_allowed=bool(defaults.get("external_auto_send_allowed", False)),
    )


def load_evaluation_registry(ai_root: Path | str) -> dict[str, dict[str, Any]]:
    root = Path(ai_root)
    data = load_yaml(root / "platform" / "evaluation" / "registry.yaml")
    rows = data.get("evaluations", [])
    if not isinstance(rows, list):
        raise RegistryValidationError("evaluation registry evaluations must be a list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise RegistryValidationError("evaluation registry row must be a mapping")
        evaluation_id = required_non_empty_str(row, "id", "id")
        result[evaluation_id] = row
    return result


def normalize_principal(
    principal: GovernanceEvaluationPrincipal | Mapping[str, Any] | None,
) -> GovernanceEvaluationPrincipal | None:
    if principal is None:
        return None
    if isinstance(principal, GovernanceEvaluationPrincipal):
        return principal
    return GovernanceEvaluationPrincipal.from_dict(principal)


def reject_unsafe_evidence(row: Mapping[str, Any]) -> None:
    direct_keys = sorted(set(row) & set(DIRECT_IDENTIFIER_KEYS))
    if direct_keys:
        raise GovernanceEvaluationPrivacyError(
            "direct identifier evidence is forbidden: " + ", ".join(direct_keys)
        )
    secret_value_keys = {key.lower() for key in SECRET_VALUE_KEYS}
    secret_keys = sorted(key for key in row if key.lower() in secret_value_keys)
    if secret_keys:
        raise GovernanceEvaluationPrivacyError(
            "secret value evidence is forbidden: " + ", ".join(secret_keys)
        )


def resolve_scope_alias(scope: str, aliases: Mapping[str, Any]) -> str:
    resolved = aliases.get(scope, scope)
    if not isinstance(resolved, str) or not resolved.strip():
        raise RegistryValidationError(f"invalid governance evaluation scope: {scope}")
    if resolved == "*":
        raise RegistryValidationError("governance evaluation wildcard scopes are forbidden")
    return resolved.strip()


def required_non_empty_str(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise GovernanceEvaluationServiceError(
        "missing required string field: " + "/".join(keys)
    )


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
        raise GovernanceEvaluationServiceError(
            f"{snake_key}/{camel_key} must be a string"
        )
    return value.strip()


def optional_bool(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    *,
    default: bool,
) -> bool:
    value = row.get(snake_key, row.get(camel_key, default))
    if not isinstance(value, bool):
        raise GovernanceEvaluationServiceError(
            f"{snake_key}/{camel_key} must be a boolean"
        )
    return value


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list | tuple):
        raise GovernanceEvaluationServiceError("expected a string list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise GovernanceEvaluationServiceError("string list values must be non-empty")
        result.append(item.strip())
    return tuple(result)


def dedupe(values: list[str] | tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result

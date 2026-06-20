from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

CAUSAL_UPLIFT_EVALUATE_SCOPE = "internal:ai-platform:causal-uplift:evaluate"
CAUSAL_UPLIFT_OPS_SCOPE = "internal:ai-platform:causal-uplift:ops"
CAUSAL_UPLIFT_ROUTE_SCOPES = {
    ("POST", "/v1/causal-uplift/evaluate"): CAUSAL_UPLIFT_EVALUATE_SCOPE,
    ("GET", "/v1/causal-uplift/health"): CAUSAL_UPLIFT_OPS_SCOPE,
    ("GET", "/v1/causal-uplift/metrics"): CAUSAL_UPLIFT_OPS_SCOPE,
}
CAUSAL_UPLIFT_MODEL_RELATIVE_PATH = (
    "models/causal/causal_uplift_baseline/causal_uplift_baseline.py"
)
RAW_ID_KEYS = (
    "account_id",
    "accountId",
    "customer_id",
    "customerId",
    "device_id",
    "deviceId",
    "email",
    "emailAddress",
    "learner_id",
    "learnerId",
    "participant_id",
    "participantId",
    "phone",
    "phoneNumber",
    "student_id",
    "studentId",
    "subject_id",
    "subjectId",
    "user_id",
    "userId",
)


class CausalUpliftServiceError(ValueError):
    """Raised when causal uplift service input or policy is invalid."""


class CausalUpliftPrivacyError(CausalUpliftServiceError):
    """Raised when causal uplift requests submit direct identifiers."""


@dataclass(frozen=True, slots=True)
class CausalUpliftPrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    use_case_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> CausalUpliftPrincipal:
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
class CausalUpliftPrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    use_case_ids: tuple[str, ...]

    def resolve(self, requested_scopes: object | None = None) -> CausalUpliftPrincipal:
        scopes = (
            self.scopes
            if requested_scopes is None
            else normalize_string_tuple(requested_scopes)
        )
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise CausalUpliftServiceError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return CausalUpliftPrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            product_ids=self.product_ids,
            use_case_ids=self.use_case_ids,
        )


@dataclass(frozen=True, slots=True)
class CausalUpliftAccessPolicy:
    policy_id: str
    principals: Mapping[str, CausalUpliftPrincipalGrant]
    wildcard_scopes_allowed: bool = False
    tenant_isolation_required: bool = True
    direct_identifier_submission_allowed: bool = False
    automated_rollout_allowed: bool = False

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> CausalUpliftPrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise CausalUpliftServiceError(
                f"causal uplift principal is not registered: {principal_id}"
            )
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class CausalUpliftEvaluateRequest:
    tenant_id: str
    product: str
    use_case_id: str
    experiment_id: str
    outcome_name: str
    treatment_name: str
    control_name: str
    treatment_count: int
    treatment_successes: int
    control_count: int
    control_successes: int
    minimum_detectable_lift: float
    confidence_level: float
    guardrail_metric_delta: float
    high_impact: bool
    segment_count: int

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> CausalUpliftEvaluateRequest:
        reject_direct_identifiers(row)
        return cls(
            tenant_id=required_non_empty_str(row, "tenant_id", "tenantId"),
            product=required_non_empty_str(row, "product", "product"),
            use_case_id=required_non_empty_str(row, "use_case_id", "useCaseId"),
            experiment_id=required_non_empty_str(
                row,
                "experiment_id",
                "experimentId",
            ),
            outcome_name=required_non_empty_str(row, "outcome_name", "outcomeName"),
            treatment_name=required_non_empty_str(
                row,
                "treatment_name",
                "treatmentName",
            ),
            control_name=required_non_empty_str(row, "control_name", "controlName"),
            treatment_count=required_positive_int(
                row,
                "treatment_count",
                "treatmentCount",
            ),
            treatment_successes=required_non_negative_int(
                row,
                "treatment_successes",
                "treatmentSuccesses",
            ),
            control_count=required_positive_int(row, "control_count", "controlCount"),
            control_successes=required_non_negative_int(
                row,
                "control_successes",
                "controlSuccesses",
            ),
            minimum_detectable_lift=optional_bounded_float(
                row,
                "minimum_detectable_lift",
                "minimumDetectableLift",
                default=0.03,
                minimum=0.0,
                maximum=1.0,
            ),
            confidence_level=optional_bounded_float(
                row,
                "confidence_level",
                "confidenceLevel",
                default=0.95,
                minimum=0.5,
                maximum=0.99,
            ),
            guardrail_metric_delta=optional_float(
                row,
                "guardrail_metric_delta",
                "guardrailMetricDelta",
                default=0.0,
            ),
            high_impact=optional_bool(row, "high_impact", "highImpact", default=True),
            segment_count=optional_positive_int(
                row,
                "segment_count",
                "segmentCount",
                default=1,
            ),
        )

    def to_model_payload(self) -> dict[str, Any]:
        return {
            "confidence_level": self.confidence_level,
            "control_count": self.control_count,
            "control_name": self.control_name,
            "control_successes": self.control_successes,
            "experiment_id": self.experiment_id,
            "guardrail_metric_delta": self.guardrail_metric_delta,
            "high_impact": self.high_impact,
            "minimum_detectable_lift": self.minimum_detectable_lift,
            "outcome_name": self.outcome_name,
            "segment_count": self.segment_count,
            "tenant_id": self.tenant_id,
            "treatment_count": self.treatment_count,
            "treatment_name": self.treatment_name,
            "treatment_successes": self.treatment_successes,
        }


@dataclass(frozen=True, slots=True)
class CausalUpliftEvaluateResponse:
    tenant_id: str
    product: str
    use_case_id: str
    experiment_id: str
    outcome_name: str
    result: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.result)
        payload.update(
            {
                "automatedRolloutAllowed": False,
                "decisionPolicy": (
                    "aggregate_uplift_review_only_human_approval_before_rollout"
                ),
                "experimentId": self.experiment_id,
                "outcomeName": self.outcome_name,
                "product": self.product,
                "tenantId": self.tenant_id,
                "useCaseId": self.use_case_id,
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class CausalUpliftMetricsSnapshot:
    request_count: int
    evaluation_count: int
    error_count: int
    direct_identifier_rejection_count: int
    human_review_count: int
    high_impact_count: int
    positive_lift_count: int
    negative_lift_count: int
    guardrail_risk_count: int
    inconclusive_count: int
    by_product: dict[str, int]
    by_use_case: dict[str, int]
    by_decision_band: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "byDecisionBand": self.by_decision_band,
            "byProduct": self.by_product,
            "byUseCase": self.by_use_case,
            "directIdentifierRejectionCount": self.direct_identifier_rejection_count,
            "errorCount": self.error_count,
            "evaluationCount": self.evaluation_count,
            "guardrailRiskCount": self.guardrail_risk_count,
            "highImpactCount": self.high_impact_count,
            "humanReviewCount": self.human_review_count,
            "inconclusiveCount": self.inconclusive_count,
            "negativeLiftCount": self.negative_lift_count,
            "positiveLiftCount": self.positive_lift_count,
            "requestCount": self.request_count,
        }


class CausalUpliftMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.evaluation_count = 0
        self.error_count = 0
        self.direct_identifier_rejection_count = 0
        self.human_review_count = 0
        self.high_impact_count = 0
        self.positive_lift_count = 0
        self.negative_lift_count = 0
        self.guardrail_risk_count = 0
        self.inconclusive_count = 0
        self.by_product: dict[str, int] = {}
        self.by_use_case: dict[str, int] = {}
        self.by_decision_band: dict[str, int] = {}

    def record_evaluation(
        self,
        request: CausalUpliftEvaluateRequest,
        result: Mapping[str, Any],
    ) -> None:
        self.request_count += 1
        self.evaluation_count += 1
        self.by_product[request.product] = self.by_product.get(request.product, 0) + 1
        self.by_use_case[request.use_case_id] = (
            self.by_use_case.get(request.use_case_id, 0) + 1
        )
        decision_band = str(result.get("decisionBand", ""))
        self.by_decision_band[decision_band] = (
            self.by_decision_band.get(decision_band, 0) + 1
        )
        if request.high_impact:
            self.high_impact_count += 1
        if bool(result.get("requiresHumanReview")):
            self.human_review_count += 1
        if decision_band == "positive_lift":
            self.positive_lift_count += 1
        if decision_band == "negative_lift":
            self.negative_lift_count += 1
        if decision_band == "guardrail_risk":
            self.guardrail_risk_count += 1
        if decision_band == "inconclusive":
            self.inconclusive_count += 1

    def record_error(self, *, direct_identifier: bool = False) -> None:
        self.request_count += 1
        self.error_count += 1
        if direct_identifier:
            self.direct_identifier_rejection_count += 1

    def snapshot(self) -> CausalUpliftMetricsSnapshot:
        return CausalUpliftMetricsSnapshot(
            request_count=self.request_count,
            evaluation_count=self.evaluation_count,
            error_count=self.error_count,
            direct_identifier_rejection_count=self.direct_identifier_rejection_count,
            human_review_count=self.human_review_count,
            high_impact_count=self.high_impact_count,
            positive_lift_count=self.positive_lift_count,
            negative_lift_count=self.negative_lift_count,
            guardrail_risk_count=self.guardrail_risk_count,
            inconclusive_count=self.inconclusive_count,
            by_product=dict(sorted(self.by_product.items())),
            by_use_case=dict(sorted(self.by_use_case.items())),
            by_decision_band=dict(sorted(self.by_decision_band.items())),
        )


class CausalUpliftRuntime:
    """Policy-aware runtime for aggregate experiment uplift evaluation."""

    def __init__(self, ai_root: Path | str) -> None:
        self.ai_root = Path(ai_root)
        self.metrics = CausalUpliftMetrics()
        self.model = load_model_class(
            self.ai_root,
            CAUSAL_UPLIFT_MODEL_RELATIVE_PATH,
            "CausalUpliftBaseline",
            "courseflow_causal_uplift_baseline_runtime",
        )()

    def evaluate(
        self,
        request: CausalUpliftEvaluateRequest | Mapping[str, Any],
        principal: CausalUpliftPrincipal | Mapping[str, Any] | None = None,
    ) -> CausalUpliftEvaluateResponse:
        try:
            evaluate_request = (
                request
                if isinstance(request, CausalUpliftEvaluateRequest)
                else CausalUpliftEvaluateRequest.from_dict(request)
            )
            authorize_causal_uplift_evaluate(
                normalize_principal(principal),
                evaluate_request,
            )
            prediction = self.model.predict(evaluate_request.to_model_payload())
            result = dict(prediction.to_dict())
        except CausalUpliftPrivacyError:
            self.metrics.record_error(direct_identifier=True)
            raise
        except Exception:
            self.metrics.record_error()
            raise
        self.metrics.record_evaluation(evaluate_request, result)
        return CausalUpliftEvaluateResponse(
            tenant_id=evaluate_request.tenant_id,
            product=evaluate_request.product,
            use_case_id=evaluate_request.use_case_id,
            experiment_id=evaluate_request.experiment_id,
            outcome_name=evaluate_request.outcome_name,
            result=result,
        )

    def health(self) -> dict[str, Any]:
        return {
            "modelId": "causal-uplift-baseline-v1",
            "routeCount": len(CAUSAL_UPLIFT_ROUTE_SCOPES),
            "serviceStatus": "healthy",
        }

    def snapshot_metrics(self) -> CausalUpliftMetricsSnapshot:
        return self.metrics.snapshot()


def load_causal_uplift_access_policy(ai_root: Path | str) -> CausalUpliftAccessPolicy:
    root = Path(ai_root)
    policy_path = (
        root
        / "platform"
        / "governance"
        / "policies"
        / "causal-uplift-access-policy.yaml"
    )
    policy = load_yaml(policy_path)
    raw_scope_aliases = policy.get("scope_aliases", {})
    if not isinstance(raw_scope_aliases, dict):
        raise RegistryValidationError(f"{policy_path} must define mapping field scope_aliases")
    scope_aliases = {
        "evaluate": CAUSAL_UPLIFT_EVALUATE_SCOPE,
        "ops": CAUSAL_UPLIFT_OPS_SCOPE,
        **raw_scope_aliases,
    }
    grants: dict[str, CausalUpliftPrincipalGrant] = {}
    for row in require_mapping_list(policy, "principals", policy_path):
        principal_id = require_str(row, "principal_id", str(policy_path))
        if principal_id in grants:
            raise RegistryValidationError(f"{policy_path} duplicates principal: {principal_id}")
        product = require_str(row, "product", str(policy_path))
        product_ids = normalize_string_tuple(row.get("product_ids", [product]))
        grants[principal_id] = CausalUpliftPrincipalGrant(
            principal_id=principal_id,
            owner_role=require_str(row, "owner_role", str(policy_path)),
            product=product,
            scopes=tuple(
                sorted(
                    {
                        expand_causal_uplift_scope_alias(
                            scope,
                            scope_aliases,
                            policy_path,
                        )
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
    return CausalUpliftAccessPolicy(
        policy_id=require_str(policy, "policy_id", str(policy_path)),
        principals=dict(sorted(grants.items())),
        wildcard_scopes_allowed=bool(defaults.get("wildcard_scopes_allowed", False)),
        tenant_isolation_required=bool(defaults.get("tenant_isolation_required", True)),
        direct_identifier_submission_allowed=bool(
            defaults.get("direct_identifier_submission_allowed", False)
        ),
        automated_rollout_allowed=bool(defaults.get("automated_rollout_allowed", False)),
    )


def authorize_causal_uplift_evaluate(
    principal: CausalUpliftPrincipal | None,
    request: CausalUpliftEvaluateRequest,
) -> None:
    if principal is None:
        return
    if "*" in principal.scopes:
        raise CausalUpliftServiceError("wildcard causal uplift scopes are forbidden")
    if CAUSAL_UPLIFT_EVALUATE_SCOPE not in principal.scopes:
        raise CausalUpliftServiceError("causal uplift evaluate scope is required")
    if principal.tenant_ids and request.tenant_id not in principal.tenant_ids:
        raise CausalUpliftServiceError(
            "causal uplift tenant is not granted to principal"
        )
    if principal.product_ids and request.product not in principal.product_ids:
        raise CausalUpliftServiceError(
            "causal uplift product is not granted to principal"
        )
    if principal.use_case_ids and request.use_case_id not in principal.use_case_ids:
        raise CausalUpliftServiceError(
            "causal uplift use case is not granted to principal"
        )


def normalize_principal(
    principal: CausalUpliftPrincipal | Mapping[str, Any] | None,
) -> CausalUpliftPrincipal | None:
    if principal is None or isinstance(principal, CausalUpliftPrincipal):
        return principal
    return CausalUpliftPrincipal.from_dict(principal)


def load_model_class(
    ai_root: Path,
    relative_path: str,
    class_name: str,
    module_name: str,
) -> type[Any]:
    module_path = ai_root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise CausalUpliftServiceError(f"cannot load model module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    model_class = getattr(module, class_name, None)
    if model_class is None:
        raise CausalUpliftServiceError(
            f"model module {relative_path} does not define {class_name}"
        )
    return model_class


def reject_direct_identifiers(row: Mapping[str, Any]) -> None:
    for key in RAW_ID_KEYS:
        value = row.get(key)
        if value is not None and str(value).strip():
            raise CausalUpliftPrivacyError(
                "causal uplift request must use aggregate snapshots and must not "
                f"include direct identifier field {key}"
            )


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list | tuple):
        raise CausalUpliftServiceError(
            "causal uplift policy values must be strings or lists"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise CausalUpliftServiceError(
                "causal uplift policy list values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def expand_causal_uplift_scope_alias(
    scope: str,
    scope_aliases: Mapping[str, str],
    policy_path: Path,
) -> str:
    expanded = scope_aliases.get(scope, scope)
    if not expanded.startswith("internal:ai-platform:causal-uplift:"):
        raise RegistryValidationError(
            f"{policy_path} has unsupported causal uplift scope: {scope}"
        )
    return expanded


def required_non_empty_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise CausalUpliftServiceError(
            f"causal uplift request must define {snake_key} or {camel_key}"
        )
    return value.strip()


def required_positive_int(row: Mapping[str, Any], snake_key: str, camel_key: str) -> int:
    value = row.get(snake_key, row.get(camel_key))
    if isinstance(value, bool) or not isinstance(value, int):
        raise CausalUpliftServiceError(
            f"causal uplift request field {snake_key} or {camel_key} must be an integer"
        )
    if value <= 0:
        raise CausalUpliftServiceError(
            f"causal uplift request field {snake_key} or {camel_key} must be positive"
        )
    return value


def required_non_negative_int(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
) -> int:
    value = row.get(snake_key, row.get(camel_key))
    if isinstance(value, bool) or not isinstance(value, int):
        raise CausalUpliftServiceError(
            f"causal uplift request field {snake_key} or {camel_key} must be an integer"
        )
    if value < 0:
        raise CausalUpliftServiceError(
            f"causal uplift request field {snake_key} or {camel_key} must be non-negative"
        )
    return value


def optional_positive_int(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    *,
    default: int,
) -> int:
    if snake_key not in row and camel_key not in row:
        return default
    return required_positive_int(row, snake_key, camel_key)


def optional_float(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    *,
    default: float,
) -> float:
    if snake_key not in row and camel_key not in row:
        return default
    value = row.get(snake_key, row.get(camel_key))
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise CausalUpliftServiceError(
            f"causal uplift request field {snake_key} or {camel_key} must be numeric"
        )
    return float(value)


def optional_bounded_float(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    result = optional_float(row, snake_key, camel_key, default=default)
    if result < minimum or result > maximum:
        raise CausalUpliftServiceError(
            f"causal uplift request field {snake_key} or {camel_key} must be "
            f"between {minimum} and {maximum}"
        )
    return result


def optional_bool(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    *,
    default: bool,
) -> bool:
    if snake_key not in row and camel_key not in row:
        return default
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, bool):
        raise CausalUpliftServiceError(
            f"causal uplift request field {snake_key} or {camel_key} must be boolean"
        )
    return value


def require_mapping_list(
    row: Mapping[str, Any],
    key: str,
    path: Path,
) -> tuple[Mapping[str, Any], ...]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{path} must define list field {key}")
    result: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{path} {key}[{index}] must be a mapping")
        result.append(item)
    return tuple(result)

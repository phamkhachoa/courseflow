from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

SEQUENCE_RISK_SCORE_SCOPE = "internal:ai-platform:sequence-risk:score"
SEQUENCE_RISK_OPS_SCOPE = "internal:ai-platform:sequence-risk:ops"
SEQUENCE_RISK_ROUTE_SCOPES = {
    ("POST", "/v1/sequence-risk/score"): SEQUENCE_RISK_SCORE_SCOPE,
    ("GET", "/v1/sequence-risk/health"): SEQUENCE_RISK_OPS_SCOPE,
    ("GET", "/v1/sequence-risk/metrics"): SEQUENCE_RISK_OPS_SCOPE,
}
SEQUENCE_RISK_MODEL_RELATIVE_PATH = (
    "models/deep_learning/sequence_risk_baseline/sequence_risk_baseline.py"
)
RAW_ID_KEYS = (
    "learner_id",
    "learnerId",
    "student_id",
    "studentId",
    "user_id",
    "userId",
    "email",
    "emailAddress",
)


class SequenceRiskServiceError(ValueError):
    """Raised when sequence risk service input or policy is invalid."""


class SequenceRiskPrivacyError(SequenceRiskServiceError):
    """Raised when a sequence risk request submits direct identifiers."""


@dataclass(frozen=True, slots=True)
class SequenceRiskPrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    use_case_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> SequenceRiskPrincipal:
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
class SequenceRiskPrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    use_case_ids: tuple[str, ...]

    def resolve(self, requested_scopes: object | None = None) -> SequenceRiskPrincipal:
        scopes = (
            self.scopes
            if requested_scopes is None
            else normalize_string_tuple(requested_scopes)
        )
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise SequenceRiskServiceError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return SequenceRiskPrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            product_ids=self.product_ids,
            use_case_ids=self.use_case_ids,
        )


@dataclass(frozen=True, slots=True)
class SequenceRiskAccessPolicy:
    policy_id: str
    principals: Mapping[str, SequenceRiskPrincipalGrant]
    wildcard_scopes_allowed: bool = False
    tenant_isolation_required: bool = True
    direct_identifier_submission_allowed: bool = False

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> SequenceRiskPrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise SequenceRiskServiceError(
                f"sequence risk principal is not registered: {principal_id}"
            )
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class SequenceRiskScoreRequest:
    tenant_id: str
    product: str
    use_case_id: str
    subject_principal_hash: str
    sequence_id: str
    feature_snapshot_at: str
    events: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> SequenceRiskScoreRequest:
        reject_direct_identifiers(row)
        return cls(
            tenant_id=required_non_empty_str(row, "tenant_id", "tenantId"),
            product=required_non_empty_str(row, "product", "product"),
            use_case_id=required_non_empty_str(row, "use_case_id", "useCaseId"),
            subject_principal_hash=required_any_non_empty_str(
                row,
                ("subject_principal_hash", "subjectPrincipalHash"),
                ("learner_principal_hash", "learnerPrincipalHash"),
                owner="sequence risk request",
            ),
            sequence_id=required_any_non_empty_str(
                row,
                ("sequence_id", "sequenceId"),
                ("course_id", "courseId"),
                owner="sequence risk request",
            ),
            feature_snapshot_at=required_non_empty_str(
                row,
                "feature_snapshot_at",
                "featureSnapshotAt",
            ),
            events=required_mapping_sequence_any(
                row,
                "events",
                "events",
                "sequence risk request",
            ),
        )

    def to_model_payload(self) -> dict[str, Any]:
        return {
            "course_id": self.sequence_id,
            "events": [dict(event) for event in self.events],
            "feature_snapshot_at": self.feature_snapshot_at,
            "learner_principal_hash": self.subject_principal_hash,
            "tenant_id": self.tenant_id,
        }


@dataclass(frozen=True, slots=True)
class SequenceRiskScoreResponse:
    tenant_id: str
    product: str
    use_case_id: str
    subject_id: str
    sequence_id: str
    result: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.result)
        risk_band = str(payload.get("riskBand", ""))
        payload.update(
            {
                "interventionPolicy": "human_review_required_before_adverse_action",
                "product": self.product,
                "requiresHumanReview": risk_band in {"high", "medium"},
                "sequenceId": self.sequence_id,
                "subjectId": self.subject_id,
                "tenantId": self.tenant_id,
                "useCaseId": self.use_case_id,
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class SequenceRiskMetricsSnapshot:
    request_count: int
    score_count: int
    error_count: int
    direct_identifier_rejection_count: int
    high_risk_count: int
    human_review_count: int
    by_product: dict[str, int]
    by_use_case: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "byProduct": self.by_product,
            "byUseCase": self.by_use_case,
            "directIdentifierRejectionCount": self.direct_identifier_rejection_count,
            "errorCount": self.error_count,
            "highRiskCount": self.high_risk_count,
            "humanReviewCount": self.human_review_count,
            "requestCount": self.request_count,
            "scoreCount": self.score_count,
        }


class SequenceRiskMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.score_count = 0
        self.error_count = 0
        self.direct_identifier_rejection_count = 0
        self.high_risk_count = 0
        self.human_review_count = 0
        self.by_product: dict[str, int] = {}
        self.by_use_case: dict[str, int] = {}

    def record_score(self, request: SequenceRiskScoreRequest, result: Mapping[str, Any]) -> None:
        self.request_count += 1
        self.score_count += 1
        self.by_product[request.product] = self.by_product.get(request.product, 0) + 1
        self.by_use_case[request.use_case_id] = (
            self.by_use_case.get(request.use_case_id, 0) + 1
        )
        risk_band = str(result.get("riskBand", ""))
        if risk_band == "high":
            self.high_risk_count += 1
        if risk_band in {"high", "medium"}:
            self.human_review_count += 1

    def record_error(self, *, direct_identifier: bool = False) -> None:
        self.request_count += 1
        self.error_count += 1
        if direct_identifier:
            self.direct_identifier_rejection_count += 1

    def snapshot(self) -> SequenceRiskMetricsSnapshot:
        return SequenceRiskMetricsSnapshot(
            request_count=self.request_count,
            score_count=self.score_count,
            error_count=self.error_count,
            direct_identifier_rejection_count=self.direct_identifier_rejection_count,
            high_risk_count=self.high_risk_count,
            human_review_count=self.human_review_count,
            by_product=dict(sorted(self.by_product.items())),
            by_use_case=dict(sorted(self.by_use_case.items())),
        )


class SequenceRiskRuntime:
    """Policy-aware runtime for recurrent sequence risk scoring."""

    def __init__(self, ai_root: Path | str) -> None:
        self.ai_root = Path(ai_root)
        self.metrics = SequenceRiskMetrics()
        self.model = load_model_class(
            self.ai_root,
            SEQUENCE_RISK_MODEL_RELATIVE_PATH,
            "SequenceRiskBaseline",
            "courseflow_sequence_risk_baseline_runtime",
        )()

    def score(
        self,
        request: SequenceRiskScoreRequest | Mapping[str, Any],
        principal: SequenceRiskPrincipal | Mapping[str, Any] | None = None,
    ) -> SequenceRiskScoreResponse:
        try:
            score_request = (
                request
                if isinstance(request, SequenceRiskScoreRequest)
                else SequenceRiskScoreRequest.from_dict(request)
            )
            authorize_sequence_risk_score(normalize_principal(principal), score_request)
            prediction = self.model.predict(score_request.to_model_payload())
            result = dict(prediction.to_dict())
        except SequenceRiskPrivacyError:
            self.metrics.record_error(direct_identifier=True)
            raise
        except Exception:
            self.metrics.record_error()
            raise
        self.metrics.record_score(score_request, result)
        return SequenceRiskScoreResponse(
            tenant_id=score_request.tenant_id,
            product=score_request.product,
            use_case_id=score_request.use_case_id,
            subject_id=score_request.subject_principal_hash,
            sequence_id=score_request.sequence_id,
            result=result,
        )

    def health(self) -> dict[str, Any]:
        return {
            "modelId": "sequence-risk-baseline-v1",
            "routeCount": len(SEQUENCE_RISK_ROUTE_SCOPES),
            "serviceStatus": "healthy",
        }

    def snapshot_metrics(self) -> SequenceRiskMetricsSnapshot:
        return self.metrics.snapshot()


def load_sequence_risk_access_policy(ai_root: Path | str) -> SequenceRiskAccessPolicy:
    root = Path(ai_root)
    policy_path = (
        root / "platform" / "governance" / "policies" / "sequence-risk-access-policy.yaml"
    )
    policy = load_yaml(policy_path)
    raw_scope_aliases = policy.get("scope_aliases", {})
    if not isinstance(raw_scope_aliases, dict):
        raise RegistryValidationError(f"{policy_path} must define mapping field scope_aliases")
    scope_aliases = {
        "score": SEQUENCE_RISK_SCORE_SCOPE,
        "ops": SEQUENCE_RISK_OPS_SCOPE,
        **raw_scope_aliases,
    }
    grants: dict[str, SequenceRiskPrincipalGrant] = {}
    for row in require_mapping_list(policy, "principals", policy_path):
        principal_id = require_str(row, "principal_id", str(policy_path))
        if principal_id in grants:
            raise RegistryValidationError(f"{policy_path} duplicates principal: {principal_id}")
        product = require_str(row, "product", str(policy_path))
        product_ids = normalize_string_tuple(row.get("product_ids", [product]))
        grants[principal_id] = SequenceRiskPrincipalGrant(
            principal_id=principal_id,
            owner_role=require_str(row, "owner_role", str(policy_path)),
            product=product,
            scopes=tuple(
                sorted(
                    {
                        expand_sequence_risk_scope_alias(scope, scope_aliases, policy_path)
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
    return SequenceRiskAccessPolicy(
        policy_id=require_str(policy, "policy_id", str(policy_path)),
        principals=dict(sorted(grants.items())),
        wildcard_scopes_allowed=bool(defaults.get("wildcard_scopes_allowed", False)),
        tenant_isolation_required=bool(defaults.get("tenant_isolation_required", True)),
        direct_identifier_submission_allowed=bool(
            defaults.get("direct_identifier_submission_allowed", False)
        ),
    )


def authorize_sequence_risk_score(
    principal: SequenceRiskPrincipal | None,
    request: SequenceRiskScoreRequest,
) -> None:
    if principal is None:
        return
    if "*" in principal.scopes:
        raise SequenceRiskServiceError("wildcard sequence risk scopes are forbidden")
    if SEQUENCE_RISK_SCORE_SCOPE not in principal.scopes:
        raise SequenceRiskServiceError("sequence risk score scope is required")
    if principal.tenant_ids and request.tenant_id not in principal.tenant_ids:
        raise SequenceRiskServiceError("sequence risk tenant is not granted to principal")
    if principal.product_ids and request.product not in principal.product_ids:
        raise SequenceRiskServiceError("sequence risk product is not granted to principal")
    if principal.use_case_ids and request.use_case_id not in principal.use_case_ids:
        raise SequenceRiskServiceError("sequence risk use case is not granted to principal")


def normalize_principal(
    principal: SequenceRiskPrincipal | Mapping[str, Any] | None,
) -> SequenceRiskPrincipal | None:
    if principal is None or isinstance(principal, SequenceRiskPrincipal):
        return principal
    return SequenceRiskPrincipal.from_dict(principal)


def load_model_class(
    ai_root: Path,
    relative_path: str,
    class_name: str,
    module_name: str,
) -> type[Any]:
    module_path = ai_root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise SequenceRiskServiceError(f"cannot load model module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    model_class = getattr(module, class_name, None)
    if model_class is None:
        raise SequenceRiskServiceError(
            f"model module {relative_path} does not define {class_name}"
        )
    return model_class


def reject_direct_identifiers(row: Mapping[str, Any]) -> None:
    for key in RAW_ID_KEYS:
        value = row.get(key)
        if value is not None and str(value).strip():
            raise SequenceRiskPrivacyError(
                f"sequence risk request must not include direct identifier field {key}"
            )


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list | tuple):
        raise SequenceRiskServiceError("sequence risk policy values must be strings or lists")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise SequenceRiskServiceError(
                "sequence risk policy list values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def expand_sequence_risk_scope_alias(
    scope: str,
    scope_aliases: Mapping[str, str],
    policy_path: Path,
) -> str:
    expanded = scope_aliases.get(scope, scope)
    if not expanded.startswith("internal:ai-platform:sequence-risk:"):
        raise RegistryValidationError(f"{policy_path} has unsupported sequence risk scope: {scope}")
    return expanded


def required_non_empty_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise SequenceRiskServiceError(
            f"sequence risk request must define {snake_key} or {camel_key}"
        )
    return value.strip()


def required_any_non_empty_str(
    row: Mapping[str, Any],
    primary_keys: tuple[str, str],
    fallback_keys: tuple[str, str],
    *,
    owner: str,
) -> str:
    for key in (*primary_keys, *fallback_keys):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise SequenceRiskServiceError(
        f"{owner} must define {primary_keys[0]} or {fallback_keys[0]}"
    )


def required_mapping_sequence_any(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    owner: str,
) -> tuple[Mapping[str, Any], ...]:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, list | tuple):
        raise SequenceRiskServiceError(
            f"{owner} field {snake_key} or {camel_key} must be a list"
        )
    result: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise SequenceRiskServiceError(f"{owner} item {index} must be a mapping")
        result.append(item)
    return tuple(result)


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

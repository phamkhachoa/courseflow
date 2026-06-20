from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

FORECAST_SCORE_SCOPE = "internal:ai-platform:forecasting:score"
FORECAST_OPS_SCOPE = "internal:ai-platform:forecasting:ops"
FORECAST_ROUTE_SCOPES = {
    ("POST", "/v1/forecasting/demand/score"): FORECAST_SCORE_SCOPE,
    ("GET", "/v1/forecasting/health"): FORECAST_OPS_SCOPE,
    ("GET", "/v1/forecasting/metrics"): FORECAST_OPS_SCOPE,
}
FORECAST_MODEL_RELATIVE_PATH = (
    "models/forecasting/demand_forecast_baseline/demand_forecast_baseline.py"
)
RAW_ID_KEYS = (
    "agent_id",
    "agentId",
    "employee_id",
    "employeeId",
    "customer_id",
    "customerId",
    "learner_id",
    "learnerId",
    "student_id",
    "studentId",
    "email",
    "emailAddress",
    "phone",
    "phoneNumber",
)


class ForecastingServiceError(ValueError):
    """Raised when forecasting service input or policy is invalid."""


class ForecastingPrivacyError(ForecastingServiceError):
    """Raised when forecasting requests submit direct identifiers."""


@dataclass(frozen=True, slots=True)
class ForecastingPrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    use_case_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> ForecastingPrincipal:
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
class ForecastingPrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    use_case_ids: tuple[str, ...]

    def resolve(self, requested_scopes: object | None = None) -> ForecastingPrincipal:
        scopes = (
            self.scopes
            if requested_scopes is None
            else normalize_string_tuple(requested_scopes)
        )
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise ForecastingServiceError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return ForecastingPrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            product_ids=self.product_ids,
            use_case_ids=self.use_case_ids,
        )


@dataclass(frozen=True, slots=True)
class ForecastingAccessPolicy:
    policy_id: str
    principals: Mapping[str, ForecastingPrincipalGrant]
    wildcard_scopes_allowed: bool = False
    tenant_isolation_required: bool = True
    direct_identifier_submission_allowed: bool = False
    automated_capacity_change_allowed: bool = False

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> ForecastingPrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise ForecastingServiceError(
                f"forecasting principal is not registered: {principal_id}"
            )
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class DemandForecastScoreRequest:
    tenant_id: str
    product: str
    use_case_id: str
    forecast_id: str
    queue_id: str
    historical_demand: tuple[int, ...]
    planned_capacity: int
    backlog_open_items: int
    avg_handle_minutes: int
    seasonal_index: float
    special_event: bool
    incident_open: bool
    forecast_horizon_days: int
    service_level_target: float

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> DemandForecastScoreRequest:
        reject_direct_identifiers(row)
        return cls(
            tenant_id=required_non_empty_str(row, "tenant_id", "tenantId"),
            product=required_non_empty_str(row, "product", "product"),
            use_case_id=required_non_empty_str(row, "use_case_id", "useCaseId"),
            forecast_id=required_non_empty_str(row, "forecast_id", "forecastId"),
            queue_id=required_non_empty_str(row, "queue_id", "queueId"),
            historical_demand=required_int_sequence(
                row,
                "historical_demand",
                "historicalDemand",
            ),
            planned_capacity=required_non_negative_int(
                row,
                "planned_capacity",
                "plannedCapacity",
            ),
            backlog_open_items=optional_non_negative_int(
                row,
                "backlog_open_items",
                "backlogOpenItems",
                default=0,
            ),
            avg_handle_minutes=optional_positive_int(
                row,
                "avg_handle_minutes",
                "avgHandleMinutes",
                default=30,
            ),
            seasonal_index=optional_positive_float(
                row,
                "seasonal_index",
                "seasonalIndex",
                default=1.0,
            ),
            special_event=optional_bool(row, "special_event", "specialEvent"),
            incident_open=optional_bool(row, "incident_open", "incidentOpen"),
            forecast_horizon_days=optional_positive_int(
                row,
                "forecast_horizon_days",
                "forecastHorizonDays",
                default=7,
            ),
            service_level_target=optional_bounded_float(
                row,
                "service_level_target",
                "serviceLevelTarget",
                default=0.85,
                minimum=0.0,
                maximum=1.0,
            ),
        )

    def to_model_payload(self) -> dict[str, Any]:
        return {
            "avg_handle_minutes": self.avg_handle_minutes,
            "backlog_open_items": self.backlog_open_items,
            "forecast_horizon_days": self.forecast_horizon_days,
            "forecast_id": self.forecast_id,
            "historical_demand": list(self.historical_demand),
            "incident_open": self.incident_open,
            "planned_capacity": self.planned_capacity,
            "queue_id": self.queue_id,
            "seasonal_index": self.seasonal_index,
            "service_level_target": self.service_level_target,
            "special_event": self.special_event,
            "tenant_id": self.tenant_id,
        }


@dataclass(frozen=True, slots=True)
class DemandForecastScoreResponse:
    tenant_id: str
    product: str
    use_case_id: str
    forecast_id: str
    queue_id: str
    result: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.result)
        payload.update(
            {
                "automatedCapacityChangeAllowed": False,
                "decisionPolicy": (
                    "human_review_required_before_staffing_or_sla_impacting_action"
                ),
                "forecastId": self.forecast_id,
                "product": self.product,
                "queueId": self.queue_id,
                "tenantId": self.tenant_id,
                "useCaseId": self.use_case_id,
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class ForecastingMetricsSnapshot:
    request_count: int
    score_count: int
    error_count: int
    direct_identifier_rejection_count: int
    high_demand_count: int
    elevated_demand_count: int
    capacity_shortfall_count: int
    human_review_count: int
    by_product: dict[str, int]
    by_use_case: dict[str, int]
    by_demand_band: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "byDemandBand": self.by_demand_band,
            "byProduct": self.by_product,
            "byUseCase": self.by_use_case,
            "capacityShortfallCount": self.capacity_shortfall_count,
            "directIdentifierRejectionCount": self.direct_identifier_rejection_count,
            "elevatedDemandCount": self.elevated_demand_count,
            "errorCount": self.error_count,
            "highDemandCount": self.high_demand_count,
            "humanReviewCount": self.human_review_count,
            "requestCount": self.request_count,
            "scoreCount": self.score_count,
        }


class ForecastingMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.score_count = 0
        self.error_count = 0
        self.direct_identifier_rejection_count = 0
        self.high_demand_count = 0
        self.elevated_demand_count = 0
        self.capacity_shortfall_count = 0
        self.human_review_count = 0
        self.by_product: dict[str, int] = {}
        self.by_use_case: dict[str, int] = {}
        self.by_demand_band: dict[str, int] = {}

    def record_score(
        self,
        request: DemandForecastScoreRequest,
        result: Mapping[str, Any],
    ) -> None:
        self.request_count += 1
        self.score_count += 1
        self.by_product[request.product] = self.by_product.get(request.product, 0) + 1
        self.by_use_case[request.use_case_id] = (
            self.by_use_case.get(request.use_case_id, 0) + 1
        )
        demand_band = str(result.get("demandBand", ""))
        self.by_demand_band[demand_band] = (
            self.by_demand_band.get(demand_band, 0) + 1
        )
        if demand_band == "high":
            self.high_demand_count += 1
        if demand_band == "elevated":
            self.elevated_demand_count += 1
        capacity_gap = result.get("capacityGapUnits")
        if isinstance(capacity_gap, int) and capacity_gap > 0:
            self.capacity_shortfall_count += 1
        if bool(result.get("requiresHumanReview")):
            self.human_review_count += 1

    def record_error(self, *, direct_identifier: bool = False) -> None:
        self.request_count += 1
        self.error_count += 1
        if direct_identifier:
            self.direct_identifier_rejection_count += 1

    def snapshot(self) -> ForecastingMetricsSnapshot:
        return ForecastingMetricsSnapshot(
            request_count=self.request_count,
            score_count=self.score_count,
            error_count=self.error_count,
            direct_identifier_rejection_count=self.direct_identifier_rejection_count,
            high_demand_count=self.high_demand_count,
            elevated_demand_count=self.elevated_demand_count,
            capacity_shortfall_count=self.capacity_shortfall_count,
            human_review_count=self.human_review_count,
            by_product=dict(sorted(self.by_product.items())),
            by_use_case=dict(sorted(self.by_use_case.items())),
            by_demand_band=dict(sorted(self.by_demand_band.items())),
        )


class ForecastingRuntime:
    """Policy-aware runtime for demand forecasting and capacity planning."""

    def __init__(self, ai_root: Path | str) -> None:
        self.ai_root = Path(ai_root)
        self.metrics = ForecastingMetrics()
        self.model = load_model_class(
            self.ai_root,
            FORECAST_MODEL_RELATIVE_PATH,
            "DemandForecastBaseline",
            "courseflow_demand_forecast_baseline_runtime",
        )()

    def score(
        self,
        request: DemandForecastScoreRequest | Mapping[str, Any],
        principal: ForecastingPrincipal | Mapping[str, Any] | None = None,
    ) -> DemandForecastScoreResponse:
        try:
            score_request = (
                request
                if isinstance(request, DemandForecastScoreRequest)
                else DemandForecastScoreRequest.from_dict(request)
            )
            authorize_forecast_score(normalize_principal(principal), score_request)
            prediction = self.model.predict(score_request.to_model_payload())
            result = dict(prediction.to_dict())
        except ForecastingPrivacyError:
            self.metrics.record_error(direct_identifier=True)
            raise
        except Exception:
            self.metrics.record_error()
            raise
        self.metrics.record_score(score_request, result)
        return DemandForecastScoreResponse(
            tenant_id=score_request.tenant_id,
            product=score_request.product,
            use_case_id=score_request.use_case_id,
            forecast_id=score_request.forecast_id,
            queue_id=score_request.queue_id,
            result=result,
        )

    def health(self) -> dict[str, Any]:
        return {
            "modelId": "operations-demand-forecast-baseline-v1",
            "routeCount": len(FORECAST_ROUTE_SCOPES),
            "serviceStatus": "healthy",
        }

    def snapshot_metrics(self) -> ForecastingMetricsSnapshot:
        return self.metrics.snapshot()


def load_forecasting_access_policy(ai_root: Path | str) -> ForecastingAccessPolicy:
    root = Path(ai_root)
    policy_path = (
        root / "platform" / "governance" / "policies" / "forecasting-access-policy.yaml"
    )
    policy = load_yaml(policy_path)
    raw_scope_aliases = policy.get("scope_aliases", {})
    if not isinstance(raw_scope_aliases, dict):
        raise RegistryValidationError(f"{policy_path} must define mapping field scope_aliases")
    scope_aliases = {
        "score": FORECAST_SCORE_SCOPE,
        "ops": FORECAST_OPS_SCOPE,
        **raw_scope_aliases,
    }
    grants: dict[str, ForecastingPrincipalGrant] = {}
    for row in require_mapping_list(policy, "principals", policy_path):
        principal_id = require_str(row, "principal_id", str(policy_path))
        if principal_id in grants:
            raise RegistryValidationError(f"{policy_path} duplicates principal: {principal_id}")
        product = require_str(row, "product", str(policy_path))
        product_ids = normalize_string_tuple(row.get("product_ids", [product]))
        grants[principal_id] = ForecastingPrincipalGrant(
            principal_id=principal_id,
            owner_role=require_str(row, "owner_role", str(policy_path)),
            product=product,
            scopes=tuple(
                sorted(
                    {
                        expand_forecast_scope_alias(scope, scope_aliases, policy_path)
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
    return ForecastingAccessPolicy(
        policy_id=require_str(policy, "policy_id", str(policy_path)),
        principals=dict(sorted(grants.items())),
        wildcard_scopes_allowed=bool(defaults.get("wildcard_scopes_allowed", False)),
        tenant_isolation_required=bool(defaults.get("tenant_isolation_required", True)),
        direct_identifier_submission_allowed=bool(
            defaults.get("direct_identifier_submission_allowed", False)
        ),
        automated_capacity_change_allowed=bool(
            defaults.get("automated_capacity_change_allowed", False)
        ),
    )


def authorize_forecast_score(
    principal: ForecastingPrincipal | None,
    request: DemandForecastScoreRequest,
) -> None:
    if principal is None:
        return
    if "*" in principal.scopes:
        raise ForecastingServiceError("wildcard forecasting scopes are forbidden")
    if FORECAST_SCORE_SCOPE not in principal.scopes:
        raise ForecastingServiceError("forecasting score scope is required")
    if principal.tenant_ids and request.tenant_id not in principal.tenant_ids:
        raise ForecastingServiceError("forecasting tenant is not granted to principal")
    if principal.product_ids and request.product not in principal.product_ids:
        raise ForecastingServiceError("forecasting product is not granted to principal")
    if principal.use_case_ids and request.use_case_id not in principal.use_case_ids:
        raise ForecastingServiceError("forecasting use case is not granted to principal")


def normalize_principal(
    principal: ForecastingPrincipal | Mapping[str, Any] | None,
) -> ForecastingPrincipal | None:
    if principal is None or isinstance(principal, ForecastingPrincipal):
        return principal
    return ForecastingPrincipal.from_dict(principal)


def load_model_class(
    ai_root: Path,
    relative_path: str,
    class_name: str,
    module_name: str,
) -> type[Any]:
    module_path = ai_root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ForecastingServiceError(f"cannot load model module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    model_class = getattr(module, class_name, None)
    if model_class is None:
        raise ForecastingServiceError(
            f"model module {relative_path} does not define {class_name}"
        )
    return model_class


def reject_direct_identifiers(row: Mapping[str, Any]) -> None:
    for key in RAW_ID_KEYS:
        value = row.get(key)
        if value is not None and str(value).strip():
            raise ForecastingPrivacyError(
                f"forecasting request must not include direct identifier field {key}"
            )


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list | tuple):
        raise ForecastingServiceError("forecasting policy values must be strings or lists")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ForecastingServiceError(
                "forecasting policy list values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def expand_forecast_scope_alias(
    scope: str,
    scope_aliases: Mapping[str, str],
    policy_path: Path,
) -> str:
    expanded = scope_aliases.get(scope, scope)
    if not expanded.startswith("internal:ai-platform:forecasting:"):
        raise RegistryValidationError(
            f"{policy_path} has unsupported forecasting scope: {scope}"
        )
    return expanded


def required_non_empty_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise ForecastingServiceError(
            f"forecasting request must define {snake_key} or {camel_key}"
        )
    return value.strip()


def required_int_sequence(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
) -> tuple[int, ...]:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, list | tuple):
        raise ForecastingServiceError(
            f"forecasting request field {snake_key} or {camel_key} must be a list"
        )
    result: list[int] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, int):
            raise ForecastingServiceError(
                f"forecasting demand history item {index} must be an integer"
            )
        if item < 0:
            raise ForecastingServiceError(
                f"forecasting demand history item {index} must be non-negative"
            )
        result.append(item)
    return tuple(result)


def required_non_negative_int(row: Mapping[str, Any], snake_key: str, camel_key: str) -> int:
    value = row.get(snake_key, row.get(camel_key))
    if isinstance(value, bool) or not isinstance(value, int):
        raise ForecastingServiceError(
            f"forecasting request field {snake_key} or {camel_key} must be an integer"
        )
    if value < 0:
        raise ForecastingServiceError(
            f"forecasting request field {snake_key} or {camel_key} must be non-negative"
        )
    return value


def optional_non_negative_int(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    *,
    default: int,
) -> int:
    if snake_key not in row and camel_key not in row:
        return default
    return required_non_negative_int(row, snake_key, camel_key)


def optional_positive_int(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    *,
    default: int,
) -> int:
    if snake_key not in row and camel_key not in row:
        return default
    value = row.get(snake_key, row.get(camel_key))
    if isinstance(value, bool) or not isinstance(value, int):
        raise ForecastingServiceError(
            f"forecasting request field {snake_key} or {camel_key} must be an integer"
        )
    if value <= 0:
        raise ForecastingServiceError(
            f"forecasting request field {snake_key} or {camel_key} must be positive"
        )
    return value


def optional_positive_float(
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
        raise ForecastingServiceError(
            f"forecasting request field {snake_key} or {camel_key} must be numeric"
        )
    result = float(value)
    if result <= 0:
        raise ForecastingServiceError(
            f"forecasting request field {snake_key} or {camel_key} must be positive"
        )
    return result


def optional_bounded_float(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    if snake_key not in row and camel_key not in row:
        return default
    value = row.get(snake_key, row.get(camel_key))
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ForecastingServiceError(
            f"forecasting request field {snake_key} or {camel_key} must be numeric"
        )
    result = float(value)
    if result < minimum or result > maximum:
        raise ForecastingServiceError(
            f"forecasting request field {snake_key} or {camel_key} must be bounded"
        )
    return result


def optional_bool(row: Mapping[str, Any], snake_key: str, camel_key: str) -> bool:
    value = row.get(snake_key, row.get(camel_key, False))
    if not isinstance(value, bool):
        raise ForecastingServiceError(
            f"forecasting request field {snake_key} or {camel_key} must be boolean"
        )
    return value


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

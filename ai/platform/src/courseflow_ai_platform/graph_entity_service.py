from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

GRAPH_ENTITY_ANALYZE_SCOPE = "internal:ai-platform:graph-entity:analyze"
GRAPH_ENTITY_OPS_SCOPE = "internal:ai-platform:graph-entity:ops"
GRAPH_ENTITY_ROUTE_SCOPES = {
    ("POST", "/v1/graph-entity/analyze"): GRAPH_ENTITY_ANALYZE_SCOPE,
    ("GET", "/v1/graph-entity/health"): GRAPH_ENTITY_OPS_SCOPE,
    ("GET", "/v1/graph-entity/metrics"): GRAPH_ENTITY_OPS_SCOPE,
}
GRAPH_ENTITY_MODEL_RELATIVE_PATH = (
    "models/anomaly_fraud/payment_fraud_baseline/payment_fraud_baseline.py"
)
RAW_ID_KEYS = (
    "account_id",
    "accountId",
    "counterparty_id",
    "counterpartyId",
    "customer_id",
    "customerId",
    "device_id",
    "deviceId",
    "email",
    "emailAddress",
    "employee_id",
    "employeeId",
    "learner_id",
    "learnerId",
    "phone",
    "phoneNumber",
    "student_id",
    "studentId",
    "user_id",
    "userId",
)


class GraphEntityServiceError(ValueError):
    """Raised when graph entity service input or policy is invalid."""


class GraphEntityPrivacyError(GraphEntityServiceError):
    """Raised when graph entity requests submit direct identifiers."""


@dataclass(frozen=True, slots=True)
class GraphEntityPrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    use_case_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> GraphEntityPrincipal:
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
class GraphEntityPrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    use_case_ids: tuple[str, ...]

    def resolve(self, requested_scopes: object | None = None) -> GraphEntityPrincipal:
        scopes = (
            self.scopes
            if requested_scopes is None
            else normalize_string_tuple(requested_scopes)
        )
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise GraphEntityServiceError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return GraphEntityPrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            product_ids=self.product_ids,
            use_case_ids=self.use_case_ids,
        )


@dataclass(frozen=True, slots=True)
class GraphEntityAccessPolicy:
    policy_id: str
    principals: Mapping[str, GraphEntityPrincipalGrant]
    wildcard_scopes_allowed: bool = False
    tenant_isolation_required: bool = True
    direct_identifier_submission_allowed: bool = False
    automated_adverse_action_allowed: bool = False

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> GraphEntityPrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise GraphEntityServiceError(
                f"graph entity principal is not registered: {principal_id}"
            )
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class GraphEntityAnalyzeRequest:
    tenant_id: str
    product: str
    use_case_id: str
    graph_context_id: str
    account_hash: str
    counterparty_hash: str
    device_fingerprint_hash: str
    linked_account_count: int
    shared_counterparty_count: int
    velocity_1h: int
    velocity_24h: int
    prior_failed_attempts_7d: int
    prior_chargeback_count: int
    amount_minor: int
    account_age_days: int
    verified_payment_methods_count: int
    currency: str
    payment_method: str
    country_code: str
    risk_review_outcome: str

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> GraphEntityAnalyzeRequest:
        reject_direct_identifiers(row)
        return cls(
            tenant_id=required_non_empty_str(row, "tenant_id", "tenantId"),
            product=required_non_empty_str(row, "product", "product"),
            use_case_id=required_non_empty_str(row, "use_case_id", "useCaseId"),
            graph_context_id=required_non_empty_str(
                row,
                "graph_context_id",
                "graphContextId",
            ),
            account_hash=required_hash_str(row, "account_hash", "accountHash"),
            counterparty_hash=required_hash_str(
                row,
                "counterparty_hash",
                "counterpartyHash",
            ),
            device_fingerprint_hash=required_hash_str(
                row,
                "device_fingerprint_hash",
                "deviceFingerprintHash",
            ),
            linked_account_count=required_non_negative_int(
                row,
                "linked_account_count",
                "linkedAccountCount",
            ),
            shared_counterparty_count=required_non_negative_int(
                row,
                "shared_counterparty_count",
                "sharedCounterpartyCount",
            ),
            velocity_1h=optional_non_negative_int(
                row,
                "velocity_1h",
                "velocity1h",
                default=0,
            ),
            velocity_24h=optional_non_negative_int(
                row,
                "velocity_24h",
                "velocity24h",
                default=0,
            ),
            prior_failed_attempts_7d=optional_non_negative_int(
                row,
                "prior_failed_attempts_7d",
                "priorFailedAttempts7d",
                default=0,
            ),
            prior_chargeback_count=optional_non_negative_int(
                row,
                "prior_chargeback_count",
                "priorChargebackCount",
                default=0,
            ),
            amount_minor=optional_non_negative_int(
                row,
                "amount_minor",
                "amountMinor",
                default=0,
            ),
            account_age_days=optional_non_negative_int(
                row,
                "account_age_days",
                "accountAgeDays",
                default=90,
            ),
            verified_payment_methods_count=optional_non_negative_int(
                row,
                "verified_payment_methods_count",
                "verifiedPaymentMethodsCount",
                default=1,
            ),
            currency=optional_non_empty_str(row, "currency", "currency", default="USD")
            .upper(),
            payment_method=optional_non_empty_str(
                row,
                "payment_method",
                "paymentMethod",
                default="card",
            ).lower(),
            country_code=optional_non_empty_str(
                row,
                "country_code",
                "countryCode",
                default="US",
            ).upper(),
            risk_review_outcome=optional_non_empty_str(
                row,
                "risk_review_outcome",
                "riskReviewOutcome",
                default="none",
            ).lower(),
        )

    def to_model_payload(self) -> dict[str, Any]:
        return {
            "account_age_days": self.account_age_days,
            "account_hash": self.account_hash,
            "amount_minor": self.amount_minor,
            "counterparty_hash": self.counterparty_hash,
            "country_code": self.country_code,
            "currency": self.currency,
            "device_fingerprint_hash": self.device_fingerprint_hash,
            "linked_account_count": self.linked_account_count,
            "payment_id": self.graph_context_id,
            "payment_method": self.payment_method,
            "prior_chargeback_count": self.prior_chargeback_count,
            "prior_failed_attempts_7d": self.prior_failed_attempts_7d,
            "risk_review_outcome": self.risk_review_outcome,
            "shared_counterparty_count": self.shared_counterparty_count,
            "tenant_id": self.tenant_id,
            "velocity_1h": self.velocity_1h,
            "velocity_24h": self.velocity_24h,
            "verified_payment_methods_count": self.verified_payment_methods_count,
        }


@dataclass(frozen=True, slots=True)
class GraphEntityAnalyzeResponse:
    tenant_id: str
    product: str
    use_case_id: str
    graph_context_id: str
    result: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        reason_codes = tuple(str(code) for code in self.result.get("reasonCodes", ()))
        links = self.result.get("entityLinkEvidence", [])
        link_count = len(links) if isinstance(links, list) else 0
        risk_band = str(self.result.get("riskBand", ""))
        graph_review_required = bool(self.result.get("requiresHumanReview")) or any(
            code
            in {
                "SHARED_COUNTERPARTY_NETWORK",
                "LINKED_ACCOUNT_CLUSTER",
                "FAILED_ATTEMPT_SPIKE",
            }
            for code in reason_codes
        )
        return {
            "adverseActionAllowed": False,
            "decisionPolicy": "graph_evidence_only_human_review_before_adverse_action",
            "entityLinkEvidence": links,
            "graphContextId": self.graph_context_id,
            "graphReviewRequired": graph_review_required,
            "linkCount": link_count,
            "modelId": str(self.result.get("modelId", "")),
            "product": self.product,
            "reasonCodes": list(reason_codes),
            "riskBand": risk_band,
            "riskScore": self.result.get("riskScore"),
            "tenantId": self.tenant_id,
            "useCaseId": self.use_case_id,
        }


@dataclass(frozen=True, slots=True)
class GraphEntityMetricsSnapshot:
    request_count: int
    analysis_count: int
    error_count: int
    direct_identifier_rejection_count: int
    graph_review_count: int
    strong_link_count: int
    medium_link_count: int
    weak_link_count: int
    by_product: dict[str, int]
    by_use_case: dict[str, int]
    by_link_type: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysisCount": self.analysis_count,
            "byLinkType": self.by_link_type,
            "byProduct": self.by_product,
            "byUseCase": self.by_use_case,
            "directIdentifierRejectionCount": self.direct_identifier_rejection_count,
            "errorCount": self.error_count,
            "graphReviewCount": self.graph_review_count,
            "mediumLinkCount": self.medium_link_count,
            "requestCount": self.request_count,
            "strongLinkCount": self.strong_link_count,
            "weakLinkCount": self.weak_link_count,
        }


class GraphEntityMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.analysis_count = 0
        self.error_count = 0
        self.direct_identifier_rejection_count = 0
        self.graph_review_count = 0
        self.strong_link_count = 0
        self.medium_link_count = 0
        self.weak_link_count = 0
        self.by_product: dict[str, int] = {}
        self.by_use_case: dict[str, int] = {}
        self.by_link_type: dict[str, int] = {}

    def record_analysis(
        self,
        request: GraphEntityAnalyzeRequest,
        response: GraphEntityAnalyzeResponse,
    ) -> None:
        payload = response.to_dict()
        self.request_count += 1
        self.analysis_count += 1
        self.by_product[request.product] = self.by_product.get(request.product, 0) + 1
        self.by_use_case[request.use_case_id] = (
            self.by_use_case.get(request.use_case_id, 0) + 1
        )
        if bool(payload.get("graphReviewRequired")):
            self.graph_review_count += 1
        links = payload.get("entityLinkEvidence", [])
        if isinstance(links, list):
            for link in links:
                if not isinstance(link, dict):
                    continue
                link_type = str(link.get("linkType", ""))
                if link_type:
                    self.by_link_type[link_type] = self.by_link_type.get(link_type, 0) + 1
                strength = str(link.get("strength", ""))
                if strength == "strong":
                    self.strong_link_count += 1
                if strength == "medium":
                    self.medium_link_count += 1
                if strength == "weak":
                    self.weak_link_count += 1

    def record_error(self, *, direct_identifier: bool = False) -> None:
        self.request_count += 1
        self.error_count += 1
        if direct_identifier:
            self.direct_identifier_rejection_count += 1

    def snapshot(self) -> GraphEntityMetricsSnapshot:
        return GraphEntityMetricsSnapshot(
            request_count=self.request_count,
            analysis_count=self.analysis_count,
            error_count=self.error_count,
            direct_identifier_rejection_count=self.direct_identifier_rejection_count,
            graph_review_count=self.graph_review_count,
            strong_link_count=self.strong_link_count,
            medium_link_count=self.medium_link_count,
            weak_link_count=self.weak_link_count,
            by_product=dict(sorted(self.by_product.items())),
            by_use_case=dict(sorted(self.by_use_case.items())),
            by_link_type=dict(sorted(self.by_link_type.items())),
        )


class GraphEntityRuntime:
    """Policy-aware runtime for entity-link evidence and graph risk triage."""

    def __init__(self, ai_root: Path | str) -> None:
        self.ai_root = Path(ai_root)
        self.metrics = GraphEntityMetrics()
        self.model = load_model_class(
            self.ai_root,
            GRAPH_ENTITY_MODEL_RELATIVE_PATH,
            "PaymentFraudRiskBaseline",
            "courseflow_graph_entity_payment_fraud_runtime",
        )()

    def analyze(
        self,
        request: GraphEntityAnalyzeRequest | Mapping[str, Any],
        principal: GraphEntityPrincipal | Mapping[str, Any] | None = None,
    ) -> GraphEntityAnalyzeResponse:
        try:
            analyze_request = (
                request
                if isinstance(request, GraphEntityAnalyzeRequest)
                else GraphEntityAnalyzeRequest.from_dict(request)
            )
            authorize_graph_entity_analyze(
                normalize_principal(principal),
                analyze_request,
            )
            prediction = self.model.predict(analyze_request.to_model_payload())
            result = dict(prediction.to_dict())
        except GraphEntityPrivacyError:
            self.metrics.record_error(direct_identifier=True)
            raise
        except Exception:
            self.metrics.record_error()
            raise
        response = GraphEntityAnalyzeResponse(
            tenant_id=analyze_request.tenant_id,
            product=analyze_request.product,
            use_case_id=analyze_request.use_case_id,
            graph_context_id=analyze_request.graph_context_id,
            result=result,
        )
        self.metrics.record_analysis(analyze_request, response)
        return response

    def health(self) -> dict[str, Any]:
        return {
            "modelId": "finance-payment-fraud-baseline-v1",
            "routeCount": len(GRAPH_ENTITY_ROUTE_SCOPES),
            "serviceStatus": "healthy",
        }

    def snapshot_metrics(self) -> GraphEntityMetricsSnapshot:
        return self.metrics.snapshot()


def load_graph_entity_access_policy(ai_root: Path | str) -> GraphEntityAccessPolicy:
    root = Path(ai_root)
    policy_path = (
        root
        / "platform"
        / "governance"
        / "policies"
        / "graph-entity-access-policy.yaml"
    )
    policy = load_yaml(policy_path)
    raw_scope_aliases = policy.get("scope_aliases", {})
    if not isinstance(raw_scope_aliases, dict):
        raise RegistryValidationError(f"{policy_path} must define mapping field scope_aliases")
    scope_aliases = {
        "analyze": GRAPH_ENTITY_ANALYZE_SCOPE,
        "ops": GRAPH_ENTITY_OPS_SCOPE,
        **raw_scope_aliases,
    }
    grants: dict[str, GraphEntityPrincipalGrant] = {}
    for row in require_mapping_list(policy, "principals", policy_path):
        principal_id = require_str(row, "principal_id", str(policy_path))
        if principal_id in grants:
            raise RegistryValidationError(f"{policy_path} duplicates principal: {principal_id}")
        product = require_str(row, "product", str(policy_path))
        product_ids = normalize_string_tuple(row.get("product_ids", [product]))
        grants[principal_id] = GraphEntityPrincipalGrant(
            principal_id=principal_id,
            owner_role=require_str(row, "owner_role", str(policy_path)),
            product=product,
            scopes=tuple(
                sorted(
                    {
                        expand_graph_entity_scope_alias(scope, scope_aliases, policy_path)
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
    return GraphEntityAccessPolicy(
        policy_id=require_str(policy, "policy_id", str(policy_path)),
        principals=dict(sorted(grants.items())),
        wildcard_scopes_allowed=bool(defaults.get("wildcard_scopes_allowed", False)),
        tenant_isolation_required=bool(defaults.get("tenant_isolation_required", True)),
        direct_identifier_submission_allowed=bool(
            defaults.get("direct_identifier_submission_allowed", False)
        ),
        automated_adverse_action_allowed=bool(
            defaults.get("automated_adverse_action_allowed", False)
        ),
    )


def authorize_graph_entity_analyze(
    principal: GraphEntityPrincipal | None,
    request: GraphEntityAnalyzeRequest,
) -> None:
    if principal is None:
        return
    if "*" in principal.scopes:
        raise GraphEntityServiceError("wildcard graph entity scopes are forbidden")
    if GRAPH_ENTITY_ANALYZE_SCOPE not in principal.scopes:
        raise GraphEntityServiceError("graph entity analyze scope is required")
    if principal.tenant_ids and request.tenant_id not in principal.tenant_ids:
        raise GraphEntityServiceError("graph entity tenant is not granted to principal")
    if principal.product_ids and request.product not in principal.product_ids:
        raise GraphEntityServiceError("graph entity product is not granted to principal")
    if principal.use_case_ids and request.use_case_id not in principal.use_case_ids:
        raise GraphEntityServiceError("graph entity use case is not granted to principal")


def normalize_principal(
    principal: GraphEntityPrincipal | Mapping[str, Any] | None,
) -> GraphEntityPrincipal | None:
    if principal is None or isinstance(principal, GraphEntityPrincipal):
        return principal
    return GraphEntityPrincipal.from_dict(principal)


def load_model_class(
    ai_root: Path,
    relative_path: str,
    class_name: str,
    module_name: str,
) -> type[Any]:
    module_path = ai_root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise GraphEntityServiceError(f"cannot load model module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    model_class = getattr(module, class_name, None)
    if model_class is None:
        raise GraphEntityServiceError(
            f"model module {relative_path} does not define {class_name}"
        )
    return model_class


def reject_direct_identifiers(row: Mapping[str, Any]) -> None:
    for key in RAW_ID_KEYS:
        value = row.get(key)
        if value is not None and str(value).strip():
            raise GraphEntityPrivacyError(
                "graph entity request must use pseudonymous hashes and must not "
                f"include direct identifier field {key}"
            )


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list | tuple):
        raise GraphEntityServiceError(
            "graph entity policy values must be strings or lists"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise GraphEntityServiceError(
                "graph entity policy list values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def expand_graph_entity_scope_alias(
    scope: str,
    scope_aliases: Mapping[str, str],
    policy_path: Path,
) -> str:
    expanded = scope_aliases.get(scope, scope)
    if not expanded.startswith("internal:ai-platform:graph-entity:"):
        raise RegistryValidationError(
            f"{policy_path} has unsupported graph entity scope: {scope}"
        )
    return expanded


def required_non_empty_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise GraphEntityServiceError(
            f"graph entity request must define {snake_key} or {camel_key}"
        )
    return value.strip()


def optional_non_empty_str(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    *,
    default: str,
) -> str:
    if snake_key not in row and camel_key not in row:
        return default
    return required_non_empty_str(row, snake_key, camel_key)


def required_hash_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = required_non_empty_str(row, snake_key, camel_key)
    if "@" in value or " " in value or value.startswith("+"):
        raise GraphEntityPrivacyError(
            f"graph entity request field {snake_key} or {camel_key} must be pseudonymous"
        )
    return value


def required_non_negative_int(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
) -> int:
    value = row.get(snake_key, row.get(camel_key))
    if isinstance(value, bool) or not isinstance(value, int):
        raise GraphEntityServiceError(
            f"graph entity request field {snake_key} or {camel_key} must be an integer"
        )
    if value < 0:
        raise GraphEntityServiceError(
            f"graph entity request field {snake_key} or {camel_key} must be non-negative"
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

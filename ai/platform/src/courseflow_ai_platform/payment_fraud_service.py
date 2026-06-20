from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

PAYMENT_FRAUD_SCORE_SCOPE = "internal:ai-platform:payment-fraud:score"
PAYMENT_FRAUD_OPS_SCOPE = "internal:ai-platform:payment-fraud:ops"
PAYMENT_FRAUD_ROUTE_SCOPES = {
    ("POST", "/v1/payment-fraud/score"): PAYMENT_FRAUD_SCORE_SCOPE,
    ("GET", "/v1/payment-fraud/health"): PAYMENT_FRAUD_OPS_SCOPE,
    ("GET", "/v1/payment-fraud/metrics"): PAYMENT_FRAUD_OPS_SCOPE,
}
PAYMENT_FRAUD_MODEL_RELATIVE_PATH = (
    "models/anomaly_fraud/payment_fraud_baseline/payment_fraud_baseline.py"
)
RAW_ID_KEYS = (
    "account_id",
    "accountId",
    "account_number",
    "accountNumber",
    "counterparty_id",
    "counterpartyId",
    "device_id",
    "deviceId",
    "email",
    "emailAddress",
    "phone",
    "phoneNumber",
    "payer_name",
    "payerName",
)
HASH_FIELD_KEYS = (
    ("account_hash", "accountHash"),
    ("counterparty_hash", "counterpartyHash"),
    ("device_fingerprint_hash", "deviceFingerprintHash"),
)


class PaymentFraudServiceError(ValueError):
    """Raised when payment fraud service input or policy is invalid."""


class PaymentFraudPrivacyError(PaymentFraudServiceError):
    """Raised when payment fraud requests submit direct identifiers."""


@dataclass(frozen=True, slots=True)
class PaymentFraudPrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    use_case_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> PaymentFraudPrincipal:
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
class PaymentFraudPrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    use_case_ids: tuple[str, ...]

    def resolve(self, requested_scopes: object | None = None) -> PaymentFraudPrincipal:
        scopes = (
            self.scopes
            if requested_scopes is None
            else normalize_string_tuple(requested_scopes)
        )
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise PaymentFraudServiceError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return PaymentFraudPrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            product_ids=self.product_ids,
            use_case_ids=self.use_case_ids,
        )


@dataclass(frozen=True, slots=True)
class PaymentFraudAccessPolicy:
    policy_id: str
    principals: Mapping[str, PaymentFraudPrincipalGrant]
    wildcard_scopes_allowed: bool = False
    tenant_isolation_required: bool = True
    direct_identifier_submission_allowed: bool = False
    automated_adverse_action_allowed: bool = False

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> PaymentFraudPrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise PaymentFraudServiceError(
                f"payment fraud principal is not registered: {principal_id}"
            )
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class PaymentFraudScoreRequest:
    tenant_id: str
    product: str
    use_case_id: str
    payment_id: str
    account_hash: str
    counterparty_hash: str
    amount_minor: int
    currency: str
    payment_method: str
    country_code: str
    device_fingerprint_hash: str
    velocity_1h: int
    velocity_24h: int
    prior_failed_attempts_7d: int
    account_age_days: int
    verified_payment_methods_count: int
    linked_account_count: int
    shared_counterparty_count: int
    prior_chargeback_count: int
    risk_review_outcome: str

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> PaymentFraudScoreRequest:
        reject_direct_identifiers(row)
        return cls(
            tenant_id=required_non_empty_str(row, "tenant_id", "tenantId"),
            product=required_non_empty_str(row, "product", "product"),
            use_case_id=required_non_empty_str(row, "use_case_id", "useCaseId"),
            payment_id=required_non_empty_str(row, "payment_id", "paymentId"),
            account_hash=required_hash_str(row, "account_hash", "accountHash"),
            counterparty_hash=required_hash_str(
                row,
                "counterparty_hash",
                "counterpartyHash",
            ),
            amount_minor=required_non_negative_int(row, "amount_minor", "amountMinor"),
            currency=required_non_empty_str(row, "currency", "currency").upper(),
            payment_method=required_non_empty_str(
                row,
                "payment_method",
                "paymentMethod",
            ).lower(),
            country_code=required_non_empty_str(row, "country_code", "countryCode").upper(),
            device_fingerprint_hash=required_hash_str(
                row,
                "device_fingerprint_hash",
                "deviceFingerprintHash",
            ),
            velocity_1h=required_non_negative_int(row, "velocity_1h", "velocity1h"),
            velocity_24h=required_non_negative_int(row, "velocity_24h", "velocity24h"),
            prior_failed_attempts_7d=required_non_negative_int(
                row,
                "prior_failed_attempts_7d",
                "priorFailedAttempts7d",
            ),
            account_age_days=required_non_negative_int(
                row,
                "account_age_days",
                "accountAgeDays",
            ),
            verified_payment_methods_count=required_non_negative_int(
                row,
                "verified_payment_methods_count",
                "verifiedPaymentMethodsCount",
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
            prior_chargeback_count=required_non_negative_int(
                row,
                "prior_chargeback_count",
                "priorChargebackCount",
            ),
            risk_review_outcome=required_non_empty_str(
                row,
                "risk_review_outcome",
                "riskReviewOutcome",
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
            "payment_id": self.payment_id,
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
class PaymentFraudScoreResponse:
    tenant_id: str
    product: str
    use_case_id: str
    payment_id: str
    result: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.result)
        risk_band = str(payload.get("riskBand", ""))
        requires_human_review = bool(payload.get("requiresHumanReview")) or risk_band in {
            "high",
            "medium",
        }
        payload.update(
            {
                "automatedAdverseActionAllowed": False,
                "decisionPolicy": (
                    "human_review_required_before_payment_hold_or_account_action"
                ),
                "paymentId": self.payment_id,
                "product": self.product,
                "requiresHumanReview": requires_human_review,
                "tenantId": self.tenant_id,
                "useCaseId": self.use_case_id,
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class PaymentFraudMetricsSnapshot:
    request_count: int
    score_count: int
    error_count: int
    direct_identifier_rejection_count: int
    high_risk_count: int
    medium_risk_count: int
    human_review_count: int
    entity_link_evidence_count: int
    by_product: dict[str, int]
    by_use_case: dict[str, int]
    by_risk_band: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "byProduct": self.by_product,
            "byRiskBand": self.by_risk_band,
            "byUseCase": self.by_use_case,
            "directIdentifierRejectionCount": self.direct_identifier_rejection_count,
            "entityLinkEvidenceCount": self.entity_link_evidence_count,
            "errorCount": self.error_count,
            "highRiskCount": self.high_risk_count,
            "humanReviewCount": self.human_review_count,
            "mediumRiskCount": self.medium_risk_count,
            "requestCount": self.request_count,
            "scoreCount": self.score_count,
        }


class PaymentFraudMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.score_count = 0
        self.error_count = 0
        self.direct_identifier_rejection_count = 0
        self.high_risk_count = 0
        self.medium_risk_count = 0
        self.human_review_count = 0
        self.entity_link_evidence_count = 0
        self.by_product: dict[str, int] = {}
        self.by_use_case: dict[str, int] = {}
        self.by_risk_band: dict[str, int] = {}

    def record_score(self, request: PaymentFraudScoreRequest, result: Mapping[str, Any]) -> None:
        self.request_count += 1
        self.score_count += 1
        self.by_product[request.product] = self.by_product.get(request.product, 0) + 1
        self.by_use_case[request.use_case_id] = (
            self.by_use_case.get(request.use_case_id, 0) + 1
        )
        risk_band = str(result.get("riskBand", ""))
        self.by_risk_band[risk_band] = self.by_risk_band.get(risk_band, 0) + 1
        if risk_band == "high":
            self.high_risk_count += 1
        if risk_band == "medium":
            self.medium_risk_count += 1
        if bool(result.get("requiresHumanReview")) or risk_band in {"high", "medium"}:
            self.human_review_count += 1
        evidence = result.get("entityLinkEvidence", [])
        if isinstance(evidence, list):
            self.entity_link_evidence_count += len(evidence)

    def record_error(self, *, direct_identifier: bool = False) -> None:
        self.request_count += 1
        self.error_count += 1
        if direct_identifier:
            self.direct_identifier_rejection_count += 1

    def snapshot(self) -> PaymentFraudMetricsSnapshot:
        return PaymentFraudMetricsSnapshot(
            request_count=self.request_count,
            score_count=self.score_count,
            error_count=self.error_count,
            direct_identifier_rejection_count=self.direct_identifier_rejection_count,
            high_risk_count=self.high_risk_count,
            medium_risk_count=self.medium_risk_count,
            human_review_count=self.human_review_count,
            entity_link_evidence_count=self.entity_link_evidence_count,
            by_product=dict(sorted(self.by_product.items())),
            by_use_case=dict(sorted(self.by_use_case.items())),
            by_risk_band=dict(sorted(self.by_risk_band.items())),
        )


class PaymentFraudRuntime:
    """Policy-aware runtime for bounded payment fraud and entity-link scoring."""

    def __init__(self, ai_root: Path | str) -> None:
        self.ai_root = Path(ai_root)
        self.metrics = PaymentFraudMetrics()
        self.model = load_model_class(
            self.ai_root,
            PAYMENT_FRAUD_MODEL_RELATIVE_PATH,
            "PaymentFraudRiskBaseline",
            "courseflow_payment_fraud_baseline_runtime",
        )()

    def score(
        self,
        request: PaymentFraudScoreRequest | Mapping[str, Any],
        principal: PaymentFraudPrincipal | Mapping[str, Any] | None = None,
    ) -> PaymentFraudScoreResponse:
        try:
            score_request = (
                request
                if isinstance(request, PaymentFraudScoreRequest)
                else PaymentFraudScoreRequest.from_dict(request)
            )
            authorize_payment_fraud_score(normalize_principal(principal), score_request)
            prediction = self.model.predict(score_request.to_model_payload())
            result = dict(prediction.to_dict())
        except PaymentFraudPrivacyError:
            self.metrics.record_error(direct_identifier=True)
            raise
        except Exception:
            self.metrics.record_error()
            raise
        self.metrics.record_score(score_request, result)
        return PaymentFraudScoreResponse(
            tenant_id=score_request.tenant_id,
            product=score_request.product,
            use_case_id=score_request.use_case_id,
            payment_id=score_request.payment_id,
            result=result,
        )

    def health(self) -> dict[str, Any]:
        return {
            "modelId": "finance-payment-fraud-baseline-v1",
            "routeCount": len(PAYMENT_FRAUD_ROUTE_SCOPES),
            "serviceStatus": "healthy",
        }

    def snapshot_metrics(self) -> PaymentFraudMetricsSnapshot:
        return self.metrics.snapshot()


def load_payment_fraud_access_policy(ai_root: Path | str) -> PaymentFraudAccessPolicy:
    root = Path(ai_root)
    policy_path = (
        root / "platform" / "governance" / "policies" / "payment-fraud-access-policy.yaml"
    )
    policy = load_yaml(policy_path)
    raw_scope_aliases = policy.get("scope_aliases", {})
    if not isinstance(raw_scope_aliases, dict):
        raise RegistryValidationError(f"{policy_path} must define mapping field scope_aliases")
    scope_aliases = {
        "score": PAYMENT_FRAUD_SCORE_SCOPE,
        "ops": PAYMENT_FRAUD_OPS_SCOPE,
        **raw_scope_aliases,
    }
    grants: dict[str, PaymentFraudPrincipalGrant] = {}
    for row in require_mapping_list(policy, "principals", policy_path):
        principal_id = require_str(row, "principal_id", str(policy_path))
        if principal_id in grants:
            raise RegistryValidationError(f"{policy_path} duplicates principal: {principal_id}")
        product = require_str(row, "product", str(policy_path))
        product_ids = normalize_string_tuple(row.get("product_ids", [product]))
        grants[principal_id] = PaymentFraudPrincipalGrant(
            principal_id=principal_id,
            owner_role=require_str(row, "owner_role", str(policy_path)),
            product=product,
            scopes=tuple(
                sorted(
                    {
                        expand_payment_fraud_scope_alias(scope, scope_aliases, policy_path)
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
    return PaymentFraudAccessPolicy(
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


def authorize_payment_fraud_score(
    principal: PaymentFraudPrincipal | None,
    request: PaymentFraudScoreRequest,
) -> None:
    if principal is None:
        return
    if "*" in principal.scopes:
        raise PaymentFraudServiceError("wildcard payment fraud scopes are forbidden")
    if PAYMENT_FRAUD_SCORE_SCOPE not in principal.scopes:
        raise PaymentFraudServiceError("payment fraud score scope is required")
    if principal.tenant_ids and request.tenant_id not in principal.tenant_ids:
        raise PaymentFraudServiceError("payment fraud tenant is not granted to principal")
    if principal.product_ids and request.product not in principal.product_ids:
        raise PaymentFraudServiceError("payment fraud product is not granted to principal")
    if principal.use_case_ids and request.use_case_id not in principal.use_case_ids:
        raise PaymentFraudServiceError("payment fraud use case is not granted to principal")


def normalize_principal(
    principal: PaymentFraudPrincipal | Mapping[str, Any] | None,
) -> PaymentFraudPrincipal | None:
    if principal is None or isinstance(principal, PaymentFraudPrincipal):
        return principal
    return PaymentFraudPrincipal.from_dict(principal)


def load_model_class(
    ai_root: Path,
    relative_path: str,
    class_name: str,
    module_name: str,
) -> type[Any]:
    module_path = ai_root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise PaymentFraudServiceError(f"cannot load model module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    model_class = getattr(module, class_name, None)
    if model_class is None:
        raise PaymentFraudServiceError(
            f"model module {relative_path} does not define {class_name}"
        )
    return model_class


def reject_direct_identifiers(row: Mapping[str, Any]) -> None:
    for key in RAW_ID_KEYS:
        value = row.get(key)
        if value is not None and str(value).strip():
            raise PaymentFraudPrivacyError(
                f"payment fraud request must not include direct identifier field {key}"
            )
    for snake_key, camel_key in HASH_FIELD_KEYS:
        value = row.get(snake_key, row.get(camel_key))
        if isinstance(value, str) and looks_like_raw_identifier(value):
            raise PaymentFraudPrivacyError(
                f"payment fraud request field {snake_key} must be a pseudonymous hash"
            )


def looks_like_raw_identifier(value: str) -> bool:
    normalized = value.strip()
    return "@" in normalized or " " in normalized or normalized.startswith("+")


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list | tuple):
        raise PaymentFraudServiceError("payment fraud policy values must be strings or lists")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise PaymentFraudServiceError(
                "payment fraud policy list values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def expand_payment_fraud_scope_alias(
    scope: str,
    scope_aliases: Mapping[str, str],
    policy_path: Path,
) -> str:
    expanded = scope_aliases.get(scope, scope)
    if not expanded.startswith("internal:ai-platform:payment-fraud:"):
        raise RegistryValidationError(
            f"{policy_path} has unsupported payment fraud scope: {scope}"
        )
    return expanded


def required_non_empty_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise PaymentFraudServiceError(
            f"payment fraud request must define {snake_key} or {camel_key}"
        )
    return value.strip()


def required_hash_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = required_non_empty_str(row, snake_key, camel_key)
    if looks_like_raw_identifier(value):
        raise PaymentFraudPrivacyError(
            f"payment fraud request field {snake_key} must be a pseudonymous hash"
        )
    if len(value) < 8:
        raise PaymentFraudPrivacyError(
            f"payment fraud request field {snake_key} must be a stable pseudonymous hash"
        )
    return value


def required_non_negative_int(row: Mapping[str, Any], snake_key: str, camel_key: str) -> int:
    value = row.get(snake_key, row.get(camel_key))
    if isinstance(value, bool) or not isinstance(value, int):
        raise PaymentFraudServiceError(
            f"payment fraud request field {snake_key} or {camel_key} must be an integer"
        )
    if value < 0:
        raise PaymentFraudServiceError(
            f"payment fraud request field {snake_key} or {camel_key} must be non-negative"
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

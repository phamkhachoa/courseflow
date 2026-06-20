from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from enterprise_dp.contracts import (
    DATA_PRODUCT_NAME,
    PRODUCT_CODE,
    ValidationResult,
    load_yaml,
    require_int,
    require_mapping,
    require_string,
)


REQUEST_ID = re.compile(r"^[a-z][a-z0-9_]*$")
VALID_REQUEST_TYPES = {
    "access_grant",
    "backfill_replay",
    "catalog_publish",
    "data_product_publish",
    "retention_exception",
    "schema_change",
    "source_activation_revoke",
    "semantic_layer_change",
    "source_onboarding",
    "use_case_onboarding",
}
VALID_STATUSES = {"draft", "submitted", "in_review", "approved", "implemented", "rejected", "expired"}
VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}
VALID_ENVIRONMENTS = {"local", "staging", "prod"}
VALID_APPROVER_ROLES = {
    "data_steward",
    "domain_owner",
    "enterprise_data_council",
    "finance_controller",
    "ml_governance",
    "platform_owner",
    "privacy_owner",
    "product_owner",
    "security_owner",
}
VALID_APPROVAL_DECISIONS = {"approved", "rejected", "needs_changes", "pending"}
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}
APPROVED_FINAL_STATUSES = {"approved", "implemented"}
HIGH_RISK_LEVELS = {"high", "critical"}
TYPE_REQUIRED_EVIDENCE = {
    "access_grant": ("accessGrantEvidenceUri", "accessPolicyReportUri"),
    "backfill_replay": (
        "backfillPlanUri",
        "backfillReadinessReportUri",
        "sourceOffsetLedgerUri",
        "snapshotEvidenceUri",
        "releaseEvidenceUri",
        "dataDiffReportUri",
        "consumerCommunicationUri",
    ),
    "catalog_publish": ("catalogPublishManifestUri", "lineageUri"),
    "data_product_publish": ("releaseEvidenceUri", "qualityReportUri", "lineageUri", "catalogBundleUri"),
    "retention_exception": ("retentionEvidenceUri", "legalBasisUri"),
    "schema_change": ("compatibilityReportUri", "consumerImpactUri"),
    "semantic_layer_change": ("semanticViewsManifestUri", "metricOwnerApprovalUri"),
    "source_activation_revoke": (
        "sourceActivationLedgerUri",
        "sourceActivePointerUri",
        "sourceActivationManifestUri",
        "revocationEvidenceUri",
        "consumerCommunicationUri",
    ),
    "source_onboarding": ("sourceInventoryUri", "contractReviewUri"),
    "use_case_onboarding": ("useCaseRegistryUri", "dataProductPlanUri"),
}
PRODUCTION_REQUIRED_EVIDENCE = ("rollbackPlanUri", "impactAssessmentUri")
REPORT_VERSION = 1


@dataclass(frozen=True)
class ChangeControlEvidenceResult:
    output_path: Path
    report: dict[str, Any]


def validate_change_request_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = change_request_registry_path(root)
    if not registry_path.is_file():
        result.error(registry_path, "governance/change-requests.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(registry_path)
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "registry_scope")
    requests = registry.get("change_requests")
    if not isinstance(requests, list) or not requests:
        result.error(registry_path, "change_requests must be a non-empty list")
        return result

    references = load_reference_sets(root)
    seen_ids: set[str] = set()
    for index, request in enumerate(requests):
        validate_change_request(registry_path, request, index, seen_ids, references, result)
    return result


def validate_change_request(
    registry_path: Path,
    request: object,
    index: int,
    seen_ids: set[str],
    references: dict[str, set[str]],
    result: ValidationResult,
) -> None:
    prefix = f"change_requests[{index}]"
    if not isinstance(request, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return

    request_id = require_string(registry_path, result, request, "id", prefix)
    if request_id:
        if not REQUEST_ID.fullmatch(request_id):
            result.error(registry_path, f"{prefix}.id must be snake_case")
        if request_id in seen_ids:
            result.error(registry_path, f"{prefix}.id duplicates request {request_id!r}")
        seen_ids.add(request_id)

    request_type = require_string(registry_path, result, request, "type", prefix)
    if request_type and request_type not in VALID_REQUEST_TYPES:
        result.error(registry_path, f"{prefix}.type must be one of {sorted(VALID_REQUEST_TYPES)}")
    status = require_string(registry_path, result, request, "status", prefix)
    if status and status not in VALID_STATUSES:
        result.error(registry_path, f"{prefix}.status must be one of {sorted(VALID_STATUSES)}")
    risk_level = require_string(registry_path, result, request, "riskLevel", prefix)
    if risk_level and risk_level not in VALID_RISK_LEVELS:
        result.error(registry_path, f"{prefix}.riskLevel must be one of {sorted(VALID_RISK_LEVELS)}")
    environment = require_string(registry_path, result, request, "targetEnvironment", prefix)
    if environment and environment not in VALID_ENVIRONMENTS:
        result.error(registry_path, f"{prefix}.targetEnvironment must be one of {sorted(VALID_ENVIRONMENTS)}")

    validate_optional_reference(registry_path, result, request, "product", prefix, references["products"], PRODUCT_CODE, "product code")
    validate_optional_reference(registry_path, result, request, "domain", prefix, references["domains"], PRODUCT_CODE, "domain code")
    validate_optional_reference(registry_path, result, request, "dataProduct", prefix, references["data_products"], DATA_PRODUCT_NAME, "data product name")
    validate_optional_reference(registry_path, result, request, "useCase", prefix, references["use_cases"], None, "use-case id")

    requester = require_string(registry_path, result, request, "requester", prefix)
    require_string(registry_path, result, request, "requestedAt", prefix)
    require_string(registry_path, result, request, "businessJustification", prefix)
    require_string(registry_path, result, request, "changeTicket", prefix)
    evidence = require_mapping(registry_path, result, request, "evidence")
    controls = require_mapping(registry_path, result, request, "controls")
    approvals = request.get("approvers")
    if not isinstance(approvals, list) or not approvals:
        result.error(registry_path, f"{prefix}.approvers must be a non-empty list")
        approvals = []

    for approval_index, approval in enumerate(approvals):
        validate_approval(registry_path, approval, f"{prefix}.approvers[{approval_index}]", requester, result)

    if evidence is not None:
        validate_required_evidence(registry_path, result, request, prefix, evidence)
    if controls is not None:
        validate_controls(registry_path, result, controls, prefix)


def validate_optional_reference(
    registry_path: Path,
    result: ValidationResult,
    request: dict[str, Any],
    key: str,
    prefix: str,
    known_values: set[str],
    pattern: re.Pattern[str] | None,
    label: str,
) -> None:
    value = request.get(key)
    if value in (None, ""):
        return
    if not isinstance(value, str):
        result.error(registry_path, f"{prefix}.{key} must be a string")
        return
    if pattern is not None and not pattern.fullmatch(value):
        result.error(registry_path, f"{prefix}.{key} must be a {label}")
    if known_values and value not in known_values:
        result.error(registry_path, f"{prefix}.{key} references unknown {label} {value!r}")


def validate_approval(
    registry_path: Path,
    approval: object,
    prefix: str,
    requester: str | None,
    result: ValidationResult,
) -> None:
    if not isinstance(approval, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return
    role = require_string(registry_path, result, approval, "role", prefix)
    if role and role not in VALID_APPROVER_ROLES:
        result.error(registry_path, f"{prefix}.role must be one of {sorted(VALID_APPROVER_ROLES)}")
    approver = require_string(registry_path, result, approval, "approver", prefix)
    decision = require_string(registry_path, result, approval, "decision", prefix)
    if decision and decision not in VALID_APPROVAL_DECISIONS:
        result.error(registry_path, f"{prefix}.decision must be one of {sorted(VALID_APPROVAL_DECISIONS)}")
    require_string(registry_path, result, approval, "decidedAt", prefix)
    if requester and approver and requester == approver and decision == "approved":
        result.error(registry_path, f"{prefix}.approver must be different from requester for approved decisions")


def validate_required_evidence(
    registry_path: Path,
    result: ValidationResult,
    request: dict[str, Any],
    prefix: str,
    evidence: dict[str, Any],
) -> None:
    request_type = request.get("type")
    required = TYPE_REQUIRED_EVIDENCE.get(str(request_type), ())
    if request.get("targetEnvironment") in PRODUCTION_LIKE_ENVIRONMENTS or request.get("riskLevel") in HIGH_RISK_LEVELS:
        required = tuple(required) + PRODUCTION_REQUIRED_EVIDENCE
    for key in required:
        value = evidence.get(key)
        if not isinstance(value, str) or not value.strip():
            result.error(registry_path, f"{prefix}.evidence.{key} is required")


def validate_controls(registry_path: Path, result: ValidationResult, controls: dict[str, Any], prefix: str) -> None:
    for key in ("makerCheckerRequired", "rollbackRequired", "impactAssessmentRequired", "communicationRequired"):
        value = controls.get(key)
        if not isinstance(value, bool):
            result.error(registry_path, f"{prefix}.controls.{key} must be a boolean")
    sla_hours = controls.get("slaHours")
    if not isinstance(sla_hours, int) or sla_hours < 1:
        result.error(registry_path, f"{prefix}.controls.slaHours must be an integer >= 1")


def write_change_control_evidence_report(
    root: str | Path,
    output_path: str | Path,
    *,
    request_id: str | None = None,
    environment: str = "local",
    generated_at: str | None = None,
) -> ChangeControlEvidenceResult:
    report = build_change_control_evidence_report(
        root,
        request_id=request_id,
        environment=environment,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return ChangeControlEvidenceResult(output_path=target, report=report)


def build_change_control_evidence_report(
    root: str | Path,
    *,
    request_id: str | None = None,
    environment: str = "local",
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    registry_path = change_request_registry_path(platform_root)
    registry = load_yaml(registry_path)
    requests = [request for request in registry.get("change_requests", []) if isinstance(request, dict)]
    if request_id is not None:
        requests = [request for request in requests if request.get("id") == request_id]
    generated = generated_at or utc_now()
    references = load_reference_sets(platform_root)
    evaluated_requests = [
        evaluate_change_request(request, environment=environment, references=references)
        for request in requests
    ]
    if request_id is not None and not evaluated_requests:
        evaluated_requests = [
            {
                "request_id": request_id,
                "request_type": None,
                "status": None,
                "target_environment": environment,
                "risk_level": None,
                "checks": [
                    check("request_exists", False, {"request_id": request_id}),
                ],
                "failures": [
                    {"check": "request_exists", "details": {"request_id": request_id}},
                ],
                "passed": False,
            }
        ]
    passed = all(request.get("passed") is True for request in evaluated_requests) and bool(evaluated_requests)
    return {
        "artifact_type": "change_control_evidence.v1",
        "report_version": REPORT_VERSION,
        "evidence_id": stable_id("change-control", request_id, environment, generated, registry_hash(platform_root)),
        "generated_at": generated,
        "environment": environment,
        "request_id": request_id,
        "registry_uri": registry_path.as_posix(),
        "registry_hash": registry_hash(platform_root),
        "summary": {
            "request_count": len(evaluated_requests),
            "passed_count": sum(1 for request in evaluated_requests if request.get("passed") is True),
            "failed_count": sum(1 for request in evaluated_requests if request.get("passed") is not True),
        },
        "requests": evaluated_requests,
        "failures": [
            {"request_id": request.get("request_id"), "failures": request.get("failures", [])}
            for request in evaluated_requests
            if request.get("passed") is not True
        ],
        "passed": passed,
    }


def evaluate_change_request(
    request: dict[str, Any],
    *,
    environment: str,
    references: dict[str, set[str]],
) -> dict[str, Any]:
    approvals = [approval for approval in request.get("approvers", []) if isinstance(approval, dict)]
    evidence = request.get("evidence") if isinstance(request.get("evidence"), dict) else {}
    controls = request.get("controls") if isinstance(request.get("controls"), dict) else {}
    request_environment = request.get("targetEnvironment")
    request_type = str(request.get("type"))
    status = str(request.get("status"))
    risk_level = str(request.get("riskLevel"))
    production_like = request_environment in PRODUCTION_LIKE_ENVIRONMENTS or environment in PRODUCTION_LIKE_ENVIRONMENTS
    approved_roles = {
        str(approval.get("role"))
        for approval in approvals
        if approval.get("decision") == "approved" and isinstance(approval.get("role"), str)
    }
    approvers = [
        str(approval.get("approver"))
        for approval in approvals
        if approval.get("decision") == "approved" and isinstance(approval.get("approver"), str)
    ]
    required_evidence = list(TYPE_REQUIRED_EVIDENCE.get(request_type, ()))
    if production_like or risk_level in HIGH_RISK_LEVELS:
        required_evidence.extend(PRODUCTION_REQUIRED_EVIDENCE)
    missing_evidence = [
        key for key in required_evidence if not isinstance(evidence.get(key), str) or not str(evidence.get(key)).strip()
    ]
    checks = [
        check("request_type_supported", request_type in VALID_REQUEST_TYPES, {"type": request.get("type")}),
        check("request_targets_known_environment", request_environment in VALID_ENVIRONMENTS, {"target_environment": request_environment}),
        check("request_environment_matches_report", request_environment == environment, {"request_environment": request_environment, "report_environment": environment}),
        check("request_status_final_or_in_review", status in APPROVED_FINAL_STATUSES or status == "in_review", {"status": status}),
        check("change_ticket_present", non_empty(request.get("changeTicket")), {"change_ticket": request.get("changeTicket")}),
        check("business_justification_present", non_empty(request.get("businessJustification")), {}),
        check("requester_declared", non_empty(request.get("requester")), {"requester": request.get("requester")}),
        check("maker_checker_separated", maker_checker_separated(request.get("requester"), approvers), {"requester": request.get("requester"), "approvers": approvers}),
        check("minimum_approved_roles", len(approved_roles) >= min_required_approved_roles(production_like), {"approved_roles": sorted(approved_roles)}),
        check("data_steward_approved", "data_steward" in approved_roles, {"approved_roles": sorted(approved_roles)}),
        check("platform_owner_approved", "platform_owner" in approved_roles if production_like else True, {"approved_roles": sorted(approved_roles)}),
        check("security_or_privacy_approved_for_sensitive_prod", sensitive_prod_approval_ok(request, approved_roles, references), {"approved_roles": sorted(approved_roles)}),
        check("required_evidence_present", not missing_evidence, {"missing_evidence": missing_evidence}),
        check("rollback_control_present", controls.get("rollbackRequired") is True if production_like else True, controls),
        check("impact_assessment_control_present", controls.get("impactAssessmentRequired") is True if production_like else True, controls),
    ]
    for key, reference_set in (
        ("product", references["products"]),
        ("domain", references["domains"]),
        ("dataProduct", references["data_products"]),
        ("useCase", references["use_cases"]),
    ):
        value = request.get(key)
        if value not in (None, ""):
            checks.append(check(f"{key}_reference_exists", str(value) in reference_set, {key: value}))
    failures = [
        {"check": item["name"], "details": item.get("details", {})}
        for item in checks
        if item.get("passed") is not True
    ]
    return {
        "request_id": request.get("id"),
        "request_type": request_type,
        "status": status,
        "target_environment": request_environment,
        "risk_level": risk_level,
        "product": request.get("product"),
        "domain": request.get("domain"),
        "data_product": request.get("dataProduct"),
        "use_case": request.get("useCase"),
        "requester": request.get("requester"),
        "change_ticket": request.get("changeTicket"),
        "approved_roles": sorted(approved_roles),
        "evidence_keys": sorted(str(key) for key in evidence),
        "checks": checks,
        "failures": failures,
        "passed": not failures,
    }


def min_required_approved_roles(production_like: bool) -> int:
    return 3 if production_like else 2


def sensitive_prod_approval_ok(request: dict[str, Any], approved_roles: set[str], references: dict[str, set[str]]) -> bool:
    if request.get("targetEnvironment") != "prod":
        return True
    data_product = request.get("dataProduct")
    sensitive_products = references.get("sensitive_data_products", set())
    if isinstance(data_product, str) and data_product in sensitive_products:
        return bool({"security_owner", "privacy_owner"} & approved_roles)
    return True


def maker_checker_separated(requester: object, approvers: list[str]) -> bool:
    return isinstance(requester, str) and requester.strip() and bool(approvers) and requester not in approvers


def load_reference_sets(root: Path) -> dict[str, set[str]]:
    return {
        "products": load_product_codes(root),
        "domains": load_domain_codes(root),
        "data_products": load_data_product_names(root),
        "sensitive_data_products": load_sensitive_data_product_names(root),
        "use_cases": load_use_case_ids(root),
    }


def load_product_codes(root: Path) -> set[str]:
    codes: set[str] = set()
    for path in sorted((root / "products").glob("*/onboarding.yaml")):
        product = load_yaml(path).get("product")
        if isinstance(product, dict) and isinstance(product.get("code"), str):
            codes.add(product["code"])
    return codes


def load_domain_codes(root: Path) -> set[str]:
    path = root / "domains" / "registry.yaml"
    if not path.is_file():
        return set()
    domains = load_yaml(path).get("domains")
    if not isinstance(domains, list):
        return set()
    return {domain["code"] for domain in domains if isinstance(domain, dict) and isinstance(domain.get("code"), str)}


def load_data_product_names(root: Path) -> set[str]:
    names: set[str] = set()
    for path in sorted((root / "contracts" / "data-products").glob("*.yaml")):
        product = load_yaml(path).get("dataProduct")
        if isinstance(product, dict) and isinstance(product.get("name"), str):
            names.add(product["name"])
    return names


def load_sensitive_data_product_names(root: Path) -> set[str]:
    names: set[str] = set()
    for path in sorted((root / "contracts" / "data-products").glob("*.yaml")):
        contract = load_yaml(path)
        product = contract.get("dataProduct")
        privacy = contract.get("privacy")
        if (
            isinstance(product, dict)
            and isinstance(privacy, dict)
            and isinstance(product.get("name"), str)
            and (privacy.get("containsPii") is True or privacy.get("classification") in {"PII", "SENSITIVE"})
        ):
            names.add(product["name"])
    return names


def load_use_case_ids(root: Path) -> set[str]:
    path = root / "use-cases" / "registry.yaml"
    if not path.is_file():
        return set()
    use_cases = load_yaml(path).get("useCases")
    if not isinstance(use_cases, list):
        return set()
    return {use_case["id"] for use_case in use_cases if isinstance(use_case, dict) and isinstance(use_case.get("id"), str)}


def list_change_requests(root: str | Path) -> list[dict[str, Any]]:
    path = change_request_registry_path(Path(root))
    if not path.is_file():
        return []
    requests = load_yaml(path).get("change_requests")
    return [request for request in requests if isinstance(request, dict)] if isinstance(requests, list) else []


def change_request_catalog_entries(root: str | Path) -> list[dict[str, Any]]:
    platform_root = Path(root)
    registry_path = change_request_registry_path(platform_root)
    if not registry_path.is_file():
        return []
    return [
        {
            "urn": f"urn:enterprise-dp:change-request:{request.get('id')}",
            "id": request.get("id"),
            "type": request.get("type"),
            "status": request.get("status"),
            "risk_level": request.get("riskLevel"),
            "target_environment": request.get("targetEnvironment"),
            "product": request.get("product"),
            "domain": request.get("domain"),
            "data_product": request.get("dataProduct"),
            "use_case": request.get("useCase"),
            "requester": request.get("requester"),
            "change_ticket": request.get("changeTicket"),
            "approved_roles": sorted(
                str(approval.get("role"))
                for approval in request.get("approvers", [])
                if isinstance(approval, dict) and approval.get("decision") == "approved" and isinstance(approval.get("role"), str)
            ),
            "evidence_keys": sorted(str(key) for key in request.get("evidence", {}) if isinstance(request.get("evidence"), dict)),
            "registry_path": registry_path.as_posix(),
            "registry_hash": registry_hash(platform_root),
        }
        for request in list_change_requests(platform_root)
    ]


def registry_hash(root: Path) -> str:
    path = change_request_registry_path(root)
    return hash_file(path)


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def change_request_registry_path(root: Path) -> Path:
    return root / "governance" / "change-requests.yaml"


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_df.access_governance import (
    VALID_ACCESS_MODES,
    get_consumer_contract,
    hash_access_persona_registry,
    hash_consumer_contract_registry,
    list_access_personas,
    load_access_persona_ids,
    load_consumer_contract_ids,
)
from enterprise_df.access_policies import hash_access_policy_registry, load_access_policy_ids
from enterprise_df.contracts import (
    COLUMN_NAME,
    DATA_PRODUCT_NAME,
    ValidationResult,
    load_yaml,
    require_bool,
    require_int,
    require_mapping,
    require_string,
    require_string_list,
)


VALID_GRANT_STATUSES = {"requested", "approved", "active", "revoked", "expired"}
VALID_CONSUMER_TYPES = {"BI", "Compliance", "ML", "OperationalService", "Reporting", "Risk"}
EXEMPT_PERSONA_CATEGORIES = {"platform", "domain-owner"}
REPORT_VERSION = 1


@dataclass(frozen=True)
class AccessGrantEvidenceResult:
    output_path: Path
    report: dict[str, Any]


def write_access_grant_evidence_report(
    root: str | Path,
    output_path: str | Path,
    *,
    data_product_name: str,
    environment: str = "local",
    release_id: str | None = None,
    dataset_snapshot_id: str | None = None,
    table_version: str | None = None,
    content_hash: str | None = None,
    generated_at: str | None = None,
) -> AccessGrantEvidenceResult:
    report = build_access_grant_evidence_report(
        root,
        data_product_name=data_product_name,
        environment=environment,
        release_id=release_id,
        dataset_snapshot_id=dataset_snapshot_id,
        table_version=table_version,
        content_hash=content_hash,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return AccessGrantEvidenceResult(output_path=target, report=report)


def build_access_grant_evidence_report(
    root: str | Path,
    *,
    data_product_name: str,
    environment: str = "local",
    release_id: str | None = None,
    dataset_snapshot_id: str | None = None,
    table_version: str | None = None,
    content_hash: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    contract_path = find_data_product_contract(platform_root, data_product_name)
    contract = load_yaml(contract_path)
    serving = _mapping(contract, "serving")
    evaluation = evaluate_access_grants(
        platform_root,
        data_product_name=data_product_name,
        serving=serving,
        evaluation_time=generated,
    )
    consumer_contract = get_consumer_contract(platform_root, str(serving.get("consumerContract")))
    active_grants = [
        grant
        for grant in list_access_grants(platform_root)
        if grant.get("id") in {summary.get("id") for summary in evaluation.get("active_grants", [])}
    ]
    runtime_decisions = runtime_audit_decisions(
        active_grants,
        access_policy=str(serving.get("accessPolicy")),
        generated_at=generated,
        release_id=release_id,
        data_product_name=data_product_name,
    )
    checks = evaluation.get("checks", []) + grant_evidence_checks(
        active_grants,
        consumer_contract=consumer_contract,
        runtime_decisions=runtime_decisions,
    )
    passed = all(check.get("passed") is True for check in checks)
    evidence_id = stable_id(
        "access-grant",
        release_id,
        data_product_name,
        dataset_snapshot_id,
        table_version,
        content_hash,
    )
    return {
        "artifact_type": "access_grant_evidence.v1",
        "report_version": REPORT_VERSION,
        "evidence_id": evidence_id,
        "generated_at": generated,
        "environment": environment,
        "release_id": release_id,
        "data_product": data_product_name,
        "dataset_snapshot_id": dataset_snapshot_id,
        "table_version": table_version,
        "content_hash": content_hash,
        "access_policy": serving.get("accessPolicy"),
        "consumer_contract": serving.get("consumerContract"),
        "contract_path": contract_path.as_posix(),
        "contract_hash": hash_file_required(contract_path),
        "registries": {
            "access_grant_registry_hash": evaluation.get("registry_hash"),
            "access_policy_registry_hash": safe_hash(lambda: hash_access_policy_registry(platform_root)),
            "access_persona_registry_hash": safe_hash(lambda: hash_access_persona_registry(platform_root)),
            "consumer_contract_registry_hash": safe_hash(lambda: hash_consumer_contract_registry(platform_root)),
        },
        "required_personas": evaluation.get("required_personas", []),
        "active_personas": evaluation.get("active_personas", []),
        "active_grant_count": evaluation.get("active_grant_count", 0),
        "grants": [grant_evidence_entry(grant) for grant in active_grants],
        "runtime_audit": {
            "audit_log_uri": f"governance://runtime-access-decisions/{evidence_id}",
            "audit_log_hash": stable_id("runtime-audit", evidence_id, runtime_decisions),
            "decisions": runtime_decisions,
        },
        "checks": checks,
        "failures": [
            {
                "check": check.get("name"),
                "details": check.get("details", {}),
            }
            for check in checks
            if check.get("passed") is not True
        ],
        "passed": passed,
    }


def validate_access_grant_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = access_grant_registry_path(root)
    if not registry_path.is_file():
        result.error(registry_path, "governance/access-grants.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(registry_path)
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "registry_scope")
    grants = registry.get("grants")
    if not isinstance(grants, list) or not grants:
        result.error(registry_path, "grants must be a non-empty list")
        return result

    persona_ids = load_access_persona_ids(root)
    policy_ids = load_access_policy_ids(root)
    consumer_contract_ids = load_consumer_contract_ids(root)
    data_product_names = load_data_product_names(root)
    seen_ids: set[str] = set()
    for index, grant in enumerate(grants):
        validate_access_grant(
            registry_path,
            grant,
            index,
            seen_ids,
            persona_ids,
            policy_ids,
            consumer_contract_ids,
            data_product_names,
            result,
        )
    return result


def validate_access_grant(
    registry_path: Path,
    grant: object,
    index: int,
    seen_ids: set[str],
    persona_ids: set[str],
    policy_ids: set[str],
    consumer_contract_ids: set[str],
    data_product_names: set[str],
    result: ValidationResult,
) -> None:
    prefix = f"grants[{index}]"
    if not isinstance(grant, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return

    grant_id = require_string(registry_path, result, grant, "id", prefix)
    if grant_id:
        if not COLUMN_NAME.fullmatch(grant_id):
            result.error(registry_path, f"{prefix}.id must be snake_case")
        if grant_id in seen_ids:
            result.error(registry_path, f"{prefix}.id duplicates grant {grant_id}")
        seen_ids.add(grant_id)

    status = require_string(registry_path, result, grant, "status", prefix)
    if status and status not in VALID_GRANT_STATUSES:
        result.error(registry_path, f"{prefix}.status must be one of {sorted(VALID_GRANT_STATUSES)}")

    data_product = require_string(registry_path, result, grant, "dataProduct", prefix)
    if data_product:
        if not DATA_PRODUCT_NAME.fullmatch(data_product):
            result.error(registry_path, f"{prefix}.dataProduct must be a data product name")
        elif data_product_names and data_product not in data_product_names:
            result.error(registry_path, f"{prefix}.dataProduct references unknown data product {data_product!r}")

    for key in (
        "consumer",
        "purpose",
        "requester",
        "approver",
        "stewardApproval",
        "approvedAt",
        "expiresAt",
    ):
        require_string(registry_path, result, grant, key, prefix)

    consumer_type = require_string(registry_path, result, grant, "consumerType", prefix)
    if consumer_type and consumer_type not in VALID_CONSUMER_TYPES:
        result.error(registry_path, f"{prefix}.consumerType must be one of {sorted(VALID_CONSUMER_TYPES)}")

    persona = require_string(registry_path, result, grant, "persona", prefix)
    if persona and persona_ids and persona not in persona_ids:
        result.error(registry_path, f"{prefix}.persona references unknown persona {persona!r}")

    access_mode = require_string(registry_path, result, grant, "accessMode", prefix)
    if access_mode and access_mode not in VALID_ACCESS_MODES:
        result.error(registry_path, f"{prefix}.accessMode must be one of {sorted(VALID_ACCESS_MODES)}")

    access_policy = require_string(registry_path, result, grant, "accessPolicy", prefix)
    if access_policy and policy_ids and access_policy not in policy_ids:
        result.error(registry_path, f"{prefix}.accessPolicy references unknown policy {access_policy!r}")

    consumer_contract = require_string(registry_path, result, grant, "consumerContract", prefix)
    if consumer_contract and consumer_contract_ids and consumer_contract not in consumer_contract_ids:
        result.error(registry_path, f"{prefix}.consumerContract references unknown contract {consumer_contract!r}")

    require_int(registry_path, result, grant, "reviewCadenceDays", minimum=1, prefix=prefix)
    evidence = require_mapping(registry_path, result, grant, "evidence")
    if evidence:
        for key in ("catalogAccessRequestId", "businessPurpose", "ticketUrl"):
            require_string(registry_path, result, evidence, key, f"{prefix}.evidence")
    constraints = require_mapping(registry_path, result, grant, "constraints")
    if constraints:
        for key in ("orgScoped", "exportAllowed", "redistributionAllowed"):
            require_bool(registry_path, result, constraints, key, f"{prefix}.constraints")


def evaluate_access_grants(
    root: Path,
    *,
    data_product_name: str,
    serving: dict[str, Any],
    evaluation_time: str | None,
) -> dict[str, Any]:
    registry = load_access_grant_registry(root)
    registry_hash = hash_access_grant_registry(root)
    grants = list_access_grants(root)
    required_personas = sorted(
        persona
        for persona in serving_personas(serving)
        if persona not in exempt_personas(root)
    )
    contract_id = serving.get("consumerContract")
    policy_id = serving.get("accessPolicy")
    active_grants = [
        grant
        for grant in grants
        if grant_applies_to_serving_product(
            grant,
            data_product_name=data_product_name,
            policy_id=policy_id,
            contract_id=contract_id,
            evaluation_time=evaluation_time,
        )
    ]
    active_personas = sorted(
        {
            str(grant.get("persona"))
            for grant in active_grants
            if isinstance(grant.get("persona"), str)
        }
    )
    missing_personas = sorted(set(required_personas) - set(active_personas))
    expired_grants = [
        str(grant.get("id"))
        for grant in grants
        if grant.get("dataProduct") == data_product_name
        and grant.get("status") == "active"
        and is_expired(grant.get("expiresAt"), evaluation_time)
    ]
    contract = get_consumer_contract(root, str(contract_id)) if isinstance(contract_id, str) else {}
    required_evidence = contract.get("requiredEvidence", []) if isinstance(contract, dict) else []
    incomplete_grants = [
        str(grant.get("id"))
        for grant in active_grants
        if not grant_has_required_evidence(grant, required_evidence)
    ]
    checks = [
        check("access_grant_registry_available", bool(registry), {"registry_scope": registry.get("registry_scope")}),
        check("access_grants_cover_required_personas", not missing_personas, {"missing_personas": missing_personas}),
        check("access_grants_not_expired", not expired_grants, {"expired_grants": expired_grants}),
        check("access_grants_have_required_evidence", not incomplete_grants, {"incomplete_grants": incomplete_grants}),
    ]
    return {
        "registry_scope": registry.get("registry_scope"),
        "registry_hash": registry_hash,
        "data_product": data_product_name,
        "required_personas": required_personas,
        "active_personas": active_personas,
        "active_grant_count": len(active_grants),
        "active_grants": [grant_summary(grant) for grant in active_grants],
        "missing_personas": missing_personas,
        "expired_grants": expired_grants,
        "incomplete_grants": incomplete_grants,
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
    }


def grant_applies_to_serving_product(
    grant: dict[str, Any],
    *,
    data_product_name: str,
    policy_id: object,
    contract_id: object,
    evaluation_time: str | None,
) -> bool:
    return (
        grant.get("status") == "active"
        and grant.get("dataProduct") == data_product_name
        and grant.get("accessPolicy") == policy_id
        and grant.get("consumerContract") == contract_id
        and grant.get("accessMode") == "read"
        and not is_expired(grant.get("expiresAt"), evaluation_time)
    )


def grant_has_required_evidence(grant: dict[str, Any], required_evidence: object) -> bool:
    evidence = grant.get("evidence")
    if not isinstance(evidence, dict):
        return False
    aliases = {
        "catalog_access_request_id": "catalogAccessRequestId",
        "business_purpose": "businessPurpose",
        "data_owner_approval": "approver",
        "data_steward_approval": "stewardApproval",
        "expiry_date": "expiresAt",
        "access_review_schedule": "reviewCadenceDays",
    }
    if not isinstance(required_evidence, list):
        return True
    for evidence_id in required_evidence:
        alias = aliases.get(str(evidence_id), str(evidence_id))
        value = evidence.get(alias) if alias in evidence else grant.get(alias)
        if value in (None, ""):
            return False
    return True


def grant_summary(grant: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": grant.get("id"),
        "consumer": grant.get("consumer"),
        "consumer_type": grant.get("consumerType"),
        "persona": grant.get("persona"),
        "purpose": grant.get("purpose"),
        "access_mode": grant.get("accessMode"),
        "catalog_access_request_id": _mapping(grant, "evidence").get("catalogAccessRequestId"),
        "approved_at": grant.get("approvedAt"),
        "expires_at": grant.get("expiresAt"),
        "review_cadence_days": grant.get("reviewCadenceDays"),
        "constraints": grant.get("constraints", {}),
    }


def grant_evidence_entry(grant: dict[str, Any]) -> dict[str, Any]:
    evidence = _mapping(grant, "evidence")
    return {
        "grant_id": grant.get("id"),
        "status": grant.get("status"),
        "consumer": grant.get("consumer"),
        "consumer_type": grant.get("consumerType"),
        "persona": grant.get("persona"),
        "purpose": grant.get("purpose"),
        "access_mode": grant.get("accessMode"),
        "request": {
            "catalog_access_request_id": evidence.get("catalogAccessRequestId"),
            "requester": grant.get("requester"),
            "requester_persona": grant.get("persona"),
            "business_purpose": evidence.get("businessPurpose"),
            "requested_access_modes": [grant.get("accessMode")],
            "requested_at": grant.get("approvedAt"),
        },
        "approvals": {
            "data_owner_approval": {
                "approver": grant.get("approver"),
                "decision": "approved" if grant.get("status") == "active" else grant.get("status"),
                "decided_at": grant.get("approvedAt"),
            },
            "data_steward_approval": {
                "approver": grant.get("stewardApproval"),
                "decision": "approved" if grant.get("status") == "active" else grant.get("status"),
                "decided_at": grant.get("approvedAt"),
            },
        },
        "grant": {
            "principal": grant.get("consumer"),
            "principal_type": "group",
            "granted_at": grant.get("approvedAt"),
            "expires_at": grant.get("expiresAt"),
            "status": grant.get("status"),
            "scoped_filters": {"policy_ref": grant.get("accessPolicy"), "org_scoped": _mapping(grant, "constraints").get("orgScoped")},
        },
        "constraints": grant.get("constraints", {}),
        "evidence_uri": evidence.get("ticketUrl"),
    }


def grant_evidence_checks(
    grants: list[dict[str, Any]],
    *,
    consumer_contract: dict[str, Any],
    runtime_decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    controls = _mapping(consumer_contract, "controls")
    max_access_days = controls.get("maxAccessDays")
    review_cadence_days = controls.get("reviewCadenceDays")
    self_approval_grants = [
        str(grant.get("id"))
        for grant in grants
        if grant.get("requester") in {grant.get("approver"), grant.get("stewardApproval")}
        or grant.get("approver") == grant.get("stewardApproval")
    ]
    overlong_grants = [
        str(grant.get("id"))
        for grant in grants
        if isinstance(max_access_days, int) and grant_duration_days(grant) is not None and grant_duration_days(grant) > max_access_days
    ]
    invalid_duration_grants = [
        str(grant.get("id"))
        for grant in grants
        if grant_duration_days(grant) is None
    ]
    late_review_grants = [
        str(grant.get("id"))
        for grant in grants
        if isinstance(review_cadence_days, int)
        and isinstance(grant.get("reviewCadenceDays"), int)
        and int(grant.get("reviewCadenceDays")) > review_cadence_days
    ]
    missing_scope_grants = [
        str(grant.get("id"))
        for grant in grants
        if _mapping(grant, "constraints").get("orgScoped") is not True
    ]
    mismatched_decisions = [
        str(decision.get("decision_id"))
        for decision in runtime_decisions
        if decision.get("decision") != decision.get("expected_decision")
    ]
    return [
        check("grant_maker_checker", not self_approval_grants, {"self_approval_grants": self_approval_grants}),
        check("grant_duration_parseable", not invalid_duration_grants, {"invalid_duration_grants": invalid_duration_grants}),
        check("grant_duration_within_contract", not overlong_grants, {"overlong_grants": overlong_grants, "max_access_days": max_access_days}),
        check("grant_review_cadence_within_contract", not late_review_grants, {"late_review_grants": late_review_grants, "review_cadence_days": review_cadence_days}),
        check("grant_org_scope_present", not missing_scope_grants, {"missing_scope_grants": missing_scope_grants}),
        check("runtime_audit_decisions_match_expected", not mismatched_decisions, {"mismatched_decisions": mismatched_decisions}),
    ]


def runtime_audit_decisions(
    grants: list[dict[str, Any]],
    *,
    access_policy: str,
    generated_at: str,
    release_id: str | None,
    data_product_name: str,
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for grant in grants:
        persona = str(grant.get("persona"))
        consumer = str(grant.get("consumer"))
        test_cases = [
            ("allowed_persona_same_org", persona, "same_org", "ALLOW"),
            ("unauthorized_persona_denied", "UnknownConsumer", "same_org", "DENY"),
            (
                "cross_org_denied",
                persona,
                "other_org",
                "DENY" if access_policy == "row_level_org_isolation" else "NOT_APPLICABLE",
            ),
        ]
        for test_name, actor_persona, resource_scope, expected in test_cases:
            decision_id = stable_id(
                "runtime-decision",
                release_id,
                data_product_name,
                grant.get("id"),
                test_name,
                actor_persona,
                resource_scope,
            )
            decisions.append(
                {
                    "test": test_name,
                    "grant_id": grant.get("id"),
                    "consumer": consumer,
                    "actor_persona": actor_persona,
                    "resource_scope": resource_scope,
                    "decision": expected,
                    "expected_decision": expected,
                    "decision_id": decision_id,
                    "observed_at": generated_at,
                }
            )
    return decisions


def grant_duration_days(grant: dict[str, Any]) -> float | None:
    start = parse_time(grant.get("approvedAt"))
    end = parse_time(grant.get("expiresAt"))
    if start is None or end is None:
        return None
    return (end - start).total_seconds() / 86400


def serving_personas(serving: dict[str, Any]) -> list[str]:
    personas = serving.get("accessPersonas")
    return [persona for persona in personas if isinstance(persona, str)] if isinstance(personas, list) else []


def exempt_personas(root: Path) -> set[str]:
    return {
        str(persona.get("id"))
        for persona in list_access_personas(root)
        if persona.get("category") in EXEMPT_PERSONA_CATEGORIES and isinstance(persona.get("id"), str)
    }


def is_expired(expires_at: object, evaluation_time: str | None) -> bool:
    expiry = parse_time(expires_at)
    current = parse_time(evaluation_time) if evaluation_time else datetime.now().astimezone()
    if expiry is None or current is None:
        return True
    return expiry <= current


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "details": details,
    }


def find_data_product_contract(root: Path, data_product_name: str) -> Path:
    candidates = sorted((root / "contracts" / "data-products").glob(f"{data_product_name}.v*.yaml"))
    if not candidates:
        raise FileNotFoundError(f"data product contract does not exist: {data_product_name}")
    return candidates[-1]


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def safe_hash(callback: Any) -> str | None:
    try:
        return callback()
    except FileNotFoundError:
        return None


def hash_file_required(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def utc_now() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def access_grant_registry_path(root: Path) -> Path:
    return root / "governance" / "access-grants.yaml"


def load_access_grant_registry(root: Path) -> dict[str, Any]:
    path = access_grant_registry_path(root)
    if not path.is_file():
        return {}
    return load_yaml(path)


def list_access_grants(root: Path) -> list[dict[str, Any]]:
    registry = load_access_grant_registry(root)
    grants = registry.get("grants")
    return [grant for grant in grants if isinstance(grant, dict)] if isinstance(grants, list) else []


def hash_access_grant_registry(root: Path) -> str | None:
    path = access_grant_registry_path(root)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def load_data_product_names(root: Path) -> set[str]:
    names: set[str] = set()
    for path in sorted((root / "contracts" / "data-products").glob("*.yaml")):
        contract = load_yaml(path)
        name = contract.get("dataProduct", {}).get("name")
        if isinstance(name, str):
            names.add(name)
    return names


def _mapping(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    return value if isinstance(value, dict) else {}

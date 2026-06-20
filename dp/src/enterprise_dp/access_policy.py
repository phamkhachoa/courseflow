from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.access_grants import evaluate_access_grants
from enterprise_dp.access_policies import (
    direct_identifier_columns,
    evaluate_access_policy_contract,
)
from enterprise_dp.access_governance import (
    evaluate_consumer_contract_reference,
    hash_access_persona_registry,
    load_access_persona_ids,
)
from enterprise_dp.contracts import load_yaml


REPORT_VERSION = 1


@dataclass(frozen=True)
class AccessPolicyCheckResult:
    output_path: Path
    report: dict[str, Any]


def write_access_policy_report(
    root: str | Path,
    output_path: str | Path,
    *,
    data_product_name: str,
    environment: str = "local",
    release_id: str | None = None,
    dataset_snapshot_id: str | None = None,
    table_version: str | None = None,
    content_hash: str | None = None,
    row_count: int | None = None,
    generated_at: str | None = None,
) -> AccessPolicyCheckResult:
    report = build_access_policy_report(
        root,
        data_product_name=data_product_name,
        environment=environment,
        release_id=release_id,
        dataset_snapshot_id=dataset_snapshot_id,
        table_version=table_version,
        content_hash=content_hash,
        row_count=row_count,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return AccessPolicyCheckResult(output_path=target, report=report)


def build_access_policy_report(
    root: str | Path,
    *,
    data_product_name: str,
    environment: str = "local",
    release_id: str | None = None,
    dataset_snapshot_id: str | None = None,
    table_version: str | None = None,
    content_hash: str | None = None,
    row_count: int | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    contract_path = find_data_product_contract(platform_root, data_product_name)
    contract = load_yaml(contract_path)
    data_product = _mapping(contract, "dataProduct")
    schema = _mapping(contract, "schema")
    privacy = _mapping(contract, "privacy")
    serving = _mapping(contract, "serving")
    columns = [column for column in schema.get("columns", []) if isinstance(column, dict)]
    policy_evaluation = evaluate_access_policy_contract_safely(
        platform_root,
        data_product_name=data_product_name,
        layer=str(data_product.get("layer")),
        privacy=privacy,
        serving=serving,
        columns=columns,
    )
    consumer_contract_evaluation = evaluate_consumer_contract_reference_safely(
        platform_root,
        data_product_name=data_product_name,
        layer=str(data_product.get("layer")),
        privacy=privacy,
        serving=serving,
    )
    grant_evaluation = evaluate_access_grants_safely(
        platform_root,
        data_product_name=data_product_name,
        serving=serving,
        evaluation_time=generated,
    )
    controls = controls_checked(
        columns=columns,
        privacy=privacy,
        serving=serving,
        known_personas=load_access_persona_ids(platform_root),
    )
    controls = registry_controls_checked("policy", policy_evaluation) + registry_controls_checked(
        "consumer_contract",
        consumer_contract_evaluation,
    ) + registry_controls_checked("access_grant", grant_evaluation) + controls
    passed = all(control["passed"] for control in controls)
    check_id = stable_id(
        "access-policy",
        release_id,
        data_product_name,
        dataset_snapshot_id,
        table_version,
        content_hash,
    )
    return {
        "artifact_type": "access_policy_check.v1",
        "report_version": REPORT_VERSION,
        "check_id": check_id,
        "generated_at": generated,
        "environment": environment,
        "release_id": release_id,
        "data_product": data_product_name,
        "contract_path": contract_path.as_posix(),
        "contract_hash": hash_file(contract_path),
        "contract_version": contract.get("contractVersion"),
        "dataset_snapshot_id": dataset_snapshot_id,
        "table_version": table_version,
        "content_hash": content_hash,
        "row_count": row_count,
        "policy": {
            "policy_id": policy_evaluation.get("policy_id"),
            "policy_name": policy_evaluation.get("policy_name"),
            "policy_version": policy_evaluation.get("policy_version"),
            "policy_status": policy_evaluation.get("status"),
            "policy_severity": policy_evaluation.get("severity"),
            "policy_owner": policy_evaluation.get("owner"),
            "policy_effective_from": policy_evaluation.get("effective_from"),
            "policy_registry_scope": policy_evaluation.get("policy_registry_scope"),
            "policy_registry_hash": policy_evaluation.get("policy_registry_hash"),
            "policy_hash": policy_evaluation.get("policy_hash"),
            "persona_registry_hash": safe_persona_registry_hash(platform_root),
            "access_policy": serving.get("accessPolicy"),
            "access_personas": serving.get("accessPersonas", []),
            "declared_personas": serving.get("accessPersonas", []),
            "allowed_personas": policy_evaluation.get("allowed_personas", []),
            "required_columns": policy_evaluation.get("required_columns", []),
            "resolved_controls": policy_evaluation.get("resolved_controls", {}),
            "consumer_contract": serving.get("consumerContract"),
            "consumer_contract_name": consumer_contract_evaluation.get("contract_name"),
            "consumer_contract_version": consumer_contract_evaluation.get("contract_version"),
            "consumer_contract_status": consumer_contract_evaluation.get("contract_status"),
            "consumer_contract_severity": consumer_contract_evaluation.get("contract_severity"),
            "consumer_contract_owner": consumer_contract_evaluation.get("contract_owner"),
            "consumer_contract_effective_from": consumer_contract_evaluation.get("contract_effective_from"),
            "consumer_contract_registry_scope": consumer_contract_evaluation.get("contract_registry_scope"),
            "consumer_contract_registry_hash": consumer_contract_evaluation.get("contract_registry_hash"),
            "consumer_contract_allowed_personas": consumer_contract_evaluation.get("allowed_personas", []),
            "consumer_contract_allowed_access_modes": consumer_contract_evaluation.get("allowed_access_modes", []),
            "consumer_contract_required_evidence": consumer_contract_evaluation.get("required_evidence", []),
            "consumer_contract_resolved_controls": consumer_contract_evaluation.get("resolved_controls", {}),
            "publication_gate": serving.get("publicationGate"),
            "tenant_isolation": privacy.get("tenantIsolation"),
            "pii_classification": privacy.get("classification"),
            "contains_pii": privacy.get("containsPii"),
            "retention_days": privacy.get("retentionDays"),
        },
        "access_grants": {
            "registry_scope": grant_evaluation.get("registry_scope"),
            "registry_hash": grant_evaluation.get("registry_hash"),
            "required_personas": grant_evaluation.get("required_personas", []),
            "active_personas": grant_evaluation.get("active_personas", []),
            "active_grant_count": grant_evaluation.get("active_grant_count", 0),
            "active_grants": grant_evaluation.get("active_grants", []),
            "missing_personas": grant_evaluation.get("missing_personas", []),
            "expired_grants": grant_evaluation.get("expired_grants", []),
            "incomplete_grants": grant_evaluation.get("incomplete_grants", []),
            "passed": grant_evaluation.get("passed") is True,
        },
        "columns": [
            {
                "name": column.get("name"),
                "pii": column.get("pii"),
                "type": column.get("type"),
            }
            for column in columns
        ],
        "controls_checked": controls,
        "test_cases": access_test_cases(serving),
        "failures": [
            {
                "control": control["control"],
                "message": control["message"],
            }
            for control in controls
            if not control["passed"]
        ],
        "passed": passed,
    }


def evaluate_access_policy_contract_safely(
    root: Path,
    *,
    data_product_name: str,
    layer: str | None,
    privacy: dict[str, Any],
    serving: dict[str, Any],
    columns: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        return evaluate_access_policy_contract(
            root,
            data_product_name=data_product_name,
            layer=layer,
            privacy=privacy,
            serving=serving,
            columns=columns,
        )
    except KeyError as exc:
        policy_id = serving.get("accessPolicy")
        return {
            "policy_id": policy_id if isinstance(policy_id, str) else None,
            "policy_name": None,
            "policy_version": None,
            "status": None,
            "severity": None,
            "owner": None,
            "effective_from": None,
            "policy_registry_scope": None,
            "policy_registry_hash": None,
            "policy_hash": None,
            "data_product": data_product_name,
            "passed": False,
            "checks": [
                {
                    "name": "policy_registered",
                    "passed": False,
                    "details": {"reason": str(exc)},
                }
            ],
            "required_columns": [],
            "allowed_personas": [],
            "resolved_controls": {},
        }


def evaluate_consumer_contract_reference_safely(
    root: Path,
    *,
    data_product_name: str,
    layer: str | None,
    privacy: dict[str, Any],
    serving: dict[str, Any],
) -> dict[str, Any]:
    try:
        return evaluate_consumer_contract_reference(
            root,
            data_product_name=data_product_name,
            layer=layer,
            privacy=privacy,
            serving=serving,
        )
    except KeyError as exc:
        contract_id = serving.get("consumerContract")
        return {
            "contract_id": contract_id if isinstance(contract_id, str) else None,
            "contract_name": None,
            "contract_version": None,
            "contract_status": None,
            "contract_severity": None,
            "contract_owner": None,
            "contract_effective_from": None,
            "contract_registry_scope": None,
            "contract_registry_hash": None,
            "data_product": data_product_name,
            "passed": False,
            "checks": [
                {
                    "name": "consumer_contract_registered",
                    "passed": False,
                    "details": {"reason": str(exc)},
                }
            ],
            "allowed_personas": [],
            "allowed_access_modes": [],
            "required_evidence": [],
            "resolved_controls": {},
        }


def evaluate_access_grants_safely(
    root: Path,
    *,
    data_product_name: str,
    serving: dict[str, Any],
    evaluation_time: str | None,
) -> dict[str, Any]:
    try:
        return evaluate_access_grants(
            root,
            data_product_name=data_product_name,
            serving=serving,
            evaluation_time=evaluation_time,
        )
    except KeyError as exc:
        return {
            "registry_scope": None,
            "registry_hash": None,
            "data_product": data_product_name,
            "required_personas": [],
            "active_personas": [],
            "active_grant_count": 0,
            "active_grants": [],
            "missing_personas": [],
            "expired_grants": [],
            "incomplete_grants": [],
            "passed": False,
            "checks": [
                {
                    "name": "access_grant_registry_resolved",
                    "passed": False,
                    "details": {"reason": str(exc)},
                }
            ],
        }


def registry_controls_checked(namespace: str, evaluation: dict[str, Any]) -> list[dict[str, Any]]:
    checks = evaluation.get("checks")
    if not isinstance(checks, list):
        return [
            control(
                f"registry_{namespace}_evaluation",
                False,
                f"{namespace} registry evaluation did not return checks",
            )
        ]
    return [
        control(
            f"registry_{check.get('name')}",
            check.get("passed") is True,
            f"access policy registry check {check.get('name')} must pass",
            check.get("details") if isinstance(check.get("details"), dict) else {},
        )
        for check in checks
        if isinstance(check, dict)
    ]


def safe_persona_registry_hash(root: Path) -> str | None:
    try:
        return hash_access_persona_registry(root)
    except FileNotFoundError:
        return None


def controls_checked(
    *,
    columns: list[dict[str, Any]],
    privacy: dict[str, Any],
    serving: dict[str, Any],
    known_personas: set[str],
) -> list[dict[str, Any]]:
    column_names = {column.get("name") for column in columns}
    pii_columns = [str(column.get("name")) for column in columns if column.get("pii") is True]
    access_personas = serving.get("accessPersonas")
    unknown_personas = [
        persona for persona in access_personas or [] if persona not in known_personas
    ]
    direct_identifiers = sorted(str(name) for name in column_names if name in direct_identifier_columns())
    return [
        control(
            "row_level_org_isolation",
            serving.get("accessPolicy") != "row_level_org_isolation" or "org_id" in column_names,
            "row_level_org_isolation requires an org_id column",
        ),
        control(
            "tenant_isolation_required_for_pii",
            privacy.get("containsPii") is not True or privacy.get("tenantIsolation") == "REQUIRED",
            "PII data products require tenantIsolation=REQUIRED",
        ),
        control(
            "pii_columns_tagged",
            privacy.get("containsPii") is not True or bool(pii_columns),
            "containsPii=true requires at least one pii=true column",
            {"pii_columns": pii_columns},
        ),
        control(
            "direct_identifier_scan",
            not direct_identifiers,
            "approved Gold/Silver serving contracts must not expose direct identifier columns",
            {"direct_identifier_columns": direct_identifiers},
        ),
        control(
            "access_personas_known",
            isinstance(access_personas, list) and bool(access_personas) and not unknown_personas,
            "accessPersonas must be non-empty and known to the platform",
            {"unknown_personas": unknown_personas},
        ),
        control(
            "consumer_contract_declared",
            isinstance(serving.get("consumerContract"), str) and bool(str(serving.get("consumerContract")).strip()),
            "consumerContract must be declared",
        ),
        control(
            "audit_logging_required",
            isinstance(serving.get("accessPolicy"), str) and bool(str(serving.get("accessPolicy")).strip()),
            "accessPolicy must be declared so audit decisions can be correlated",
        ),
    ]


def access_test_cases(serving: dict[str, Any]) -> list[dict[str, Any]]:
    access_policy = serving.get("accessPolicy")
    personas = serving.get("accessPersonas", [])
    allowed_persona = personas[0] if isinstance(personas, list) and personas else "DataPlatformOperator"
    return [
        {
            "name": "allowed_persona_same_org",
            "actor_persona": allowed_persona,
            "action": "read",
            "resource_scope": "same_org",
            "expected_decision": "ALLOW",
            "control": "persona_allowlist",
        },
        {
            "name": "unauthorized_persona_denied",
            "actor_persona": "UnknownConsumer",
            "action": "read",
            "resource_scope": "same_org",
            "expected_decision": "DENY",
            "control": "persona_allowlist",
        },
        {
            "name": "cross_org_denied",
            "actor_persona": allowed_persona,
            "action": "read",
            "resource_scope": "other_org",
            "expected_decision": "DENY" if access_policy == "row_level_org_isolation" else "NOT_APPLICABLE",
            "control": "row_level_org_isolation",
        },
    ]


def control(control_name: str, passed: bool, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "control": control_name,
        "passed": passed,
        "message": message,
        "details": details or {},
    }


def find_data_product_contract(root: Path, data_product_name: str) -> Path:
    candidates = sorted((root / "contracts" / "data-products").glob(f"{data_product_name}.v*.yaml"))
    if not candidates:
        raise FileNotFoundError(f"data product contract does not exist: {data_product_name}")
    return candidates[-1]


def stable_id(*parts: object) -> str:
    value = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _mapping(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    return value if isinstance(value, dict) else {}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

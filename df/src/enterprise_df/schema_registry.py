from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_df.contracts import VALID_COMPATIBILITY_MODES, load_yaml


REPORT_VERSION = 1


@dataclass(frozen=True)
class SchemaRegistryCheckResult:
    output_path: Path
    report: dict[str, Any]


def write_schema_registry_report(
    root: str | Path,
    output_path: str | Path,
    *,
    topic_name: str | None = None,
    registry_uri: str | None = None,
    generated_at: str | None = None,
) -> SchemaRegistryCheckResult:
    report = build_schema_registry_report(
        root,
        topic_name=topic_name,
        registry_uri=registry_uri,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SchemaRegistryCheckResult(output_path=target, report=report)


def build_schema_registry_report(
    root: str | Path,
    *,
    topic_name: str | None = None,
    registry_uri: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    all_topic_contracts = load_topic_contracts(platform_root)
    topic_contracts = filter_topic_contracts(all_topic_contracts, topic_name=topic_name)
    subjects = [subject_report(platform_root, path, contract, all_topic_contracts) for path, contract in topic_contracts]
    passed = all(subject["compatibility_passed"] for subject in subjects)
    return {
        "artifact_type": "schema_registry_compatibility_report.v1",
        "report_version": REPORT_VERSION,
        "generated_at": generated_at or utc_now(),
        "registry_uri": registry_uri or "local-json-schema-registry-preflight",
        "mode": "local_preflight",
        "compatibility_passed": passed,
        "subject_count": len(subjects),
        "subjects": subjects,
        "summary": {
            "passed_subjects": sum(1 for subject in subjects if subject["compatibility_passed"]),
            "failed_subjects": sum(1 for subject in subjects if not subject["compatibility_passed"]),
        },
    }


def load_topic_contracts(root: Path, *, topic_name: str | None = None) -> list[tuple[Path, dict[str, Any]]]:
    contracts: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((root / "contracts" / "topics").glob("*.yaml")):
        contract = load_yaml(path)
        name = contract.get("topic", {}).get("name")
        if topic_name and name != topic_name:
            continue
        contracts.append((path, contract))
    if topic_name and not contracts:
        raise FileNotFoundError(f"topic contract does not exist: {topic_name}")
    return contracts


def filter_topic_contracts(
    contracts: list[tuple[Path, dict[str, Any]]],
    *,
    topic_name: str | None = None,
) -> list[tuple[Path, dict[str, Any]]]:
    if not topic_name:
        return contracts
    filtered = [
        (path, contract)
        for path, contract in contracts
        if contract.get("topic", {}).get("name") == topic_name
    ]
    if not filtered:
        raise FileNotFoundError(f"topic contract does not exist: {topic_name}")
    return filtered


def subject_report(
    root: Path,
    path: Path,
    contract: dict[str, Any],
    all_topic_contracts: list[tuple[Path, dict[str, Any]]],
) -> dict[str, Any]:
    topic = _mapping(contract, "topic")
    schema = _mapping(contract, "schema")
    topic_name = str(topic.get("name"))
    contract_version = contract.get("contractVersion")
    compatibility_mode = schema.get("compatibility")
    envelope_path = root / str(schema.get("envelopeSchema"))
    payload_path = root / str(schema.get("payloadSchema"))
    envelope_schema, envelope_errors = load_json_schema(envelope_path)
    payload_schema, payload_errors = load_json_schema(payload_path)
    prior_versions = prior_topic_versions(topic_name, all_topic_contracts)
    compatibility_checks = compatibility_check_results(
        root,
        topic_name=topic_name,
        compatibility_mode=compatibility_mode,
        payload_schema=payload_schema,
        prior_versions=prior_versions,
    )
    checks = [
        check_result("topic_contract_exists", True, {"path": path.as_posix()}),
        check_result(
            "compatibility_mode_supported",
            compatibility_mode in VALID_COMPATIBILITY_MODES,
            {"compatibility": compatibility_mode, "supported": sorted(VALID_COMPATIBILITY_MODES)},
        ),
        check_result(
            "envelope_schema_valid_json",
            not envelope_errors,
            {"path": envelope_path.as_posix(), "errors": envelope_errors},
        ),
        check_result(
            "payload_schema_valid_json",
            not payload_errors,
            {"path": payload_path.as_posix(), "errors": payload_errors},
        ),
        *compatibility_checks,
    ]
    return {
        "subject": f"{topic_name}-value",
        "topic": topic_name,
        "contract_path": path.as_posix(),
        "contract_hash": hash_file(path),
        "contract_version": contract_version,
        "product": topic.get("product"),
        "domain": topic.get("domain"),
        "compatibility": compatibility_mode,
        "envelope_schema": schema_entry(envelope_path, envelope_schema),
        "payload_schema": schema_entry(payload_path, payload_schema),
        "prior_versions_checked": [item["topic_name"] for item in prior_versions],
        "compatibility_passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def compatibility_check_results(
    root: Path,
    *,
    topic_name: str,
    compatibility_mode: object,
    payload_schema: dict[str, Any] | None,
    prior_versions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if compatibility_mode not in VALID_COMPATIBILITY_MODES:
        return [
            check_result(
                "backward_transitive_local",
                False,
                {"reason": "unsupported_compatibility_mode", "compatibility": compatibility_mode},
            )
        ]
    if payload_schema is None:
        return [
            check_result(
                "backward_transitive_local",
                False,
                {"reason": "payload_schema_invalid"},
            )
        ]
    if not prior_versions:
        return [
            check_result(
                "backward_transitive_local",
                True,
                {"reason": "no_prior_versions", "topic": topic_name},
            )
        ]

    checks: list[dict[str, Any]] = []
    for prior in prior_versions:
        prior_payload_path = root / prior["payload_schema_path"]
        prior_payload_schema, errors = load_json_schema(prior_payload_path)
        if errors or prior_payload_schema is None:
            checks.append(
                check_result(
                    "backward_transitive_local",
                    False,
                    {
                        "prior_topic": prior["topic_name"],
                        "reason": "prior_payload_schema_invalid",
                        "errors": errors,
                    },
                )
            )
            continue
        violations = backward_compatibility_violations(prior_payload_schema, payload_schema)
        checks.append(
            check_result(
                "backward_transitive_local",
                not violations,
                {
                    "prior_topic": prior["topic_name"],
                    "violations": violations,
                },
            )
        )
    return checks


def backward_compatibility_violations(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    previous_required = set(previous.get("required", [])) if isinstance(previous.get("required"), list) else set()
    current_required = set(current.get("required", [])) if isinstance(current.get("required"), list) else set()
    previous_properties = _mapping(previous, "properties")
    current_properties = _mapping(current, "properties")
    violations: list[str] = []

    removed_required = sorted(previous_required - current_required)
    if removed_required:
        violations.append(f"required fields removed or made optional: {removed_required}")

    for field in sorted(previous_required):
        if field not in current_properties:
            violations.append(f"required field removed from properties: {field}")

    for field, previous_property in sorted(previous_properties.items()):
        if field not in current_properties:
            continue
        if not isinstance(previous_property, dict) or not isinstance(current_properties[field], dict):
            continue
        previous_type = normalize_json_type(previous_property.get("type"))
        current_type = normalize_json_type(current_properties[field].get("type"))
        if previous_type and current_type and not previous_type.issubset(current_type):
            violations.append(f"field {field} type narrowed from {sorted(previous_type)} to {sorted(current_type)}")
    return violations


def prior_topic_versions(topic_name: str, contracts: list[tuple[Path, dict[str, Any]]]) -> list[dict[str, Any]]:
    base, version = split_topic_version(topic_name)
    if version is None:
        return []
    prior: list[dict[str, Any]] = []
    for path, contract in contracts:
        other_name = contract.get("topic", {}).get("name")
        if not isinstance(other_name, str):
            continue
        other_base, other_version = split_topic_version(other_name)
        if other_base != base or other_version is None or other_version >= version:
            continue
        schema = _mapping(contract, "schema")
        payload_schema_path = schema.get("payloadSchema")
        if isinstance(payload_schema_path, str):
            prior.append(
                {
                    "topic_name": other_name,
                    "version": other_version,
                    "contract_path": path.as_posix(),
                    "payload_schema_path": payload_schema_path,
                }
            )
    return sorted(prior, key=lambda item: item["version"])


def split_topic_version(topic_name: str) -> tuple[str, int | None]:
    marker = ".v"
    if marker not in topic_name:
        return topic_name, None
    base, version_text = topic_name.rsplit(marker, 1)
    try:
        return base, int(version_text)
    except ValueError:
        return topic_name, None


def schema_entry(path: Path, schema: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "hash": hash_file(path) if path.is_file() else None,
        "id": schema.get("$id") if schema else None,
        "title": schema.get("title") if schema else None,
    }


def load_json_schema(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.is_file():
        return None, [f"schema file does not exist: {path.as_posix()}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON: {exc.msg}"]
    if not isinstance(data, dict):
        return None, ["schema root must be a JSON object"]
    return data, []


def check_result(check: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "check": check,
        "passed": passed,
        "details": details,
    }


def normalize_json_type(value: object) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return set(value)
    return set()


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

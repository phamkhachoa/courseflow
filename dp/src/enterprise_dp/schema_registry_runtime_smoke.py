from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.event_backbone_smoke import (
    CommandRunner,
    DEFAULT_COMPOSE_FILE,
    execute_step,
    resolve_compose_path,
    run_command,
)
from enterprise_dp.schema_registry import build_schema_registry_report


DEFAULT_SERVICE = "schema-registry"
DEFAULT_REGISTRY_URL = "http://localhost:18082"
DEFAULT_GROUP_ID = "enterprise-dp-local-smoke"
DEFAULT_GENERATED_AT = "2026-01-15T09:15:20Z"


@dataclass(frozen=True)
class SchemaRegistryRuntimeSmokeResult:
    output_path: Path
    report: dict[str, Any]


@dataclass(frozen=True)
class HttpResult:
    method: str
    path: str
    status: int
    body: bytes
    error: str | None = None


def write_schema_registry_runtime_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    topic_name: str | None = None,
    compose_file: str | Path | None = None,
    service: str = DEFAULT_SERVICE,
    registry_url: str = DEFAULT_REGISTRY_URL,
    group_id: str = DEFAULT_GROUP_ID,
    release_id: str = "local-schema-registry-runtime-smoke",
    environment: str = "local",
    generated_at: str | None = None,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
    wait_attempts: int = 30,
    wait_interval_seconds: float = 1.0,
    start_runtime: bool = True,
) -> SchemaRegistryRuntimeSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or DEFAULT_GENERATED_AT
    compatibility = build_schema_registry_report(
        platform_root,
        topic_name=topic_name,
        registry_uri=registry_url,
        generated_at=generated,
    )
    compatibility_path = target_dir / "schema-registry-compatibility-report.json"
    compatibility_path.write_text(f"{canonical_json(compatibility)}\n", encoding="utf-8")
    compose_path = resolve_compose_path(platform_root, compose_file or DEFAULT_COMPOSE_FILE)
    runner = command_runner or run_command
    command_log: list[dict[str, Any]] = []
    http_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    registry_info: dict[str, Any] = {}
    subjects: list[dict[str, Any]] = []

    try:
        if start_runtime:
            execute_step(
                command_log,
                runner,
                ["docker", "compose", "-f", compose_path.as_posix(), "up", "-d", service],
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="compose_up_schema_registry",
            )
        registry_info = wait_for_registry(
            registry_url,
            http_log=http_log,
            attempts=wait_attempts,
            interval_seconds=wait_interval_seconds,
        )
        for subject in compatibility.get("subjects", []) if isinstance(compatibility.get("subjects"), list) else []:
            if not isinstance(subject, dict):
                continue
            subjects.append(publish_subject(platform_root, registry_url, group_id, subject, http_log=http_log))
    except RuntimeError as exc:
        failed_checks.append({"check": "schema_registry_runtime_command", "message": str(exc)})

    failed_checks.extend(
        failed_schema_registry_runtime_checks(
            compatibility=compatibility,
            subjects=subjects,
            registry_info=registry_info,
        )
    )
    publication_manifest = build_publication_manifest(
        generated_at=generated,
        environment=environment,
        registry_url=registry_url,
        subjects=subjects,
    )
    publication_manifest_path = target_dir / "schema-registry-publication-manifest.json"
    publication_manifest_path.write_text(f"{canonical_json(publication_manifest)}\n", encoding="utf-8")
    report = {
        "artifact_type": "schema_registry_runtime_smoke_report.v1",
        "report_version": 1,
        "capability_id": "schema-registry-compatibility",
        "report_id": f"schema-registry-runtime-smoke:{environment}:{release_id}:{group_id}",
        "generated_at": generated,
        "environment": environment,
        "release_id": release_id,
        "runtime_scope": {
            "mode": "local_apicurio_ccompat_v7_publication_readback",
            "covered": [
                "apicurio_registry_container_started",
                "registry_system_info_endpoint_reachable",
                "topic_payload_schema_subjects_published_or_reused",
                "subject_compatibility_config_applied",
                "published_subject_versions_read_back",
                "published_schema_hash_matches_contract",
                "publication_manifest_generated",
            ],
            "not_covered": [
                "production_registry_authentication_authorization",
                "production_registry_ha_storage",
                "producer_schema_id_enforcement",
                "broker_or_sink_schema_validation",
                "external_attestation_for_production_registry",
            ],
        },
        "registry": {
            "vendor": "apicurio",
            "api": "confluent_compatible_v7",
            "uri": registry_url,
            "group_id": group_id,
            "service": service,
            "compose_file": compose_path.as_posix(),
            "info": registry_info,
        },
        "compatibility_report": {
            "path": compatibility_path.as_posix(),
            "hash": hash_file(compatibility_path),
            "artifact_type": compatibility.get("artifact_type"),
            "compatibility_passed": compatibility.get("compatibility_passed"),
            "subject_count": compatibility.get("subject_count"),
        },
        "publication_manifest": {
            "path": publication_manifest_path.as_posix(),
            "hash": hash_file(publication_manifest_path),
            "artifact_type": publication_manifest.get("artifact_type"),
            "subject_count": len(publication_manifest.get("subjects", [])),
        },
        "subjects": subjects,
        "commands": command_log,
        "http_exchanges": http_log,
        "summary": {
            "registry_vendor": "apicurio",
            "registry_api": "confluent_compatible_v7",
            "registry_uri": registry_url,
            "group_id": group_id,
            "compatibility_passed": compatibility.get("compatibility_passed") is True,
            "subject_count": len(subjects),
            "published_subject_count": sum(1 for subject in subjects if subject.get("registered") is True),
            "readback_passed_count": sum(1 for subject in subjects if subject.get("readback_passed") is True),
            "hash_match_count": sum(1 for subject in subjects if subject.get("payload_schema_hash_matches") is True),
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        },
    }
    report["passed"] = not failed_checks
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SchemaRegistryRuntimeSmokeResult(output_path=target, report=report)


def wait_for_registry(
    registry_url: str,
    *,
    http_log: list[dict[str, Any]],
    attempts: int,
    interval_seconds: float,
) -> dict[str, Any]:
    last_error = None
    for _ in range(attempts):
        result = http_request(registry_url, "GET", "/apis/registry/v2/system/info", http_log=http_log)
        if result.status == 200:
            return parse_json_object(result.body)
        last_error = result.error or result.body[:300].decode("utf-8", errors="replace")
        if interval_seconds > 0:
            time.sleep(interval_seconds)
    raise RuntimeError(f"schema registry did not become ready: {last_error}")


def publish_subject(
    root: Path,
    registry_url: str,
    group_id: str,
    compatibility_subject: dict[str, Any],
    *,
    http_log: list[dict[str, Any]],
) -> dict[str, Any]:
    subject = str(compatibility_subject.get("subject") or "")
    payload_schema = compatibility_subject.get("payload_schema") if isinstance(compatibility_subject.get("payload_schema"), dict) else {}
    schema_path = Path(str(payload_schema.get("path") or ""))
    if not schema_path.is_absolute():
        schema_path = root / schema_path
    schema_bytes = schema_path.read_bytes()
    expected_hash = hash_file(schema_path)
    encoded_subject = quote(subject, safe="")
    publish = http_request(
        registry_url,
        "POST",
        f"/apis/ccompat/v7/subjects/{encoded_subject}/versions",
        body=json.dumps({"schema": schema_bytes.decode("utf-8"), "schemaType": "JSON"}).encode("utf-8"),
        headers={
            "Content-Type": "application/vnd.schemaregistry.v1+json",
            "X-Registry-GroupId": group_id,
        },
        http_log=http_log,
    )
    if publish.status not in {200, 201}:
        raise RuntimeError(f"failed to publish schema subject {subject}: HTTP {publish.status} {publish.error or publish.body[:300]!r}")
    publish_json = parse_json_object(publish.body)
    compatibility = str(compatibility_subject.get("compatibility") or "BACKWARD_TRANSITIVE")
    config_update = http_request(
        registry_url,
        "PUT",
        f"/apis/ccompat/v7/config/{encoded_subject}",
        body=json.dumps({"compatibility": compatibility}).encode("utf-8"),
        headers={
            "Content-Type": "application/vnd.schemaregistry.v1+json",
            "X-Registry-GroupId": group_id,
        },
        http_log=http_log,
    )
    config = http_request(
        registry_url,
        "GET",
        f"/apis/ccompat/v7/config/{encoded_subject}",
        headers={"X-Registry-GroupId": group_id},
        http_log=http_log,
    )
    version = http_request(
        registry_url,
        "GET",
        f"/apis/ccompat/v7/subjects/{encoded_subject}/versions/latest",
        headers={"X-Registry-GroupId": group_id},
        http_log=http_log,
    )
    content = http_request(
        registry_url,
        "GET",
        f"/apis/ccompat/v7/subjects/{encoded_subject}/versions/latest/schema",
        headers={"X-Registry-GroupId": group_id},
        http_log=http_log,
    )
    config_json = parse_json_object(config.body) if config.status == 200 else {}
    version_json = parse_json_object(version.body) if version.status == 200 else {}
    actual_hash = hash_bytes(content.body) if content.status == 200 else None
    schema_id = publish_json.get("id") or version_json.get("id")
    return {
        "subject": subject,
        "topic": compatibility_subject.get("topic"),
        "product": compatibility_subject.get("product"),
        "domain": compatibility_subject.get("domain"),
        "contract_path": compatibility_subject.get("contract_path"),
        "contract_hash": compatibility_subject.get("contract_hash"),
        "registered": version.status == 200 and content.status == 200,
        "created_or_reused": publish.status in {200, 201},
        "schema_id": str(schema_id) if schema_id is not None else None,
        "artifact_id": subject,
        "group_id": group_id,
        "version": version_json.get("version"),
        "artifact_type": version_json.get("schemaType") or "JSON",
        "state": "ENABLED" if version.status == 200 else None,
        "compatibility": config_json.get("compatibilityLevel"),
        "expected_compatibility": compatibility,
        "compatibility_configured": config.status == 200 and config_json.get("compatibilityLevel") == compatibility,
        "payload_schema_path": schema_path.as_posix(),
        "payload_schema_hash": expected_hash,
        "published_payload_schema_hash": actual_hash,
        "payload_schema_hash_matches": actual_hash == expected_hash,
        "readback_passed": content.status == 200 and actual_hash == expected_hash,
        "producer_enforced": False,
        "broker_validation": False,
        "registry_uri": registry_url,
        "http_status": {
            "publish": publish.status,
            "config_update": config_update.status,
            "config": config.status,
            "version": version.status,
            "content": content.status,
        },
    }


def http_request(
    registry_url: str,
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    http_log: list[dict[str, Any]],
) -> HttpResult:
    request = Request(f"{registry_url.rstrip('/')}{path}", data=body, method=method, headers=headers or {})
    try:
        with urlopen(request, timeout=20) as response:
            payload = response.read()
            result = HttpResult(method=method, path=path, status=response.status, body=payload)
    except HTTPError as exc:
        result = HttpResult(method=method, path=path, status=exc.code, body=exc.read(), error=str(exc))
    except URLError as exc:
        result = HttpResult(method=method, path=path, status=0, body=b"", error=str(exc))
    http_log.append(
        {
            "method": result.method,
            "path": result.path,
            "status": result.status,
            "body_preview": result.body[:500].decode("utf-8", errors="replace"),
            "error": result.error,
        }
    )
    return result


def build_publication_manifest(
    *,
    generated_at: str,
    environment: str,
    registry_url: str,
    subjects: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "schema_registry_publication_manifest.v1",
        "report_version": 1,
        "generated_at": generated_at,
        "environment": environment,
        "registry_vendor": "apicurio",
        "registry_api": "confluent_compatible_v7",
        "registry_uri": registry_url,
        "subjects": [
            {
                "subject": subject.get("subject"),
                "topic": subject.get("topic"),
                "registered": subject.get("registered"),
                "schema_id": subject.get("schema_id"),
                "artifact_id": subject.get("artifact_id"),
                "version": subject.get("version"),
                "compatibility": subject.get("compatibility"),
                "payload_schema_hash": subject.get("payload_schema_hash"),
                "producer_enforced": subject.get("producer_enforced"),
                "broker_validation": subject.get("broker_validation"),
                "registry_uri": subject.get("registry_uri"),
            }
            for subject in subjects
        ],
    }


def failed_schema_registry_runtime_checks(
    *,
    compatibility: dict[str, Any],
    subjects: list[dict[str, Any]],
    registry_info: dict[str, Any],
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if not registry_info:
        failed.append({"check": "registry_system_info_reachable"})
    if compatibility.get("compatibility_passed") is not True:
        failed.append({"check": "compatibility_report_passed", "compatibility_passed": compatibility.get("compatibility_passed")})
    expected_subject_count = compatibility.get("subject_count") if isinstance(compatibility.get("subject_count"), int) else 0
    if len(subjects) != expected_subject_count:
        failed.append({"check": "subject_count_published", "expected": expected_subject_count, "actual": len(subjects)})
    for subject in subjects:
        if subject.get("registered") is not True:
            failed.append({"check": "subject_registered", "subject": subject.get("subject"), "http_status": subject.get("http_status")})
        if subject.get("schema_id") is None:
            failed.append({"check": "subject_schema_id_present", "subject": subject.get("subject")})
        if subject.get("version") is None:
            failed.append({"check": "subject_version_present", "subject": subject.get("subject")})
        if subject.get("compatibility_configured") is not True:
            failed.append(
                {
                    "check": "subject_compatibility_configured",
                    "subject": subject.get("subject"),
                    "expected": subject.get("expected_compatibility"),
                    "actual": subject.get("compatibility"),
                }
            )
        if subject.get("readback_passed") is not True:
            failed.append(
                {
                    "check": "subject_readback_hash_matches",
                    "subject": subject.get("subject"),
                    "expected": subject.get("payload_schema_hash"),
                    "actual": subject.get("published_payload_schema_hash"),
                }
            )
    return failed


def parse_json_object(payload: bytes) -> dict[str, Any]:
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("schema registry response must be a JSON object")
    return data


def hash_bytes(payload: bytes) -> str:
    import hashlib

    return f"sha256:{hashlib.sha256(payload).hexdigest()}"

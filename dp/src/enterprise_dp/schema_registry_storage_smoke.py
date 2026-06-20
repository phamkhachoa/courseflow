from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any
from urllib.parse import quote

from enterprise_dp.catalog import canonical_json
from enterprise_dp.event_backbone_smoke import CommandResult, CommandRunner, run_command, stable_id
from enterprise_dp.schema_registry_auth_smoke import hash_bytes
from enterprise_dp.schema_registry_runtime_smoke import HttpResult, http_request, parse_json_object


DEFAULT_SQL_IMAGE = "apicurio/apicurio-registry-sql:2.6.5.Final"
DEFAULT_POSTGRES_IMAGE = "postgres:16-alpine"
DEFAULT_GENERATED_AT = "2026-01-15T09:15:20Z"
DEFAULT_NETWORK = "enterprise-dp-schema-registry-storage-smoke"
DEFAULT_POSTGRES_CONTAINER = "enterprise-dp-schema-registry-storage-postgres"
DEFAULT_REGISTRY_A_CONTAINER = "enterprise-dp-schema-registry-storage-a"
DEFAULT_REGISTRY_B_CONTAINER = "enterprise-dp-schema-registry-storage-b"
DEFAULT_REGISTRY_A_PORT = 18084
DEFAULT_REGISTRY_B_PORT = 18085
DEFAULT_GROUP_ID = "enterprise-dp-storage-smoke"
DEFAULT_SUBJECT = "dp.local.schema_registry_storage_smoke-value"
POSTGRES_USER = "registry"
POSTGRES_DB = "registry"
POSTGRES_PASSWORD = "registry_local_only_change_me"


@dataclass(frozen=True)
class SchemaRegistryStorageSmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_schema_registry_storage_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    sql_image: str = DEFAULT_SQL_IMAGE,
    postgres_image: str = DEFAULT_POSTGRES_IMAGE,
    network: str = DEFAULT_NETWORK,
    postgres_container: str = DEFAULT_POSTGRES_CONTAINER,
    registry_a_container: str = DEFAULT_REGISTRY_A_CONTAINER,
    registry_b_container: str = DEFAULT_REGISTRY_B_CONTAINER,
    registry_a_port: int = DEFAULT_REGISTRY_A_PORT,
    registry_b_port: int = DEFAULT_REGISTRY_B_PORT,
    group_id: str = DEFAULT_GROUP_ID,
    subject: str = DEFAULT_SUBJECT,
    release_id: str = "local-schema-registry-storage-smoke",
    environment: str = "local",
    generated_at: str | None = None,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 600,
    wait_attempts: int = 45,
    wait_interval_seconds: float = 1.0,
    start_runtime: bool = True,
    cleanup_runtime: bool = True,
    registry_a_url: str | None = None,
    registry_b_url: str | None = None,
) -> SchemaRegistryStorageSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or DEFAULT_GENERATED_AT
    runner = command_runner or run_command
    command_log: list[dict[str, Any]] = []
    http_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    registry_a = registry_a_url or f"http://localhost:{registry_a_port}"
    registry_b = registry_b_url or f"http://localhost:{registry_b_port}"
    registry_a_info: dict[str, Any] = {}
    registry_b_info: dict[str, Any] = {}
    probes: dict[str, Any] = {}

    try:
        if start_runtime:
            prepare_storage_runtime(
                platform_root,
                target_dir,
                command_log,
                runner,
                sql_image=sql_image,
                postgres_image=postgres_image,
                network=network,
                postgres_container=postgres_container,
                registry_a_container=registry_a_container,
                registry_b_container=registry_b_container,
                registry_a_port=registry_a_port,
                registry_b_port=registry_b_port,
                timeout_seconds=command_timeout_seconds,
                http_log=http_log,
                wait_attempts=wait_attempts,
                wait_interval_seconds=wait_interval_seconds,
            )
        registry_a_info = wait_for_registry_resilient(
            registry_a,
            http_log=http_log,
            attempts=wait_attempts,
            interval_seconds=wait_interval_seconds,
        )
        registry_b_info = wait_for_registry_resilient(
            registry_b,
            http_log=http_log,
            attempts=wait_attempts,
            interval_seconds=wait_interval_seconds,
        )
        probes = run_storage_probes(registry_a, registry_b, group_id=group_id, subject=subject, http_log=http_log)
        if start_runtime:
            restart_registry_replica(
                platform_root,
                command_log,
                runner,
                registry_a_container=registry_a_container,
                timeout_seconds=command_timeout_seconds,
            )
            wait_for_registry_resilient(
                registry_a,
                http_log=http_log,
                attempts=wait_attempts,
                interval_seconds=wait_interval_seconds,
            )
            probes["replica_a_after_restart"] = readback_probe(
                registry_a,
                group_id=group_id,
                subject=subject,
                expected_schema_hash=probes.get("published_schema_hash"),
                expected_compatibility=probes.get("expected_compatibility"),
                expected_schema_id=probes.get("published_schema_id"),
                http_log=http_log,
            )
    except Exception as exc:
        failed_checks.append({"check": "schema_registry_storage_smoke_command", "message": str(exc)})
    finally:
        if start_runtime and cleanup_runtime:
            cleanup_storage_runtime(
                platform_root,
                command_log,
                runner,
                network=network,
                postgres_container=postgres_container,
                registry_a_container=registry_a_container,
                registry_b_container=registry_b_container,
                timeout_seconds=command_timeout_seconds,
            )

    failed_checks.extend(
        failed_storage_checks(
            registry_a_info=registry_a_info,
            registry_b_info=registry_b_info,
            probes=probes,
        )
    )
    report = build_schema_registry_storage_smoke_report(
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        sql_image=sql_image,
        postgres_image=postgres_image,
        registry_a_url=registry_a,
        registry_b_url=registry_b,
        group_id=group_id,
        subject=subject,
        network=network,
        registry_a_info=registry_a_info,
        registry_b_info=registry_b_info,
        probes=probes,
        command_log=command_log,
        http_log=http_log,
        failed_checks=failed_checks,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SchemaRegistryStorageSmokeResult(output_path=target, report=report)


def prepare_storage_runtime(
    root: Path,
    output_dir: Path,
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    sql_image: str,
    postgres_image: str,
    network: str,
    postgres_container: str,
    registry_a_container: str,
    registry_b_container: str,
    registry_a_port: int,
    registry_b_port: int,
    timeout_seconds: int,
    http_log: list[dict[str, Any]],
    wait_attempts: int,
    wait_interval_seconds: float,
) -> None:
    cleanup_storage_runtime(
        root,
        command_log,
        runner,
        network=network,
        postgres_container=postgres_container,
        registry_a_container=registry_a_container,
        registry_b_container=registry_b_container,
        timeout_seconds=timeout_seconds,
    )
    run_step(
        command_log,
        runner,
        ["docker", "network", "create", network],
        cwd=root,
        timeout_seconds=timeout_seconds,
        step="create_storage_smoke_network",
    )
    with tempfile.TemporaryDirectory(prefix="enterprise-dp-schema-registry-storage-smoke-") as env_root:
        env_dir = Path(env_root)
        postgres_env = env_dir / "postgres.env"
        registry_env = env_dir / "registry.env"
        postgres_env.write_text(
            f"POSTGRES_USER={POSTGRES_USER}\nPOSTGRES_PASSWORD={POSTGRES_PASSWORD}\nPOSTGRES_DB={POSTGRES_DB}\n",
            encoding="utf-8",
        )
        registry_env.write_text(
            "\n".join(
                [
                    f"REGISTRY_DATASOURCE_URL=jdbc:postgresql://{postgres_container}:5432/{POSTGRES_DB}",
                    f"REGISTRY_DATASOURCE_USERNAME={POSTGRES_USER}",
                    f"REGISTRY_DATASOURCE_PASSWORD={POSTGRES_PASSWORD}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        run_step(
            command_log,
            runner,
            [
                "docker",
                "run",
                "-d",
                "--name",
                postgres_container,
                "--network",
                network,
                "--env-file",
                postgres_env.as_posix(),
                postgres_image,
            ],
            cwd=root,
            timeout_seconds=timeout_seconds,
            step="start_registry_postgres",
            redacted_args=[
                "docker",
                "run",
                "-d",
                "--name",
                postgres_container,
                "--network",
                network,
                "--env-file",
                "<redacted-postgres-env>",
                postgres_image,
            ],
        )
        wait_for_postgres(root, command_log, runner, postgres_container=postgres_container, timeout_seconds=timeout_seconds)
        start_registry_sql_replica(
            root,
            command_log,
            runner,
            registry_env=registry_env,
            container=registry_a_container,
            port=registry_a_port,
            network=network,
            sql_image=sql_image,
            timeout_seconds=timeout_seconds,
            step="start_schema_registry_sql_replica_a",
        )
        wait_for_registry_resilient(
            f"http://localhost:{registry_a_port}",
            http_log=http_log,
            attempts=wait_attempts,
            interval_seconds=wait_interval_seconds,
        )
        start_registry_sql_replica(
            root,
            command_log,
            runner,
            registry_env=registry_env,
            container=registry_b_container,
            port=registry_b_port,
            network=network,
            sql_image=sql_image,
            timeout_seconds=timeout_seconds,
            step="start_schema_registry_sql_replica_b",
        )


def start_registry_sql_replica(
    root: Path,
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    registry_env: Path,
    container: str,
    port: int,
    network: str,
    sql_image: str,
    timeout_seconds: int,
    step: str,
) -> None:
    run_step(
        command_log,
        runner,
        [
            "docker",
            "run",
            "-d",
            "--name",
            container,
            "--network",
            network,
            "-p",
            f"{port}:8080",
            "--env-file",
            registry_env.as_posix(),
            sql_image,
        ],
        cwd=root,
        timeout_seconds=timeout_seconds,
        step=step,
        redacted_args=[
            "docker",
            "run",
            "-d",
            "--name",
            container,
            "--network",
            network,
            "-p",
            f"{port}:8080",
            "--env-file",
            "<redacted-registry-env>",
            sql_image,
        ],
    )


def wait_for_postgres(
    root: Path,
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    postgres_container: str,
    timeout_seconds: int,
) -> None:
    last_result: CommandResult | None = None
    for _ in range(45):
        last_result = run_step(
            command_log,
            runner,
            ["docker", "exec", postgres_container, "pg_isready", "-U", POSTGRES_USER, "-d", POSTGRES_DB],
            cwd=root,
            timeout_seconds=timeout_seconds,
            step="postgres_ready_probe",
            raise_on_error=False,
        )
        if last_result.returncode == 0:
            return
        time.sleep(1)
    detail = last_result.stderr if last_result else "no pg_isready result"
    raise RuntimeError(f"postgres did not become ready: {detail[:300]}")


def wait_for_registry_resilient(
    registry_url: str,
    *,
    http_log: list[dict[str, Any]],
    attempts: int,
    interval_seconds: float,
) -> dict[str, Any]:
    last_error = None
    for _ in range(attempts):
        try:
            result = http_request(registry_url, "GET", "/apis/registry/v2/system/info", http_log=http_log)
        except OSError as exc:
            last_error = str(exc)
            http_log.append(
                {
                    "method": "GET",
                    "path": "/apis/registry/v2/system/info",
                    "status": 0,
                    "body_preview": "",
                    "error": last_error,
                }
            )
        else:
            if result.status == 200:
                return parse_json_object(result.body)
            last_error = result.error or result.body[:300].decode("utf-8", errors="replace")
        if interval_seconds > 0:
            time.sleep(interval_seconds)
    raise RuntimeError(f"schema registry did not become ready: {last_error}")


def restart_registry_replica(
    root: Path,
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    registry_a_container: str,
    timeout_seconds: int,
) -> None:
    run_step(
        command_log,
        runner,
        ["docker", "restart", registry_a_container],
        cwd=root,
        timeout_seconds=timeout_seconds,
        step="restart_schema_registry_sql_replica_a",
    )


def cleanup_storage_runtime(
    root: Path,
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    network: str,
    postgres_container: str,
    registry_a_container: str,
    registry_b_container: str,
    timeout_seconds: int,
) -> None:
    run_step(
        command_log,
        runner,
        ["docker", "rm", "-f", registry_a_container, registry_b_container, postgres_container],
        cwd=root,
        timeout_seconds=timeout_seconds,
        step="cleanup_schema_registry_storage_containers",
        raise_on_error=False,
    )
    run_step(
        command_log,
        runner,
        ["docker", "network", "rm", network],
        cwd=root,
        timeout_seconds=timeout_seconds,
        step="cleanup_schema_registry_storage_network",
        raise_on_error=False,
    )


def run_step(
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    args: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    step: str,
    input_text: str | None = None,
    raise_on_error: bool = True,
    redacted_args: list[str] | None = None,
) -> CommandResult:
    try:
        result = runner(args, input_text, cwd, timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        result = CommandResult(
            tuple(args),
            124,
            (exc.stdout or "").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or ""),
            (exc.stderr or "").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or ""),
        )
    command_log.append(
        {
            "step": step,
            "args": list(redacted_args or result.args),
            "returncode": result.returncode,
            "stdout_preview": result.stdout[:500],
            "stderr_preview": result.stderr[:500],
        }
    )
    if raise_on_error and result.returncode != 0:
        detail = result.stderr[:500] or result.stdout[:500]
        if result.returncode == 124:
            detail = detail or f"command timed out after {timeout_seconds} seconds"
        raise RuntimeError(f"{step} failed with exit {result.returncode}: {detail}")
    return result


def run_storage_probes(
    registry_a_url: str,
    registry_b_url: str,
    *,
    group_id: str,
    subject: str,
    http_log: list[dict[str, Any]],
) -> dict[str, Any]:
    encoded_subject = quote(subject, safe="")
    schema_text = canonical_json(storage_probe_schema())
    publish_path = f"/apis/ccompat/v7/subjects/{encoded_subject}/versions"
    config_path = f"/apis/ccompat/v7/config/{encoded_subject}"
    publish = http_request(
        registry_a_url,
        "POST",
        publish_path,
        body=json.dumps({"schema": schema_text, "schemaType": "JSON"}).encode("utf-8"),
        headers={
            "Content-Type": "application/vnd.schemaregistry.v1+json",
            "X-Registry-GroupId": group_id,
        },
        http_log=http_log,
    )
    if publish.status not in {200, 201}:
        raise RuntimeError(f"failed to publish schema through replica A: HTTP {publish.status} {publish.error}")
    publish_json = parse_json_object(publish.body)
    expected_hash = hash_bytes(schema_text.encode("utf-8"))
    expected_compatibility = "BACKWARD_TRANSITIVE"
    config = http_request(
        registry_a_url,
        "PUT",
        config_path,
        body=json.dumps({"compatibility": expected_compatibility}).encode("utf-8"),
        headers={
            "Content-Type": "application/vnd.schemaregistry.v1+json",
            "X-Registry-GroupId": group_id,
        },
        http_log=http_log,
    )
    return {
        "published_schema_id": str(publish_json.get("id")) if publish_json.get("id") is not None else None,
        "published_schema_hash": expected_hash,
        "expected_compatibility": expected_compatibility,
        "replica_a_publish": probe_result(publish, expected_statuses={200, 201}),
        "replica_a_set_compatibility": probe_result(config, expected_statuses={200}),
        "replica_b_read_after_write": readback_probe(
            registry_b_url,
            group_id=group_id,
            subject=subject,
            expected_schema_hash=expected_hash,
            expected_compatibility=expected_compatibility,
            expected_schema_id=str(publish_json.get("id")) if publish_json.get("id") is not None else None,
            http_log=http_log,
        ),
    }


def readback_probe(
    registry_url: str,
    *,
    group_id: str,
    subject: str,
    expected_schema_hash: object,
    expected_compatibility: object,
    expected_schema_id: object,
    http_log: list[dict[str, Any]],
) -> dict[str, Any]:
    encoded_subject = quote(subject, safe="")
    version = http_request(
        registry_url,
        "GET",
        f"/apis/ccompat/v7/subjects/{encoded_subject}/versions/latest",
        headers={"X-Registry-GroupId": group_id},
        http_log=http_log,
    )
    schema = http_request(
        registry_url,
        "GET",
        f"/apis/ccompat/v7/subjects/{encoded_subject}/versions/latest/schema",
        headers={"X-Registry-GroupId": group_id},
        http_log=http_log,
    )
    config = http_request(
        registry_url,
        "GET",
        f"/apis/ccompat/v7/config/{encoded_subject}",
        headers={"X-Registry-GroupId": group_id},
        http_log=http_log,
    )
    version_json = parse_json_object(version.body) if version.status == 200 else {}
    config_json = parse_json_object(config.body) if config.status == 200 else {}
    actual_hash = hash_bytes(schema.body) if schema.status == 200 else None
    schema_id = str(version_json.get("id")) if version_json.get("id") is not None else None
    compatibility = config_json.get("compatibilityLevel")
    checks = {
        "version_read": version.status == 200,
        "schema_read": schema.status == 200,
        "config_read": config.status == 200,
        "schema_hash_matches": actual_hash == expected_schema_hash,
        "schema_id_matches": expected_schema_id is None or schema_id == expected_schema_id,
        "compatibility_matches": compatibility == expected_compatibility,
    }
    return {
        "registry_url": registry_url,
        "schema_id": schema_id,
        "version": version_json.get("version"),
        "schema_hash": actual_hash,
        "expected_schema_hash": expected_schema_hash,
        "compatibility": compatibility,
        "expected_compatibility": expected_compatibility,
        "http_status": {
            "version": version.status,
            "schema": schema.status,
            "config": config.status,
        },
        "checks": checks,
        "passed": all(checks.values()),
    }


def probe_result(result: HttpResult, *, expected_statuses: set[int]) -> dict[str, Any]:
    return {
        "method": result.method,
        "path": result.path,
        "status": result.status,
        "expected_statuses": sorted(expected_statuses),
        "passed": result.status in expected_statuses,
        "error": result.error,
    }


def failed_storage_checks(
    *,
    registry_a_info: dict[str, Any],
    registry_b_info: dict[str, Any],
    probes: dict[str, Any],
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if not registry_a_info:
        failed.append({"check": "registry_replica_a_system_info_reachable"})
    if not registry_b_info:
        failed.append({"check": "registry_replica_b_system_info_reachable"})
    for name in ("replica_a_publish", "replica_a_set_compatibility", "replica_b_read_after_write", "replica_a_after_restart"):
        probe = probes.get(name) if isinstance(probes.get(name), dict) else {}
        if probe.get("passed") is not True:
            failed.append({"check": name, "probe": probe})
    return failed


def build_schema_registry_storage_smoke_report(
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    sql_image: str,
    postgres_image: str,
    registry_a_url: str,
    registry_b_url: str,
    group_id: str,
    subject: str,
    network: str,
    registry_a_info: dict[str, Any],
    registry_b_info: dict[str, Any],
    probes: dict[str, Any],
    command_log: list[dict[str, Any]],
    http_log: list[dict[str, Any]],
    failed_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    replica_b_passed = isinstance(probes.get("replica_b_read_after_write"), dict) and probes[
        "replica_b_read_after_write"
    ].get("passed") is True
    restart_passed = isinstance(probes.get("replica_a_after_restart"), dict) and probes["replica_a_after_restart"].get(
        "passed"
    ) is True
    passed = not failed_checks
    summary = {
        "registry_a_uri": registry_a_url,
        "registry_b_uri": registry_b_url,
        "group_id": group_id,
        "subject": subject,
        "storage_backend": "postgresql",
        "registry_replica_count": 2,
        "shared_sql_storage_configured": True,
        "secret_env_files_persisted": False,
        "cross_replica_read_after_write_passed": replica_b_passed,
        "replica_restart_durable_readback_passed": restart_passed,
        "published_schema_id": probes.get("published_schema_id"),
        "published_schema_hash": probes.get("published_schema_hash"),
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
    }
    return {
        "artifact_type": "schema_registry_storage_smoke_report.v1",
        "report_version": 1,
        "capability_id": "schema-registry-compatibility",
        "report_id": stable_id("schema-registry-storage-smoke", environment, release_id, registry_a_url, registry_b_url),
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "runtime_scope": {
            "mode": "local_apicurio_sql_shared_postgres_two_replicas",
            "covered": [
                "apicurio_sql_registry_replicas_started",
                "shared_postgres_storage_backend_configured",
                "replica_a_publish_and_configure_subject",
                "replica_b_cross_replica_read_after_write",
                "replica_a_restart_durable_readback",
            ],
            "not_covered": [
                "managed_ha_postgres_or_database_cluster",
                "multi_az_registry_deployment",
                "load_balancer_failover_routing",
                "backup_restore_or_pitr_drill",
                "schema_registry_database_migration_runbook",
                "production_secret_rotation",
            ],
        },
        "registry": {
            "vendor": "apicurio",
            "api": "confluent_compatible_v7",
            "sql_image": sql_image,
            "replicas": [
                {"name": "replica-a", "uri": registry_a_url, "info": registry_a_info},
                {"name": "replica-b", "uri": registry_b_url, "info": registry_b_info},
            ],
            "storage": {
                "backend": "postgresql",
                "postgres_image": postgres_image,
                "network": network,
                "secret_values_redacted": True,
                "secret_env_files_persisted": False,
            },
        },
        "probes": probes,
        "commands": command_log,
        "http_exchanges": http_log,
        "summary": summary,
        "passed": passed,
    }


def storage_probe_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Enterprise DP schema registry storage smoke probe",
        "type": "object",
        "additionalProperties": False,
        "required": ["eventId", "subject", "replica"],
        "properties": {
            "eventId": {"type": "string"},
            "subject": {"type": "string"},
            "replica": {"type": "string"},
        },
    }

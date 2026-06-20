from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.event_backbone_smoke import CommandResult, CommandRunner, execute_step, run_command, stable_id


DEFAULT_IMAGE = "redpandadata/redpanda:v24.2.8"
DEFAULT_CONTAINER_NAME = "enterprise-dp-local-broker-acl-smoke"
DEFAULT_GENERATED_AT = "2026-01-15T09:15:20Z"
DEFAULT_TOPIC = "dp.local.broker.acl.smoke"
DEFAULT_GROUP = "dp.local.broker.acl.smoke.group"
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASSWORD = "admin-secret"
DEFAULT_ALLOWED_USER = "dp_allowed"
DEFAULT_ALLOWED_PASSWORD = "allowed-secret"
DEFAULT_DENIED_USER = "dp_denied"
DEFAULT_DENIED_PASSWORD = "denied-secret"


@dataclass(frozen=True)
class BrokerAclSmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_broker_acl_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    image: str = DEFAULT_IMAGE,
    container_name: str = DEFAULT_CONTAINER_NAME,
    topic: str = DEFAULT_TOPIC,
    group: str = DEFAULT_GROUP,
    release_id: str = "local-broker-acl-smoke",
    environment: str = "local",
    generated_at: str | None = None,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
    start_runtime: bool = True,
    cleanup_runtime: bool = True,
) -> BrokerAclSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or DEFAULT_GENERATED_AT
    config_dir = target_dir / "redpanda-acl-config"
    config_path = config_dir / "redpanda.yaml"
    write_redpanda_acl_config(config_path)
    config_mount_dir = config_dir.resolve()
    runner = command_runner or run_command
    command_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    health_probe: dict[str, Any] = {"passed": False}
    user_probe: dict[str, Any] = {"passed": False}
    acl_probe: dict[str, Any] = {"passed": False}
    allowed_produce_probe: dict[str, Any] = {"passed": False}
    denied_produce_probe: dict[str, Any] = {"passed": False}

    try:
        if start_runtime:
            execute_step(
                command_log,
                runner,
                ["docker", "rm", "-f", container_name],
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="cleanup_existing_acl_container",
                raise_on_error=False,
            )
            execute_step(
                command_log,
                runner,
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    container_name,
                    "-v",
                    f"{config_mount_dir.as_posix()}:/etc/redpanda",
                    image,
                    "redpanda",
                    "start",
                    "--check=false",
                ],
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="start_sasl_acl_redpanda",
            )
        health_probe = wait_for_broker_acl_health(
            command_log,
            runner,
            container_name=container_name,
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
        )
        create_sasl_users(
            command_log,
            runner,
            container_name=container_name,
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
        )
        execute_step(
            command_log,
            runner,
            ["docker", "exec", container_name, "rpk", "cluster", "config", "set", "kafka_enable_authorization", "true"],
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step="enable_kafka_authorization",
        )
        admin_auth = rpk_auth(DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASSWORD)
        execute_step(
            command_log,
            runner,
            ["docker", "exec", container_name, "sh", "-lc", f"rpk topic create {topic} {admin_auth}"],
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step="admin_create_acl_topic",
        )
        acl_topic = execute_step(
            command_log,
            runner,
            [
                "docker",
                "exec",
                container_name,
                "sh",
                "-lc",
                f"rpk security acl create --allow-principal {DEFAULT_ALLOWED_USER} "
                f"--operation read,write,describe --topic {topic} {admin_auth}",
            ],
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step="admin_create_allowed_topic_acl",
        )
        acl_group = execute_step(
            command_log,
            runner,
            [
                "docker",
                "exec",
                container_name,
                "sh",
                "-lc",
                f"rpk security acl create --allow-principal {DEFAULT_ALLOWED_USER} "
                f"--operation describe,read --group {group} {admin_auth}",
            ],
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step="admin_create_allowed_group_acl",
        )
        user_list = execute_step(
            command_log,
            runner,
            ["docker", "exec", container_name, "sh", "-lc", f"rpk security user list {admin_auth}"],
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step="admin_list_sasl_users",
        )
        user_probe = sasl_user_probe(user_list.stdout)
        acl_probe = acl_creation_probe(acl_topic.stdout, acl_group.stdout, topic=topic, group=group)
        allowed_produce = execute_step(
            command_log,
            runner,
            [
                "docker",
                "exec",
                "-i",
                container_name,
                "sh",
                "-lc",
                f"rpk topic produce {topic} {rpk_auth(DEFAULT_ALLOWED_USER, DEFAULT_ALLOWED_PASSWORD)}",
            ],
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            input_text='{"acl":"allowed"}\n',
            step="allowed_user_produce_probe",
        )
        allowed_produce_probe = allowed_probe(allowed_produce)
        denied_produce = execute_step(
            command_log,
            runner,
            [
                "docker",
                "exec",
                "-i",
                container_name,
                "sh",
                "-lc",
                f"rpk topic produce {topic} {rpk_auth(DEFAULT_DENIED_USER, DEFAULT_DENIED_PASSWORD)}",
            ],
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            input_text='{"acl":"denied"}\n',
            step="denied_user_produce_probe",
            raise_on_error=False,
        )
        denied_produce_probe = denied_acl_probe(denied_produce)
    except RuntimeError as exc:
        failed_checks.append({"check": "broker_acl_smoke_command", "message": str(exc)})
    finally:
        if cleanup_runtime:
            execute_step(
                command_log,
                runner,
                ["docker", "rm", "-f", container_name],
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="cleanup_acl_container",
                raise_on_error=False,
            )

    failed_checks.extend(
        failed_broker_acl_checks(
            health_probe=health_probe,
            user_probe=user_probe,
            acl_probe=acl_probe,
            allowed_produce_probe=allowed_produce_probe,
            denied_produce_probe=denied_produce_probe,
        )
    )
    report = build_broker_acl_smoke_report(
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        image=image,
        container_name=container_name,
        topic=topic,
        group=group,
        config_path=config_path,
        command_log=command_log,
        health_probe=health_probe,
        user_probe=user_probe,
        acl_probe=acl_probe,
        allowed_produce_probe=allowed_produce_probe,
        denied_produce_probe=denied_produce_probe,
        failed_checks=failed_checks,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return BrokerAclSmokeResult(output_path=target, report=report)


def write_redpanda_acl_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """redpanda:
  data_directory: /var/lib/redpanda/data
  seed_servers: []
  rpc_server:
    address: 0.0.0.0
    port: 33145
  advertised_rpc_api:
    address: 127.0.0.1
    port: 33145
  kafka_api:
    - address: 0.0.0.0
      port: 9092
      name: sasl_listener
      authentication_method: sasl
  advertised_kafka_api:
    - address: 127.0.0.1
      port: 9092
      name: sasl_listener
  admin:
    address: 0.0.0.0
    port: 9644
  developer_mode: true
  superusers:
    - admin
rpk:
  tune_network: false
  tune_disk_scheduler: false
  tune_disk_nomerges: false
  tune_disk_irq: false
  tune_fstrim: false
  tune_cpu: false
  tune_aio_events: false
  tune_clocksource: false
  tune_swappiness: false
  enable_memory_locking: false
""",
        encoding="utf-8",
    )


def wait_for_broker_acl_health(
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    container_name: str,
    cwd: Path,
    timeout_seconds: int,
    attempts: int = 60,
) -> dict[str, Any]:
    last = CommandResult((), 1, "", "not started")
    for attempt in range(1, attempts + 1):
        last = execute_step(
            command_log,
            runner,
            ["docker", "exec", container_name, "rpk", "cluster", "health"],
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            step=f"wait_acl_broker_health_{attempt}",
            raise_on_error=False,
        )
        if last.returncode == 0 and "Healthy:" in last.stdout and "true" in last.stdout:
            return {"passed": True, "attempt": attempt, "stdout_preview": last.stdout[:500]}
    return {
        "passed": False,
        "attempt": attempts,
        "stdout_preview": last.stdout[:500],
        "stderr_preview": last.stderr[:500],
    }


def create_sasl_users(
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    container_name: str,
    cwd: Path,
    timeout_seconds: int,
) -> None:
    for user, password, step in (
        (DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASSWORD, "create_admin_sasl_user"),
        (DEFAULT_ALLOWED_USER, DEFAULT_ALLOWED_PASSWORD, "create_allowed_sasl_user"),
        (DEFAULT_DENIED_USER, DEFAULT_DENIED_PASSWORD, "create_denied_sasl_user"),
    ):
        execute_step(
            command_log,
            runner,
            ["docker", "exec", container_name, "rpk", "security", "user", "create", user, "-p", password],
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            step=step,
            raise_on_error=False,
        )


def rpk_auth(user: str, password: str) -> str:
    return f"-X brokers=127.0.0.1:9092 -X user={user} -X pass={password} -X sasl.mechanism=SCRAM-SHA-256"


def sasl_user_probe(stdout: str) -> dict[str, Any]:
    users = set(stdout.split())
    expected = {DEFAULT_ADMIN_USER, DEFAULT_ALLOWED_USER, DEFAULT_DENIED_USER}
    return {"passed": expected.issubset(users), "expected_users": sorted(expected), "observed_users": sorted(users)}


def acl_creation_probe(topic_stdout: str, group_stdout: str, *, topic: str = DEFAULT_TOPIC, group: str = DEFAULT_GROUP) -> dict[str, Any]:
    combined = f"{topic_stdout}\n{group_stdout}"
    expected_tokens = [
        "User:dp_allowed",
        "TOPIC",
        topic,
        "WRITE",
        "READ",
        "GROUP",
        group,
        "ALLOW",
    ]
    return {
        "passed": all(token in combined for token in expected_tokens),
        "expected_tokens": expected_tokens,
        "stdout_preview_hash": stable_id("acl-create-stdout", combined[:2000]),
    }


def allowed_probe(result: CommandResult) -> dict[str, Any]:
    produced = result.returncode == 0 and "Produced to partition" in result.stdout
    return {
        "passed": produced,
        "returncode": result.returncode,
        "stdout_preview": result.stdout[:500],
        "stderr_preview": result.stderr[:500],
    }


def denied_acl_probe(result: CommandResult) -> dict[str, Any]:
    error_text = (result.stderr or result.stdout).strip()
    denied = result.returncode != 0 and (
        "TOPIC_AUTHORIZATION_FAILED" in error_text or "authorization failed" in error_text.lower()
    )
    return {
        "passed": denied,
        "blocked": result.returncode != 0,
        "authorization_denied_verified": denied,
        "returncode": result.returncode,
        "error_preview": error_text[:500],
    }


def failed_broker_acl_checks(
    *,
    health_probe: dict[str, Any],
    user_probe: dict[str, Any],
    acl_probe: dict[str, Any],
    allowed_produce_probe: dict[str, Any],
    denied_produce_probe: dict[str, Any],
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if health_probe.get("passed") is not True:
        failed.append({"check": "broker_acl_redpanda_healthy", **health_probe})
    if user_probe.get("passed") is not True:
        failed.append({"check": "broker_acl_sasl_users_created", **user_probe})
    if acl_probe.get("passed") is not True:
        failed.append({"check": "broker_acl_allowed_principal_acl_created", **acl_probe})
    if allowed_produce_probe.get("passed") is not True:
        failed.append({"check": "broker_acl_allowed_user_can_produce", **allowed_produce_probe})
    if denied_produce_probe.get("passed") is not True:
        failed.append({"check": "broker_acl_denied_user_blocked", **denied_produce_probe})
    return failed


def build_broker_acl_smoke_report(
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    image: str,
    container_name: str,
    topic: str,
    group: str,
    config_path: Path,
    command_log: list[dict[str, Any]],
    health_probe: dict[str, Any],
    user_probe: dict[str, Any],
    acl_probe: dict[str, Any],
    allowed_produce_probe: dict[str, Any],
    denied_produce_probe: dict[str, Any],
    failed_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    report = {
        "artifact_type": "broker_acl_smoke_report.v1",
        "report_version": 1,
        "capability_id": "event-cdc-ingestion-runtime",
        "report_id": f"broker-acl-smoke:{environment}:{release_id}",
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "runtime_scope": {
            "mode": "local_redpanda_sasl_scram_acl_authorization",
            "covered": [
                "redpanda_sasl_listener_started",
                "superuser_and_client_sasl_users_created",
                "kafka_authorization_enabled",
                "topic_and_group_acl_created_for_allowed_principal",
                "allowed_principal_produce_succeeded",
                "denied_principal_produce_blocked",
            ],
            "not_covered": [
                "production_mtls_listener",
                "production_secret_rotation",
                "production_broker_audit_log_export",
            ],
        },
        "redpanda": {
            "image": image,
            "container_name": container_name,
            "config": {
                "path": config_path.as_posix(),
                "hash": hash_file(config_path) if config_path.is_file() else None,
                "sasl_listener": True,
                "superuser": DEFAULT_ADMIN_USER,
            },
            "topic": topic,
            "group": group,
            "mechanism": "SCRAM-SHA-256",
        },
        "health_probe": health_probe,
        "user_probe": user_probe,
        "acl_probe": acl_probe,
        "allowed_produce_probe": allowed_produce_probe,
        "denied_produce_probe": denied_produce_probe,
        "commands": redact_command_log(command_log),
        "summary": {
            "broker_acl_enforced": denied_produce_probe.get("authorization_denied_verified") is True,
            "allowed_user_can_produce": allowed_produce_probe.get("passed") is True,
            "denied_user_blocked": denied_produce_probe.get("blocked") is True,
            "authorization_denied_verified": denied_produce_probe.get("authorization_denied_verified") is True,
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        },
    }
    report["passed"] = not failed_checks
    return report


def redact_command_log(command_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [redact_value(command) for command in command_log]


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        redacted = value
        for secret in (DEFAULT_ADMIN_PASSWORD, DEFAULT_ALLOWED_PASSWORD, DEFAULT_DENIED_PASSWORD):
            redacted = redacted.replace(secret, "<redacted>")
        return redacted
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    return value

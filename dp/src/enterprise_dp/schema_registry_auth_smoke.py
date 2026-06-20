from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from enterprise_dp.catalog import canonical_json
from enterprise_dp.event_backbone_smoke import (
    CommandRunner,
    DEFAULT_COMPOSE_FILE,
    execute_step,
    resolve_compose_path,
    run_command,
    stable_id,
)
from enterprise_dp.schema_registry_runtime_smoke import HttpResult, http_request, wait_for_registry


DEFAULT_SERVICE = "schema-registry"
DEFAULT_REGISTRY_URL = "http://localhost:18082"
DEFAULT_GATEWAY_HOST = "127.0.0.1"
DEFAULT_GATEWAY_PORT = 18083
DEFAULT_GROUP_ID = "enterprise-dp-auth-smoke"
DEFAULT_GENERATED_AT = "2026-01-15T09:15:20Z"
DEFAULT_SUBJECT = "dp.local.schema_registry_auth_smoke-value"
PUBLISHER_TOKEN = "local-schema-registry-publisher-token"
READER_TOKEN = "local-schema-registry-reader-token"
DENIED_TOKEN = "local-schema-registry-denied-token"


@dataclass(frozen=True)
class SchemaRegistryAuthSmokeResult:
    output_path: Path
    report: dict[str, Any]


@dataclass(frozen=True)
class AuthDecision:
    allowed: bool
    status: int
    principal: str | None
    token_id: str | None
    reason: str


class SchemaRegistryAuthGateway:
    def __init__(self, server: ThreadingHTTPServer, thread: threading.Thread, audit_log: list[dict[str, Any]]) -> None:
        self.server = server
        self.thread = thread
        self.audit_log = audit_log

    @property
    def url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def write_schema_registry_auth_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    compose_file: str | Path | None = None,
    service: str = DEFAULT_SERVICE,
    registry_url: str = DEFAULT_REGISTRY_URL,
    gateway_host: str = DEFAULT_GATEWAY_HOST,
    gateway_port: int = DEFAULT_GATEWAY_PORT,
    group_id: str = DEFAULT_GROUP_ID,
    subject: str = DEFAULT_SUBJECT,
    release_id: str = "local-schema-registry-auth-smoke",
    environment: str = "local",
    generated_at: str | None = None,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
    wait_attempts: int = 30,
    wait_interval_seconds: float = 1.0,
    start_runtime: bool = True,
) -> SchemaRegistryAuthSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or DEFAULT_GENERATED_AT
    compose_path = resolve_compose_path(platform_root, compose_file or DEFAULT_COMPOSE_FILE)
    runner = command_runner or run_command
    command_log: list[dict[str, Any]] = []
    http_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    registry_info: dict[str, Any] = {}
    gateway: SchemaRegistryAuthGateway | None = None
    probes: dict[str, dict[str, Any]] = {}
    audit_log: list[dict[str, Any]] = []

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
        gateway = start_auth_gateway(
            upstream_registry_url=registry_url,
            host=gateway_host,
            port=gateway_port,
            audit_log=audit_log,
        )
        probes = run_auth_probes(gateway.url, group_id=group_id, subject=subject, http_log=http_log)
    except RuntimeError as exc:
        failed_checks.append({"check": "schema_registry_auth_smoke_command", "message": str(exc)})
    finally:
        if gateway is not None:
            gateway.close()

    failed_checks.extend(
        failed_auth_checks(
            registry_info=registry_info,
            gateway_started=gateway is not None,
            probes=probes,
            audit_log=audit_log,
        )
    )
    report = build_schema_registry_auth_smoke_report(
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        registry_url=registry_url,
        gateway_url=gateway.url if gateway is not None else None,
        group_id=group_id,
        subject=subject,
        compose_path=compose_path,
        registry_info=registry_info,
        command_log=command_log,
        http_log=http_log,
        probes=probes,
        audit_log=audit_log,
        failed_checks=failed_checks,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SchemaRegistryAuthSmokeResult(output_path=target, report=report)


def start_auth_gateway(
    *,
    upstream_registry_url: str,
    host: str,
    port: int,
    audit_log: list[dict[str, Any]],
) -> SchemaRegistryAuthGateway:
    class Handler(BaseHTTPRequestHandler):
        server_version = "EnterpriseDPSchemaRegistryAuthGateway/1.0"

        def do_GET(self) -> None:  # noqa: N802
            self._handle()

        def do_POST(self) -> None:  # noqa: N802
            self._handle()

        def do_PUT(self) -> None:  # noqa: N802
            self._handle()

        def do_DELETE(self) -> None:  # noqa: N802
            self._handle()

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _handle(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length") or "0"))
            decision = authorize_request(self.command, self.path, self.headers.get("Authorization"))
            event = {
                "event_type": "schema_registry_authz_decision",
                "method": self.command,
                "path": self.path,
                "principal": decision.principal,
                "token_id": decision.token_id,
                "decision": "allow" if decision.allowed else "deny",
                "reason": decision.reason,
                "status": decision.status,
            }
            if not decision.allowed:
                audit_log.append(event)
                self._write_json(decision.status, {"error": decision.reason})
                return
            upstream = forward_to_registry(
                upstream_registry_url,
                self.command,
                self.path,
                body=body,
                headers={
                    key: value
                    for key, value in self.headers.items()
                    if key.lower() not in {"host", "authorization", "content-length"}
                },
            )
            event["upstream_status"] = upstream.status
            audit_log.append(event)
            self.send_response(upstream.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(upstream.body)))
            self.end_headers()
            self.wfile.write(upstream.body)

        def _write_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return SchemaRegistryAuthGateway(server, thread, audit_log)


def authorize_request(method: str, path: str, authorization: str | None) -> AuthDecision:
    token = bearer_token(authorization)
    if token is None:
        return AuthDecision(False, 401, None, None, "missing_bearer_token")
    identities = {
        PUBLISHER_TOKEN: {
            "principal": "dp_schema_registry_publisher",
            "token_id": "local-publisher",
            "roles": {"schema_registry_publisher", "schema_registry_reader"},
        },
        READER_TOKEN: {
            "principal": "dp_schema_registry_reader",
            "token_id": "local-reader",
            "roles": {"schema_registry_reader"},
        },
        DENIED_TOKEN: {
            "principal": "dp_schema_registry_denied",
            "token_id": "local-denied",
            "roles": set(),
        },
    }
    identity = identities.get(token)
    if identity is None:
        return AuthDecision(False, 401, None, "unknown", "unknown_bearer_token")
    roles = identity["roles"]
    principal = str(identity["principal"])
    token_id = str(identity["token_id"])
    parsed_path = urlparse(path).path
    if not parsed_path.startswith("/apis/ccompat/v7/"):
        return AuthDecision(False, 403, principal, token_id, "path_not_in_schema_registry_scope")
    if method in {"POST", "PUT", "DELETE"}:
        allowed = "schema_registry_publisher" in roles
        return AuthDecision(allowed, 200 if allowed else 403, principal, token_id, "publisher_role_required")
    if method == "GET":
        allowed = bool({"schema_registry_reader", "schema_registry_publisher"} & roles)
        return AuthDecision(allowed, 200 if allowed else 403, principal, token_id, "reader_role_required")
    return AuthDecision(False, 403, principal, token_id, "method_not_allowed")


def bearer_token(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    prefix = "Bearer "
    if not value.startswith(prefix):
        return None
    token = value.removeprefix(prefix).strip()
    return token or None


def forward_to_registry(
    registry_url: str,
    method: str,
    path: str,
    *,
    body: bytes,
    headers: dict[str, str],
) -> HttpResult:
    request = Request(f"{registry_url.rstrip('/')}{path}", data=body or None, method=method, headers=headers)
    try:
        with urlopen(request, timeout=20) as response:
            payload = response.read()
            return HttpResult(method=method, path=path, status=response.status, body=payload)
    except HTTPError as exc:
        return HttpResult(method=method, path=path, status=exc.code, body=exc.read(), error=str(exc))
    except URLError as exc:
        return HttpResult(method=method, path=path, status=0, body=b"", error=str(exc))


def run_auth_probes(
    gateway_url: str,
    *,
    group_id: str,
    subject: str,
    http_log: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    encoded_subject = quote(subject, safe="")
    schema_text = canonical_json(auth_probe_schema())
    publish_path = f"/apis/ccompat/v7/subjects/{encoded_subject}/versions"
    config_path = f"/apis/ccompat/v7/config/{encoded_subject}"
    latest_schema_path = f"/apis/ccompat/v7/subjects/{encoded_subject}/versions/latest/schema"
    probes: dict[str, dict[str, Any]] = {}
    probes["missing_token_read_denied"] = probe_result(
        http_request(gateway_url, "GET", latest_schema_path, headers={"X-Registry-GroupId": group_id}, http_log=http_log),
        expected_statuses={401},
    )
    probes["unknown_token_read_denied"] = probe_result(
        gateway_request(gateway_url, "GET", latest_schema_path, token="unknown-token", group_id=group_id, http_log=http_log),
        expected_statuses={401},
    )
    probes["denied_token_read_denied"] = probe_result(
        gateway_request(gateway_url, "GET", latest_schema_path, token=DENIED_TOKEN, group_id=group_id, http_log=http_log),
        expected_statuses={403},
    )
    probes["reader_write_denied"] = probe_result(
        gateway_request(
            gateway_url,
            "POST",
            publish_path,
            token=READER_TOKEN,
            group_id=group_id,
            body=json.dumps({"schema": schema_text, "schemaType": "JSON"}).encode("utf-8"),
            http_log=http_log,
        ),
        expected_statuses={403},
    )
    probes["publisher_publish_allowed"] = probe_result(
        gateway_request(
            gateway_url,
            "POST",
            publish_path,
            token=PUBLISHER_TOKEN,
            group_id=group_id,
            body=json.dumps({"schema": schema_text, "schemaType": "JSON"}).encode("utf-8"),
            http_log=http_log,
        ),
        expected_statuses={200, 201},
    )
    probes["publisher_config_allowed"] = probe_result(
        gateway_request(
            gateway_url,
            "PUT",
            config_path,
            token=PUBLISHER_TOKEN,
            group_id=group_id,
            body=json.dumps({"compatibility": "BACKWARD_TRANSITIVE"}).encode("utf-8"),
            http_log=http_log,
        ),
        expected_statuses={200},
    )
    read = gateway_request(gateway_url, "GET", latest_schema_path, token=READER_TOKEN, group_id=group_id, http_log=http_log)
    probes["reader_read_allowed"] = probe_result(
        read,
        expected_statuses={200},
        extra={"schema_hash_matches": hash_bytes(read.body) == hash_bytes(schema_text.encode("utf-8")) if read.status == 200 else False},
    )
    return probes


def gateway_request(
    gateway_url: str,
    method: str,
    path: str,
    *,
    token: str,
    group_id: str,
    http_log: list[dict[str, Any]],
    body: bytes | None = None,
) -> HttpResult:
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Registry-GroupId": group_id,
        "Content-Type": "application/vnd.schemaregistry.v1+json",
    }
    return http_request(gateway_url, method, path, body=body, headers=headers, http_log=http_log)


def probe_result(result: HttpResult, *, expected_statuses: set[int], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    passed = result.status in expected_statuses
    payload = {
        "method": result.method,
        "path": result.path,
        "status": result.status,
        "expected_statuses": sorted(expected_statuses),
        "passed": passed,
        "error": result.error,
    }
    if extra:
        payload.update(extra)
        if any(value is False for value in extra.values() if isinstance(value, bool)):
            payload["passed"] = False
    return payload


def failed_auth_checks(
    *,
    registry_info: dict[str, Any],
    gateway_started: bool,
    probes: dict[str, dict[str, Any]],
    audit_log: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if not registry_info:
        failed.append({"check": "registry_system_info_reachable"})
    if not gateway_started:
        failed.append({"check": "auth_gateway_started"})
    required_probes = [
        "missing_token_read_denied",
        "unknown_token_read_denied",
        "denied_token_read_denied",
        "reader_write_denied",
        "publisher_publish_allowed",
        "publisher_config_allowed",
        "reader_read_allowed",
    ]
    for name in required_probes:
        probe = probes.get(name) if isinstance(probes.get(name), dict) else {}
        if probe.get("passed") is not True:
            failed.append({"check": name, "probe": probe})
    decisions = {event.get("decision") for event in audit_log if isinstance(event, dict)}
    if not {"allow", "deny"}.issubset(decisions) or len(audit_log) < len(required_probes):
        failed.append({"check": "auth_audit_log_complete", "event_count": len(audit_log), "decisions": sorted(decisions)})
    return failed


def build_schema_registry_auth_smoke_report(
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    registry_url: str,
    gateway_url: str | None,
    group_id: str,
    subject: str,
    compose_path: Path,
    registry_info: dict[str, Any],
    command_log: list[dict[str, Any]],
    http_log: list[dict[str, Any]],
    probes: dict[str, dict[str, Any]],
    audit_log: list[dict[str, Any]],
    failed_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    passed = not failed_checks
    summary = {
        "registry_uri": registry_url,
        "gateway_uri": gateway_url,
        "group_id": group_id,
        "subject": subject,
        "auth_gateway_enforced": passed,
        "missing_token_denied": probes.get("missing_token_read_denied", {}).get("passed"),
        "unknown_token_denied": probes.get("unknown_token_read_denied", {}).get("passed"),
        "denied_token_blocked": probes.get("denied_token_read_denied", {}).get("passed"),
        "reader_write_denied": probes.get("reader_write_denied", {}).get("passed"),
        "publisher_publish_allowed": probes.get("publisher_publish_allowed", {}).get("passed"),
        "publisher_config_allowed": probes.get("publisher_config_allowed", {}).get("passed"),
        "reader_read_allowed": probes.get("reader_read_allowed", {}).get("passed"),
        "reader_read_schema_hash_matches": probes.get("reader_read_allowed", {}).get("schema_hash_matches"),
        "authorization_audit_event_count": len(audit_log),
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
    }
    return {
        "artifact_type": "schema_registry_auth_smoke_report.v1",
        "report_version": 1,
        "capability_id": "schema-registry-compatibility",
        "report_id": stable_id("schema-registry-auth-smoke", environment, release_id, registry_url, subject),
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "runtime_scope": {
            "mode": "local_token_auth_gateway_to_apicurio_ccompat_v7",
            "covered": [
                "schema_registry_auth_gateway_started",
                "publisher_token_can_publish_schema",
                "publisher_token_can_set_compatibility",
                "reader_token_can_read_schema",
                "reader_token_write_denied",
                "missing_token_denied",
                "unknown_token_denied",
                "unprivileged_token_denied",
                "authorization_decisions_audited",
            ],
            "not_covered": [
                "production_oidc_jwks_validation",
                "keycloak_group_claim_mapping",
                "production_registry_ha_storage",
                "production_secret_rotation",
                "external_api_gateway_or_waf",
            ],
        },
        "registry": {
            "vendor": "apicurio",
            "api": "confluent_compatible_v7",
            "uri": registry_url,
            "group_id": group_id,
            "compose_file": compose_path.as_posix(),
            "info": registry_info,
        },
        "auth_gateway": {
            "uri": gateway_url,
            "policy_mode": "local_static_bearer_token_rbac",
            "principals": [
                {
                    "principal": "dp_schema_registry_publisher",
                    "token_id": "local-publisher",
                    "roles": ["schema_registry_publisher", "schema_registry_reader"],
                },
                {
                    "principal": "dp_schema_registry_reader",
                    "token_id": "local-reader",
                    "roles": ["schema_registry_reader"],
                },
                {"principal": "dp_schema_registry_denied", "token_id": "local-denied", "roles": []},
            ],
        },
        "probes": probes,
        "authorization_audit_log": audit_log,
        "commands": command_log,
        "http_exchanges": http_log,
        "summary": summary,
        "passed": passed,
    }


def auth_probe_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Enterprise DP schema registry auth smoke probe",
        "type": "object",
        "additionalProperties": False,
        "required": ["eventId", "subject"],
        "properties": {
            "eventId": {"type": "string"},
            "subject": {"type": "string"},
        },
    }


def hash_bytes(payload: bytes) -> str:
    import hashlib

    return f"sha256:{hashlib.sha256(payload).hexdigest()}"

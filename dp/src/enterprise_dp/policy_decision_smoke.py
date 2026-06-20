from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any
from urllib import error, request

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.event_backbone_smoke import CommandResult, CommandRunner, run_command, stable_id
from enterprise_dp.schema_registry_auth_smoke import hash_bytes


DEFAULT_OPA_IMAGE = "openpolicyagent/opa:0.70.0"
DEFAULT_CONTAINER = "enterprise-dp-opa-policy-decision-smoke"
DEFAULT_PORT = 18186
DEFAULT_GENERATED_AT = "2026-01-15T09:15:20Z"


@dataclass(frozen=True)
class PolicyDecisionSmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_policy_decision_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    opa_image: str = DEFAULT_OPA_IMAGE,
    container_name: str = DEFAULT_CONTAINER,
    port: int = DEFAULT_PORT,
    release_id: str = "local-policy-decision-smoke",
    environment: str = "local",
    generated_at: str | None = None,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
    wait_attempts: int = 30,
    wait_interval_seconds: float = 1.0,
    start_runtime: bool = True,
    cleanup_runtime: bool = True,
    pdp_url: str | None = None,
) -> PolicyDecisionSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or DEFAULT_GENERATED_AT
    runner = command_runner or run_command
    command_log: list[dict[str, Any]] = []
    http_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    opa_url = pdp_url or f"http://127.0.0.1:{port}"
    policy_dir = target_dir / "policy"
    audit_events_path = target_dir / "audit" / "policy-decision-audit.jsonl"
    audit_manifest_path = target_dir / "audit" / "policy-decision-audit-manifest.json"

    try:
        if start_runtime:
            write_policy_bundle(policy_dir)
            start_opa_runtime(
                platform_root,
                command_log,
                runner,
                policy_dir=policy_dir,
                opa_image=opa_image,
                container_name=container_name,
                port=port,
                timeout_seconds=command_timeout_seconds,
            )
        wait_for_opa(
            opa_url,
            http_log=http_log,
            attempts=wait_attempts,
            interval_seconds=wait_interval_seconds,
        )
        probes = run_policy_decision_probes(opa_url, http_log=http_log)
    except Exception as exc:
        failed_checks.append({"check": "policy_decision_smoke_command", "message": str(exc)})
        probes = {}
    finally:
        if start_runtime and cleanup_runtime:
            cleanup_opa_runtime(
                platform_root,
                command_log,
                runner,
                container_name=container_name,
                timeout_seconds=command_timeout_seconds,
            )

    failed_checks.extend(failed_policy_decision_checks(probes))
    audit_sink = write_policy_decision_audit_sink(
        audit_events_path,
        audit_manifest_path,
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        probes=probes,
    )
    if audit_sink.get("passed") is not True:
        failed_checks.append(
            {
                "check": "policy_decision_audit_sink_passed",
                "event_count": audit_sink.get("event_count", 0),
                "failed_event_count": audit_sink.get("failed_event_count", 0),
            }
        )
    report = build_policy_decision_smoke_report(
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        opa_image=opa_image,
        pdp_url=opa_url,
        policy_dir=policy_dir,
        command_log=command_log,
        http_log=http_log,
        probes=probes,
        audit_sink=audit_sink,
        audit_events_path=audit_events_path,
        audit_manifest_path=audit_manifest_path,
        failed_checks=failed_checks,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return PolicyDecisionSmokeResult(output_path=target, report=report)


def write_policy_bundle(policy_dir: Path) -> None:
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "enterprise_dp_authz.rego").write_text(policy_bundle_source(), encoding="utf-8")


def policy_bundle_source() -> str:
    return """
package enterprise.dp.authz

default allow = false
default approve_policy_change = false

allow {
  input.action == "select"
  input.resource.layer == "gold"
  input.resource.domain == "finance"
  has_role("finance_reader")
}

deny_reasons["not_authorized"] {
  not allow
}

row_filter["org_id"] = org {
  allow
  org := input.user.org_id
  org != ""
}

mask[column] {
  allow
  column := input.resource.pii[_]
  not has_role("pii_cleartext")
}

approve_policy_change {
  input.action == "approve_policy_change"
  input.change.status == "PENDING_APPROVAL"
  input.change.requester != input.approver.subject
  input.change.reason != ""
  input.change.evidence_hash != ""
  input.change.risk != ""
  approver_has_role
}

policy_admin_denials["maker_checker_conflict"] {
  input.action == "approve_policy_change"
  input.change.requester == input.approver.subject
}

policy_admin_denials["missing_policy_approver_role"] {
  input.action == "approve_policy_change"
  not approver_has_role
}

policy_admin_denials["missing_reason"] {
  input.action == "approve_policy_change"
  input.change.reason == ""
}

policy_admin_denials["missing_evidence"] {
  input.action == "approve_policy_change"
  input.change.evidence_hash == ""
}

approver_has_role {
  input.approver.roles[_] == "policy_approver"
}

has_role(role) {
  input.user.roles[_] == role
}
""".strip() + "\n"


def start_opa_runtime(
    root: Path,
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    policy_dir: Path,
    opa_image: str,
    container_name: str,
    port: int,
    timeout_seconds: int,
) -> None:
    cleanup_opa_runtime(root, command_log, runner, container_name=container_name, timeout_seconds=timeout_seconds)
    execute_step(
        command_log,
        runner,
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            f"{port}:8181",
            "-v",
            f"{policy_dir.resolve().as_posix()}:/policies:ro",
            opa_image,
            "run",
            "--server",
            "--addr",
            "0.0.0.0:8181",
            "--set=decision_logs.console=true",
            "/policies",
        ],
        cwd=root,
        timeout_seconds=timeout_seconds,
        step="start_opa_policy_decision_point",
    )


def cleanup_opa_runtime(
    root: Path,
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    container_name: str,
    timeout_seconds: int,
) -> None:
    execute_step(
        command_log,
        runner,
        ["docker", "rm", "-f", container_name],
        cwd=root,
        timeout_seconds=timeout_seconds,
        step="cleanup_opa_policy_decision_point",
        raise_on_error=False,
    )


def execute_step(
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    args: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    step: str,
    raise_on_error: bool = True,
) -> CommandResult:
    result = runner(args, None, cwd, timeout_seconds)
    command_log.append(
        {
            "step": step,
            "args": list(result.args),
            "returncode": result.returncode,
            "stdout_preview": result.stdout[:500],
            "stderr_preview": result.stderr[:500],
        }
    )
    if raise_on_error and result.returncode != 0:
        detail = result.stderr or result.stdout
        raise RuntimeError(f"{step} failed: {detail[:500]}")
    return result


def wait_for_opa(
    pdp_url: str,
    *,
    http_log: list[dict[str, Any]],
    attempts: int,
    interval_seconds: float,
) -> None:
    last_error = ""
    for _ in range(attempts):
        result = opa_request(pdp_url, "GET", "/health", None, http_log=http_log)
        if result["status"] == 200:
            return
        last_error = result.get("error") or str(result.get("body_preview") or "")
        if interval_seconds > 0:
            time.sleep(interval_seconds)
    raise RuntimeError(f"OPA policy decision point did not become ready: {last_error}")


def run_policy_decision_probes(pdp_url: str, *, http_log: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "finance_reader_masked": access_decision_probe(
            "finance_reader_masked",
            opa_request(
                pdp_url,
                "POST",
                "/v1/data/enterprise/dp/authz",
                access_input(roles=["finance_reader"], org_id="org-allowed", pii=["beneficiary_id_hash"]),
                http_log=http_log,
            ),
            expect_allow=True,
            expect_row_filter={"org_id": "org-allowed"},
            expect_mask=["beneficiary_id_hash"],
        ),
        "finance_reader_cleartext": access_decision_probe(
            "finance_reader_cleartext",
            opa_request(
                pdp_url,
                "POST",
                "/v1/data/enterprise/dp/authz",
                access_input(roles=["finance_reader", "pii_cleartext"], org_id="org-allowed", pii=["beneficiary_id_hash"]),
                http_log=http_log,
            ),
            expect_allow=True,
            expect_row_filter={"org_id": "org-allowed"},
            expect_mask=[],
        ),
        "unauthorized_default_deny": access_decision_probe(
            "unauthorized_default_deny",
            opa_request(
                pdp_url,
                "POST",
                "/v1/data/enterprise/dp/authz",
                access_input(roles=[], org_id="org-denied", pii=["beneficiary_id_hash"]),
                http_log=http_log,
            ),
            expect_allow=False,
            expect_row_filter={},
            expect_mask=[],
            expect_denial="not_authorized",
        ),
        "policy_admin_approval": policy_admin_probe(
            "policy_admin_approval",
            opa_request(
                pdp_url,
                "POST",
                "/v1/data/enterprise/dp/authz",
                policy_admin_input(
                    requester="alice",
                    approver="bob",
                    approver_roles=["policy_approver"],
                    reason="approve row filter change for finance gold",
                    evidence_hash="sha256:policy-change-evidence",
                ),
                http_log=http_log,
            ),
            expect_approved=True,
            expect_denials=[],
        ),
        "policy_admin_self_approval_denied": policy_admin_probe(
            "policy_admin_self_approval_denied",
            opa_request(
                pdp_url,
                "POST",
                "/v1/data/enterprise/dp/authz",
                policy_admin_input(
                    requester="alice",
                    approver="alice",
                    approver_roles=["policy_approver"],
                    reason="self approve should fail",
                    evidence_hash="sha256:policy-change-evidence",
                ),
                http_log=http_log,
            ),
            expect_approved=False,
            expect_denials=["maker_checker_conflict"],
        ),
        "policy_admin_missing_evidence_denied": policy_admin_probe(
            "policy_admin_missing_evidence_denied",
            opa_request(
                pdp_url,
                "POST",
                "/v1/data/enterprise/dp/authz",
                policy_admin_input(
                    requester="alice",
                    approver="bob",
                    approver_roles=["policy_approver"],
                    reason="missing evidence should fail",
                    evidence_hash="",
                ),
                http_log=http_log,
            ),
            expect_approved=False,
            expect_denials=["missing_evidence"],
        ),
    }


def access_input(*, roles: list[str], org_id: str, pii: list[str]) -> dict[str, Any]:
    return {
        "action": "select",
        "user": {"subject": "finance-ops-analyst", "roles": roles, "org_id": org_id},
        "resource": {"domain": "finance", "layer": "gold", "name": "gold.finance_benefit_reconciliation", "pii": pii},
    }


def policy_admin_input(
    *,
    requester: str,
    approver: str,
    approver_roles: list[str],
    reason: str,
    evidence_hash: str,
) -> dict[str, Any]:
    return {
        "action": "approve_policy_change",
        "change": {
            "id": "policy-change-finance-gold-row-filter",
            "status": "PENDING_APPROVAL",
            "requester": requester,
            "risk": "high",
            "reason": reason,
            "evidence_hash": evidence_hash,
        },
        "approver": {"subject": approver, "roles": approver_roles},
    }


def access_decision_probe(
    name: str,
    response: dict[str, Any],
    *,
    expect_allow: bool,
    expect_row_filter: dict[str, str],
    expect_mask: list[str],
    expect_denial: str | None = None,
) -> dict[str, Any]:
    result = response.get("json", {}).get("result") if isinstance(response.get("json"), dict) else {}
    result = result if isinstance(result, dict) else {}
    mask = sorted(result.get("mask") or [])
    denials = sorted(result.get("deny_reasons") or [])
    checks = {
        "http_ok": response.get("status") == 200,
        "allow_matches": result.get("allow") is expect_allow,
        "row_filter_matches": (result.get("row_filter") or {}) == expect_row_filter,
        "mask_matches": mask == sorted(expect_mask),
        "expected_denial_present": expect_denial is None or expect_denial in denials,
    }
    return {
        "name": name,
        "passed": all(checks.values()),
        "checks": checks,
        "http_status": response.get("status"),
        "allow": result.get("allow"),
        "row_filter": result.get("row_filter") or {},
        "mask": mask,
        "deny_reasons": denials,
    }


def policy_admin_probe(
    name: str,
    response: dict[str, Any],
    *,
    expect_approved: bool,
    expect_denials: list[str],
) -> dict[str, Any]:
    result = response.get("json", {}).get("result") if isinstance(response.get("json"), dict) else {}
    result = result if isinstance(result, dict) else {}
    denials = sorted(result.get("policy_admin_denials") or [])
    checks = {
        "http_ok": response.get("status") == 200,
        "approval_matches": result.get("approve_policy_change") is expect_approved,
        "expected_denials_present": all(item in denials for item in expect_denials),
    }
    return {
        "name": name,
        "passed": all(checks.values()),
        "checks": checks,
        "http_status": response.get("status"),
        "approved": result.get("approve_policy_change"),
        "policy_admin_denials": denials,
    }


def opa_request(
    base_url: str,
    method: str,
    path: str,
    input_payload: dict[str, Any] | None,
    *,
    http_log: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = None
    headers = {}
    if input_payload is not None:
        payload = json.dumps({"input": input_payload}, sort_keys=True).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(f"{base_url}{path}", data=payload, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=5) as response:
            body = response.read()
            status = response.status
            parsed = json.loads(body.decode("utf-8")) if body else {}
            error_message = None
    except error.HTTPError as exc:
        body = exc.read()
        status = exc.code
        parsed = parse_json(body)
        error_message = str(exc)
    except OSError as exc:
        body = b""
        status = 0
        parsed = {}
        error_message = str(exc)
    http_log.append(
        {
            "method": method,
            "path": path,
            "status": status,
            "input_hash": hash_bytes(canonical_json(input_payload).encode("utf-8")) if input_payload is not None else None,
            "body_preview": body[:500].decode("utf-8", errors="replace"),
            "error": error_message,
        }
    )
    return {"status": status, "json": parsed, "error": error_message, "body": body}


def parse_json(body: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(body.decode("utf-8")) if body else {}
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def failed_policy_decision_checks(probes: dict[str, Any]) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    expected = {
        "finance_reader_masked": "OPA allow decision with row filter and mask did not pass.",
        "finance_reader_cleartext": "OPA cleartext allow decision did not pass.",
        "unauthorized_default_deny": "OPA default deny decision did not pass.",
        "policy_admin_approval": "OPA policy-admin approval decision did not pass.",
        "policy_admin_self_approval_denied": "OPA maker-checker self-approval denial did not pass.",
        "policy_admin_missing_evidence_denied": "OPA missing-evidence denial did not pass.",
    }
    for key, message in expected.items():
        probe = probes.get(key)
        if not isinstance(probe, dict) or probe.get("passed") is not True:
            failed.append({"check": key, "message": message, "probe": probe or {}})
    return failed


def write_policy_decision_audit_sink(
    events_path: Path,
    manifest_path: Path,
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    probes: dict[str, Any],
) -> dict[str, Any]:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events = []
    for name, probe in sorted(probes.items()):
        if not isinstance(probe, dict):
            continue
        events.append(
            {
                "event_type": "policy_decision",
                "generated_at": generated_at,
                "environment": environment,
                "release_id": release_id,
                "probe": name,
                "passed": probe.get("passed") is True,
                "decision": {
                    "allow": probe.get("allow"),
                    "approved": probe.get("approved"),
                    "mask": probe.get("mask", []),
                    "row_filter": probe.get("row_filter", {}),
                    "deny_reasons": probe.get("deny_reasons", []),
                    "policy_admin_denials": probe.get("policy_admin_denials", []),
                },
            }
        )
    events_path.write_text("".join(f"{canonical_json(event)}\n" for event in events), encoding="utf-8")
    failed_count = sum(1 for event in events if event["passed"] is not True)
    manifest = {
        "artifact_type": "policy_decision_audit_manifest.v1",
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "events_path": events_path.as_posix(),
        "events_hash": hash_file(events_path),
        "event_count": len(events),
        "failed_event_count": failed_count,
        "passed": bool(events) and failed_count == 0,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    return manifest


def build_policy_decision_smoke_report(
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    opa_image: str,
    pdp_url: str,
    policy_dir: Path,
    command_log: list[dict[str, Any]],
    http_log: list[dict[str, Any]],
    probes: dict[str, Any],
    audit_sink: dict[str, Any],
    audit_events_path: Path,
    audit_manifest_path: Path,
    failed_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    summary = {
        "pdp": "opa",
        "pdp_url": pdp_url,
        "opa_image": opa_image,
        "decision_api_reachable": any(item.get("path") == "/health" and item.get("status") == 200 for item in http_log),
        "finance_reader_allowed": probe_passed(probes, "finance_reader_masked"),
        "cleartext_role_unmasked": probe_passed(probes, "finance_reader_cleartext"),
        "unauthorized_default_denied": probe_passed(probes, "unauthorized_default_deny"),
        "row_filter_decision_present": probe_value(probes, "finance_reader_masked", "row_filter") == {"org_id": "org-allowed"},
        "column_mask_decision_present": "beneficiary_id_hash" in probe_value(probes, "finance_reader_masked", "mask", []),
        "policy_admin_approval_passed": probe_passed(probes, "policy_admin_approval"),
        "policy_admin_self_approval_denied": probe_passed(probes, "policy_admin_self_approval_denied"),
        "policy_admin_missing_evidence_denied": probe_passed(probes, "policy_admin_missing_evidence_denied"),
        "audit_sink_passed": audit_sink.get("passed") is True,
        "audit_event_count": audit_sink.get("event_count", 0),
        "audit_failed_event_count": audit_sink.get("failed_event_count", 0),
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
    }
    passed = not failed_checks
    return {
        "artifact_type": "policy_decision_smoke_report.v1",
        "report_version": 1,
        "capability_id": "runtime-security-enforcement",
        "report_id": stable_id("policy-decision-smoke", environment, release_id, pdp_url),
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "runtime_scope": {
            "mode": "local_opa_http_policy_decision_point",
            "covered": [
                "opa_policy_decision_point_started",
                "opa_http_decision_api_reachable",
                "gold_finance_select_allow_decision",
                "unauthorized_default_deny_decision",
                "row_filter_decision_returned",
                "column_mask_decision_returned",
                "policy_admin_maker_checker_approval",
                "policy_admin_self_approval_denied",
                "policy_admin_missing_evidence_denied",
                "structured_policy_decision_audit_written",
            ],
            "not_covered": [
                "keycloak_or_oidc_authentication",
                "production_opa_or_ranger_cluster_ha",
                "production_policy_bundle_signing",
                "production_policy_bundle_distribution",
                "siem_audit_export",
                "production_secret_rotation",
            ],
        },
        "pdp": {
            "engine": "opa",
            "image": opa_image,
            "url": pdp_url,
            "policy_files": [policy_file_ref(policy_dir / "enterprise_dp_authz.rego")],
        },
        "probes": probes,
        "audit_sink": {
            "mode": "local_jsonl_structured_policy_decision_audit",
            "events_path": audit_events_path.as_posix(),
            "events_hash": hash_file(audit_events_path) if audit_events_path.is_file() else None,
            "manifest_path": audit_manifest_path.as_posix(),
            "manifest_hash": hash_file(audit_manifest_path) if audit_manifest_path.is_file() else None,
            "passed": audit_sink.get("passed") is True,
            "event_count": audit_sink.get("event_count", 0),
            "failed_event_count": audit_sink.get("failed_event_count", 0),
        },
        "commands": command_log,
        "http_exchanges": http_log,
        "summary": summary,
        "passed": passed,
    }


def probe_passed(probes: dict[str, Any], key: str) -> bool:
    return isinstance(probes.get(key), dict) and probes[key].get("passed") is True


def probe_value(probes: dict[str, Any], key: str, field: str, default: Any = None) -> Any:
    if not isinstance(probes.get(key), dict):
        return default
    return probes[key].get(field, default)


def policy_file_ref(path: Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "exists": path.is_file(),
        "hash": hash_file(path) if path.is_file() else None,
    }

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import yaml

from enterprise_dp.secret_rotation_ops import write_secret_rotation_ops_report


ROOT = Path(__file__).resolve().parents[1]


def test_secret_rotation_ops_report_passes_with_managed_evidence(tmp_path: Path) -> None:
    evidence = write_managed_secret_rotation_evidence(tmp_path / "managed-secret-evidence.json", environment="staging")

    result = write_secret_rotation_ops_report(
        ROOT,
        tmp_path / "secret-rotation-ops.json",
        environment="staging",
        evidence_path=evidence,
        generated_at="2026-06-16T12:05:00Z",
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    summary = report["summary"]

    assert report["artifact_type"] == "secret_rotation_ops_report.v1"
    assert report["capability_id"] == "production-secret-rotation"
    assert report["mode"] == "managed_secret_manager_evidence"
    assert report["readiness_state"] == "production_like_ready"
    assert report["passed"] is True
    assert summary["p0_service_count"] > 0
    assert summary["covered_service_count"] == summary["p0_service_count"]
    assert summary["failed_service_count"] == 0
    assert summary["managed_secret_manager_ha"] is True
    assert summary["kms_hsm_custody"] is True
    assert summary["audit_sink_siem_exported"] is True


def test_secret_rotation_ops_report_fails_closed_for_local_environment(tmp_path: Path) -> None:
    evidence = write_managed_secret_rotation_evidence(tmp_path / "managed-secret-evidence.json", environment="local")

    result = write_secret_rotation_ops_report(
        ROOT,
        tmp_path / "secret-rotation-ops.json",
        environment="local",
        evidence_path=evidence,
        generated_at="2026-06-16T12:05:00Z",
    )

    failed_checks = {item["name"] for item in result.report["checks"] if item["passed"] is not True}

    assert result.report["passed"] is False
    assert result.report["readiness_state"] == "not_ready"
    assert "environment_production_like" in failed_checks


def test_secret_rotation_ops_report_fails_when_p0_service_coverage_missing(tmp_path: Path) -> None:
    evidence = write_managed_secret_rotation_evidence(tmp_path / "managed-secret-evidence.json", environment="staging")
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["service_secrets"] = payload["service_secrets"][:-1]
    evidence.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    result = write_secret_rotation_ops_report(
        ROOT,
        tmp_path / "secret-rotation-ops.json",
        environment="staging",
        evidence_path=evidence,
        generated_at="2026-06-16T12:05:00Z",
    )

    failed_checks = {item["name"] for item in result.report["checks"] if item["passed"] is not True}

    assert result.report["passed"] is False
    assert result.report["summary"]["failed_service_count"] == 1
    assert "p0_runtime_service_secret_coverage" in failed_checks


def test_secret_rotation_ops_cli(tmp_path: Path) -> None:
    evidence = write_managed_secret_rotation_evidence(tmp_path / "managed-secret-evidence.json", environment="staging")
    output = tmp_path / "secret-rotation-ops.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "secret-rotation-ops-report",
            "--root",
            str(ROOT),
            "--output",
            str(output),
            "--environment",
            "staging",
            "--evidence",
            str(evidence),
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["readiness_state"] == "production_like_ready"
    assert output.is_file()


def write_managed_secret_rotation_evidence(path: Path, *, environment: str) -> Path:
    services = p0_runtime_services()
    payload = {
        "artifact_type": "managed_secret_rotation_evidence.v1",
        "environment": environment,
        "generated_at": "2026-06-16T12:00:00Z",
        "valid_until": "2026-06-17T12:00:00Z",
        "passed": True,
        "secret_manager": {
            "provider": "aws-secrets-manager",
            "ha_enabled": True,
            "kms_key_id": "arn:aws:kms:ap-southeast-1:111122223333:key/dp-runtime",
            "kms_key_hash": fake_sha256("dp-runtime-kms"),
            "hsm_backed": True,
            "cross_region_replication": True,
            "backup_restore_tested": True,
        },
        "controls": {
            "managed_secret_manager_ha": True,
            "workload_identity_federation": True,
            "kms_hsm_custody": True,
            "rotation_policy_enforced": True,
            "old_versions_denied": True,
            "unauthorized_identity_denied": True,
            "missing_secret_denied": True,
            "orchestrator_injection_redacted": True,
            "plaintext_secret_material_persisted": False,
        },
        "service_secrets": [
            {
                "service_id": service["serviceId"],
                "secret_handle": f"secrets://{environment}/dp/{service['serviceId']}",
                "service_identity": f"svc-dp-{service['serviceId']}",
                "identity_mode": "workload_identity",
                "active_version": "v20260616",
                "kms_key_id": "arn:aws:kms:ap-southeast-1:111122223333:key/dp-runtime",
                "key_hash": fake_sha256(f"{service['serviceId']}:key"),
                "rotation_policy_id": "rot-90d-managed",
                "latest_rotation_at": "2026-06-16T11:30:00Z",
                "old_version_revoked": True,
                "old_version_denied": True,
                "unauthorized_identity_denied": True,
                "missing_secret_denied": True,
                "plaintext_secret_material_persisted": False,
            }
            for service in services
        ],
        "audit_sink": {
            "sink_uri": f"siem://enterprise/{environment}/secret-rotation",
            "events_hash": fake_sha256("secret-rotation-audit-events"),
            "event_count": len(services) * 6,
            "failed_event_count": 0,
            "siem_exported": True,
        },
        "attestation": {
            "attached": True,
            "signature_verified": True,
            "subject_hash_matches": True,
            "signing_key_id": "external-auditor-kms-2026",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def p0_runtime_services() -> list[dict[str, object]]:
    topology = yaml.safe_load((ROOT / "platform" / "runtime" / "topology.yaml").read_text(encoding="utf-8"))
    return [
        service
        for service in topology["runtimeServices"]
        if isinstance(service, dict) and service.get("p0Required") is True
    ]


def fake_sha256(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.orchestration_runtime_ops import write_orchestration_runtime_ops_report


ROOT = Path(__file__).resolve().parents[1]


def test_orchestration_runtime_ops_report_passes_with_managed_runtime_evidence(tmp_path: Path) -> None:
    evidence = write_managed_orchestration_runtime_evidence(
        tmp_path / "orchestration-runtime-evidence.json",
        environment="staging",
    )

    result = write_orchestration_runtime_ops_report(
        ROOT,
        tmp_path / "orchestration-runtime-ops.json",
        environment="staging",
        evidence_path=evidence,
        generated_at="2026-06-16T12:05:00Z",
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    summary = report["summary"]

    assert report["artifact_type"] == "orchestration_runtime_ops_report.v1"
    assert report["capability_id"] == "production-orchestration-runtime"
    assert report["mode"] == "runtime_attested"
    assert report["readiness_state"] == "production_like_ready"
    assert report["passed"] is True
    assert summary["replica_count"] == 3
    assert summary["availability_zones"] == 3
    assert summary["distributed_executor_enabled"] is True
    assert summary["kubernetes_run_launcher_enabled"] is True
    assert summary["managed_run_storage"] is True
    assert summary["schedule_tick_history_passed"] is True
    assert summary["retry_policy_verified"] is True
    assert summary["backfill_materialization_history_passed"] is True
    assert summary["secret_injection_verified"] is True
    assert summary["metrics_exported"] is True


def test_orchestration_runtime_ops_report_fails_closed_for_local_environment(tmp_path: Path) -> None:
    evidence = write_managed_orchestration_runtime_evidence(
        tmp_path / "orchestration-runtime-evidence.json",
        environment="local",
    )

    result = write_orchestration_runtime_ops_report(
        ROOT,
        tmp_path / "orchestration-runtime-ops.json",
        environment="local",
        evidence_path=evidence,
        generated_at="2026-06-16T12:05:00Z",
    )
    failed_checks = {item["name"] for item in result.report["checks"] if item["passed"] is not True}

    assert result.report["passed"] is False
    assert result.report["readiness_state"] == "not_ready"
    assert "environment_production_like" in failed_checks


def test_orchestration_runtime_ops_report_rejects_thin_runtime_evidence(tmp_path: Path) -> None:
    evidence = write_managed_orchestration_runtime_evidence(
        tmp_path / "orchestration-runtime-evidence.json",
        environment="staging",
    )
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["run_launcher"]["distributed_executor_enabled"] = False
    payload["run_launcher"]["kubernetes_run_launcher_enabled"] = False
    payload["run_storage"]["managed_run_storage"] = False
    payload["day2"]["schedule_tick_history_passed"] = False
    payload["day2"]["backfill_materialization_history_passed"] = False
    payload["source_version"]["image_digest"] = "not-a-digest"
    evidence.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    result = write_orchestration_runtime_ops_report(
        ROOT,
        tmp_path / "orchestration-runtime-ops.json",
        environment="staging",
        evidence_path=evidence,
        generated_at="2026-06-16T12:05:00Z",
    )
    failed_checks = {item["name"] for item in result.report["checks"] if item["passed"] is not True}

    assert result.report["passed"] is False
    assert result.report["summary"]["failed_check_count"] >= 5
    assert {
        "distributed_or_kubernetes_run_launcher",
        "managed_run_storage_enabled",
        "schedule_tick_history_passed",
        "backfill_materialization_history_passed",
        "image_digest_declared",
    }.issubset(failed_checks)


def test_orchestration_runtime_ops_report_rejects_sample_or_unredacted_evidence(tmp_path: Path) -> None:
    evidence = write_managed_orchestration_runtime_evidence(
        tmp_path / "orchestration-runtime-evidence.json",
        environment="staging",
    )
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["sample"] = True
    payload["token"] = "plain-runtime-token"
    evidence.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    result = write_orchestration_runtime_ops_report(
        ROOT,
        tmp_path / "orchestration-runtime-ops.json",
        environment="staging",
        evidence_path=evidence,
        generated_at="2026-06-16T12:05:00Z",
    )
    failed_checks = {item["name"] for item in result.report["checks"] if item["passed"] is not True}

    assert result.report["passed"] is False
    assert "sample_evidence_denied" in failed_checks
    assert "plaintext_secret_material_absent" in failed_checks


def test_orchestration_runtime_ops_cli(tmp_path: Path) -> None:
    evidence = write_managed_orchestration_runtime_evidence(
        tmp_path / "orchestration-runtime-evidence.json",
        environment="staging",
    )
    output = tmp_path / "orchestration-runtime-ops.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "orchestration-runtime-ops-report",
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
    assert summary["kubernetes_run_launcher_enabled"] is True
    assert summary["managed_run_storage"] is True
    assert output.is_file()


def write_managed_orchestration_runtime_evidence(path: Path, *, environment: str) -> Path:
    release_id = f"{environment}-orchestration-runtime-release"
    change_ticket = "CHG-DP-ORCH-20260616"
    deployment_id = f"dagster-{environment}-workspace"
    service_identity = f"svc-dp-{environment}-orchestration"
    run_storage_uri = f"postgresql://dagster-run-storage.{environment}.dp.internal/dagster"
    upstream_hash = fake_sha256("dagster-day2-smoke-report")
    payload = {
        "artifact_type": "managed_orchestration_runtime_evidence.v1",
        "environment": environment,
        "generated_at": "2026-06-16T12:00:00Z",
        "valid_until": "2026-06-17T12:00:00Z",
        "passed": True,
        "evidence_source": "external_attestation",
        "production_evidence": True,
        "sample": False,
        "redacted": True,
        "release_id": release_id,
        "change_ticket": change_ticket,
        "source_version": {
            "git_sha": "0123456789abcdef0123456789abcdef01234567",
            "image_digest": fake_sha256(f"{environment}:dagster-image"),
        },
        "orchestrator": {
            "provider": "dagster",
            "service_id": "orchestration",
            "deployment_id": deployment_id,
            "service_identity": service_identity,
            "endpoint_uri": f"https://dagster.{environment}.dp.example",
            "run_history_hash": fake_sha256(f"{environment}:run-history"),
        },
        "deployment": {
            "replica_count": 3,
            "daemon_replica_count": 2,
            "scheduler_replica_count": 2,
            "worker_replica_count": 4,
            "availability_zones": 3,
            "multi_az": True,
            "health_check_passed": True,
            "managed_service": True,
            "ha_mode": "managed_ha",
        },
        "run_launcher": {
            "distributed_executor_enabled": True,
            "kubernetes_run_launcher_enabled": True,
            "isolated_run_workers": True,
            "run_queue_enabled": True,
        },
        "run_storage": {
            "storage_uri": run_storage_uri,
            "managed_run_storage": True,
            "persistent": True,
            "ha_enabled": True,
            "backup_enabled": True,
            "run_history_readback_passed": True,
            "asset_state_readback_passed": True,
        },
        "day2": {
            "schedule_tick_history_passed": True,
            "retry_policy_verified": True,
            "retry_backoff_seconds": 30,
            "backfill_materialization_history_passed": True,
            "production_backfill_scheduler": True,
            "backfill_partition_count": 5,
            "materialization_event_count": 5,
            "worker_restart_recovered": True,
            "failed_run_recovered": True,
        },
        "security": {
            "service_identity_authorized": True,
            "secret_injection_verified": True,
            "raw_secret_material_persisted": False,
            "network_private": True,
        },
        "metrics": {
            "metrics_exported": True,
            "run_failure_alert_configured": True,
            "scheduler_lag_metric_exported": True,
        },
        "audit_sink": {
            "sink_uri": f"siem://enterprise/{environment}/orchestration-runtime",
            "events_hash": fake_sha256("orchestration-runtime-audit-events"),
            "event_count": 37,
            "failed_event_count": 0,
        },
        "attestation": {
            "attached": True,
            "signature_verified": True,
            "subject_hash_matches": True,
            "subject_hash": fake_sha256("orchestration-runtime-attestation-subject"),
        },
        "upstream_evidence": [
            {
                "name": "dagster_day2_smoke",
                "artifact_type": "dagster_day2_smoke_report.v1",
                "artifact_hash": upstream_hash,
                "passed": True,
            }
        ],
        "binding": {
            "release_id_hash": fake_sha256(release_id),
            "change_ticket_hash": fake_sha256(change_ticket),
            "orchestrator_deployment_id_hash": fake_sha256(deployment_id),
            "orchestrator_service_identity_hash": fake_sha256(service_identity),
            "run_storage_uri_hash": fake_sha256(run_storage_uri),
            "upstream_evidence_hashes": [upstream_hash],
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def fake_sha256(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"

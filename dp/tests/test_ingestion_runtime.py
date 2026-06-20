from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import yaml

from enterprise_dp.ingestion_runtime import (
    build_ingestion_runtime_ops_report,
    write_ingestion_runtime_evidence_artifact,
    write_ingestion_runtime_ops_report,
)


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-16T13:45:00Z"
VALID_UNTIL = "2026-06-16T14:00:00Z"
HASH = "sha256:1111111111111111111111111111111111111111111111111111111111111111"


def test_ingestion_runtime_report_allows_local_preflight_without_machine_evidence() -> None:
    report = build_ingestion_runtime_ops_report(
        ROOT,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert report["artifact_type"] == "event_cdc_ingestion_runtime_report.v1"
    assert report["readiness_state"] == "local_preflight_ready"
    assert report["passed"] is True
    assert report["evidence"]["attached"] is False
    assert report["summary"]["p0_failed_source_count"] == 0


def test_ingestion_runtime_report_blocks_prod_without_machine_evidence() -> None:
    report = build_ingestion_runtime_ops_report(
        ROOT,
        environment="prod",
        generated_at=GENERATED_AT,
    )

    failed_checks = {check["name"] for check in report["checks"] if check["passed"] is not True}
    assert report["passed"] is False
    assert report["readiness_state"] == "not_ready"
    assert "evidence_attached_for_production_like" in failed_checks
    assert report["summary"]["p0_failed_source_count"] >= 1
    assert report["decision_board"]["page_now"]


def test_ingestion_runtime_report_passes_with_complete_machine_evidence(tmp_path: Path) -> None:
    evidence_path = write_ingestion_runtime_evidence(tmp_path, environment="prod")

    report = build_ingestion_runtime_ops_report(
        ROOT,
        environment="prod",
        evidence_path=evidence_path,
        generated_at=GENERATED_AT,
    )

    assert report["passed"] is True
    assert report["readiness_state"] == "production_like_ready"
    assert report["summary"]["p0_failed_source_count"] == 0
    assert report["summary"]["running_connector_count"] >= report["summary"]["p0_source_count"]


def test_ingestion_runtime_report_blocks_connector_lag_dlt_and_backpressure_failures(tmp_path: Path) -> None:
    p0_source = p0_source_ids()[0]
    evidence_path = write_ingestion_runtime_evidence(
        tmp_path,
        environment="prod",
        source_updates={
            p0_source: {
                "deployment_state": "failed",
                "tasks_running": 0,
                "lag": {"max_lag_records": 5001, "max_lag_seconds": 1200},
                "dlt": {"enabled": False, "topic": "", "unresolved_count": 7},
                "backpressure_state": "throttled",
                "broker": {"topic_exists": False, "producer_acl": False, "consumer_acl": True},
            }
        },
    )

    report = build_ingestion_runtime_ops_report(
        ROOT,
        environment="prod",
        evidence_path=evidence_path,
        generated_at=GENERATED_AT,
    )

    failed = report["decision_board"]["p0_failed_sources"][0]
    assert report["passed"] is False
    assert failed["source_id"] == p0_source
    assert set(failed["issues"]) >= {
        "connector_not_running",
        "connector_tasks_not_running",
        "lag_records_over_slo",
        "lag_seconds_over_slo",
        "dlt_policy_missing",
        "dlt_unresolved_over_slo",
        "backpressure_active",
        "broker_topic_acl_not_ready",
    }


def test_ingestion_runtime_report_blocks_wrong_environment_synthetic_and_expired_evidence(tmp_path: Path) -> None:
    evidence_path = write_ingestion_runtime_evidence(
        tmp_path,
        environment="staging",
        source_kind="synthetic_fixture",
        generated_at="2026-06-16T13:45:00Z",
        valid_until="2026-06-16T13:00:00Z",
    )

    report = build_ingestion_runtime_ops_report(
        ROOT,
        environment="prod",
        evidence_path=evidence_path,
        generated_at=GENERATED_AT,
    )

    failed_checks = {check["name"] for check in report["checks"] if check["passed"] is not True}
    assert report["passed"] is False
    assert "evidence_environment_matches" in failed_checks
    assert "production_evidence_not_synthetic" in failed_checks
    assert "production_evidence_not_expired" in failed_checks


def test_ingestion_runtime_report_writer_and_cli(tmp_path: Path) -> None:
    output_path = tmp_path / "ingestion-runtime" / "local.json"
    result = write_ingestion_runtime_ops_report(
        ROOT,
        output_path,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "ingestion-runtime" / "prod.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "ingestion-runtime-check",
            "--root",
            str(ROOT),
            "--environment",
            "prod",
            "--output",
            str(cli_output),
            "--generated-at",
            GENERATED_AT,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["passed"] is False
    assert summary["summary"]["p0_failed_source_count"] >= 1
    assert cli_output.is_file()


def test_ingestion_runtime_evidence_normalizer_outputs_report_ready_machine_evidence(tmp_path: Path) -> None:
    inputs = write_machine_runtime_inputs(tmp_path)
    result = write_ingestion_runtime_evidence_artifact(
        ROOT,
        tmp_path / "ingestion-runtime" / "normalized-evidence.json",
        environment="prod",
        source_kind="ci_tool_output",
        kafka_connect_status_path=inputs["connect"],
        lag_metrics_path=inputs["lag"],
        dlt_report_path=inputs["dlt"],
        backpressure_report_path=inputs["backpressure"],
        offset_ledgers_path=inputs["offset"],
        broker_checks_path=inputs["broker"],
        generated_at=GENERATED_AT,
        valid_until=VALID_UNTIL,
        ci_run_id="ci-runtime-123",
        issuer_tool="sre-runtime-exporter",
        issuer_tool_version="1.0.0",
    )

    assert result.evidence["artifact_type"] == "ingestion_runtime_evidence.v1"
    assert result.evidence["source_registry"]["hash"].startswith("sha256:")
    assert len(result.evidence["connectors"]) == len(source_registry_sources())
    assert result.manifest_path.is_file()
    assert result.manifest["artifact_type"] == "ingestion_runtime_evidence_manifest.v1"
    assert result.manifest["readiness_args"]["command"] == "ingestion-runtime-check"
    report = build_ingestion_runtime_ops_report(
        ROOT,
        environment="prod",
        evidence_path=result.output_path,
        generated_at=GENERATED_AT,
    )
    assert report["passed"] is True
    assert report["readiness_state"] == "production_like_ready"
    assert report["summary"]["p0_failed_source_count"] == 0


def test_ingestion_runtime_evidence_normalizer_surfaces_broker_failures(tmp_path: Path) -> None:
    p0_source = p0_source_ids()[0]
    inputs = write_machine_runtime_inputs(
        tmp_path,
        source_updates={
            p0_source: {
                "broker": {"topic_exists": True, "producer_acl": False, "consumer_acl": True},
            }
        },
    )
    result = write_ingestion_runtime_evidence_artifact(
        ROOT,
        tmp_path / "ingestion-runtime" / "normalized-evidence.json",
        environment="prod",
        source_kind="ci_tool_output",
        kafka_connect_status_path=inputs["connect"],
        lag_metrics_path=inputs["lag"],
        dlt_report_path=inputs["dlt"],
        backpressure_report_path=inputs["backpressure"],
        offset_ledgers_path=inputs["offset"],
        broker_checks_path=inputs["broker"],
        generated_at=GENERATED_AT,
        valid_until=VALID_UNTIL,
    )
    report = build_ingestion_runtime_ops_report(
        ROOT,
        environment="prod",
        evidence_path=result.output_path,
        generated_at=GENERATED_AT,
    )

    failed = report["decision_board"]["p0_failed_sources"][0]
    assert report["passed"] is False
    assert failed["source_id"] == p0_source
    assert "broker_topic_acl_not_ready" in failed["issues"]
    assert any(action["action"] == "repair_topic_or_acl" for action in failed["next_actions"])


def test_ingestion_runtime_evidence_normalizer_cli_then_runtime_check(tmp_path: Path) -> None:
    inputs = write_machine_runtime_inputs(tmp_path)
    evidence_path = tmp_path / "ingestion-runtime" / "cli-normalized-evidence.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "ingestion-runtime-evidence-normalize",
            "--root",
            str(ROOT),
            "--environment",
            "prod",
            "--source-kind",
            "ci_tool_output",
            "--kafka-connect-status",
            str(inputs["connect"]),
            "--lag-metrics",
            str(inputs["lag"]),
            "--dlt-report",
            str(inputs["dlt"]),
            "--backpressure-report",
            str(inputs["backpressure"]),
            "--offset-ledgers",
            str(inputs["offset"]),
            "--broker-checks",
            str(inputs["broker"]),
            "--output",
            str(evidence_path),
            "--generated-at",
            GENERATED_AT,
            "--valid-until",
            VALID_UNTIL,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    cli_summary = json.loads(completed.stdout)
    assert cli_summary["connector_count"] == len(source_registry_sources())
    assert cli_summary["p0_connector_count"] == len(p0_source_ids())
    assert cli_summary["readiness_args"]["evidence"] == str(evidence_path)
    assert Path(cli_summary["manifest"]).is_file()

    report_path = tmp_path / "ingestion-runtime" / "prod-report.json"
    check = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "ingestion-runtime-check",
            "--root",
            str(ROOT),
            "--environment",
            "prod",
            "--evidence",
            str(evidence_path),
            "--output",
            str(report_path),
            "--generated-at",
            GENERATED_AT,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0
    assert json.loads(check.stdout)["passed"] is True
    assert report_path.is_file()


def test_ingestion_runtime_evidence_normalizer_does_not_copy_secret_fields(tmp_path: Path) -> None:
    secret = "password=super-secret-token"
    inputs = write_machine_runtime_inputs(
        tmp_path,
        source_updates={
            p0_source_ids()[0]: {
                "connect": {
                    "config": {"database.password": secret},
                    "trace": f"connector log leaked {secret}",
                }
            }
        },
    )
    result = write_ingestion_runtime_evidence_artifact(
        ROOT,
        tmp_path / "ingestion-runtime" / "normalized-evidence.json",
        environment="prod",
        source_kind="ci_tool_output",
        kafka_connect_status_path=inputs["connect"],
        lag_metrics_path=inputs["lag"],
        dlt_report_path=inputs["dlt"],
        backpressure_report_path=inputs["backpressure"],
        offset_ledgers_path=inputs["offset"],
        broker_checks_path=inputs["broker"],
        generated_at=GENERATED_AT,
        valid_until=VALID_UNTIL,
    )

    assert secret not in result.output_path.read_text(encoding="utf-8")
    assert secret not in result.manifest_path.read_text(encoding="utf-8")


def write_ingestion_runtime_evidence(
    tmp_path: Path,
    *,
    environment: str,
    source_kind: str = "ci_tool_output",
    generated_at: str = GENERATED_AT,
    valid_until: str = VALID_UNTIL,
    source_updates: dict[str, dict[str, object]] | None = None,
) -> Path:
    connectors = []
    for source in source_registry_sources():
        source_id = source["sourceId"]
        connector = {
            "source_id": source_id,
            "connector_id": f"{source_id}-connector",
            "connector_type": source.get("source", {}).get("type", "outbox"),
            "deployment_state": "running",
            "tasks_total": 1,
            "tasks_running": 1,
            "backpressure_state": "clear",
            "lag": {"max_lag_records": 25, "max_lag_seconds": 45},
            "dlt": {"enabled": True, "topic": f"dlt.{source_id}", "unresolved_count": 0},
            "broker": {"topic_exists": True, "producer_acl": True, "consumer_acl": True},
            "offset_ledger": {"uri": f"evidence://offset-ledger/{source_id}.json", "hash": HASH},
            "last_successful_commit_at": "2026-06-16T13:40:00Z",
        }
        if source_updates and source_id in source_updates:
            connector.update(source_updates[source_id])
        connectors.append(connector)
    payload = {
        "artifact_type": "ingestion_runtime_evidence.v1",
        "report_version": 1,
        "generated_at": generated_at,
        "valid_until": valid_until,
        "environment": environment,
        "source_kind": source_kind,
        "connectors": connectors,
    }
    path = tmp_path / "ingestion-runtime" / f"{environment}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    return path


def write_machine_runtime_inputs(
    tmp_path: Path,
    *,
    source_updates: dict[str, dict[str, dict[str, object]]] | None = None,
) -> dict[str, Path]:
    connect_rows = []
    lag_rows = []
    dlt_rows = []
    backpressure_rows = []
    offset_rows = []
    broker_rows = []
    for source in source_registry_sources():
        source_id = str(source["sourceId"])
        update = source_updates.get(source_id, {}) if source_updates else {}
        connect = {
            "source_id": source_id,
            "name": f"{source_id}-connector",
            "connector_type": source.get("source", {}).get("type", "outbox"),
            "connector": {"state": "RUNNING"},
            "tasks": [{"state": "RUNNING"}],
        } | update.get("connect", {})
        lag = {
            "source_id": source_id,
            "max_lag_records": 25,
            "max_lag_seconds": 45,
        } | update.get("lag", {})
        dlt = {
            "source_id": source_id,
            "enabled": True,
            "topic": f"dlt.{source_id}",
            "unresolved_count": 0,
        } | update.get("dlt", {})
        backpressure = {
            "source_id": source_id,
            "state": "clear",
        } | update.get("backpressure", {})
        offset = {
            "source_id": source_id,
            "uri": f"evidence://offset-ledger/{source_id}.json",
            "hash": HASH,
            "last_successful_commit_at": "2026-06-16T13:40:00Z",
        } | update.get("offset", {})
        broker = {
            "source_id": source_id,
            "topic_exists": True,
            "producer_acl": True,
            "consumer_acl": True,
        } | update.get("broker", {})
        connect_rows.append(connect)
        lag_rows.append(lag)
        dlt_rows.append(dlt)
        backpressure_rows.append(backpressure)
        offset_rows.append(offset)
        broker_rows.append(broker)

    base = tmp_path / "machine-runtime"
    base.mkdir(parents=True)
    paths = {
        "connect": base / "kafka-connect-status.json",
        "lag": base / "lag-metrics.json",
        "dlt": base / "dlt-report.json",
        "backpressure": base / "backpressure-report.json",
        "offset": base / "offset-ledgers.json",
        "broker": base / "broker-checks.json",
    }
    paths["connect"].write_text(json.dumps({"connectors": connect_rows}, sort_keys=True), encoding="utf-8")
    paths["lag"].write_text(json.dumps({"sources": lag_rows}, sort_keys=True), encoding="utf-8")
    paths["dlt"].write_text(json.dumps({"sources": dlt_rows}, sort_keys=True), encoding="utf-8")
    paths["backpressure"].write_text(json.dumps({"sources": backpressure_rows}, sort_keys=True), encoding="utf-8")
    paths["offset"].write_text(json.dumps({"sources": offset_rows}, sort_keys=True), encoding="utf-8")
    paths["broker"].write_text(json.dumps({"sources": broker_rows}, sort_keys=True), encoding="utf-8")
    return paths


def source_registry_sources() -> list[dict[str, object]]:
    registry = yaml.safe_load((ROOT / "platform" / "ingestion" / "source-registry.yaml").read_text(encoding="utf-8"))
    return [source for source in registry["sources"] if isinstance(source, dict)]


def p0_source_ids() -> list[str]:
    return [str(source["sourceId"]) for source in source_registry_sources() if source.get("priority") == "P0"]

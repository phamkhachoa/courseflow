from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import yaml

from enterprise_dp.lakehouse_ops import build_bronze_lakehouse_ops_report, write_bronze_lakehouse_ops_report


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-16T14:30:00Z"
VALID_UNTIL = "2026-06-16T15:30:00Z"
HASH = "sha256:1111111111111111111111111111111111111111111111111111111111111111"


def test_bronze_lakehouse_ops_allows_local_preflight_without_machine_evidence() -> None:
    report = build_bronze_lakehouse_ops_report(
        ROOT,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert report["artifact_type"] == "bronze_lakehouse_ops_report.v1"
    assert report["readiness_state"] == "local_preflight_ready"
    assert report["passed"] is True
    assert report["summary"]["p0_failed_table_count"] == 0


def test_bronze_lakehouse_ops_blocks_prod_without_ledgers_and_maintenance() -> None:
    report = build_bronze_lakehouse_ops_report(
        ROOT,
        environment="prod",
        generated_at=GENERATED_AT,
    )

    failed_global = {check["name"] for check in report["checks"] if check["passed"] is not True}
    assert report["passed"] is False
    assert report["readiness_state"] == "not_ready"
    assert "maintenance_evidence_attached_for_production_like" in failed_global
    assert report["summary"]["p0_failed_table_count"] >= 1
    assert report["decision_board"]["page_now"]


def test_bronze_lakehouse_ops_passes_with_complete_production_like_evidence(tmp_path: Path) -> None:
    ledgers = write_offset_ledgers(tmp_path, environment="prod")
    maintenance = write_maintenance_evidence(tmp_path, environment="prod")

    report = build_bronze_lakehouse_ops_report(
        ROOT,
        environment="prod",
        offset_ledger_paths=ledgers,
        maintenance_evidence_path=maintenance,
        generated_at=GENERATED_AT,
    )

    assert report["passed"] is True
    assert report["readiness_state"] == "production_like_ready"
    assert report["summary"]["ledger_attached_count"] >= report["summary"]["p0_source_count"]
    assert report["summary"]["maintenance_attached_count"] >= report["summary"]["p0_source_count"]


def test_bronze_lakehouse_ops_blocks_bad_maintenance_and_ledger(tmp_path: Path) -> None:
    p0_source = p0_sources()[0]
    ledgers = write_offset_ledgers(
        tmp_path,
        environment="prod",
        source_updates={
            p0_source["sourceId"]: {
                "target": {
                    "commit_status": "failed",
                    "table_format": "parquet",
                    "target_snapshot_id": None,
                    "table_metadata_uri": None,
                    "table_metadata_hash": None,
                },
                "counts": {"quarantined_record_count": 4},
                "replay": None,
            }
        },
    )
    maintenance = write_maintenance_evidence(
        tmp_path,
        environment="prod",
        table_updates={
            p0_source["canonical"]["bronzeTarget"]: {
                "append_only_enforced": False,
                "compaction": {"status": "failed"},
                "orphan_cleanup": {"status": "failed"},
                "table_properties": {"format-version": "1", "commit.retry.num-retries": 1},
            }
        },
    )

    report = build_bronze_lakehouse_ops_report(
        ROOT,
        environment="prod",
        offset_ledger_paths=ledgers,
        maintenance_evidence_path=maintenance,
        generated_at=GENERATED_AT,
    )

    failed = report["decision_board"]["p0_failed_tables"][0]
    assert report["passed"] is False
    assert failed["source_id"] == p0_source["sourceId"]
    assert set(failed["issues"]) >= {
        "table_format_not_iceberg",
        "commit_not_committed",
        "quarantine_not_empty",
        "replay_proof_missing",
        "iceberg_snapshot_metadata_missing",
        "append_only_not_enforced",
        "compaction_not_passing",
        "orphan_cleanup_not_passing",
        "iceberg_properties_not_ready",
    }


def test_bronze_lakehouse_ops_blocks_wrong_environment_synthetic_and_expired_maintenance(tmp_path: Path) -> None:
    ledgers = write_offset_ledgers(tmp_path, environment="prod")
    maintenance = write_maintenance_evidence(
        tmp_path,
        environment="staging",
        source_kind="synthetic_fixture",
        valid_until="2026-06-16T13:00:00Z",
    )

    report = build_bronze_lakehouse_ops_report(
        ROOT,
        environment="prod",
        offset_ledger_paths=ledgers,
        maintenance_evidence_path=maintenance,
        generated_at=GENERATED_AT,
    )

    failed_global = {check["name"] for check in report["checks"] if check["passed"] is not True}
    assert report["passed"] is False
    assert "maintenance_environment_matches" in failed_global
    assert "production_maintenance_not_synthetic" in failed_global
    assert "production_maintenance_not_expired" in failed_global


def test_bronze_lakehouse_ops_writer_and_cli(tmp_path: Path) -> None:
    output_path = tmp_path / "bronze-lakehouse" / "local.json"
    result = write_bronze_lakehouse_ops_report(
        ROOT,
        output_path,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "bronze-lakehouse" / "prod.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "bronze-lakehouse-ops-report",
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
    assert summary["summary"]["p0_failed_table_count"] >= 1
    assert cli_output.is_file()


def write_offset_ledgers(
    tmp_path: Path,
    *,
    environment: str,
    source_updates: dict[str, dict[str, object]] | None = None,
) -> list[Path]:
    paths = []
    for source in p0_sources():
        source_id = source["sourceId"]
        bronze_target = source["canonical"]["bronzeTarget"]
        payload = {
            "artifact_type": "source_offset_ledger.v1",
            "ledger_version": 1,
            "ledger_id": f"ledger-{source_id}",
            "generated_at": GENERATED_AT,
            "environment": environment,
            "source_id": source_id,
            "source": {"source_id": source_id},
            "ingestion": {
                "manifest_uri": f"evidence://bronze/{source_id}/manifest.json",
                "manifest_hash": HASH,
                "topic": source["canonical"]["topic"],
                "bronze_target": bronze_target,
            },
            "replay": {
                "manifest_uri": f"evidence://bronze/{source_id}/replay.json",
                "manifest_hash": HASH,
                "quality_passed": True,
                "new_row_count": 0,
                "replay_skipped_count": 10,
            },
            "target": {
                "table_format": "iceberg",
                "target_table": bronze_target,
                "target_snapshot_id": f"snapshot-{source_id}",
                "table_metadata_uri": f"s3://dp-prod-lakehouse/{bronze_target}/metadata/00001.metadata.json",
                "table_metadata_hash": HASH,
                "commit_status": "committed",
            },
            "watermarks": [
                {
                    "source_topic": source["canonical"]["topic"],
                    "source_partition": 0,
                    "min_offset": 1,
                    "max_offset": 10,
                    "row_count": 10,
                }
            ],
            "record_bindings": [{"source_record_hash_sha256": HASH, "payload_hash_sha256": HASH, "bronze_row_hash_sha256": HASH}],
            "counts": {
                "input_record_count": 10,
                "committed_record_count": 10,
                "quarantined_record_count": 0,
                "duplicate_record_count": 0,
            },
            "checks": [],
            "failures": [],
            "passed": True,
        }
        if source_updates and source_id in source_updates:
            deep_update(payload, source_updates[source_id])
        path = tmp_path / "offset-ledgers" / f"{source_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        paths.append(path)
    return paths


def write_maintenance_evidence(
    tmp_path: Path,
    *,
    environment: str,
    source_kind: str = "ci_tool_output",
    valid_until: str = VALID_UNTIL,
    table_updates: dict[str, dict[str, object]] | None = None,
) -> Path:
    tables = []
    for source in p0_sources():
        table = source["canonical"]["bronzeTarget"]
        row = {
            "table": table,
            "append_only_enforced": True,
            "compaction": {"status": "passed", "small_file_count": 0, "target_file_size_bytes": 536870912},
            "snapshot_retention": {"status": "passed", "min_snapshots_to_keep": 20, "max_snapshot_age_ms": 7776000000},
            "orphan_cleanup": {"status": "not_due"},
            "table_properties": {
                "format-version": "2",
                "commit.retry.num-retries": 4,
                "write.target-file-size-bytes": 536870912,
            },
        }
        if table_updates and table in table_updates:
            deep_update(row, table_updates[table])
        tables.append(row)
    payload = {
        "artifact_type": "bronze_lakehouse_maintenance_evidence.v1",
        "report_version": 1,
        "generated_at": GENERATED_AT,
        "valid_until": valid_until,
        "environment": environment,
        "source_kind": source_kind,
        "tables": tables,
    }
    path = tmp_path / "maintenance" / f"{environment}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def source_registry_sources() -> list[dict[str, object]]:
    registry = yaml.safe_load((ROOT / "platform" / "ingestion" / "source-registry.yaml").read_text(encoding="utf-8"))
    return [source for source in registry["sources"] if isinstance(source, dict)]


def p0_sources() -> list[dict[str, object]]:
    return [source for source in source_registry_sources() if source.get("priority") == "P0"]


def deep_update(target: dict[str, object], updates: dict[str, object]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_update(target[key], value)
        else:
            target[key] = value

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pyarrow as pa

from enterprise_dp.event_backbone_smoke import read_jsonl
from enterprise_dp.live_bronze_ingestion_smoke import (
    invalid_schema_record,
    write_live_bronze_ingestion_smoke_report,
)
from enterprise_dp.trino_sql_smoke import CommandResult


ROOT = Path(__file__).resolve().parents[1]


def test_live_bronze_ingestion_smoke_writes_bronze_iceberg_and_quarantine(
    tmp_path: Path,
) -> None:
    source_records = read_jsonl(ROOT / "samples" / "finance" / "benefit_settled.jsonl")[:1]
    valid = source_records[0]
    consumed = [
        {"partition": 0, "offset": 0, "record": valid},
        {"partition": 0, "offset": 1, "record": valid},
        {"partition": 0, "offset": 2, "record": invalid_schema_record(valid)},
    ]
    fake_catalog = FakeIcebergCatalog()
    fake_trino = FakeTrinoExecutor(fake_catalog)

    result = write_live_bronze_ingestion_smoke_report(
        ROOT,
        tmp_path / "live-bronze-ingestion-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="live-bronze-test",
        generated_at="2026-01-15T09:15:20Z",
        ingested_at="2026-01-15T09:15:05Z",
        source_records_override=source_records,
        consumed_records_override=consumed,
        pyiceberg_catalog_override=fake_catalog,
        trino_executor_override=fake_trino,
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    summary = report["summary"]

    assert report == result.report
    assert report["artifact_type"] == "live_bronze_ingestion_runtime_report.v1"
    assert report["passed"] is True
    assert report["runtime_scope"]["mode"] == "local_source_postgres_outbox_redpanda_to_bronze_iceberg_minio"
    assert "production_connector_ha" in report["runtime_scope"]["not_covered"]
    assert summary["source_record_count"] == 1
    assert summary["consumed_record_count"] == 3
    assert summary["approved_row_count"] == 1
    assert summary["duplicate_skipped_count"] == 1
    assert summary["quarantine_row_count"] == 1
    assert summary["trino_row_count"] == 1
    assert summary["snapshot_count_after"] == 2
    assert summary["restart_resume_passed"] is True
    assert summary["dlt_quarantine_passed"] is True
    assert summary["failed_check_count"] == 0
    assert report["bronze_probe"]["source_offset_max"] == 2
    assert report["restart_resume_probe"]["resume_from_offset"] == 3


def test_live_bronze_ingestion_smoke_fails_without_invalid_schema_quarantine(
    tmp_path: Path,
) -> None:
    source_records = read_jsonl(ROOT / "samples" / "finance" / "benefit_settled.jsonl")[:1]
    consumed = [{"partition": 0, "offset": 0, "record": source_records[0]}]
    fake_catalog = FakeIcebergCatalog()
    fake_trino = FakeTrinoExecutor(fake_catalog)

    result = write_live_bronze_ingestion_smoke_report(
        ROOT,
        tmp_path / "live-bronze-ingestion-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="live-bronze-fail",
        generated_at="2026-01-15T09:15:20Z",
        ingested_at="2026-01-15T09:15:05Z",
        source_records_override=source_records,
        consumed_records_override=consumed,
        pyiceberg_catalog_override=fake_catalog,
        trino_executor_override=fake_trino,
    )

    assert result.report["passed"] is False
    assert any(item["check"] == "invalid_schema_quarantine_or_dlt" for item in result.report["summary"]["failed_checks"])


class FakeTrinoExecutor:
    def __init__(self, catalog: "FakeIcebergCatalog") -> None:
        self.catalog = catalog

    def __call__(self, sql: str, step: str) -> CommandResult:
        if step == "create_live_bronze_iceberg_table":
            self.catalog.replace_table(("bronze_runtime_smoke", "events_benefit_settled"), [])
            return CommandResult(("fake",), 0, "", "")
        if step == "query_live_bronze_row_count":
            count = len(self.catalog.rows(("bronze_runtime_smoke", "events_benefit_settled")))
            return CommandResult(("fake",), 0, f'"{count}"\n', "")
        if step == "query_live_bronze_snapshots":
            count = len(self.catalog.load_table(("bronze_runtime_smoke", "events_benefit_settled")).snapshots())
            return CommandResult(("fake",), 0, f'"{count}"\n', "")
        if step == "query_live_bronze_files":
            return CommandResult(("fake",), 0, '"1"\n', "")
        raise AssertionError(f"unexpected Trino step: {step}")


class FakeIcebergCatalog:
    def __init__(self) -> None:
        self._tables: dict[tuple[str, str], FakeIcebergTableState] = {
            ("bronze_runtime_smoke", "events_benefit_settled"): FakeIcebergTableState(rows=[], version=1)
        }

    def replace_table(self, identifier: tuple[str, str], rows: list[dict[str, Any]]) -> None:
        self._tables[identifier] = FakeIcebergTableState(rows=list(rows), version=1)

    def load_table(self, identifier: tuple[str, str]) -> "FakeIcebergTable":
        state = self._tables[identifier]
        return FakeIcebergTable(state, loaded_version=state.version)

    def rows(self, identifier: tuple[str, str]) -> list[dict[str, Any]]:
        return list(self._tables[identifier].rows)


class FakeIcebergTableState:
    def __init__(self, *, rows: list[dict[str, Any]], version: int) -> None:
        self.rows = rows
        self.version = version


class FakeIcebergTable:
    def __init__(self, state: FakeIcebergTableState, *, loaded_version: int) -> None:
        self.state = state
        self.loaded_version = loaded_version
        self.metadata_location = f"s3://fake/metadata/{loaded_version}.metadata.json"

    def snapshots(self) -> list[object]:
        return [object() for _ in range(self.state.version)]

    def scan(self) -> "FakeScan":
        return FakeScan(self.state.rows)

    def append(self, table: pa.Table) -> None:
        self.state.rows.extend(table.to_pylist())
        self.state.version += 1


class FakeScan:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def to_arrow(self) -> pa.Table:
        if not self.rows:
            return pa.table({})
        return pa.Table.from_pylist(self.rows)

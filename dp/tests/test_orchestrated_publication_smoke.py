from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pyarrow as pa

from enterprise_dp.catalog import canonical_json
from enterprise_dp.event_backbone_smoke import read_jsonl
from enterprise_dp.orchestrated_publication_smoke import write_orchestrated_publication_smoke_report
from enterprise_dp.trino_sql_smoke import CommandResult


ROOT = Path(__file__).resolve().parents[1]


def test_orchestrated_publication_smoke_publishes_silver_gold_from_live_bronze(
    tmp_path: Path,
) -> None:
    bronze_events = read_jsonl(ROOT / "samples" / "finance" / "benefit_settled.jsonl")[:2]
    fake_catalog = FakeIcebergCatalog(bronze_rows=bronze_rows_from_events(bronze_events))
    fake_trino = FakeTrinoExecutor(fake_catalog)

    result = write_orchestrated_publication_smoke_report(
        ROOT,
        tmp_path / "orchestrated-publication-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="orchestrated-publication-test",
        generated_at="2026-01-15T09:15:20Z",
        live_bronze_report_override=live_bronze_report(),
        pyiceberg_catalog_override=fake_catalog,
        trino_executor_override=fake_trino,
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    summary = report["summary"]

    assert report == result.report
    assert report["artifact_type"] == "orchestrated_live_publication_report.v1"
    assert report["passed"] is True
    assert report["capability_ids"] == ["silver-gold-publication"]
    assert report["runtime_scope"]["mode"] == "local_dagster_in_process_bronze_iceberg_to_silver_gold_publication"
    assert "distributed_executor_or_kubernetes_run_launcher" in report["runtime_scope"]["not_covered"]
    assert summary["bronze_row_count"] == 2
    assert summary["silver_row_count"] == 2
    assert summary["gold_row_count"] == 2
    assert summary["trino_silver_row_count"] == 2
    assert summary["trino_gold_row_count"] == 2
    assert summary["promotion_passed"] is True
    assert summary["activation_passed"] is True
    assert summary["publication_ops_passed"] is True
    assert summary["active_pointer_drift_negative_test_passed"] is True
    assert summary["dagster_retry_event_count"] >= 1
    assert summary["asset_materialization_count"] >= 2
    assert summary["failed_check_count"] == 0


def test_orchestrated_publication_smoke_fails_without_bronze_rows(tmp_path: Path) -> None:
    fake_catalog = FakeIcebergCatalog(bronze_rows=[])
    fake_trino = FakeTrinoExecutor(fake_catalog)

    result = write_orchestrated_publication_smoke_report(
        ROOT,
        tmp_path / "orchestrated-publication-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="orchestrated-publication-empty-test",
        generated_at="2026-01-15T09:15:20Z",
        live_bronze_report_override=live_bronze_report(),
        pyiceberg_catalog_override=fake_catalog,
        trino_executor_override=fake_trino,
    )

    assert result.report["passed"] is False
    assert any(item["check"] == "dagster_publication_job_passed" for item in result.report["summary"]["failed_checks"])


def bronze_rows_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "payload_json": canonical_json(event),
            "payload_hash": f"sha256:test-{index}",
            "ingested_at": "2026-01-15T09:15:05Z",
        }
        for index, event in enumerate(events)
    ]


def live_bronze_report() -> dict[str, Any]:
    return {
        "artifact_type": "live_bronze_ingestion_runtime_report.v1",
        "generated_at": "2026-01-15T09:15:20Z",
        "passed": True,
        "summary": {
            "source_id": "enterprise-commerce-benefit-settled-outbox",
            "bronze_target": "bronze.events_benefit_settled",
            "iceberg_table": "iceberg.bronze_runtime_smoke.events_benefit_settled",
            "ingested_at": "2026-01-15T09:15:05Z",
            "live_bronze_iceberg_sink_passed": True,
            "restart_resume_passed": True,
            "dlt_quarantine_passed": True,
            "approved_row_count": 2,
            "duplicate_skipped_count": 1,
            "quarantine_row_count": 1,
        },
        "bronze_probe": {
            "offset_ledger": {
                "topic": "finance.benefit_settled.v1",
                "group_id": "enterprise-dp-live-bronze-ingestion",
                "partitions": [{"partition": 0, "committed_offset": 2}],
            }
        },
    }


class FakeTrinoExecutor:
    def __init__(self, catalog: "FakeIcebergCatalog") -> None:
        self.catalog = catalog

    def __call__(self, sql: str, step: str) -> CommandResult:
        if step == "create_live_silver_gold_iceberg_tables":
            self.catalog.replace_table(("publication_runtime_smoke", "finance_benefit_transactions"), [], version=0)
            self.catalog.replace_table(("publication_runtime_smoke", "finance_benefit_reconciliation"), [], version=0)
            return CommandResult(("fake",), 0, "", "")
        if step == "query_live_silver_row_count":
            return CommandResult(
                ("fake",),
                0,
                f'"{len(self.catalog.rows(("publication_runtime_smoke", "finance_benefit_transactions")))}"\n',
                "",
            )
        if step == "query_live_gold_row_count":
            return CommandResult(
                ("fake",),
                0,
                f'"{len(self.catalog.rows(("publication_runtime_smoke", "finance_benefit_reconciliation")))}"\n',
                "",
            )
        if step == "query_live_gold_snapshots":
            count = len(self.catalog.load_table(("publication_runtime_smoke", "finance_benefit_reconciliation")).snapshots())
            return CommandResult(("fake",), 0, f'"{count}"\n', "")
        if step == "query_live_gold_files":
            return CommandResult(("fake",), 0, '"1"\n', "")
        raise AssertionError(f"unexpected Trino step: {step}")


class FakeIcebergCatalog:
    def __init__(self, *, bronze_rows: list[dict[str, Any]]) -> None:
        self._tables: dict[tuple[str, str], FakeIcebergTableState] = {
            ("bronze_runtime_smoke", "events_benefit_settled"): FakeIcebergTableState(
                rows=list(bronze_rows),
                version=1 if bronze_rows else 0,
            )
        }

    def replace_table(self, identifier: tuple[str, str], rows: list[dict[str, Any]], *, version: int = 0) -> None:
        self._tables[identifier] = FakeIcebergTableState(rows=list(rows), version=version)

    def load_table(self, identifier: tuple[str, str]) -> "FakeIcebergTable":
        state = self._tables[identifier]
        return FakeIcebergTable(state, loaded_version=state.version)

    def rows(self, identifier: tuple[str, str]) -> list[dict[str, Any]]:
        return list(self._tables[identifier].rows)


class FakeIcebergTableState:
    def __init__(self, *, rows: list[dict[str, Any]], version: int) -> None:
        self.rows = rows
        self.version = version


class FakeSnapshot:
    def __init__(self, snapshot_id: int) -> None:
        self.snapshot_id = snapshot_id


class FakeIcebergTable:
    def __init__(self, state: FakeIcebergTableState, *, loaded_version: int) -> None:
        self.state = state
        self.loaded_version = loaded_version
        self.metadata_location = f"s3://fake/metadata/{loaded_version}.metadata.json"

    def snapshots(self) -> list[FakeSnapshot]:
        return [FakeSnapshot(index + 1) for index in range(self.state.version)]

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

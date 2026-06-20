from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pyarrow as pa

from enterprise_dp.catalog_compatibility_smoke import write_catalog_compatibility_smoke_report
from enterprise_dp.trino_sql_smoke import CommandResult


ROOT = Path(__file__).resolve().parents[1]


def test_catalog_cross_engine_smoke_proves_trino_pyiceberg_and_stale_commit_guard(
    tmp_path: Path,
) -> None:
    fake_catalog = FakeIcebergCatalog()
    fake_trino = FakeTrinoExecutor(fake_catalog)

    result = write_catalog_compatibility_smoke_report(
        ROOT,
        tmp_path / "catalog-cross-engine-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="catalog-cross-engine-test",
        generated_at="2026-01-15T09:15:20Z",
        pyiceberg_catalog_override=fake_catalog,
        trino_executor_override=fake_trino,
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    summary = report["summary"]

    assert report == result.report
    assert report["artifact_type"] == "catalog_cross_engine_smoke_report.v1"
    assert report["passed"] is True
    assert report["runtime_scope"]["mode"] == "local_trino_pyiceberg_jdbc_catalog_minio_cross_engine"
    assert "production_catalog_ha" in report["runtime_scope"]["not_covered"]
    assert summary["cross_engine_commit_compatibility_passed"] is True
    assert summary["catalog_concurrency_locking_passed"] is True
    assert summary["stale_commit_rejected"] is True
    assert summary["trino_initial_row_count"] == 2
    assert summary["pyiceberg_readback_row_count"] == 3
    assert summary["trino_read_after_pyiceberg_passed"] is True
    assert summary["snapshot_count_after_pyiceberg"] == 3
    assert summary["concurrency_snapshot_count_after"] == summary["concurrency_snapshot_count_before"] + 1
    assert summary["failed_check_count"] == 0
    assert report["cross_engine_probe"]["trino_readback_after_pyiceberg"] == [
        {"engine": "pyiceberg", "row_count": 1, "amount_sum": 300},
        {"engine": "trino", "row_count": 2, "amount_sum": 300},
    ]
    assert report["concurrency_probe"]["stale_commit_error"]["type"] == "RuntimeError"


def test_catalog_cross_engine_smoke_fails_when_trino_cannot_see_pyiceberg_commit(
    tmp_path: Path,
) -> None:
    fake_catalog = FakeIcebergCatalog()
    fake_trino = FakeTrinoExecutor(fake_catalog, hide_pyiceberg_rows=True)

    result = write_catalog_compatibility_smoke_report(
        ROOT,
        tmp_path / "catalog-cross-engine-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="catalog-cross-engine-fail",
        generated_at="2026-01-15T09:15:20Z",
        pyiceberg_catalog_override=fake_catalog,
        trino_executor_override=fake_trino,
    )

    assert result.report["passed"] is False
    assert result.report["summary"]["cross_engine_commit_compatibility_passed"] is False
    assert any(
        item["check"] == "cross_engine_commit_compatibility"
        for item in result.report["summary"]["failed_checks"]
    )


class FakeTrinoExecutor:
    def __init__(self, catalog: "FakeIcebergCatalog", *, hide_pyiceberg_rows: bool = False) -> None:
        self.catalog = catalog
        self.hide_pyiceberg_rows = hide_pyiceberg_rows

    def __call__(self, sql: str, step: str) -> CommandResult:
        if step == "show_catalogs":
            return CommandResult(("fake",), 0, '"iceberg"\n', "")
        if step in {"create_cross_engine_table_with_trino", "create_concurrency_table_with_trino"}:
            table = "catalog_cross_engine_probe" if "catalog_cross_engine_probe" in sql else "catalog_lock_probe"
            rows = (
                [
                    {"id": 1, "engine": "trino", "amount": 100},
                    {"id": 2, "engine": "trino", "amount": 200},
                ]
                if table == "catalog_cross_engine_probe"
                else [{"id": 1, "engine": "trino", "amount": 100}]
            )
            self.catalog.replace_table(("finance_iceberg_smoke", table), rows)
            return CommandResult(("fake",), 0, "", "")
        if step == "query_cross_engine_table_after_pyiceberg_append":
            rows = self.catalog.rows(("finance_iceberg_smoke", "catalog_cross_engine_probe"))
            if self.hide_pyiceberg_rows:
                rows = [row for row in rows if row["engine"] != "pyiceberg"]
            return CommandResult(("fake",), 0, aggregate_rows(rows), "")
        if step == "query_cross_engine_snapshots":
            count = len(self.catalog.load_table(("finance_iceberg_smoke", "catalog_cross_engine_probe")).snapshots())
            return CommandResult(("fake",), 0, f'"{count}"\n', "")
        raise AssertionError(f"unexpected Trino step: {step}")


def aggregate_rows(rows: list[dict[str, Any]]) -> str:
    by_engine: dict[str, dict[str, int]] = {}
    for row in rows:
        target = by_engine.setdefault(str(row["engine"]), {"row_count": 0, "amount_sum": 0})
        target["row_count"] += 1
        target["amount_sum"] += int(row["amount"])
    return "".join(
        f'"{engine}","{values["row_count"]}","{values["amount_sum"]}"\n'
        for engine, values in sorted(by_engine.items())
    )


class FakeIcebergCatalog:
    def __init__(self) -> None:
        self._tables: dict[tuple[str, str], FakeIcebergTableState] = {}

    def replace_table(self, identifier: tuple[str, str], rows: list[dict[str, Any]]) -> None:
        self._tables[identifier] = FakeIcebergTableState(rows=list(rows), version=2)

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
        if self.loaded_version != self.state.version:
            raise RuntimeError(
                f"Requirement failed: branch main has changed: expected id {self.loaded_version}, "
                f"found {self.state.version}"
            )
        self.state.rows.extend(table.to_pylist())
        self.state.version += 1


class FakeScan:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def to_arrow(self) -> pa.Table:
        return pa.table(
            {
                "id": [int(row["id"]) for row in self.rows],
                "engine": [str(row["engine"]) for row in self.rows],
                "amount": [int(row["amount"]) for row in self.rows],
            }
        )

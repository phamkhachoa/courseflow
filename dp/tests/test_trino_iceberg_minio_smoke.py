from __future__ import annotations

import json
from pathlib import Path

from botocore.exceptions import ClientError

from enterprise_dp.live_lakehouse_smoke import write_live_lakehouse_smoke_report
from enterprise_dp.trino_iceberg_minio_smoke import write_trino_iceberg_minio_smoke_report
from enterprise_dp.trino_sql_smoke import CommandResult


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-01-15T09:15:20Z"
QUERY_OUTPUT = (
    '"EXCEPTION","3","17000","16500","-500","-120"\n'
    '"MATCHED","1","8000","8000","0","0"\n'
)


def test_trino_iceberg_minio_smoke_creates_queries_and_verifies_minio_objects(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live" / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live" / "run",
        release_id="trino-iceberg-minio-test",
        generated_at=GENERATED_AT,
    )
    runner = FakeTrinoIcebergRunner()

    result = write_trino_iceberg_minio_smoke_report(
        ROOT,
        tmp_path / "trino-iceberg" / "trino-iceberg-minio-smoke-report.json",
        output_dir=tmp_path / "trino-iceberg" / "run",
        live_lakehouse_smoke_report_path=live.output_path,
        release_id="trino-iceberg-minio-test",
        generated_at=GENERATED_AT,
        command_runner=runner,
        wait_interval_seconds=0,
        s3_client_override=FakeIcebergS3(),
    )
    report = json.loads(result.output_path.read_text(encoding="utf-8"))

    assert report == result.report
    assert report["artifact_type"] == "trino_iceberg_minio_smoke_report.v1"
    assert report["passed"] is True
    assert report["runtime_scope"]["mode"] == "local_trino_iceberg_jdbc_catalog_minio_s3"
    assert "runtime_security_enforcement" in report["runtime_scope"]["not_covered"]
    assert report["summary"]["query_mode"] == "iceberg_jdbc_catalog_minio_s3"
    assert report["summary"]["row_count"] == 4
    assert report["summary"]["query_passed"] is True
    assert report["summary"]["snapshot_count"] == 2
    assert report["summary"]["iceberg_file_count"] == 1
    assert report["summary"]["minio_object_count"] == 3
    assert report["summary"]["minio_data_object_count"] == 1
    assert report["summary"]["minio_metadata_object_count"] == 2
    assert report["summary"]["minio_encrypted_object_count"] == 3
    assert report["summary"]["object_store_encryption_policy_enforced"] is True
    assert report["summary"]["trino_iceberg_objects_encrypted"] is True
    assert report["query_probe"]["result"] == report["expected_query_probe"]
    assert any("CREATE TABLE iceberg.finance_iceberg_smoke.finance_benefit_reconciliation" in sql for sql in runner.sql)


def test_trino_iceberg_minio_smoke_fails_when_catalog_is_unavailable(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live" / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live" / "run",
        release_id="trino-iceberg-minio-fail",
        generated_at=GENERATED_AT,
    )

    result = write_trino_iceberg_minio_smoke_report(
        ROOT,
        tmp_path / "trino-iceberg" / "trino-iceberg-minio-smoke-report.json",
        output_dir=tmp_path / "trino-iceberg" / "run",
        live_lakehouse_smoke_report_path=live.output_path,
        release_id="trino-iceberg-minio-fail",
        generated_at=GENERATED_AT,
        command_runner=CatalogUnavailableRunner(),
        wait_attempts=1,
        wait_interval_seconds=0,
        s3_client_override=FakeIcebergS3(),
    )

    assert result.report["passed"] is False
    assert result.report["summary"]["failed_check_count"] >= 1
    assert any(item["check"] == "trino_iceberg_minio_runtime_command" for item in result.report["summary"]["failed_checks"])
    assert result.output_path.is_file()


class FakeTrinoIcebergRunner:
    def __init__(self) -> None:
        self.sql: list[str] = []

    def __call__(self, args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        if "up" in args:
            return CommandResult(tuple(args), 0, "started", "")
        if "psql" in args:
            assert input_text and "CREATE TABLE IF NOT EXISTS iceberg_tables" in input_text
            return CommandResult(tuple(args), 0, "CREATE TABLE\nCREATE TABLE\n", "")
        sql = args[-1]
        self.sql.append(sql)
        if sql == "SELECT 1":
            return CommandResult(tuple(args), 0, '"1"\n', "")
        if sql == "SHOW CATALOGS":
            return CommandResult(tuple(args), 0, '"iceberg"\n"memory"\n', "")
        if "CREATE TABLE iceberg.finance_iceberg_smoke.finance_benefit_reconciliation" in sql:
            return CommandResult(tuple(args), 0, "DROP TABLE\nCREATE SCHEMA\nCREATE TABLE\nINSERT: 4 rows\n", "")
        if "GROUP BY reconciliation_status" in sql:
            return CommandResult(tuple(args), 0, QUERY_OUTPUT, "")
        if "$snapshots" in sql:
            return CommandResult(tuple(args), 0, '"2"\n', "")
        if "$files" in sql:
            return CommandResult(tuple(args), 0, '"1"\n', "")
        raise AssertionError(f"unexpected command: {args}")


class CatalogUnavailableRunner(FakeTrinoIcebergRunner):
    def __call__(self, args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        if "up" in args or "psql" in args:
            return super().__call__(args, input_text, cwd, timeout_seconds)
        sql = args[-1]
        if sql == "SELECT 1":
            return CommandResult(tuple(args), 0, '"1"\n', "")
        if sql == "SHOW CATALOGS":
            return CommandResult(tuple(args), 0, '"memory"\n', "")
        return CommandResult(tuple(args), 1, "", "Catalog iceberg does not exist")


class FakeIcebergS3:
    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.encryption: dict[str, dict] = {}
        self.policy_enabled: dict[str, bool] = {}
        self.objects: dict[tuple[str, str], dict] = {}

    def head_bucket(self, *, Bucket: str) -> dict:
        if Bucket not in self.buckets:
            raise Exception("NoSuchBucket")
        return {}

    def create_bucket(self, *, Bucket: str) -> dict:
        self.buckets.add(Bucket)
        return {}

    def put_bucket_encryption(self, *, Bucket: str, ServerSideEncryptionConfiguration: dict) -> dict:
        assert Bucket in self.buckets
        self.encryption[Bucket] = ServerSideEncryptionConfiguration
        return {}

    def get_bucket_encryption(self, *, Bucket: str) -> dict:
        assert Bucket in self.buckets
        return {"ServerSideEncryptionConfiguration": self.encryption[Bucket]}

    def put_bucket_policy(self, *, Bucket: str, Policy: str) -> dict:
        assert Bucket in self.buckets
        self.policy_enabled[Bucket] = True
        self.objects[(Bucket, "warehouse/finance_iceberg_smoke/finance_benefit_reconciliation/data/00000.parquet")] = {
            "Size": 991,
            "ServerSideEncryption": "AES256",
        }
        self.objects[(Bucket, "warehouse/finance_iceberg_smoke/finance_benefit_reconciliation/metadata/00000.metadata.json")] = {
            "Size": 2500,
            "ServerSideEncryption": "AES256",
        }
        self.objects[(Bucket, "warehouse/finance_iceberg_smoke/finance_benefit_reconciliation/metadata/snap-1.avro")] = {
            "Size": 1200,
            "ServerSideEncryption": "AES256",
        }
        return {}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ServerSideEncryption: str | None = None) -> dict:
        assert Bucket in self.buckets
        if self.policy_enabled.get(Bucket) and ServerSideEncryption != "AES256":
            raise ClientError(
                {"Error": {"Code": "AccessDenied"}, "ResponseMetadata": {"HTTPStatusCode": 403}},
                "PutObject",
            )
        self.objects[(Bucket, Key)] = {
            "Size": len(Body),
            "ServerSideEncryption": ServerSideEncryption,
        }
        return {}

    def head_object(self, *, Bucket: str, Key: str) -> dict:
        item = self.objects[(Bucket, Key)]
        return {
            "ContentLength": item["Size"],
            "ServerSideEncryption": item.get("ServerSideEncryption"),
        }

    def list_objects_v2(self, *, Bucket: str, Prefix: str) -> dict:
        assert Bucket in self.buckets
        contents = [
            {"Key": key, "Size": item["Size"]}
            for (object_bucket, key), item in sorted(self.objects.items())
            if object_bucket == Bucket and key.startswith(Prefix)
        ]
        return {
            "KeyCount": len(contents),
            "Contents": contents,
        }

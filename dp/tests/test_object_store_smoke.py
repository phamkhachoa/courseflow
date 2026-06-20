from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

from botocore.exceptions import ClientError

from enterprise_dp.live_lakehouse_smoke import write_live_lakehouse_smoke_report
from enterprise_dp.object_store_smoke import write_object_store_commit_smoke_report


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-01-15T09:15:20Z"


def test_object_store_commit_smoke_uploads_and_reads_back_parquet(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live" / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live" / "run",
        release_id="object-store-smoke-test",
        generated_at=GENERATED_AT,
    )
    fake_s3 = FakeS3(tmp_path / "fake-s3")

    result = write_object_store_commit_smoke_report(
        ROOT,
        tmp_path / "object-store" / "object-store-commit-smoke-report.json",
        output_dir=tmp_path / "object-store" / "run",
        live_lakehouse_smoke_report_path=live.output_path,
        bucket="enterprise-dp-test",
        endpoint_url="http://fake-minio.local",
        release_id="object-store-smoke-test",
        generated_at=GENERATED_AT,
        s3_client_override=fake_s3,
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))

    assert report == result.report
    assert report["artifact_type"] == "object_store_commit_smoke_report.v1"
    assert report["passed"] is True
    assert report["runtime_scope"]["mode"] == "local_minio_s3_parquet_commit"
    assert "iceberg_catalog_commit" in report["runtime_scope"]["not_covered"]
    assert report["object_store"]["bucket"] == "enterprise-dp-test"
    assert report["summary"]["object_count"] == 3
    assert report["summary"]["uploaded_object_count"] == 3
    assert report["summary"]["readback_passed_count"] == 3
    assert report["summary"]["encrypted_object_count"] == 3
    assert report["summary"]["encryption_policy_enforced"] is True
    assert report["summary"]["unencrypted_put_denied"] is True
    assert report["summary"]["encrypted_put_allowed"] is True
    assert report["summary"]["sse_algorithm"] == "AES256"
    gold = next(item for item in report["object_commits"] if item["data_product"] == "gold.finance_benefit_reconciliation")
    assert gold["s3_uri"].startswith("s3://enterprise-dp-test/")
    assert gold["readback_passed"] is True
    assert gold["row_count"] == 4
    assert gold["metadata"]["data-product"] == "gold.finance_benefit_reconciliation"
    assert gold["server_side_encryption"] == "AES256"


def test_object_store_commit_smoke_cli_requires_live_minio(tmp_path: Path) -> None:
    output = tmp_path / "object-store" / "report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "object-store-commit-smoke",
            "--root",
            str(ROOT),
            "--output-dir",
            str(tmp_path / "run"),
            "--output",
            str(output),
            "--endpoint-url",
            "http://127.0.0.1:1",
            "--generated-at",
            GENERATED_AT,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert not output.exists()


class FakeS3:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.buckets: set[str] = set()
        self.metadata: dict[tuple[str, str], dict[str, str]] = {}
        self.sse: dict[tuple[str, str], str | None] = {}
        self.encryption: dict[str, dict] = {}
        self.policy_enabled: dict[str, bool] = {}

    def head_bucket(self, *, Bucket: str) -> dict:
        if Bucket not in self.buckets:
            raise Exception("NoSuchBucket")
        return {}

    def create_bucket(self, *, Bucket: str) -> dict:
        self.buckets.add(Bucket)
        (self.root / Bucket).mkdir(parents=True, exist_ok=True)
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
        return {}

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ServerSideEncryption: str | None = None,
        Metadata: dict | None = None,
    ) -> dict:
        assert Bucket in self.buckets
        if self.policy_enabled.get(Bucket) and ServerSideEncryption != "AES256":
            raise ClientError(
                {"Error": {"Code": "AccessDenied"}, "ResponseMetadata": {"HTTPStatusCode": 403}},
                "PutObject",
            )
        target = self.root / Bucket / Key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Body)
        self.metadata[(Bucket, Key)] = dict(Metadata or {})
        self.sse[(Bucket, Key)] = ServerSideEncryption
        return {}

    def upload_file(self, Filename: str, Bucket: str, Key: str, ExtraArgs: dict | None = None) -> None:
        assert Bucket in self.buckets
        if self.policy_enabled.get(Bucket) and (ExtraArgs or {}).get("ServerSideEncryption") != "AES256":
            raise ClientError(
                {"Error": {"Code": "AccessDenied"}, "ResponseMetadata": {"HTTPStatusCode": 403}},
                "PutObject",
            )
        target = self.root / Bucket / Key
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Filename, target)
        self.metadata[(Bucket, Key)] = dict((ExtraArgs or {}).get("Metadata", {}))
        self.sse[(Bucket, Key)] = (ExtraArgs or {}).get("ServerSideEncryption")

    def head_object(self, *, Bucket: str, Key: str) -> dict:
        path = self.root / Bucket / Key
        data = path.read_bytes()
        return {
            "ETag": f'"fake-{len(data)}"',
            "ContentLength": len(data),
            "Metadata": self.metadata.get((Bucket, Key), {}),
            "ServerSideEncryption": self.sse.get((Bucket, Key)),
        }

    def download_file(self, Bucket: str, Key: str, Filename: str) -> None:
        source = self.root / Bucket / Key
        target = Path(Filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

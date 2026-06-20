from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import pyarrow as pa
import pyarrow.parquet as pq

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.event_backbone_smoke import CommandRunner, resolve_compose_path, run_command
from enterprise_dp.live_lakehouse_smoke import (
    DEFAULT_EVALUATION_TIME,
    DEFAULT_FINANCE_SCHEMA_ID,
    DEFAULT_GENERATED_AT,
    DEFAULT_INGESTED_AT,
    DEFAULT_BUILT_AT,
    DEFAULT_SNAPSHOT_ID,
    write_live_lakehouse_smoke_report,
)


DEFAULT_BUCKET = "enterprise-dp-local-lakehouse"
DEFAULT_ENDPOINT_URL = "http://localhost:19000"
DEFAULT_ACCESS_KEY = "enterprise_dp_local"
DEFAULT_SECRET_KEY = "enterprise_dp_local_only_change_me"
DEFAULT_SSE_ALGORITHM = "AES256"
DEFAULT_MINIO_SERVICE = "minio"
DEFAULT_PROBE_ACCESS_KEY = "dp_sse_probe"
DEFAULT_PROBE_SECRET_KEY = "dp_sse_probe_secret_change_me"


@dataclass(frozen=True)
class ObjectStoreCommitSmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_object_store_commit_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    live_lakehouse_smoke_report_path: str | Path | None = None,
    bucket: str = DEFAULT_BUCKET,
    endpoint_url: str = DEFAULT_ENDPOINT_URL,
    access_key: str = DEFAULT_ACCESS_KEY,
    secret_key: str = DEFAULT_SECRET_KEY,
    region_name: str = "us-east-1",
    sse_algorithm: str = DEFAULT_SSE_ALGORITHM,
    compose_file: str | Path | None = None,
    minio_service: str = DEFAULT_MINIO_SERVICE,
    probe_access_key: str = DEFAULT_PROBE_ACCESS_KEY,
    probe_secret_key: str = DEFAULT_PROBE_SECRET_KEY,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 60,
    use_case_id: str = "finance-benefit-reconciliation",
    release_id: str = "local-object-store-commit-smoke",
    environment: str = "local",
    generated_at: str | None = None,
    s3_client_override: Any | None = None,
) -> ObjectStoreCommitSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    generated = generated_at or DEFAULT_GENERATED_AT
    if live_lakehouse_smoke_report_path:
        live_report_path = Path(live_lakehouse_smoke_report_path)
        live_report = load_json(live_report_path)
    else:
        live_result = write_live_lakehouse_smoke_report(
            platform_root,
            target_dir / "live-lakehouse-smoke-report.json",
            output_dir=target_dir / "live-lakehouse-run",
            use_case_id=use_case_id,
            release_id=release_id,
            environment=environment,
            generated_at=generated,
            ingested_at=DEFAULT_INGESTED_AT,
            built_at=DEFAULT_BUILT_AT,
            evaluation_time=DEFAULT_EVALUATION_TIME,
            schema_id=DEFAULT_FINANCE_SCHEMA_ID,
            snapshot_id=DEFAULT_SNAPSHOT_ID,
        )
        live_report_path = live_result.output_path
        live_report = live_result.report

    client = s3_client_override or s3_client(
        endpoint_url=endpoint_url,
        access_key=access_key,
        secret_key=secret_key,
        region_name=region_name,
    )
    compose_path = resolve_compose_path(platform_root, compose_file)
    runner = command_runner or run_command
    object_prefix = f"{environment}/{release_id}"
    minio_admin_setup = {"configured": False, "skipped": True, "steps": []}
    probe_client = client
    if s3_client_override is None:
        minio_admin_setup = configure_minio_probe_user(
            runner,
            platform_root=platform_root,
            compose_path=compose_path,
            minio_service=minio_service,
            root_access_key=access_key,
            root_secret_key=secret_key,
            bucket=bucket,
            prefix=object_prefix,
            sse_algorithm=sse_algorithm,
            probe_access_key=probe_access_key,
            probe_secret_key=probe_secret_key,
            command_timeout_seconds=command_timeout_seconds,
        )
        probe_client = s3_client(
            endpoint_url=endpoint_url,
            access_key=probe_access_key,
            secret_key=probe_secret_key,
            region_name=region_name,
        )
    encryption_policy = configure_bucket_encryption_policy(
        client,
        bucket=bucket,
        prefix=object_prefix,
        sse_algorithm=sse_algorithm,
        probe_client=probe_client,
    )
    bucket_created = encryption_policy.get("bucket_created") is True
    object_commits = [
        upload_and_verify_commit(
            client,
            bucket=bucket,
            commit=commit,
            download_dir=target_dir / "downloads",
            prefix=object_prefix,
            sse_algorithm=sse_algorithm,
        )
        for commit in live_report.get("table_commits", [])
        if isinstance(commit, dict)
    ]
    failed_checks = failed_object_store_checks(live_report, object_commits, encryption_policy)
    report = {
        "artifact_type": "object_store_commit_smoke_report.v1",
        "report_version": 1,
        "capability_id": "bronze-lakehouse-evidence",
        "report_id": f"object-store-commit-smoke:{environment}:{use_case_id}:{release_id}",
        "generated_at": generated,
        "environment": environment,
        "release_id": release_id,
        "use_case_id": use_case_id,
        "runtime_scope": {
            "mode": "local_minio_s3_parquet_commit",
            "covered": [
                "minio_s3_bucket_created_or_reused",
                "bronze_silver_gold_parquet_uploaded_to_object_store",
                "s3_head_object_metadata_verified",
                "s3_download_readback_verified_with_pyarrow",
                "local_file_hash_bound_to_object_metadata",
            ],
            "not_covered": [
                "iceberg_catalog_commit",
                "trino_or_dremio_remote_query_runtime",
                "dagster_or_airflow_run_history",
                "runtime_security_enforcement",
                "production_kms_key_rotation",
                "cloud_provider_bucket_policy_attestation",
                "cross_account_object_store_access_policy",
            ],
        },
        "object_store": {
            "provider": "minio",
            "endpoint_url": endpoint_url,
            "bucket": bucket,
            "bucket_created": bucket_created,
        },
        "minio_admin_setup": minio_admin_setup,
        "encryption_policy": encryption_policy,
        "live_lakehouse_smoke": {
            "path": live_report_path.as_posix(),
            "hash": hash_file(live_report_path),
            "passed": live_report.get("passed") is True,
        },
        "object_commits": object_commits,
        "summary": {
            "object_count": len(object_commits),
            "uploaded_object_count": sum(1 for item in object_commits if item.get("uploaded") is True),
            "readback_passed_count": sum(1 for item in object_commits if item.get("readback_passed") is True),
            "encrypted_object_count": sum(
                1 for item in object_commits if item.get("server_side_encryption") == sse_algorithm
            ),
            "encryption_policy_enforced": encryption_policy.get("passed") is True,
            "unencrypted_put_denied": encryption_policy.get("unencrypted_put_denied") is True,
            "encrypted_put_allowed": encryption_policy.get("encrypted_put_allowed") is True,
            "sse_algorithm": sse_algorithm,
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        },
    }
    report["passed"] = not failed_checks
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return ObjectStoreCommitSmokeResult(output_path=target, report=report)


def upload_and_verify_commit(
    client: Any,
    *,
    bucket: str,
    commit: dict[str, Any],
    download_dir: Path,
    prefix: str,
    sse_algorithm: str,
) -> dict[str, Any]:
    data_product = str(commit.get("data_product"))
    parquet_path = Path(str(commit.get("parquet_path")))
    object_key = f"{prefix}/{data_product.replace('.', '/')}/{parquet_path.name}"
    local_hash = hash_file(parquet_path)
    client.upload_file(
        parquet_path.as_posix(),
        bucket,
        object_key,
        ExtraArgs={
            "ServerSideEncryption": sse_algorithm,
            "Metadata": {
                "data-product": data_product,
                "snapshot-id": str(commit.get("snapshot_id")),
                "local-sha256": local_hash.removeprefix("sha256:"),
            }
        },
    )
    head = client.head_object(Bucket=bucket, Key=object_key)
    download_path = download_dir / object_key
    download_path.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(bucket, object_key, download_path.as_posix())
    local_table = pq.read_table(parquet_path)
    downloaded_table = pq.read_table(download_path)
    download_hash = hash_file(download_path)
    readback_passed = (
        download_hash == local_hash
        and downloaded_table.num_rows == local_table.num_rows == commit.get("row_count")
        and downloaded_table.schema.equals(local_table.schema)
    )
    return {
        "data_product": data_product,
        "bucket": bucket,
        "key": object_key,
        "s3_uri": f"s3://{bucket}/{object_key}",
        "uploaded": True,
        "etag": str(head.get("ETag", "")).strip('"'),
        "content_length": head.get("ContentLength"),
        "metadata": head.get("Metadata", {}),
        "server_side_encryption": head.get("ServerSideEncryption"),
        "local_parquet_path": parquet_path.as_posix(),
        "local_parquet_hash": local_hash,
        "download_path": download_path.as_posix(),
        "download_hash": download_hash,
        "row_count": local_table.num_rows,
        "column_count": local_table.num_columns,
        "schema_fingerprint": schema_fingerprint(local_table.schema),
        "readback_passed": readback_passed,
        "passed": (
            readback_passed
            and head.get("ContentLength") == parquet_path.stat().st_size
            and head.get("ServerSideEncryption") == sse_algorithm
        ),
    }


def failed_object_store_checks(
    live_report: dict[str, Any],
    object_commits: list[dict[str, Any]],
    encryption_policy: dict[str, Any],
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if live_report.get("passed") is not True:
        failed.append({"check": "live_lakehouse_smoke_passed", "passed": live_report.get("passed")})
    if not object_commits:
        failed.append({"check": "object_commits_present"})
    if encryption_policy.get("passed") is not True:
        failed.append(
            {
                "check": "object_store_encryption_policy_enforced",
                "unencrypted_put_denied": encryption_policy.get("unencrypted_put_denied"),
                "encrypted_put_allowed": encryption_policy.get("encrypted_put_allowed"),
                "encrypted_head_sse": encryption_policy.get("encrypted_head_sse"),
                "errors": encryption_policy.get("errors", []),
            }
        )
    for commit in object_commits:
        if commit.get("passed") is not True:
            failed.append(
                {
                    "check": "object_store_commit",
                    "data_product": commit.get("data_product"),
                    "readback_passed": commit.get("readback_passed"),
                    "server_side_encryption": commit.get("server_side_encryption"),
                }
            )
    return failed


def configure_bucket_encryption_policy(
    client: Any,
    *,
    bucket: str,
    prefix: str,
    sse_algorithm: str = DEFAULT_SSE_ALGORITHM,
    probe_client: Any | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    bucket_created = ensure_bucket(client, bucket)
    encryption_config = {
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": sse_algorithm,
                }
            }
        ]
    }
    try:
        client.put_bucket_encryption(
            Bucket=bucket,
            ServerSideEncryptionConfiguration=encryption_config,
        )
        configured = True
    except Exception as exc:
        configured = False
        errors.append(f"put_bucket_encryption:{type(exc).__name__}:{exc}")
    try:
        readback = client.get_bucket_encryption(Bucket=bucket).get("ServerSideEncryptionConfiguration")
    except Exception as exc:
        readback = None
        errors.append(f"get_bucket_encryption:{type(exc).__name__}:{exc}")
    policy = bucket_encryption_policy(bucket=bucket, prefix=prefix, sse_algorithm=sse_algorithm)
    try:
        client.put_bucket_policy(Bucket=bucket, Policy=canonical_json(policy))
        policy_applied = True
    except Exception as exc:
        policy_applied = False
        errors.append(f"put_bucket_policy:{type(exc).__name__}:{exc}")
    policy_probe_client = probe_client or client
    probe = verify_bucket_encryption_policy(policy_probe_client, bucket=bucket, prefix=prefix, sse_algorithm=sse_algorithm)
    errors.extend(probe.get("errors", []))
    return {
        "mode": "local_minio_sse_s3_bucket_policy",
        "sse_algorithm": sse_algorithm,
        "prefix": prefix,
        "bucket_created": bucket_created,
        "bucket_default_encryption_configured": configured,
        "bucket_default_encryption_readback": readback,
        "bucket_policy_applied": policy_applied,
        "bucket_policy": policy,
        **probe,
        "errors": errors,
        "passed": (
            configured
            and readback is not None
            and policy_applied
            and probe.get("unencrypted_put_denied") is True
            and probe.get("encrypted_put_allowed") is True
            and probe.get("encrypted_head_sse") == sse_algorithm
        ),
    }


def configure_minio_probe_user(
    runner: CommandRunner,
    *,
    platform_root: Path,
    compose_path: Path,
    minio_service: str,
    root_access_key: str,
    root_secret_key: str,
    bucket: str,
    prefix: str,
    sse_algorithm: str,
    probe_access_key: str,
    probe_secret_key: str,
    command_timeout_seconds: int,
) -> dict[str, Any]:
    policy_name = "dp-sse-probe-policy"
    policy_path = "/tmp/dp-sse-probe-policy.json"
    alias = "local"
    policy = probe_user_policy(bucket=bucket, prefix=prefix, sse_algorithm=sse_algorithm)
    steps: list[dict[str, Any]] = []

    def run_step(step: str, extra: list[str], input_text: str | None = None, raise_on_error: bool = True) -> None:
        args = ["docker", "compose", "-f", compose_path.as_posix(), "exec", "-T", minio_service, *extra]
        result = runner(args, input_text, platform_root, command_timeout_seconds)
        steps.append(
            {
                "step": step,
                "returncode": result.returncode,
                "stdout_preview": result.stdout[:300],
                "stderr_preview": result.stderr[:300],
            }
        )
        if raise_on_error and result.returncode != 0:
            detail = result.stderr[:500] or result.stdout[:500]
            raise RuntimeError(f"{step} failed with exit code {result.returncode}: {detail}")

    run_step("minio_alias_set", ["mc", "alias", "set", alias, "http://localhost:9000", root_access_key, root_secret_key])
    run_step("minio_probe_user_remove_existing", ["mc", "admin", "user", "rm", alias, probe_access_key], raise_on_error=False)
    run_step("minio_probe_policy_remove_existing", ["mc", "admin", "policy", "rm", alias, policy_name], raise_on_error=False)
    run_step("minio_probe_user_add", ["mc", "admin", "user", "add", alias, probe_access_key, probe_secret_key])
    run_step("minio_probe_policy_file_write", ["sh", "-lc", f"cat > {policy_path}"], canonical_json(policy))
    run_step("minio_probe_policy_create", ["mc", "admin", "policy", "create", alias, policy_name, policy_path])
    run_step("minio_probe_policy_attach", ["mc", "admin", "policy", "attach", alias, policy_name, "--user", probe_access_key])
    return {
        "configured": True,
        "skipped": False,
        "probe_access_key": probe_access_key,
        "policy_name": policy_name,
        "policy": policy,
        "steps": steps,
    }


def probe_user_policy(*, bucket: str, prefix: str, sse_algorithm: str) -> dict[str, Any]:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Action": ["s3:PutObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/{prefix}/*"],
                "Condition": {
                    "StringNotEquals": {
                        "s3:x-amz-server-side-encryption": sse_algorithm,
                    }
                },
            },
            {
                "Effect": "Deny",
                "Action": ["s3:PutObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/{prefix}/*"],
                "Condition": {
                    "Null": {
                        "s3:x-amz-server-side-encryption": "true",
                    }
                },
            },
            {
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/{prefix}/*"],
            },
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{bucket}"],
                "Condition": {"StringLike": {"s3:prefix": [f"{prefix}/*"]}},
            },
        ],
    }


def bucket_encryption_policy(*, bucket: str, prefix: str, sse_algorithm: str) -> dict[str, Any]:
    resource = f"arn:aws:s3:::{bucket}/{prefix}/*"
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DenyIncorrectServerSideEncryptionHeader",
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:PutObject",
                "Resource": resource,
                "Condition": {
                    "StringNotEquals": {
                        "s3:x-amz-server-side-encryption": sse_algorithm,
                    }
                },
            },
            {
                "Sid": "DenyMissingServerSideEncryptionHeader",
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:PutObject",
                "Resource": resource,
                "Condition": {
                    "Null": {
                        "s3:x-amz-server-side-encryption": "true",
                    }
                },
            },
        ],
    }


def verify_bucket_encryption_policy(
    client: Any,
    *,
    bucket: str,
    prefix: str,
    sse_algorithm: str,
) -> dict[str, Any]:
    unencrypted_key = f"{prefix}/_encryption_policy_probe/unencrypted.txt"
    encrypted_key = f"{prefix}/_encryption_policy_probe/encrypted.txt"
    errors: list[str] = []
    try:
        client.put_object(Bucket=bucket, Key=unencrypted_key, Body=b"deny")
        unencrypted_put_denied = False
    except Exception as exc:
        unencrypted_put_denied = object_put_was_denied(exc)
        if not unencrypted_put_denied:
            errors.append(f"unencrypted_put:{type(exc).__name__}:{exc}")
    try:
        client.put_object(
            Bucket=bucket,
            Key=encrypted_key,
            Body=b"allow",
            ServerSideEncryption=sse_algorithm,
        )
        encrypted_head = client.head_object(Bucket=bucket, Key=encrypted_key)
        encrypted_put_allowed = True
        encrypted_head_sse = encrypted_head.get("ServerSideEncryption")
    except Exception as exc:
        encrypted_put_allowed = False
        encrypted_head_sse = None
        errors.append(f"encrypted_put:{type(exc).__name__}:{exc}")
    return {
        "unencrypted_probe_key": unencrypted_key,
        "encrypted_probe_key": encrypted_key,
        "unencrypted_put_denied": unencrypted_put_denied,
        "encrypted_put_allowed": encrypted_put_allowed,
        "encrypted_head_sse": encrypted_head_sse,
        "errors": errors,
    }


def object_put_was_denied(exc: Exception) -> bool:
    if isinstance(exc, ClientError):
        error = exc.response.get("Error", {})
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        return status == 403 or str(error.get("Code", "")).lower() in {"accessdenied", "access denied"}
    return "accessdenied" in str(exc).replace(" ", "").lower()


def ensure_bucket(client: Any, bucket: str) -> bool:
    try:
        client.head_bucket(Bucket=bucket)
        return False
    except ClientError as exc:
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        error_code = exc.response.get("Error", {}).get("Code")
        if status_code not in {301, 403, 404} and error_code not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        client.create_bucket(Bucket=bucket)
        return True
    except Exception:
        # Test doubles and some S3-compatible clients use plain exceptions for missing buckets.
        client.create_bucket(Bucket=bucket)
        return True


def s3_client(*, endpoint_url: str, access_key: str, secret_key: str, region_name: str) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region_name,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def schema_fingerprint(schema: pa.Schema) -> str:
    return f"sha256:{hashlib.sha256(str(schema).encode('utf-8')).hexdigest()}"


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import yaml

from enterprise_df.source_readiness_bundle import run_source_readiness_bundle
from enterprise_df.source_activation_ledger import write_source_activation_manifest_from_bundle, write_source_revocation_manifest


ROOT = Path(__file__).resolve().parents[1]
BILLING_SOURCE_ID = "billing-platform-billing-transaction-settled-outbox"
BILLING_SAMPLE = ROOT / "samples" / "billing" / "billing_transaction_settled.jsonl"
GENERATED_AT = "2026-01-18T10:00:00Z"
ACTIVATED_AT = "2026-01-18T11:00:00Z"
EXPIRES_AT = "2026-07-18T11:00:00Z"
AS_OF = "2026-06-16T12:00:00Z"
INGESTED_AT = "2026-01-18T10:01:00Z"
REPLAYED_AT = "2026-01-18T10:05:00Z"
BILLING_SNAPSHOT_ID = "iceberg-snapshot-billing-transaction-settled-0001"
BILLING_METADATA_URI = "s3://df-staging-lakehouse/warehouse/bronze/events_billing_transaction_settled/metadata/00001.metadata.json"
BILLING_METADATA_HASH = "sha256:2222222222222222222222222222222222222222222222222222222222222222"


def test_source_activation_ops_report_active_ok_returns_zero(tmp_path: Path) -> None:
    ledger_path, pointer_dir = activate_billing_source(tmp_path)
    output_path = tmp_path / "ops" / "source-activation-ops.json"

    completed = run_ops_cli(ledger_path, pointer_dir, output_path, as_of=AS_OF)

    assert completed.returncode == 0, completed.stderr
    report = json.loads(output_path.read_text(encoding="utf-8"))
    billing = source_row(report)
    assert report["passed"] is True
    assert billing["activation_state"] == "active"
    assert billing["effective_status"] == "production_ready"
    assert billing["block_reason"] is None
    assert billing["risk_state"] == "ok"


def test_source_activation_ops_report_expiring_soon_warns_but_returns_zero(tmp_path: Path) -> None:
    ledger_path, pointer_dir = activate_billing_source(tmp_path, expires_at="2026-06-20T11:00:00Z")
    output_path = tmp_path / "ops" / "source-activation-ops.json"

    completed = run_ops_cli(ledger_path, pointer_dir, output_path, as_of=AS_OF, expiring_within_days=30)

    assert completed.returncode == 0, completed.stderr
    report = json.loads(output_path.read_text(encoding="utf-8"))
    billing = source_row(report)
    assert billing["risk_state"] == "expiring_soon"
    assert billing["days_to_expiry"] == 4
    assert report["summary"]["expiring_soon_count"] == 1


def test_source_activation_ops_report_expired_returns_nonzero(tmp_path: Path) -> None:
    ledger_path, pointer_dir = activate_billing_source(tmp_path, expires_at="2026-02-18T11:00:00Z")
    output_path = tmp_path / "ops" / "source-activation-ops.json"

    completed = run_ops_cli(ledger_path, pointer_dir, output_path, as_of=AS_OF)

    assert completed.returncode == 1
    billing = source_row(json.loads(output_path.read_text(encoding="utf-8")))
    assert billing["risk_state"] == "activation_expired"
    assert billing["block_reason"] == "activation_expired"


def test_source_activation_ops_report_registry_hash_drift_returns_nonzero(tmp_path: Path) -> None:
    ledger_path, pointer_dir = activate_billing_source(tmp_path)
    mutate_first_activation(ledger_path, {"sourceRegistryHash": "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"})
    output_path = tmp_path / "ops" / "source-activation-ops.json"

    completed = run_ops_cli(ledger_path, pointer_dir, output_path, as_of=AS_OF)

    assert completed.returncode == 1
    billing = source_row(json.loads(output_path.read_text(encoding="utf-8")))
    assert billing["risk_state"] == "source_registry_hash_mismatch"
    assert billing["block_reason"] == "source_registry_hash_mismatch"


def test_source_activation_ops_report_missing_pointer_returns_nonzero(tmp_path: Path) -> None:
    ledger_path, pointer_dir = activate_billing_source(tmp_path)
    for path in pointer_dir.glob("*.json"):
        path.unlink()
    output_path = tmp_path / "ops" / "source-activation-ops.json"

    completed = run_ops_cli(ledger_path, pointer_dir, output_path, as_of=AS_OF)

    assert completed.returncode == 1
    billing = source_row(json.loads(output_path.read_text(encoding="utf-8")))
    assert billing["risk_state"] == "active_pointer_missing"
    assert "active_pointer_missing" in billing["issues"]


def test_source_activation_ops_report_revoked_returns_nonzero(tmp_path: Path) -> None:
    ledger_path, pointer_dir = activate_billing_source(tmp_path)
    pointer_path = next(pointer_dir.glob("*.json"))
    write_source_revocation_manifest(
        ROOT,
        tmp_path / "revocation" / "billing-source-revocation.json",
        source_id=BILLING_SOURCE_ID,
        environment="staging",
        requested_by="billing-platform-sa",
        approved_by="data-platform-lead",
        change_request_id="revoke_billing_platform_source_activation_staging",
        ledger_path=ledger_path,
        active_state_path=pointer_path,
        generated_at="2026-06-17T10:30:00Z",
        reason="Readiness evidence is stale for the Billing Platform source.",
        evidence_uri="evidence://source-activations/billing-platform/staging/revocation-analysis-2026-06-17.json",
    )
    output_path = tmp_path / "ops" / "source-activation-ops.json"

    completed = run_ops_cli(ledger_path, pointer_dir, output_path, as_of="2026-06-18T12:00:00Z")

    assert completed.returncode == 1
    report = json.loads(output_path.read_text(encoding="utf-8"))
    billing = source_row(report)
    assert billing["risk_state"] == "revoked"
    assert billing["block_reason"] == "activation_not_active:revoked"
    assert report["summary"]["revoked_count"] == 1
    assert report["summary"]["critical_issue_count"] == 1


def activate_billing_source(tmp_path: Path, *, expires_at: str = EXPIRES_AT) -> tuple[Path, Path]:
    bundle = run_source_readiness_bundle(
        ROOT,
        BILLING_SOURCE_ID,
        BILLING_SAMPLE,
        tmp_path / "passing-bundle",
        environment="staging",
        bundle_id="billing-source-activation-ops",
        generated_at=GENERATED_AT,
        ingested_at=INGESTED_AT,
        replayed_at=REPLAYED_AT,
        schema_registry_uri="https://schema-registry.staging.example",
        change_request_id="onboard_billing_platform_source_readiness",
        target_snapshot_id=BILLING_SNAPSHOT_ID,
        table_metadata_uri=BILLING_METADATA_URI,
        table_metadata_hash=BILLING_METADATA_HASH,
        openlineage_namespace="enterprise-df://staging",
        openlineage_producer="https://enterprise-df.staging.example/openlineage-export",
    )
    ledger_path = tmp_path / "governance" / "source-activations.yaml"
    pointer_dir = tmp_path / "governance" / "source-active-pointers"
    active_state_path = pointer_dir / f"{BILLING_SOURCE_ID}.staging.json"
    result = write_source_activation_manifest_from_bundle(
        ROOT,
        bundle.summary_path,
        tmp_path / "activation" / "billing-source-activation.json",
        requested_by="billing-platform-sa",
        approved_by="data-platform-lead",
        change_request_id="onboard_billing_platform_source_readiness",
        ledger_path=ledger_path,
        active_state_path=active_state_path,
        generated_at=ACTIVATED_AT,
        expires_at=expires_at,
        reason="Activate Billing Platform source after source-to-Bronze readiness evidence passed.",
    )
    assert result.manifest["passed"] is True
    return ledger_path, pointer_dir


def run_ops_cli(
    ledger_path: Path,
    pointer_dir: Path,
    output_path: Path,
    *,
    as_of: str,
    expiring_within_days: int = 30,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_df.cli",
            "source-activation-ops-report",
            "--root",
            str(ROOT),
            "--output",
            str(output_path),
            "--environment",
            "staging",
            "--ledger",
            str(ledger_path),
            "--active-pointer-dir",
            str(pointer_dir),
            "--as-of",
            as_of,
            "--expiring-within-days",
            str(expiring_within_days),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def source_row(report: dict[str, object]) -> dict[str, object]:
    sources = report["sources"]
    assert isinstance(sources, list)
    return next(source for source in sources if isinstance(source, dict) and source["source_id"] == BILLING_SOURCE_ID)


def mutate_first_activation(ledger_path: Path, updates: dict[str, object]) -> None:
    registry = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    registry["activations"][0].update(updates)
    ledger_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

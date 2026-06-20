from __future__ import annotations

import base64
import copy
import hashlib
from pathlib import Path
import subprocess
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import yaml

from enterprise_dp.attestations import (
    attestation_signing_payload,
    write_schema_registry_publication_attestation,
    validate_evidence_trust_key_registry,
    validate_trust_key,
    verify_attestation_file,
    verify_external_evidence_attestation,
)
from enterprise_dp.contracts import ValidationResult


ROOT = Path(__file__).resolve().parents[1]
TEST_SIGNING_SEED = bytes(range(32))


def test_evidence_trust_key_registry_is_valid() -> None:
    result = validate_evidence_trust_key_registry(ROOT)

    assert result.errors == []
    assert result.checked_count == 1


def test_trust_key_registry_requires_producers_list() -> None:
    registry = yaml.safe_load((ROOT / "platform" / "security" / "evidence-trust-keys.yaml").read_text(encoding="utf-8"))
    key = copy.deepcopy(registry["keys"][0])
    del key["producers"]
    result = ValidationResult()

    validate_trust_key(ROOT / "platform" / "security" / "evidence-trust-keys.yaml", key, 0, set(), result)

    assert any("keys[0].producers must be a non-empty string list" in error for error in result.errors)


def test_ed25519_external_attestation_verifies_with_registered_key() -> None:
    report = signed_attestation()
    verification = verify_external_evidence_attestation(
        ROOT,
        report,
        evidence_kind="schema_registry",
        environment="prod",
    )

    assert verification.passed is True
    assert verification.required["signature_verified"] is True
    assert verification.required["signing_key_id_registered"] is True


def test_attestation_payload_tamper_fails_signature_verification() -> None:
    report = signed_attestation()
    report["subject_hash"] = "sha256:" + ("0" * 64)

    verification = verify_external_evidence_attestation(
        ROOT,
        report,
        evidence_kind="schema_registry",
        environment="prod",
    )

    assert verification.passed is False
    assert verification.required["signature_verified"] is False


def test_attestation_unknown_key_fails_closed() -> None:
    report = signed_attestation()
    report["signing_key_id"] = "unknown-ed25519-key"

    verification = verify_external_evidence_attestation(
        ROOT,
        report,
        evidence_kind="schema_registry",
        environment="prod",
    )

    assert verification.passed is False
    assert verification.required["signing_key_id_registered"] is False


def test_attestation_key_scope_and_expiry_fail_closed() -> None:
    expired = signed_attestation(generated_at="2028-01-15T10:10:10Z")
    wrong_environment = signed_attestation(environment="dev")

    expired_verification = verify_external_evidence_attestation(
        ROOT,
        expired,
        evidence_kind="schema_registry",
        environment="prod",
    )
    wrong_environment_verification = verify_external_evidence_attestation(
        ROOT,
        wrong_environment,
        evidence_kind="schema_registry",
        environment="dev",
    )

    assert expired_verification.passed is False
    assert expired_verification.required["key_time_valid"] is False
    assert wrong_environment_verification.passed is False
    assert wrong_environment_verification.required["key_environment_allowed"] is False


def test_attestation_producer_scope_fails_closed() -> None:
    report = signed_attestation(producer="untrusted-producer")

    verification = verify_external_evidence_attestation(
        ROOT,
        report,
        evidence_kind="schema_registry",
        environment="prod",
    )

    assert verification.passed is False
    assert verification.required["key_producer_allowed"] is False


def test_verify_attestation_file_and_cli(tmp_path: Path) -> None:
    attestation_path = tmp_path / "schema-attestation.json"
    attestation_path.write_text(canonical_test_json(signed_attestation()), encoding="utf-8")

    result = verify_attestation_file(
        ROOT,
        attestation_path,
        evidence_kind="schema_registry",
        environment="prod",
        release_id="unit-test-release",
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "attestation-verify",
            "--root",
            str(ROOT),
            "--input",
            str(attestation_path),
            "--evidence-kind",
            "schema_registry",
            "--environment",
            "prod",
            "--release-id",
            "unit-test-release",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    mismatch = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "attestation-verify",
            "--root",
            str(ROOT),
            "--input",
            str(attestation_path),
            "--evidence-kind",
            "schema_registry",
            "--environment",
            "prod",
            "--release-id",
            "wrong-release",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result["passed"] is True
    assert completed.returncode == 0, completed.stderr
    assert mismatch.returncode == 1


def test_schema_registry_publication_attestation_binds_manifest_hash(tmp_path: Path) -> None:
    publication_path = write_publication_manifest(tmp_path)
    runtime_path = write_runtime_smoke(tmp_path, publication_path)

    result = write_schema_registry_publication_attestation(
        ROOT,
        tmp_path / "schema-registry-publication-attestation.json",
        publication_manifest_path=publication_path,
        schema_registry_runtime_smoke_report_path=runtime_path,
        environment="staging",
        generated_at="2026-01-15T10:10:10Z",
    )
    verification = verify_attestation_file(
        ROOT,
        result.output_path,
        evidence_kind="schema_registry",
        environment="staging",
        release_id="schema-runtime-unit",
        subject_path=publication_path,
    )

    assert result.report["artifact_type"] == "external_evidence_attestation.v1"
    assert result.report["subject_hash"] == sha256_file(publication_path)
    assert result.report["source_runtime_smoke"]["binding_checks"]["runtime_publication_hash_matches_subject"] is True
    assert result.report["signing_key_material_source"] == "local_deterministic_ci_fixture"
    assert verification["passed"] is True
    assert verification["required"]["signature_verified"] is True
    assert verification["required"]["subject_hash_matches"] is True


def test_schema_registry_publication_attestation_rejects_runtime_hash_mismatch(tmp_path: Path) -> None:
    publication_path = write_publication_manifest(tmp_path)
    runtime_path = write_runtime_smoke(tmp_path, publication_path, manifest_hash="sha256:" + ("0" * 64))

    try:
        write_schema_registry_publication_attestation(
            ROOT,
            tmp_path / "schema-registry-publication-attestation.json",
            publication_manifest_path=publication_path,
            schema_registry_runtime_smoke_report_path=runtime_path,
            environment="staging",
        )
    except ValueError as exc:
        assert "runtime_publication_hash_matches_subject" in str(exc)
    else:
        raise AssertionError("attestation should reject a runtime publication hash mismatch")


def signed_attestation(
    *,
    evidence_kind: str = "schema_registry",
    environment: str = "prod",
    generated_at: str = "2026-01-15T10:10:10Z",
    producer: str = "data-platform-control-plane",
) -> dict[str, object]:
    payload: dict[str, object] = {
        "artifact_type": "external_evidence_attestation.v1",
        "evidence_kind": evidence_kind,
        "subject_uri": f"s3://dp-evidence/{evidence_kind}/unit-test.json",
        "subject_hash": "sha256:" + hashlib.sha256(evidence_kind.encode("utf-8")).hexdigest(),
        "environment": environment,
        "release_id": "unit-test-release",
        "producer": producer,
        "generated_at": generated_at,
        "signature_algorithm": "Ed25519",
        "signing_key_id": "local-test-ed25519-2026",
        "passed": True,
    }
    return sign(payload)


def sign(payload: dict[str, object]) -> dict[str, object]:
    signed = copy.deepcopy(payload)
    signature = Ed25519PrivateKey.from_private_bytes(TEST_SIGNING_SEED).sign(attestation_signing_payload(signed))
    signed["signature"] = f"base64:{base64.b64encode(signature).decode()}"
    return signed


def canonical_test_json(payload: dict[str, object]) -> str:
    import json

    return f"{json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(',', ':'))}\n"


def write_publication_manifest(tmp_path: Path) -> Path:
    path = tmp_path / "schema-registry-publication-manifest.json"
    payload = {
        "artifact_type": "schema_registry_publication_manifest.v1",
        "generated_at": "2026-01-15T10:10:10Z",
        "environment": "local",
        "registry_uri": "http://localhost:18082",
        "subjects": [
            {
                "subject": "finance.benefit_settled.v1-value",
                "registered": True,
                "schema_id": "42",
                "payload_schema_hash": "sha256:" + hashlib.sha256(b"schema").hexdigest(),
            }
        ],
    }
    path.write_text(canonical_test_json(payload), encoding="utf-8")
    return path


def write_runtime_smoke(tmp_path: Path, publication_path: Path, *, manifest_hash: str | None = None) -> Path:
    path = tmp_path / "schema-registry-runtime-smoke-report.json"
    payload = {
        "artifact_type": "schema_registry_runtime_smoke_report.v1",
        "generated_at": "2026-01-15T10:10:10Z",
        "release_id": "schema-runtime-unit",
        "passed": True,
        "publication_manifest": {
            "path": publication_path.as_posix(),
            "hash": manifest_hash or sha256_file(publication_path),
            "artifact_type": "schema_registry_publication_manifest.v1",
        },
    }
    path.write_text(canonical_test_json(payload), encoding="utf-8")
    return path


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()

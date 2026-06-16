from __future__ import annotations

import base64
import copy
import hashlib
from pathlib import Path
import subprocess
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import yaml

from enterprise_df.attestations import (
    attestation_signing_payload,
    validate_evidence_trust_key_registry,
    validate_trust_key,
    verify_attestation_file,
    verify_external_evidence_attestation,
)
from enterprise_df.contracts import ValidationResult


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
            "enterprise_df.cli",
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
            "enterprise_df.cli",
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
        "subject_uri": f"s3://df-evidence/{evidence_kind}/unit-test.json",
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

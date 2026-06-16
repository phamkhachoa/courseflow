from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from enterprise_df.contracts import ValidationResult, load_yaml


TRUST_KEY_REGISTRY_PATH = Path("platform/security/evidence-trust-keys.yaml")
VALID_ALGORITHMS = {"Ed25519"}
VALID_EVIDENCE_KINDS = {"schema_registry", "access_policy", "access_grant", "retention_erasure"}
VALID_KEY_STATUSES = {"active", "disabled", "deprecated"}


@dataclass(frozen=True)
class AttestationVerification:
    passed: bool
    required: dict[str, bool]
    details: dict[str, Any]


def validate_evidence_trust_key_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    path = root / TRUST_KEY_REGISTRY_PATH
    if not path.is_file():
        result.error(path, "platform/security/evidence-trust-keys.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(path)
    if not isinstance(registry.get("version"), int) or registry.get("version") < 1:
        result.error(path, "version must be an integer >= 1")
    if not _non_empty_string(registry.get("registry_scope")):
        result.error(path, "registry_scope must be a non-empty string")

    keys = registry.get("keys")
    if not isinstance(keys, list) or not keys:
        result.error(path, "keys must be a non-empty list")
        return result

    seen_ids: set[str] = set()
    for index, key in enumerate(keys):
        validate_trust_key(path, key, index, seen_ids, result)
    return result


def validate_trust_key(
    path: Path,
    key: object,
    index: int,
    seen_ids: set[str],
    result: ValidationResult,
) -> None:
    prefix = f"keys[{index}]"
    if not isinstance(key, dict):
        result.error(path, f"{prefix} must be an object")
        return

    key_id = key.get("id")
    if not _non_empty_string(key_id):
        result.error(path, f"{prefix}.id must be a non-empty string")
    elif key_id in seen_ids:
        result.error(path, f"{prefix}.id duplicates key id {key_id!r}")
    else:
        seen_ids.add(str(key_id))

    for field in ("name", "owner"):
        if not _non_empty_string(key.get(field)):
            result.error(path, f"{prefix}.{field} must be a non-empty string")
    if key.get("status") not in VALID_KEY_STATUSES:
        result.error(path, f"{prefix}.status must be one of {sorted(VALID_KEY_STATUSES)}")
    if key.get("algorithm") not in VALID_ALGORITHMS:
        result.error(path, f"{prefix}.algorithm must be one of {sorted(VALID_ALGORITHMS)}")
    if decode_base64_field(key.get("publicKey")) is None:
        result.error(path, f"{prefix}.publicKey must be base64 encoded")
    if parse_time(key.get("validFrom")) is None:
        result.error(path, f"{prefix}.validFrom must be an ISO timestamp")
    if key.get("validUntil") is not None and parse_time(key.get("validUntil")) is None:
        result.error(path, f"{prefix}.validUntil must be an ISO timestamp")
    for field in ("environments", "evidenceKinds", "producers", "subjectUriPrefixes"):
        values = key.get(field)
        if not isinstance(values, list) or not values or not all(_non_empty_string(item) for item in values):
            result.error(path, f"{prefix}.{field} must be a non-empty string list")
    for evidence_kind in key.get("evidenceKinds", []) if isinstance(key.get("evidenceKinds"), list) else []:
        if evidence_kind not in VALID_EVIDENCE_KINDS:
            result.error(path, f"{prefix}.evidenceKinds contains unsupported value {evidence_kind!r}")


def verify_external_evidence_attestation(
    root: Path,
    report: dict[str, Any],
    *,
    evidence_kind: str,
    environment: str,
) -> AttestationVerification:
    registry_path = root / TRUST_KEY_REGISTRY_PATH
    registry = load_yaml(registry_path) if registry_path.is_file() else {}
    keys = registry.get("keys")
    key_id = report.get("signing_key_id")
    key = find_trust_key(keys, key_id)
    generated_at = parse_time(report.get("generated_at"))
    signature = decode_base64_field(report.get("signature"))
    public_key_bytes = decode_base64_field(key.get("publicKey")) if isinstance(key, dict) else None
    subject_uri = report.get("subject_uri")
    producer = report.get("producer")

    required = {
        "trust_registry_present": registry_path.is_file(),
        "signing_key_id_registered": isinstance(key, dict),
        "signature_algorithm": report.get("signature_algorithm") == "Ed25519" and (not isinstance(key, dict) or key.get("algorithm") == "Ed25519"),
        "key_active": isinstance(key, dict) and key.get("status") == "active",
        "key_environment_allowed": isinstance(key, dict) and environment in _string_list(key.get("environments")),
        "key_evidence_kind_allowed": isinstance(key, dict) and evidence_kind in _string_list(key.get("evidenceKinds")),
        "key_producer_allowed": isinstance(key, dict) and producer in _string_list(key.get("producers")),
        "key_time_valid": isinstance(key, dict) and generated_at is not None and key_valid_at(key, generated_at),
        "subject_uri_prefix_allowed": isinstance(key, dict) and subject_uri_allowed(subject_uri, key),
        "public_key_parseable": public_key_bytes is not None,
        "signature_parseable": signature is not None,
        "signature_verified": False,
    }
    if public_key_bytes is not None and signature is not None:
        required["signature_verified"] = verify_ed25519_signature(public_key_bytes, signature, attestation_signing_payload(report))

    return AttestationVerification(
        passed=all(required.values()),
        required=required,
        details={
            "trust_registry_path": registry_path.as_posix(),
            "signing_key_id": key_id,
            "signature_algorithm": report.get("signature_algorithm"),
            "key_status": key.get("status") if isinstance(key, dict) else None,
            "key_owner": key.get("owner") if isinstance(key, dict) else None,
        },
    )


def verify_attestation_file(
    root: str | Path,
    input_path: str | Path,
    *,
    evidence_kind: str,
    environment: str,
    release_id: str | None = None,
) -> dict[str, Any]:
    path = Path(input_path)
    report = load_json(path)
    verification = verify_external_evidence_attestation(
        Path(root),
        report,
        evidence_kind=evidence_kind,
        environment=environment,
    )
    required = {
        "artifact_type": report.get("artifact_type") == "external_evidence_attestation.v1",
        "evidence_kind": report.get("evidence_kind") == evidence_kind,
        "environment": report.get("environment") == environment,
        "release_id": release_id is None or report.get("release_id") == release_id,
        "passed": report.get("passed") is True,
        **verification.required,
    }
    return {
        "artifact_type": report.get("artifact_type"),
        "input": path.as_posix(),
        "evidence_kind": report.get("evidence_kind"),
        "expected_evidence_kind": evidence_kind,
        "environment": report.get("environment"),
        "expected_environment": environment,
        "release_id": report.get("release_id"),
        "expected_release_id": release_id,
        "subject_uri": report.get("subject_uri"),
        "subject_hash": report.get("subject_hash"),
        "producer": report.get("producer"),
        "signing_key_id": report.get("signing_key_id"),
        "signature_algorithm": report.get("signature_algorithm"),
        "required": required,
        "passed": all(required.values()),
    }


def attestation_signing_payload(report: dict[str, Any]) -> bytes:
    payload = {
        key: value
        for key, value in report.items()
        if key != "signature"
    }
    return canonical_json(payload).encode("utf-8")


def verify_ed25519_signature(public_key_bytes: bytes, signature: bytes, payload: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(signature, payload)
    except (InvalidSignature, ValueError):
        return False
    return True


def find_trust_key(keys: object, key_id: object) -> dict[str, Any] | None:
    if not _non_empty_string(key_id) or not isinstance(keys, list):
        return None
    for key in keys:
        if isinstance(key, dict) and key.get("id") == key_id:
            return key
    return None


def key_valid_at(key: dict[str, Any], generated_at: datetime) -> bool:
    valid_from = parse_time(key.get("validFrom"))
    valid_until = parse_time(key.get("validUntil")) if key.get("validUntil") else None
    if valid_from is not None and generated_at < valid_from:
        return False
    if valid_until is not None and generated_at >= valid_until:
        return False
    return True


def subject_uri_allowed(subject_uri: object, key: dict[str, Any]) -> bool:
    if not _non_empty_string(subject_uri):
        return False
    prefixes = _string_list(key.get("subjectUriPrefixes"))
    return bool(prefixes) and any(str(subject_uri).startswith(prefix) for prefix in prefixes)


def decode_base64_field(value: object) -> bytes | None:
    if not _non_empty_string(value):
        return None
    text = str(value)
    if text.startswith("base64:"):
        text = text.removeprefix("base64:")
    try:
        return base64.b64decode(text, validate=True)
    except ValueError:
        return None


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def canonical_json(record: Any) -> str:
    return json.dumps(record, allow_nan=False, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON object expected")
    return data


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if _non_empty_string(item)]


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())

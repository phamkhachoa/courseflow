from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import base64
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.event_backbone_smoke import stable_id
from enterprise_dp.schema_registry_auth_smoke import hash_bytes


DEFAULT_GENERATED_AT = "2026-01-15T09:15:20Z"
DEFAULT_ISSUER = "https://identity.local/realms/enterprise-dp"
DEFAULT_AUDIENCE = "enterprise-dp-runtime"
DEFAULT_REQUIRED_ROLE = "data-platform-runtime-reader"
DEFAULT_KEY_ID = "enterprise-dp-local-rs256-2026-01"


@dataclass(frozen=True)
class OidcAuthSmokeResult:
    output_path: Path
    report: dict[str, Any]


@dataclass(frozen=True)
class OidcIssuer:
    issuer: str
    audience: str
    key_id: str
    private_key: rsa.RSAPrivateKey
    jwks: dict[str, Any]


@dataclass(frozen=True)
class TokenValidation:
    accepted: bool
    reason: str
    subject: str | None
    token_id: str | None
    token_hash: str | None
    roles: list[str]
    claims: dict[str, Any]


def write_oidc_auth_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    issuer: str = DEFAULT_ISSUER,
    audience: str = DEFAULT_AUDIENCE,
    required_role: str = DEFAULT_REQUIRED_ROLE,
    key_id: str = DEFAULT_KEY_ID,
    release_id: str = "local-oidc-auth-smoke",
    environment: str = "local",
    generated_at: str | None = None,
) -> OidcAuthSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or DEFAULT_GENERATED_AT
    validation_time = parse_utc(generated) + timedelta(minutes=1)
    audit_events_path = target_dir / "audit" / "oidc-auth-audit.jsonl"
    audit_manifest_path = target_dir / "audit" / "oidc-auth-audit-manifest.json"

    issuer_bundle = create_oidc_issuer(issuer=issuer, audience=audience, key_id=key_id)
    probes = run_oidc_auth_probes(
        issuer_bundle,
        required_role=required_role,
        validation_time=validation_time,
    )
    audit_sink = write_oidc_audit_sink(
        audit_events_path,
        audit_manifest_path,
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        probes=probes,
    )
    failed_checks = failed_oidc_auth_checks(
        probes=probes,
        audit_sink=audit_sink,
        jwks=issuer_bundle.jwks,
        key_id=key_id,
    )
    report = build_oidc_auth_smoke_report(
        root=platform_root,
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        issuer_bundle=issuer_bundle,
        required_role=required_role,
        validation_time=validation_time,
        probes=probes,
        audit_sink=audit_sink,
        audit_events_path=audit_events_path,
        audit_manifest_path=audit_manifest_path,
        failed_checks=failed_checks,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return OidcAuthSmokeResult(output_path=target, report=report)


def create_oidc_issuer(*, issuer: str, audience: str, key_id: str) -> OidcIssuer:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "kid": key_id,
        "alg": "RS256",
        "n": b64url_uint(public_numbers.n),
        "e": b64url_uint(public_numbers.e),
    }
    return OidcIssuer(
        issuer=issuer,
        audience=audience,
        key_id=key_id,
        private_key=private_key,
        jwks={"keys": [jwk]},
    )


def run_oidc_auth_probes(
    issuer_bundle: OidcIssuer,
    *,
    required_role: str,
    validation_time: datetime,
) -> dict[str, dict[str, Any]]:
    valid_token = sign_access_token(
        issuer_bundle,
        subject="dp-runtime-finance-reader",
        roles=[required_role, "finance_reader"],
        issued_at=validation_time - timedelta(minutes=1),
        expires_at=validation_time + timedelta(hours=1),
    )
    wrong_audience_token = sign_access_token(
        issuer_bundle,
        subject="dp-runtime-wrong-audience",
        audience="wrong-enterprise-client",
        roles=[required_role],
        issued_at=validation_time - timedelta(minutes=1),
        expires_at=validation_time + timedelta(hours=1),
    )
    issuer_mismatch_token = sign_access_token(
        issuer_bundle,
        subject="dp-runtime-wrong-issuer",
        issuer="https://identity.local/realms/other",
        roles=[required_role],
        issued_at=validation_time - timedelta(minutes=1),
        expires_at=validation_time + timedelta(hours=1),
    )
    expired_token = sign_access_token(
        issuer_bundle,
        subject="dp-runtime-expired",
        roles=[required_role],
        issued_at=validation_time - timedelta(hours=2),
        expires_at=validation_time - timedelta(minutes=1),
    )
    missing_role_token = sign_access_token(
        issuer_bundle,
        subject="dp-runtime-no-role",
        roles=["finance_reader"],
        issued_at=validation_time - timedelta(minutes=1),
        expires_at=validation_time + timedelta(hours=1),
    )
    unknown_kid_token = sign_access_token(
        issuer_bundle,
        subject="dp-runtime-unknown-kid",
        roles=[required_role],
        issued_at=validation_time - timedelta(minutes=1),
        expires_at=validation_time + timedelta(hours=1),
        key_id="unknown-kid",
    )
    tampered_token = tamper_jwt_signature(valid_token)

    probe_specs = {
        "valid_token_accepted": (valid_token, True, "accepted"),
        "missing_token_denied": (None, False, "missing_token"),
        "wrong_audience_denied": (wrong_audience_token, False, "invalid_audience"),
        "issuer_mismatch_denied": (issuer_mismatch_token, False, "invalid_issuer"),
        "expired_token_denied": (expired_token, False, "token_expired"),
        "tampered_signature_denied": (tampered_token, False, "invalid_signature"),
        "unknown_kid_denied": (unknown_kid_token, False, "unknown_key_id"),
        "missing_required_role_denied": (missing_role_token, False, "missing_required_role"),
    }
    probes: dict[str, dict[str, Any]] = {}
    for name, (token, expected_accepted, expected_reason) in probe_specs.items():
        validation = validate_access_token(
            token,
            issuer=issuer_bundle.issuer,
            audience=issuer_bundle.audience,
            required_role=required_role,
            jwks=issuer_bundle.jwks,
            validation_time=validation_time,
        )
        probes[name] = {
            "passed": validation.accepted is expected_accepted and validation.reason == expected_reason,
            "expected_accepted": expected_accepted,
            "expected_reason": expected_reason,
            "accepted": validation.accepted,
            "reason": validation.reason,
            "subject": validation.subject,
            "token_id": validation.token_id,
            "token_hash": validation.token_hash,
            "roles": validation.roles,
        }
    return probes


def sign_access_token(
    issuer_bundle: OidcIssuer,
    *,
    subject: str,
    roles: list[str],
    issued_at: datetime,
    expires_at: datetime,
    issuer: str | None = None,
    audience: str | None = None,
    key_id: str | None = None,
) -> str:
    token_id = f"oidc-smoke-{uuid4()}"
    header = {"alg": "RS256", "typ": "JWT", "kid": key_id or issuer_bundle.key_id}
    claims = {
        "iss": issuer or issuer_bundle.issuer,
        "sub": subject,
        "aud": audience or issuer_bundle.audience,
        "iat": int(issued_at.timestamp()),
        "nbf": int((issued_at - timedelta(seconds=5)).timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": token_id,
        "realm_access": {"roles": roles},
        "resource_access": {issuer_bundle.audience: {"roles": roles}},
    }
    signing_input = b".".join([b64url_json(header), b64url_json(claims)])
    signature = issuer_bundle.private_key.sign(
        signing_input,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return ".".join([signing_input.decode("ascii"), b64url_encode(signature)])


def validate_access_token(
    token: str | None,
    *,
    issuer: str,
    audience: str,
    required_role: str,
    jwks: dict[str, Any],
    validation_time: datetime,
) -> TokenValidation:
    if not token:
        return TokenValidation(False, "missing_token", None, None, None, [], {})
    token_hash = hash_bytes(token.encode("utf-8"))
    try:
        header, claims, signing_input, signature = decode_jwt(token)
    except ValueError:
        return TokenValidation(False, "malformed_token", None, None, token_hash, [], {})
    subject = str(claims.get("sub")) if claims.get("sub") is not None else None
    token_id = str(claims.get("jti")) if claims.get("jti") is not None else None
    roles = sorted(token_roles(claims, audience))
    if header.get("alg") != "RS256":
        return TokenValidation(False, "unsupported_algorithm", subject, token_id, token_hash, roles, claims)
    key = jwk_for_kid(jwks, str(header.get("kid") or ""))
    if key is None:
        return TokenValidation(False, "unknown_key_id", subject, token_id, token_hash, roles, claims)
    try:
        key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
    except InvalidSignature:
        return TokenValidation(False, "invalid_signature", subject, token_id, token_hash, roles, claims)
    if claims.get("iss") != issuer:
        return TokenValidation(False, "invalid_issuer", subject, token_id, token_hash, roles, claims)
    if not audience_matches(claims.get("aud"), audience):
        return TokenValidation(False, "invalid_audience", subject, token_id, token_hash, roles, claims)
    now = int(validation_time.timestamp())
    if int(claims.get("nbf", 0)) > now:
        return TokenValidation(False, "token_not_yet_valid", subject, token_id, token_hash, roles, claims)
    if int(claims.get("exp", 0)) <= now:
        return TokenValidation(False, "token_expired", subject, token_id, token_hash, roles, claims)
    if required_role not in roles:
        return TokenValidation(False, "missing_required_role", subject, token_id, token_hash, roles, claims)
    return TokenValidation(True, "accepted", subject, token_id, token_hash, roles, claims)


def write_oidc_audit_sink(
    events_path: Path,
    manifest_path: Path,
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    probes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, Any]] = []
    for probe_name, probe in probes.items():
        event = {
            "event_type": "oidc_runtime_authn_decision",
            "generated_at": generated_at,
            "environment": environment,
            "release_id": release_id,
            "probe": probe_name,
            "decision": "allow" if probe.get("accepted") is True else "deny",
            "reason": probe.get("reason"),
            "subject": probe.get("subject"),
            "token_id": probe.get("token_id"),
            "token_hash": probe.get("token_hash"),
            "passed": probe.get("passed") is True,
        }
        events.append(event)
    with events_path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(f"{canonical_json(event)}\n")
    failed_event_count = sum(1 for event in events if event["passed"] is not True)
    manifest = {
        "artifact_type": "oidc_auth_audit_manifest.v1",
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "event_count": len(events),
        "failed_event_count": failed_event_count,
        "events_path": events_path.as_posix(),
        "events_hash": hash_file(events_path),
        "raw_access_tokens_persisted": False,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    return {
        "passed": failed_event_count == 0 and len(events) >= 8,
        "event_count": len(events),
        "failed_event_count": failed_event_count,
        "events_path": events_path.as_posix(),
        "events_hash": hash_file(events_path),
        "manifest_path": manifest_path.as_posix(),
        "manifest_hash": hash_file(manifest_path),
        "raw_access_tokens_persisted": False,
    }


def failed_oidc_auth_checks(
    *,
    probes: dict[str, dict[str, Any]],
    audit_sink: dict[str, Any],
    jwks: dict[str, Any],
    key_id: str,
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    keys = jwks.get("keys") if isinstance(jwks, dict) else None
    if not isinstance(keys, list) or not any(item.get("kid") == key_id for item in keys if isinstance(item, dict)):
        failed.append({"check": "jwks_key_published", "key_id": key_id})
    for name in [
        "valid_token_accepted",
        "missing_token_denied",
        "wrong_audience_denied",
        "issuer_mismatch_denied",
        "expired_token_denied",
        "tampered_signature_denied",
        "unknown_kid_denied",
        "missing_required_role_denied",
    ]:
        if probes.get(name, {}).get("passed") is not True:
            failed.append({"check": name, "probe": probes.get(name)})
    if audit_sink.get("passed") is not True:
        failed.append(
            {
                "check": "oidc_auth_audit_sink_passed",
                "event_count": audit_sink.get("event_count", 0),
                "failed_event_count": audit_sink.get("failed_event_count", 0),
            }
        )
    if audit_sink.get("raw_access_tokens_persisted") is not False:
        failed.append({"check": "raw_access_tokens_not_persisted"})
    return failed


def build_oidc_auth_smoke_report(
    *,
    root: Path,
    generated_at: str,
    environment: str,
    release_id: str,
    issuer_bundle: OidcIssuer,
    required_role: str,
    validation_time: datetime,
    probes: dict[str, dict[str, Any]],
    audit_sink: dict[str, Any],
    audit_events_path: Path,
    audit_manifest_path: Path,
    failed_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    key = issuer_bundle.jwks.get("keys", [{}])[0]
    summary = {
        "issuer": issuer_bundle.issuer,
        "audience": issuer_bundle.audience,
        "required_role": required_role,
        "key_id": issuer_bundle.key_id,
        "jwks_key_count": len(issuer_bundle.jwks.get("keys", [])),
        "jwks_key_published": key.get("kid") == issuer_bundle.key_id and key.get("alg") == "RS256",
        "rs256_signature_validation_passed": probe_passed(probes, "valid_token_accepted")
        and probe_passed(probes, "tampered_signature_denied"),
        "issuer_validation_passed": probe_passed(probes, "valid_token_accepted")
        and probe_passed(probes, "issuer_mismatch_denied"),
        "audience_validation_passed": probe_passed(probes, "valid_token_accepted")
        and probe_passed(probes, "wrong_audience_denied"),
        "expiry_validation_passed": probe_passed(probes, "valid_token_accepted")
        and probe_passed(probes, "expired_token_denied"),
        "required_role_denied": probe_passed(probes, "missing_required_role_denied"),
        "unknown_kid_denied": probe_passed(probes, "unknown_kid_denied"),
        "missing_token_denied": probe_passed(probes, "missing_token_denied"),
        "valid_token_accepted": probe_passed(probes, "valid_token_accepted"),
        "audit_sink_passed": audit_sink.get("passed") is True,
        "audit_event_count": audit_sink.get("event_count", 0),
        "audit_failed_event_count": audit_sink.get("failed_event_count", 0),
        "raw_access_tokens_persisted": False,
        "private_key_persisted": False,
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
    }
    passed = not failed_checks
    return {
        "artifact_type": "oidc_auth_smoke_report.v1",
        "report_version": 1,
        "capability_id": "runtime-security-enforcement",
        "report_id": stable_id("oidc-auth-smoke", environment, release_id, issuer_bundle.issuer, issuer_bundle.audience),
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "runtime_scope": {
            "mode": "local_oidc_rs256_jwks_validation",
            "covered": [
                "oidc_issuer_metadata_modeled",
                "jwks_rs256_public_key_published",
                "jwt_rs256_signature_verified",
                "issuer_claim_verified",
                "audience_claim_verified",
                "expiry_and_not_before_claims_verified",
                "required_role_claim_authorization",
                "missing_token_denied",
                "unknown_kid_denied",
                "tampered_signature_denied",
                "structured_oidc_authn_audit_written_without_raw_tokens",
            ],
            "not_covered": [
                "enterprise_keycloak_realm_deployment",
                "keycloak_group_claim_mapping",
                "idp_group_sync",
                "token_introspection_endpoint",
                "production_oidc_provider_ha",
                "jwks_rotation_from_managed_idp",
                "production_secret_rotation",
            ],
        },
        "issuer": {
            "issuer": issuer_bundle.issuer,
            "audience": issuer_bundle.audience,
            "jwks": issuer_bundle.jwks,
            "private_key_persisted": False,
            "root": root.as_posix(),
        },
        "validation": {
            "validation_time": validation_time.isoformat().replace("+00:00", "Z"),
            "required_role": required_role,
            "algorithm": "RS256",
        },
        "probes": probes,
        "audit_sink": {
            "mode": "local_jsonl_structured_oidc_authn_audit",
            "events_path": audit_events_path.as_posix(),
            "events_hash": hash_file(audit_events_path) if audit_events_path.is_file() else None,
            "manifest_path": audit_manifest_path.as_posix(),
            "manifest_hash": hash_file(audit_manifest_path) if audit_manifest_path.is_file() else None,
            "raw_access_tokens_persisted": False,
        },
        "summary": summary,
        "passed": passed,
    }


def probe_passed(probes: dict[str, dict[str, Any]], name: str) -> bool:
    return probes.get(name, {}).get("passed") is True


def decode_jwt(token: str) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("jwt must have three segments")
    header = json.loads(b64url_decode(parts[0]))
    claims = json.loads(b64url_decode(parts[1]))
    if not isinstance(header, dict) or not isinstance(claims, dict):
        raise ValueError("jwt header and claims must be objects")
    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    signature = b64url_decode(parts[2])
    return header, claims, signing_input, signature


def jwk_for_kid(jwks: dict[str, Any], key_id: str) -> rsa.RSAPublicKey | None:
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        return None
    for key in keys:
        if not isinstance(key, dict) or key.get("kid") != key_id:
            continue
        if key.get("kty") != "RSA":
            return None
        numbers = rsa.RSAPublicNumbers(e=b64url_to_uint(str(key["e"])), n=b64url_to_uint(str(key["n"])))
        return numbers.public_key()
    return None


def token_roles(claims: dict[str, Any], audience: str) -> set[str]:
    roles: set[str] = set()
    realm_access = claims.get("realm_access")
    if isinstance(realm_access, dict) and isinstance(realm_access.get("roles"), list):
        roles.update(str(role) for role in realm_access["roles"])
    resource_access = claims.get("resource_access")
    if isinstance(resource_access, dict):
        audience_access = resource_access.get(audience)
        if isinstance(audience_access, dict) and isinstance(audience_access.get("roles"), list):
            roles.update(str(role) for role in audience_access["roles"])
    if isinstance(claims.get("roles"), list):
        roles.update(str(role) for role in claims["roles"])
    return roles


def audience_matches(actual: Any, expected: str) -> bool:
    if actual == expected:
        return True
    if isinstance(actual, list):
        return expected in actual
    return False


def tamper_jwt_signature(token: str) -> str:
    header, payload, signature = token.split(".")
    signature_bytes = bytearray(b64url_decode(signature))
    if not signature_bytes:
        return f"{header}.{payload}.{signature}A"
    signature_bytes[0] ^= 1
    return f"{header}.{payload}.{b64url_encode(bytes(signature_bytes))}"


def parse_utc(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def b64url_json(payload: dict[str, Any]) -> bytes:
    return b64url_encode_bytes(canonical_json(payload).encode("utf-8")).encode("ascii")


def b64url_encode(payload: bytes) -> str:
    return b64url_encode_bytes(payload)


def b64url_encode_bytes(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def b64url_decode(payload: str) -> bytes:
    padded = payload + ("=" * (-len(payload) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def b64url_uint(value: int) -> str:
    width = max(1, (value.bit_length() + 7) // 8)
    return b64url_encode(value.to_bytes(width, "big"))


def b64url_to_uint(value: str) -> int:
    return int.from_bytes(b64url_decode(value), "big")

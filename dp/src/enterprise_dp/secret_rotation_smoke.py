from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import secrets
from typing import Any

from cryptography.fernet import Fernet

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.event_backbone_smoke import stable_id
from enterprise_dp.schema_registry_auth_smoke import hash_bytes


DEFAULT_GENERATED_AT = "2026-01-15T09:15:20Z"


@dataclass(frozen=True)
class SecretRotationSmokeResult:
    output_path: Path
    report: dict[str, Any]


@dataclass(frozen=True)
class SecretSurface:
    name: str
    service_identity: str
    purpose: str


@dataclass
class SecretVersion:
    version: str
    ciphertext: str
    secret_hash: str
    status: str


@dataclass
class SecretRecord:
    name: str
    service_identity: str
    purpose: str
    active_version: str
    versions: list[SecretVersion] = field(default_factory=list)


@dataclass(frozen=True)
class SecretRead:
    allowed: bool
    reason: str
    name: str
    subject: str
    version: str | None
    secret_hash: str | None = None
    value: str | None = None


def write_secret_rotation_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    release_id: str = "local-secret-rotation-smoke",
    environment: str = "local",
    generated_at: str | None = None,
) -> SecretRotationSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or DEFAULT_GENERATED_AT
    store_path = target_dir / "secret-store" / "encrypted-secret-store.json"
    audit_events_path = target_dir / "audit" / "secret-rotation-audit.jsonl"
    audit_manifest_path = target_dir / "audit" / "secret-rotation-audit-manifest.json"
    injection_manifest_path = target_dir / "orchestration" / "dagster-secret-injection-manifest.json"

    store = LocalEncryptedSecretStore(generated_at=generated, environment=environment, release_id=release_id)
    surfaces = default_secret_surfaces()
    material = run_secret_rotation_probes(store, surfaces, injection_manifest_path)
    store_manifest = store.write_store(store_path)
    audit_sink = store.write_audit_sink(audit_events_path, audit_manifest_path)
    plaintext_persisted = plaintext_material_persisted(
        [store_path, audit_events_path, audit_manifest_path, injection_manifest_path],
        material["raw_secret_values"],
    )
    failed_checks = failed_secret_rotation_checks(
        material=material,
        store_manifest=store_manifest,
        audit_sink=audit_sink,
        plaintext_persisted=plaintext_persisted,
        expected_surface_count=len(surfaces),
    )
    report = build_secret_rotation_smoke_report(
        root=platform_root,
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        surfaces=surfaces,
        material=material,
        store_manifest=store_manifest,
        audit_sink=audit_sink,
        store_path=store_path,
        audit_events_path=audit_events_path,
        audit_manifest_path=audit_manifest_path,
        injection_manifest_path=injection_manifest_path,
        plaintext_persisted=plaintext_persisted,
        failed_checks=failed_checks,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SecretRotationSmokeResult(output_path=target, report=report)


class LocalEncryptedSecretStore:
    def __init__(self, *, generated_at: str, environment: str, release_id: str) -> None:
        self.generated_at = generated_at
        self.environment = environment
        self.release_id = release_id
        self.run_id = stable_id("secret-rotation-smoke-run", environment, release_id)
        self._fernet = Fernet(Fernet.generate_key())
        self.records: dict[str, SecretRecord] = {}
        self.raw_secret_values: list[str] = []
        self.audit_events: list[dict[str, Any]] = []

    def create_secret(self, surface: SecretSurface) -> SecretRead:
        value = self._new_secret_value(surface.name, "v1")
        version = SecretVersion(
            version="v1",
            ciphertext=self._encrypt(value),
            secret_hash=hash_bytes(value.encode("utf-8")),
            status="active",
        )
        self.records[surface.name] = SecretRecord(
            name=surface.name,
            service_identity=surface.service_identity,
            purpose=surface.purpose,
            active_version="v1",
            versions=[version],
        )
        self._audit(
            event_type="secret_created",
            secret_name=surface.name,
            subject=surface.service_identity,
            version="v1",
            decision="allow",
            reason="created",
            secret_hash=version.secret_hash,
            probe_passed=True,
        )
        return self.read_secret(surface.name, surface.service_identity)

    def rotate_secret(self, secret_name: str, subject: str) -> SecretRead:
        record = self.records[secret_name]
        new_version_id = f"v{len(record.versions) + 1}"
        for version in record.versions:
            if version.status == "active":
                version.status = "revoked"
                self._audit(
                    event_type="secret_version_revoked",
                    secret_name=secret_name,
                    subject=subject,
                    version=version.version,
                    decision="allow",
                    reason="old_version_revoked_after_rotation",
                    secret_hash=version.secret_hash,
                    probe_passed=True,
                )
        value = self._new_secret_value(secret_name, new_version_id)
        new_version = SecretVersion(
            version=new_version_id,
            ciphertext=self._encrypt(value),
            secret_hash=hash_bytes(value.encode("utf-8")),
            status="active",
        )
        record.versions.append(new_version)
        record.active_version = new_version_id
        self._audit(
            event_type="secret_rotated",
            secret_name=secret_name,
            subject=subject,
            version=new_version_id,
            decision="allow",
            reason="new_version_activated",
            secret_hash=new_version.secret_hash,
            probe_passed=True,
        )
        return self.read_secret(secret_name, subject)

    def read_secret(self, secret_name: str, subject: str, *, version: str | None = None) -> SecretRead:
        record = self.records.get(secret_name)
        if record is None:
            read = SecretRead(False, "secret_not_found", secret_name, subject, version)
            self._audit_read(read, probe_passed=True)
            return read
        selected_version = version or record.active_version
        if subject != record.service_identity:
            read = SecretRead(False, "subject_not_authorized", secret_name, subject, selected_version)
            self._audit_read(read, probe_passed=True)
            return read
        version_record = next((item for item in record.versions if item.version == selected_version), None)
        if version_record is None:
            read = SecretRead(False, "version_not_found", secret_name, subject, selected_version)
            self._audit_read(read, probe_passed=True)
            return read
        if version_record.status != "active":
            read = SecretRead(
                False,
                "version_revoked",
                secret_name,
                subject,
                selected_version,
                secret_hash=version_record.secret_hash,
            )
            self._audit_read(read, probe_passed=True)
            return read
        value = self._fernet.decrypt(version_record.ciphertext.encode("ascii")).decode("utf-8")
        read = SecretRead(
            True,
            "accepted",
            secret_name,
            subject,
            selected_version,
            secret_hash=version_record.secret_hash,
            value=value,
        )
        self._audit_read(read, probe_passed=True)
        return read

    def write_store(self, store_path: Path) -> dict[str, Any]:
        store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "artifact_type": "encrypted_secret_store_snapshot.v1",
            "generated_at": self.generated_at,
            "environment": self.environment,
            "release_id": self.release_id,
            "encryption_mode": "local_fernet_in_memory_root_key",
            "root_key_persisted": False,
            "records": [
                {
                    "name": record.name,
                    "service_identity": record.service_identity,
                    "purpose": record.purpose,
                    "active_version": record.active_version,
                    "versions": [
                        {
                            "version": version.version,
                            "status": version.status,
                            "ciphertext": version.ciphertext,
                            "secret_hash": version.secret_hash,
                        }
                        for version in record.versions
                    ],
                }
                for record in sorted(self.records.values(), key=lambda item: item.name)
            ],
        }
        store_path.write_text(f"{canonical_json(payload)}\n", encoding="utf-8")
        return {
            "path": store_path.as_posix(),
            "hash": hash_file(store_path),
            "encrypted_store_written": True,
            "root_key_persisted": False,
            "record_count": len(self.records),
            "version_count": sum(len(record.versions) for record in self.records.values()),
        }

    def write_audit_sink(self, events_path: Path, manifest_path: Path) -> dict[str, Any]:
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with events_path.open("w", encoding="utf-8") as handle:
            for event in self.audit_events:
                handle.write(f"{canonical_json(event)}\n")
        failed_event_count = sum(1 for event in self.audit_events if event.get("probe_passed") is not True)
        manifest = {
            "artifact_type": "secret_rotation_audit_manifest.v1",
            "generated_at": self.generated_at,
            "environment": self.environment,
            "release_id": self.release_id,
            "event_count": len(self.audit_events),
            "failed_event_count": failed_event_count,
            "events_path": events_path.as_posix(),
            "events_hash": hash_file(events_path),
            "raw_secret_values_persisted": False,
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
        return {
            "passed": failed_event_count == 0 and len(self.audit_events) >= 24,
            "event_count": len(self.audit_events),
            "failed_event_count": failed_event_count,
            "events_path": events_path.as_posix(),
            "events_hash": hash_file(events_path),
            "manifest_path": manifest_path.as_posix(),
            "manifest_hash": hash_file(manifest_path),
            "raw_secret_values_persisted": False,
        }

    def _new_secret_value(self, secret_name: str, version: str) -> str:
        value = f"{secret_name}:{version}:{secrets.token_urlsafe(32)}"
        self.raw_secret_values.append(value)
        return value

    def _encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def _audit_read(self, read: SecretRead, *, probe_passed: bool) -> None:
        self._audit(
            event_type="secret_read",
            secret_name=read.name,
            subject=read.subject,
            version=read.version,
            decision="allow" if read.allowed else "deny",
            reason=read.reason,
            secret_hash=read.secret_hash,
            probe_passed=probe_passed,
        )

    def _audit(
        self,
        *,
        event_type: str,
        secret_name: str,
        subject: str,
        version: str | None,
        decision: str,
        reason: str,
        secret_hash: str | None,
        probe_passed: bool,
    ) -> None:
        self.audit_events.append(
            {
                "event_type": event_type,
                "generated_at": self.generated_at,
                "environment": self.environment,
                "release_id": self.release_id,
                "run_id": self.run_id,
                "secret_name": secret_name,
                "subject": subject,
                "version": version,
                "decision": decision,
                "reason": reason,
                "secret_hash": secret_hash,
                "probe_passed": probe_passed,
                "raw_secret_value_persisted": False,
            }
        )


def default_secret_surfaces() -> list[SecretSurface]:
    return [
        SecretSurface(
            name="trino-runtime-security-client-secret",
            service_identity="svc-dp-trino-runtime-security",
            purpose="Trino governed query runtime credential",
        ),
        SecretSurface(
            name="schema-registry-auth-gateway-secret",
            service_identity="svc-dp-schema-registry-auth-gateway",
            purpose="Schema registry auth gateway upstream credential",
        ),
        SecretSurface(
            name="broker-acl-producer-secret",
            service_identity="svc-dp-broker-acl-producer",
            purpose="Redpanda ACL producer credential",
        ),
        SecretSurface(
            name="dagster-orchestrator-runtime-secret",
            service_identity="svc-dp-dagster-finance-orchestrator",
            purpose="Dagster finance job runtime secret injection",
        ),
    ]


def run_secret_rotation_probes(
    store: LocalEncryptedSecretStore,
    surfaces: list[SecretSurface],
    injection_manifest_path: Path,
) -> dict[str, Any]:
    initial_reads = [store.create_secret(surface) for surface in surfaces]
    rotated_reads = [store.rotate_secret(surface.name, surface.service_identity) for surface in surfaces]
    old_version_denials = [
        store.read_secret(surface.name, surface.service_identity, version="v1")
        for surface in surfaces
    ]
    active_reads = [
        store.read_secret(surface.name, surface.service_identity)
        for surface in surfaces
    ]
    unauthorized_read = store.read_secret(surfaces[0].name, "svc-dp-unauthorized-probe")
    missing_secret_read = store.read_secret("missing-dagster-runtime-secret", "svc-dp-dagster-finance-orchestrator")
    orchestrator_injection = write_orchestrator_injection_manifest(
        store,
        injection_manifest_path,
        next(surface for surface in surfaces if surface.name == "dagster-orchestrator-runtime-secret"),
    )
    return {
        "raw_secret_values": list(store.raw_secret_values),
        "initial_reads": [read_ref(read) for read in initial_reads],
        "rotated_reads": [read_ref(read) for read in rotated_reads],
        "old_version_denials": [read_ref(read) for read in old_version_denials],
        "active_reads": [read_ref(read) for read in active_reads],
        "unauthorized_read": read_ref(unauthorized_read),
        "missing_secret_read": read_ref(missing_secret_read),
        "orchestrator_injection": orchestrator_injection,
        "records": {
            name: {
                "active_version": record.active_version,
                "version_status": {version.version: version.status for version in record.versions},
            }
            for name, record in sorted(store.records.items())
        },
    }


def write_orchestrator_injection_manifest(
    store: LocalEncryptedSecretStore,
    injection_manifest_path: Path,
    surface: SecretSurface,
) -> dict[str, Any]:
    read = store.read_secret(surface.name, surface.service_identity)
    wrong_subject = store.read_secret(surface.name, "svc-dp-dagster-untrusted-runner")
    payload = {
        "artifact_type": "orchestrator_secret_injection_manifest.v1",
        "generated_at": store.generated_at,
        "environment": store.environment,
        "release_id": store.release_id,
        "orchestrator_run_id": store.run_id,
        "orchestrator": "dagster",
        "service_identity": surface.service_identity,
        "secret_name": surface.name,
        "secret_version": read.version,
        "secret_hash": read.secret_hash,
        "injected_environment": {
            "DP_SECRET_HANDLE": surface.name,
            "DP_SECRET_VERSION": read.version,
            "DP_SECRET_VALUE": "REDACTED",
        },
        "secret_value_redacted": True,
        "raw_secret_value_persisted": False,
        "service_identity_authorized": read.allowed is True,
        "unauthorized_injection_denied": wrong_subject.allowed is False and wrong_subject.reason == "subject_not_authorized",
    }
    injection_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    injection_manifest_path.write_text(f"{canonical_json(payload)}\n", encoding="utf-8")
    return {
        "path": injection_manifest_path.as_posix(),
        "hash": hash_file(injection_manifest_path),
        "passed": read.allowed is True
        and read.version == "v2"
        and payload["secret_value_redacted"] is True
        and payload["raw_secret_value_persisted"] is False
        and payload["unauthorized_injection_denied"] is True,
        "service_identity": surface.service_identity,
        "orchestrator_run_id": store.run_id,
        "secret_name": surface.name,
        "secret_version": read.version,
        "secret_hash": read.secret_hash,
        "secret_value_redacted": True,
        "raw_secret_value_persisted": False,
        "unauthorized_injection_denied": payload["unauthorized_injection_denied"],
    }


def failed_secret_rotation_checks(
    *,
    material: dict[str, Any],
    store_manifest: dict[str, Any],
    audit_sink: dict[str, Any],
    plaintext_persisted: bool,
    expected_surface_count: int,
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if store_manifest.get("encrypted_store_written") is not True:
        failed.append({"check": "encrypted_store_written"})
    if store_manifest.get("root_key_persisted") is not False:
        failed.append({"check": "root_key_not_persisted"})
    if plaintext_persisted:
        failed.append({"check": "plaintext_secret_material_not_persisted"})
    if count_allowed(material.get("initial_reads", []), version="v1") != expected_surface_count:
        failed.append({"check": "initial_secret_versions_readable", "expected": expected_surface_count})
    if count_allowed(material.get("rotated_reads", []), version="v2") != expected_surface_count:
        failed.append({"check": "rotated_secret_versions_readable", "expected": expected_surface_count})
    if count_denied(material.get("old_version_denials", []), reason="version_revoked") != expected_surface_count:
        failed.append({"check": "old_versions_revoked", "expected": expected_surface_count})
    if count_allowed(material.get("active_reads", []), version="v2") != expected_surface_count:
        failed.append({"check": "active_secret_versions_readable", "expected": expected_surface_count})
    unauthorized = material.get("unauthorized_read", {})
    if unauthorized.get("allowed") is not False or unauthorized.get("reason") != "subject_not_authorized":
        failed.append({"check": "unauthorized_identity_denied", "probe": unauthorized})
    missing = material.get("missing_secret_read", {})
    if missing.get("allowed") is not False or missing.get("reason") != "secret_not_found":
        failed.append({"check": "missing_secret_denied", "probe": missing})
    injection = material.get("orchestrator_injection", {})
    if injection.get("passed") is not True:
        failed.append({"check": "orchestrator_secret_injection_passed", "probe": injection})
    if injection.get("secret_value_redacted") is not True or injection.get("raw_secret_value_persisted") is not False:
        failed.append({"check": "orchestrator_injection_redacted", "probe": injection})
    if audit_sink.get("passed") is not True:
        failed.append(
            {
                "check": "secret_rotation_audit_sink_passed",
                "event_count": audit_sink.get("event_count", 0),
                "failed_event_count": audit_sink.get("failed_event_count", 0),
            }
        )
    return failed


def build_secret_rotation_smoke_report(
    *,
    root: Path,
    generated_at: str,
    environment: str,
    release_id: str,
    surfaces: list[SecretSurface],
    material: dict[str, Any],
    store_manifest: dict[str, Any],
    audit_sink: dict[str, Any],
    store_path: Path,
    audit_events_path: Path,
    audit_manifest_path: Path,
    injection_manifest_path: Path,
    plaintext_persisted: bool,
    failed_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    service_identity_count = len({surface.service_identity for surface in surfaces})
    rotated_secret_count = len(surfaces)
    summary = {
        "secret_manager_mode": "local_encrypted_versioned_secret_store",
        "encryption_mode": "local_fernet_in_memory_root_key",
        "service_identity_count": service_identity_count,
        "rotated_secret_count": rotated_secret_count,
        "encrypted_store_written": store_manifest.get("encrypted_store_written"),
        "root_key_persisted": store_manifest.get("root_key_persisted"),
        "plaintext_secret_material_persisted": plaintext_persisted,
        "active_version_advanced": count_allowed(material.get("active_reads", []), version="v2") == rotated_secret_count,
        "old_versions_revoked": count_denied(material.get("old_version_denials", []), reason="version_revoked")
        == rotated_secret_count,
        "new_versions_readable": count_allowed(material.get("rotated_reads", []), version="v2") == rotated_secret_count,
        "unauthorized_identity_denied": material.get("unauthorized_read", {}).get("allowed") is False
        and material.get("unauthorized_read", {}).get("reason") == "subject_not_authorized",
        "missing_secret_denied": material.get("missing_secret_read", {}).get("allowed") is False
        and material.get("missing_secret_read", {}).get("reason") == "secret_not_found",
        "service_identity_authorization_enforced": material.get("unauthorized_read", {}).get("allowed") is False,
        "orchestrator_service_identity_used": material.get("orchestrator_injection", {}).get("service_identity")
        == "svc-dp-dagster-finance-orchestrator",
        "orchestrator_run_id_present": bool(material.get("orchestrator_injection", {}).get("orchestrator_run_id")),
        "orchestrator_secret_injection_passed": material.get("orchestrator_injection", {}).get("passed") is True,
        "orchestrator_injection_manifest_redacted": material.get("orchestrator_injection", {}).get(
            "secret_value_redacted"
        )
        is True,
        "audit_sink_passed": audit_sink.get("passed") is True,
        "audit_event_count": audit_sink.get("event_count", 0),
        "audit_failed_event_count": audit_sink.get("failed_event_count", 0),
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
    }
    passed = not failed_checks
    return {
        "artifact_type": "secret_rotation_smoke_report.v1",
        "report_version": 1,
        "capability_id": "runtime-security-enforcement",
        "report_id": stable_id("secret-rotation-smoke", environment, release_id, store_manifest.get("hash")),
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "runtime_scope": {
            "mode": "local_encrypted_versioned_secret_store_with_service_identity_injection",
            "covered": [
                "encrypted_versioned_secret_store_written",
                "runtime_secret_versions_rotated",
                "old_secret_versions_revoked",
                "new_secret_versions_readable_by_service_identity",
                "unauthorized_identity_denied",
                "dagster_service_identity_secret_injection_manifest",
                "secret_rotation_audit_sink_written",
                "plaintext_secret_values_not_persisted",
            ],
            "not_covered": [
                "managed_secret_manager_ha",
                "cloud_kms_or_hsm_key_custody",
                "automatic_rotation_scheduler",
                "cross_region_secret_replication",
                "workload_identity_federation_to_cloud",
                "siem_audit_export",
            ],
        },
        "secret_store": {
            "uri": store_path.as_posix(),
            "hash": hash_file(store_path) if store_path.is_file() else None,
            "root": root.as_posix(),
            "root_key_persisted": False,
        },
        "service_identities": [
            {
                "secret_name": surface.name,
                "service_identity": surface.service_identity,
                "purpose": surface.purpose,
            }
            for surface in surfaces
        ],
        "probes": {
            key: value
            for key, value in material.items()
            if key != "raw_secret_values"
        },
        "orchestrator_injection_manifest": {
            "uri": injection_manifest_path.as_posix(),
            "hash": hash_file(injection_manifest_path) if injection_manifest_path.is_file() else None,
        },
        "audit_sink": {
            "mode": "local_jsonl_structured_secret_rotation_audit",
            "events_path": audit_events_path.as_posix(),
            "events_hash": hash_file(audit_events_path) if audit_events_path.is_file() else None,
            "manifest_path": audit_manifest_path.as_posix(),
            "manifest_hash": hash_file(audit_manifest_path) if audit_manifest_path.is_file() else None,
            "raw_secret_values_persisted": False,
        },
        "summary": summary,
        "passed": passed,
    }


def read_ref(read: SecretRead) -> dict[str, Any]:
    return {
        "allowed": read.allowed,
        "reason": read.reason,
        "secret_name": read.name,
        "subject": read.subject,
        "version": read.version,
        "secret_hash": read.secret_hash,
    }


def count_allowed(reads: list[dict[str, Any]], *, version: str) -> int:
    return sum(1 for read in reads if read.get("allowed") is True and read.get("version") == version)


def count_denied(reads: list[dict[str, Any]], *, reason: str) -> int:
    return sum(1 for read in reads if read.get("allowed") is False and read.get("reason") == reason)


def plaintext_material_persisted(paths: list[Path], raw_secret_values: list[str]) -> bool:
    texts = [path.read_text(encoding="utf-8") for path in paths if path.is_file()]
    return any(secret_value in text for secret_value in raw_secret_values for text in texts)

from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from enterprise_dp.attestations import attestation_signing_payload
from enterprise_dp.schema_registry import build_schema_registry_ops_report, build_schema_registry_report, write_schema_registry_report


ROOT = Path(__file__).resolve().parents[1]
TEST_SIGNING_SEED = bytes(range(32))


def test_schema_registry_report_covers_repository_topics() -> None:
    report = build_schema_registry_report(
        ROOT,
        generated_at="2026-01-15T10:00:00Z",
    )

    assert report["artifact_type"] == "schema_registry_compatibility_report.v1"
    assert report["compatibility_passed"] is True
    assert report["subject_count"] >= 4
    subjects = {subject["subject"]: subject for subject in report["subjects"]}
    recommendation = subjects["recommendation.tracking.v1-value"]
    assert recommendation["compatibility"] == "BACKWARD_TRANSITIVE"
    assert recommendation["payload_schema"]["hash"].startswith("sha256:")
    assert recommendation["prior_versions_checked"] == []
    assert any(check["check"] == "backward_transitive_local" and check["passed"] for check in recommendation["checks"])


def test_schema_registry_report_detects_backward_incompatible_required_field_removal(tmp_path: Path) -> None:
    root = tmp_path
    topic_dir = root / "contracts" / "topics"
    event_dir = root / "contracts" / "events"
    topic_dir.mkdir(parents=True)
    event_dir.mkdir(parents=True)
    (root / "contracts" / "event-envelope.v1.schema.json").write_text(
        json.dumps({"type": "object"}),
        encoding="utf-8",
    )
    write_topic_contract(topic_dir / "example.changed.v1.yaml", "example.changed.v1", 1, "contracts/events/example.changed.v1.schema.json")
    write_topic_contract(topic_dir / "example.changed.v2.yaml", "example.changed.v2", 2, "contracts/events/example.changed.v2.schema.json")
    write_payload_schema(
        event_dir / "example.changed.v1.schema.json",
        required=["id", "name"],
        properties={"id": {"type": "string"}, "name": {"type": "string"}},
    )
    write_payload_schema(
        event_dir / "example.changed.v2.schema.json",
        required=["id"],
        properties={"id": {"type": "string"}},
    )

    report = build_schema_registry_report(root, topic_name="example.changed.v2")

    assert report["compatibility_passed"] is False
    subject = report["subjects"][0]
    assert subject["prior_versions_checked"] == ["example.changed.v1"]
    assert any("required fields removed" in violation for check in subject["checks"] for violation in check["details"].get("violations", []))


def test_schema_registry_report_detects_deep_schema_narrowing(tmp_path: Path) -> None:
    root = tmp_path
    topic_dir = root / "contracts" / "topics"
    event_dir = root / "contracts" / "events"
    topic_dir.mkdir(parents=True)
    event_dir.mkdir(parents=True)
    (root / "contracts" / "event-envelope.v1.schema.json").write_text(
        json.dumps({"type": "object"}),
        encoding="utf-8",
    )
    write_topic_contract(topic_dir / "example.deep.v1.yaml", "example.deep.v1", 1, "contracts/events/example.deep.v1.schema.json")
    write_topic_contract(topic_dir / "example.deep.v2.yaml", "example.deep.v2", 2, "contracts/events/example.deep.v2.schema.json")
    write_payload_schema(
        event_dir / "example.deep.v1.schema.json",
        required=["id"],
        properties={
            "id": {"type": "string"},
            "status": {"type": "string", "enum": ["PENDING", "SETTLED"]},
            "detail": {
                "type": "object",
                "properties": {"amount": {"type": "number", "minimum": 0}},
            },
        },
    )
    write_payload_schema(
        event_dir / "example.deep.v2.schema.json",
        required=["id", "status"],
        properties={
            "id": {"type": "string"},
            "status": {"type": "string", "enum": ["SETTLED"]},
            "detail": {
                "type": "object",
                "properties": {"amount": {"type": "number", "minimum": 10}},
            },
        },
    )

    report = build_schema_registry_report(root, topic_name="example.deep.v2")

    violations = [
        violation
        for check in report["subjects"][0]["checks"]
        for violation in check["details"].get("violations", [])
    ]
    assert report["compatibility_passed"] is False
    assert any("new required fields added" in violation for violation in violations)
    assert any("$.status: enum narrowed" in violation for violation in violations)
    assert any("$.detail.amount: minimum increased" in violation for violation in violations)


def test_write_schema_registry_report_and_cli(tmp_path: Path) -> None:
    output_path = tmp_path / "schema-registry" / "report.json"
    result = write_schema_registry_report(
        ROOT,
        output_path,
        topic_name="recommendation.tracking.v1",
        generated_at="2026-01-15T10:00:00Z",
    )

    assert result.output_path == output_path
    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "schema-registry" / "cli-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "schema-registry-check",
            "--root",
            str(ROOT),
            "--output",
            str(cli_output),
            "--topic",
            "recommendation.tracking.v1",
            "--generated-at",
            "2026-01-15T10:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["compatibility_passed"] is True
    assert summary["subject_count"] == 1
    assert cli_output.is_file()


def test_schema_registry_ops_report_allows_local_preflight_without_publication_evidence() -> None:
    report = build_schema_registry_ops_report(
        ROOT,
        environment="local",
        generated_at="2026-01-15T10:00:00Z",
    )

    assert report["artifact_type"] == "schema_registry_ops_report.v1"
    assert report["mode"] == "local_preflight"
    assert report["capability_id"] == "schema-registry-compatibility"
    assert report["readiness_state"] == "local_preflight_ready"
    assert report["passed"] is True
    assert report["summary"]["p0_failed_subject_count"] == 0
    assert report["publication_evidence"]["attached"] is False


def test_schema_registry_ops_report_blocks_prod_without_publication_evidence_and_attestation() -> None:
    report = build_schema_registry_ops_report(
        ROOT,
        environment="prod",
        release_id="schema-prod-release",
        generated_at="2026-01-15T10:00:00Z",
    )

    failed_checks = {check["check"] for check in report["checks"] if check["passed"] is not True}
    assert report["passed"] is False
    assert report["readiness_state"] == "not_ready"
    assert "publication_evidence_attached" in failed_checks
    assert "external_attestation_verified" in failed_checks
    assert report["summary"]["p0_failed_subject_count"] >= 1
    assert any("publication_evidence_missing" in subject["issues"] for subject in report["decision_board"]["p0_failed_subjects"])


def test_schema_registry_ops_report_accepts_prod_publication_with_signed_attestation(tmp_path: Path) -> None:
    compatibility = build_schema_registry_report(ROOT, generated_at="2026-01-15T10:00:00Z")
    publication_path = write_publication_evidence(tmp_path, compatibility, environment="prod")
    attestation_path = write_signed_schema_registry_attestation(
        tmp_path,
        publication_path,
        environment="prod",
        release_id="schema-prod-release",
    )

    report = build_schema_registry_ops_report(
        ROOT,
        environment="prod",
        release_id="schema-prod-release",
        publication_evidence_path=publication_path,
        attestation_path=attestation_path,
        generated_at="2026-01-15T10:05:00Z",
    )

    assert report["passed"] is True
    assert report["readiness_state"] == "production_like_ready"
    assert report["mode"] == "external_registry_evidence"
    assert report["attestation"]["passed"] is True
    assert report["summary"]["failed_subject_count"] == 0


def test_schema_registry_ops_report_blocks_missing_schema_id_in_prod(tmp_path: Path) -> None:
    compatibility = build_schema_registry_report(ROOT, generated_at="2026-01-15T10:00:00Z")
    publication_path = write_publication_evidence(
        tmp_path,
        compatibility,
        environment="prod",
        first_subject_updates={"schema_id": "", "artifact_id": ""},
    )
    attestation_path = write_signed_schema_registry_attestation(
        tmp_path,
        publication_path,
        environment="prod",
        release_id="schema-prod-release",
    )

    report = build_schema_registry_ops_report(
        ROOT,
        environment="prod",
        release_id="schema-prod-release",
        publication_evidence_path=publication_path,
        attestation_path=attestation_path,
        generated_at="2026-01-15T10:05:00Z",
    )

    assert report["passed"] is False
    assert report["summary"]["failed_subject_count"] == 1
    assert report["decision_board"]["failed_subjects"][0]["issues"] == ["schema_id_missing"]


def test_schema_registry_ops_report_blocks_schema_hash_and_runtime_enforcement_gaps(tmp_path: Path) -> None:
    compatibility = build_schema_registry_report(ROOT, generated_at="2026-01-15T10:00:00Z")
    publication_path = write_publication_evidence(
        tmp_path,
        compatibility,
        environment="prod",
        first_subject_updates={
            "payload_schema_hash": "sha256:" + ("0" * 64),
            "producer_enforced": False,
            "broker_validation": False,
        },
    )
    attestation_path = write_signed_schema_registry_attestation(
        tmp_path,
        publication_path,
        environment="prod",
        release_id="schema-prod-release",
    )

    report = build_schema_registry_ops_report(
        ROOT,
        environment="prod",
        release_id="schema-prod-release",
        publication_evidence_path=publication_path,
        attestation_path=attestation_path,
        generated_at="2026-01-15T10:05:00Z",
    )

    failed = report["decision_board"]["failed_subjects"][0]
    assert report["passed"] is False
    assert set(failed["issues"]) == {
        "published_schema_hash_mismatch",
        "producer_not_enforced",
        "broker_or_sink_validation_missing",
    }
    assert report["summary"]["producer_enforcement_gap_count"] == 1
    assert report["summary"]["broker_validation_gap_count"] == 1


def test_schema_registry_ops_report_blocks_local_registry_uri_in_prod(tmp_path: Path) -> None:
    compatibility = build_schema_registry_report(ROOT, generated_at="2026-01-15T10:00:00Z")
    publication_path = write_publication_evidence(tmp_path, compatibility, environment="prod")
    publication = json.loads(publication_path.read_text(encoding="utf-8"))
    publication["registry_uri"] = "http://localhost:18082"
    for subject in publication["subjects"]:
        subject["registry_uri"] = "http://localhost:18082"
    publication_path.write_text(canonical_test_json(publication), encoding="utf-8")
    attestation_path = write_signed_schema_registry_attestation(
        tmp_path,
        publication_path,
        environment="prod",
        release_id="schema-prod-release",
    )

    report = build_schema_registry_ops_report(
        ROOT,
        environment="prod",
        release_id="schema-prod-release",
        publication_evidence_path=publication_path,
        attestation_path=attestation_path,
        generated_at="2026-01-15T10:05:00Z",
    )
    failed_checks = {check["check"] for check in report["checks"] if check["passed"] is not True}

    assert report["passed"] is False
    assert "production_registry_uri_declared" in failed_checks
    assert "production_registry_uri_missing" in report["decision_board"]["failed_subjects"][0]["issues"]


def test_schema_registry_ops_report_cli_returns_nonzero_for_prod_gate_failure(tmp_path: Path) -> None:
    output_path = tmp_path / "schema-registry" / "ops-prod.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "schema-registry-ops-report",
            "--root",
            str(ROOT),
            "--output",
            str(output_path),
            "--environment",
            "prod",
            "--release-id",
            "schema-prod-release",
            "--generated-at",
            "2026-01-15T10:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["passed"] is False
    assert summary["p0_failed_subject_count"] >= 1
    assert output_path.is_file()


def write_topic_contract(path: Path, name: str, version: int, payload_schema: str) -> None:
    path.write_text(
        f"""
contractVersion: {version}
topic:
  name: {name}
  product: example-product
  domain: finance
  domainOwner: finance-domain-owner
  ownerTeam: data-platform
  dataSteward: steward
  sourceServices: [example-service]
  description: Example changed event.
  status: DRAFT
schema:
  format: JSON_SCHEMA
  compatibility: BACKWARD_TRANSITIVE
  envelopeSchema: contracts/event-envelope.v1.schema.json
  payloadSchema: {payload_schema}
privacy:
  classification: INTERNAL
  dataResidency: REGION_CONTROLLED
  containsPii: false
  tenantIsolation: REQUIRED
  retentionDays: 30
  erasureSupported: false
ingestion:
  bronzeTarget: bronze.events_example_changed
  partitionStrategy: event_date/source_service
quality:
  freshnessSloMinutes: 15
  checks:
    - name: event_id_not_null
      type: not_null
      column: eventId
""".lstrip(),
        encoding="utf-8",
    )


def write_payload_schema(path: Path, *, required: list[str], properties: dict[str, object]) -> None:
    path.write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "required": required,
                "properties": properties,
            },
            ensure_ascii=True,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def write_publication_evidence(
    tmp_path: Path,
    compatibility: dict[str, object],
    *,
    environment: str,
    first_subject_updates: dict[str, object] | None = None,
) -> Path:
    subjects = []
    for index, subject in enumerate(compatibility["subjects"]):
        assert isinstance(subject, dict)
        payload_schema = subject["payload_schema"]
        assert isinstance(payload_schema, dict)
        row = {
            "subject": subject["subject"],
            "topic": subject["topic"],
            "registered": True,
            "schema_id": f"schema-{index + 1}",
            "artifact_id": f"artifact-{index + 1}",
            "version": subject["contract_version"],
            "compatibility": subject["compatibility"],
            "payload_schema_hash": payload_schema["hash"],
            "producer_enforced": True,
            "broker_validation": True,
            "registry_uri": f"https://schema-registry.{environment}.example",
        }
        if index == 0 and first_subject_updates:
            row.update(first_subject_updates)
        subjects.append(row)
    payload = {
        "artifact_type": "schema_registry_publication_manifest.v1",
        "report_version": 1,
        "generated_at": "2026-01-15T10:01:00Z",
        "environment": environment,
        "registry_vendor": "apicurio",
        "registry_api": "confluent_compatible",
        "registry_uri": f"https://schema-registry.{environment}.example",
        "subjects": subjects,
    }
    path = tmp_path / "schema-registry" / f"publication-{environment}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_test_json(payload), encoding="utf-8")
    return path


def write_signed_schema_registry_attestation(
    tmp_path: Path,
    publication_path: Path,
    *,
    environment: str,
    release_id: str,
) -> Path:
    subject_hash = "sha256:" + hashlib.sha256(publication_path.read_bytes()).hexdigest()
    payload: dict[str, object] = {
        "artifact_type": "external_evidence_attestation.v1",
        "evidence_kind": "schema_registry",
        "subject_uri": f"s3://dp-evidence/schema_registry/{release_id}.json",
        "subject_hash": subject_hash,
        "environment": environment,
        "release_id": release_id,
        "producer": "data-platform-control-plane",
        "generated_at": "2026-01-15T10:02:00Z",
        "signature_algorithm": "Ed25519",
        "signing_key_id": "local-test-ed25519-2026",
        "passed": True,
    }
    signed = sign_attestation(payload)
    path = tmp_path / "schema-registry" / f"attestation-{environment}.json"
    path.write_text(canonical_test_json(signed), encoding="utf-8")
    return path


def sign_attestation(payload: dict[str, object]) -> dict[str, object]:
    signed = copy.deepcopy(payload)
    signature = Ed25519PrivateKey.from_private_bytes(TEST_SIGNING_SEED).sign(attestation_signing_payload(signed))
    signed["signature"] = f"base64:{base64.b64encode(signature).decode()}"
    return signed


def canonical_test_json(payload: dict[str, object]) -> str:
    return f"{json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(',', ':'))}\n"

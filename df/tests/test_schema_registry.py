from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_df.schema_registry import build_schema_registry_report, write_schema_registry_report


ROOT = Path(__file__).resolve().parents[1]


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
            "enterprise_df.cli",
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

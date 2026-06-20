from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.control_tower import write_data_product_control_tower_report
from enterprise_dp.incidents import build_incident_report, validate_incident_report, validate_incident_registry


ROOT = Path(__file__).resolve().parents[1]


def test_incident_report_turns_control_tower_blockers_into_operational_queue(tmp_path: Path) -> None:
    control_tower_path = tmp_path / "control-tower.json"
    write_data_product_control_tower_report(
        ROOT,
        control_tower_path,
        generated_at="2026-06-16T11:00:00Z",
    )

    report = build_incident_report(
        control_tower_path,
        generated_at="2026-06-16T11:05:00Z",
    )

    assert report["artifact_type"] == "incident_slo_report.v1"
    assert report["readiness_state"] == "incident_action_required"
    assert report["passed"] is False
    assert report["summary"]["incident_count"] >= 1
    assert report["summary"]["open_p0_count"] >= 1
    assert report["decision_board"]["page_now"]
    assert any(incident["category"] == "platform_capability" for incident in report["incidents"])
    assert any(incident["runbook"] == "dp/ops-runbooks/data-platform-p0-gates.md" for incident in report["incidents"])

    validation = validate_incident_report(report)
    assert validation.errors == []


def test_incident_report_preserves_existing_registry_state_and_sla_age(tmp_path: Path) -> None:
    control_tower_path = tmp_path / "control-tower.json"
    write_data_product_control_tower_report(
        ROOT,
        control_tower_path,
        generated_at="2026-06-16T11:00:00Z",
    )
    first_report = build_incident_report(control_tower_path, generated_at="2026-06-16T11:05:00Z")
    first_incident = first_report["incidents"][0]
    registry = tmp_path / "incidents.yaml"
    registry.write_text(
        "\n".join(
            [
                "incidents:",
                f"  - id: {first_incident['incident_id']}",
                f"    fingerprint: {first_incident['fingerprint']}",
                "    severity: P0",
                "    state: INVESTIGATING",
                "    ownerTeam: data-platform-sre",
                "    assignee: sre-oncall",
                "    openedAt: '2026-06-16T08:00:00Z'",
                "    slaTargetMinutes: 120",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = validate_incident_registry(tmp_path)
    assert result.errors == []

    report = build_incident_report(
        control_tower_path,
        incident_registry_path=registry,
        generated_at="2026-06-16T11:05:00Z",
    )
    incident = next(item for item in report["incidents"] if item["fingerprint"] == first_incident["fingerprint"])

    assert incident["state"] == "INVESTIGATING"
    assert incident["assignee"] == "sre-oncall"
    assert incident["owner_team"] == "data-platform-sre"
    assert incident["sla_age_minutes"] == 185
    assert incident["sla_state"] == "BREACHED"
    assert incident["escalation_required"] is True
    assert report["summary"]["sla_breached_count"] >= 1


def test_incident_report_cli_fails_when_open_p0_incidents_exist(tmp_path: Path) -> None:
    control_tower_path = tmp_path / "control-tower.json"
    output_path = tmp_path / "incidents.json"
    write_data_product_control_tower_report(
        ROOT,
        control_tower_path,
        generated_at="2026-06-16T11:00:00Z",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "incident-report",
            "--control-tower-report",
            str(control_tower_path),
            "--output",
            str(output_path),
            "--generated-at",
            "2026-06-16T11:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert output_path.is_file()
    summary = json.loads(completed.stdout)
    assert summary["passed"] is False
    assert summary["summary"]["open_p0_count"] >= 1
    assert summary["page_now"]

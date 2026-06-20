from __future__ import annotations

import json
from pathlib import Path

from enterprise_dp.secret_rotation_smoke import write_secret_rotation_smoke_report


ROOT = Path(__file__).resolve().parents[1]


def test_secret_rotation_smoke_verifies_rotation_injection_and_redaction(tmp_path: Path) -> None:
    result = write_secret_rotation_smoke_report(
        ROOT,
        tmp_path / "secret-rotation-smoke-report.json",
        output_dir=tmp_path / "secret-rotation-run",
        release_id="secret-rotation-review-pack",
        generated_at="2026-01-15T09:15:20Z",
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    summary = report["summary"]
    store_text = Path(report["secret_store"]["uri"]).read_text(encoding="utf-8")
    audit_text = Path(report["audit_sink"]["events_path"]).read_text(encoding="utf-8")
    injection_text = Path(report["orchestrator_injection_manifest"]["uri"]).read_text(encoding="utf-8")
    injection = json.loads(injection_text)

    assert report["artifact_type"] == "secret_rotation_smoke_report.v1"
    assert report["passed"] is True
    assert summary["secret_manager_mode"] == "local_encrypted_versioned_secret_store"
    assert summary["service_identity_count"] == 4
    assert summary["rotated_secret_count"] == 4
    assert summary["active_version_advanced"] is True
    assert summary["old_versions_revoked"] is True
    assert summary["new_versions_readable"] is True
    assert summary["unauthorized_identity_denied"] is True
    assert summary["missing_secret_denied"] is True
    assert summary["orchestrator_service_identity_used"] is True
    assert summary["orchestrator_run_id_present"] is True
    assert summary["orchestrator_secret_injection_passed"] is True
    assert summary["orchestrator_injection_manifest_redacted"] is True
    assert summary["plaintext_secret_material_persisted"] is False
    assert summary["audit_sink_passed"] is True
    assert report["secret_store"]["root_key_persisted"] is False
    assert injection["service_identity"] == "svc-dp-dagster-finance-orchestrator"
    assert injection["secret_version"] == "v2"
    assert injection["secret_value_redacted"] is True
    assert injection["raw_secret_value_persisted"] is False
    assert injection["unauthorized_injection_denied"] is True
    assert "managed_secret_manager_ha" in report["runtime_scope"]["not_covered"]
    assert "cloud_kms_or_hsm_key_custody" in report["runtime_scope"]["not_covered"]
    assert "REDACTED" in injection_text
    assert "secret-rotation-review-pack" in audit_text
    assert '"raw_secret_values":' not in json.dumps(report)
    assert "DP_SECRET_VALUE" in injection_text
    assert "gAAAA" in store_text
    assert "gAAAA" not in audit_text

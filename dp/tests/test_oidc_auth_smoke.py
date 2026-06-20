from __future__ import annotations

import json
from pathlib import Path

from enterprise_dp.oidc_auth_smoke import write_oidc_auth_smoke_report


ROOT = Path(__file__).resolve().parents[1]


def test_oidc_auth_smoke_verifies_jwks_claims_denials_and_redacted_audit(tmp_path: Path) -> None:
    result = write_oidc_auth_smoke_report(
        ROOT,
        tmp_path / "oidc-auth-smoke-report.json",
        output_dir=tmp_path / "oidc-run",
        release_id="oidc-review-pack",
        generated_at="2026-01-15T09:15:20Z",
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    summary = report["summary"]
    audit_text = Path(report["audit_sink"]["events_path"]).read_text(encoding="utf-8")
    audit_events = [json.loads(line) for line in audit_text.splitlines() if line.strip()]

    assert report["artifact_type"] == "oidc_auth_smoke_report.v1"
    assert report["passed"] is True
    assert summary["jwks_key_published"] is True
    assert summary["rs256_signature_validation_passed"] is True
    assert summary["issuer_validation_passed"] is True
    assert summary["audience_validation_passed"] is True
    assert summary["expiry_validation_passed"] is True
    assert summary["required_role_denied"] is True
    assert summary["unknown_kid_denied"] is True
    assert summary["missing_token_denied"] is True
    assert summary["audit_sink_passed"] is True
    assert summary["audit_event_count"] == 8
    assert summary["raw_access_tokens_persisted"] is False
    assert summary["private_key_persisted"] is False
    assert report["issuer"]["jwks"]["keys"][0]["alg"] == "RS256"
    assert report["issuer"]["private_key_persisted"] is False
    assert "enterprise_keycloak_realm_deployment" in report["runtime_scope"]["not_covered"]
    assert "production_secret_rotation" in report["runtime_scope"]["not_covered"]
    assert all("token_hash" in event for event in audit_events)
    assert "access_token" not in audit_text
    assert "eyJ" not in audit_text

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from enterprise_dp.policy_decision_smoke import write_policy_decision_smoke_report


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-01-15T09:15:20Z"


def test_policy_decision_smoke_verifies_opa_decisions_and_maker_checker(tmp_path: Path) -> None:
    server = FakeOpaServer()
    try:
        result = write_policy_decision_smoke_report(
            ROOT,
            tmp_path / "policy-decision-smoke-report.json",
            output_dir=tmp_path / "policy-decision-run",
            release_id="policy-decision-test",
            generated_at=GENERATED_AT,
            start_runtime=False,
            pdp_url=server.url,
            wait_interval_seconds=0,
        )
    finally:
        server.close()

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert report == result.report
    assert report["artifact_type"] == "policy_decision_smoke_report.v1"
    assert report["passed"] is True
    assert report["summary"]["pdp"] == "opa"
    assert report["summary"]["decision_api_reachable"] is True
    assert report["summary"]["finance_reader_allowed"] is True
    assert report["summary"]["unauthorized_default_denied"] is True
    assert report["summary"]["row_filter_decision_present"] is True
    assert report["summary"]["column_mask_decision_present"] is True
    assert report["summary"]["policy_admin_approval_passed"] is True
    assert report["summary"]["policy_admin_self_approval_denied"] is True
    assert report["summary"]["policy_admin_missing_evidence_denied"] is True
    assert report["summary"]["audit_sink_passed"] is True
    assert report["summary"]["audit_event_count"] == 6
    assert "keycloak_or_oidc_authentication" in report["runtime_scope"]["not_covered"]
    assert "production_secret_rotation" in report["runtime_scope"]["not_covered"]
    assert Path(report["audit_sink"]["events_path"]).is_file()
    assert Path(report["audit_sink"]["manifest_path"]).is_file()


class FakeOpaServer:
    def __init__(self) -> None:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/health":
                    self._write_json(200, {})
                    return
                self._write_json(404, {"error": "not found"})

            def do_POST(self) -> None:  # noqa: N802
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or "0")).decode("utf-8"))
                input_payload = payload.get("input", {})
                if input_payload.get("action") == "approve_policy_change":
                    change = input_payload.get("change", {})
                    approver = input_payload.get("approver", {})
                    denials = []
                    if change.get("requester") == approver.get("subject"):
                        denials.append("maker_checker_conflict")
                    if not change.get("evidence_hash"):
                        denials.append("missing_evidence")
                    approved = not denials and "policy_approver" in approver.get("roles", [])
                    self._write_json(
                        200,
                        {
                            "result": {
                                "approve_policy_change": approved,
                                "policy_admin_denials": denials,
                            }
                        },
                    )
                    return
                roles = input_payload.get("user", {}).get("roles", [])
                allowed = "finance_reader" in roles
                result = {"allow": allowed}
                if allowed:
                    result["row_filter"] = {"org_id": input_payload.get("user", {}).get("org_id")}
                    result["mask"] = [] if "pii_cleartext" in roles else input_payload.get("resource", {}).get("pii", [])
                else:
                    result["deny_reasons"] = ["not_authorized"]
                    result["row_filter"] = {}
                    result["mask"] = []
                self._write_json(200, {"result": result})

            def log_message(self, format: str, *args) -> None:
                return

            def _write_json(self, status: int, payload: dict) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from enterprise_dp.schema_registry_auth_smoke import (
    DENIED_TOKEN,
    PUBLISHER_TOKEN,
    READER_TOKEN,
    write_schema_registry_auth_smoke_report,
)


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-01-15T09:15:20Z"


def test_schema_registry_auth_smoke_enforces_allow_deny_and_audit(tmp_path: Path) -> None:
    upstream = FakeSchemaRegistryServer()
    try:
        result = write_schema_registry_auth_smoke_report(
            ROOT,
            tmp_path / "schema-registry-auth-smoke-report.json",
            output_dir=tmp_path / "run",
            registry_url=upstream.url,
            gateway_port=0,
            release_id="schema-auth-unit",
            generated_at=GENERATED_AT,
            start_runtime=False,
            wait_interval_seconds=0,
        )
    finally:
        upstream.close()

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    report_text = json.dumps(report, sort_keys=True)

    assert report == result.report
    assert report["artifact_type"] == "schema_registry_auth_smoke_report.v1"
    assert report["passed"] is True
    assert report["summary"]["auth_gateway_enforced"] is True
    assert report["summary"]["missing_token_denied"] is True
    assert report["summary"]["unknown_token_denied"] is True
    assert report["summary"]["denied_token_blocked"] is True
    assert report["summary"]["reader_write_denied"] is True
    assert report["summary"]["publisher_publish_allowed"] is True
    assert report["summary"]["publisher_config_allowed"] is True
    assert report["summary"]["reader_read_allowed"] is True
    assert report["summary"]["reader_read_schema_hash_matches"] is True
    assert report["summary"]["authorization_audit_event_count"] >= 7
    assert "production_registry_ha_storage" in report["runtime_scope"]["not_covered"]
    assert "production_secret_rotation" in report["runtime_scope"]["not_covered"]
    assert PUBLISHER_TOKEN not in report_text
    assert READER_TOKEN not in report_text
    assert DENIED_TOKEN not in report_text
    assert any(event["decision"] == "deny" and event["reason"] == "missing_bearer_token" for event in report["authorization_audit_log"])
    assert any(event["decision"] == "allow" and event["principal"] == "dp_schema_registry_publisher" for event in report["authorization_audit_log"])


class FakeSchemaRegistryServer:
    def __init__(self) -> None:
        self.schema = b"{}"
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/apis/registry/v2/system/info":
                    self._write_json(200, {"name": "apicurio-registry", "version": "2.6.5.Final"})
                    return
                if self.path.endswith("/versions/latest/schema"):
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(parent.schema)))
                    self.end_headers()
                    self.wfile.write(parent.schema)
                    return
                self._write_json(404, {"error": "not found"})

            def do_POST(self) -> None:  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or "0")).decode("utf-8"))
                parent.schema = str(body["schema"]).encode("utf-8")
                self._write_json(200, {"id": 77})

            def do_PUT(self) -> None:  # noqa: N802
                self.rfile.read(int(self.headers.get("Content-Length") or "0"))
                self._write_json(200, {"compatibility": "BACKWARD_TRANSITIVE"})

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

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from enterprise_dp.schema_registry_auth_smoke import hash_bytes
from enterprise_dp.schema_registry_storage_smoke import (
    build_schema_registry_storage_smoke_report,
    run_storage_probes,
)


GENERATED_AT = "2026-01-15T09:15:20Z"


def test_schema_registry_storage_probes_cross_replica_read_after_write() -> None:
    store: dict[str, dict] = {}
    replica_a = FakeSharedRegistryServer(store)
    replica_b = FakeSharedRegistryServer(store)
    http_log: list[dict] = []
    try:
        probes = run_storage_probes(
            replica_a.url,
            replica_b.url,
            group_id="unit-storage-smoke",
            subject="unit.storage-value",
            http_log=http_log,
        )
        probes["replica_a_after_restart"] = probes["replica_b_read_after_write"]
        report = build_schema_registry_storage_smoke_report(
            generated_at=GENERATED_AT,
            environment="local",
            release_id="unit-storage",
            sql_image="apicurio/apicurio-registry-sql:2.6.5.Final",
            postgres_image="postgres:16-alpine",
            registry_a_url=replica_a.url,
            registry_b_url=replica_b.url,
            group_id="unit-storage-smoke",
            subject="unit.storage-value",
            network="unit",
            registry_a_info={"name": "apicurio-registry"},
            registry_b_info={"name": "apicurio-registry"},
            probes=probes,
            command_log=[],
            http_log=http_log,
            failed_checks=[],
        )
    finally:
        replica_a.close()
        replica_b.close()

    assert probes["replica_a_publish"]["passed"] is True
    assert probes["replica_a_set_compatibility"]["passed"] is True
    assert probes["replica_b_read_after_write"]["passed"] is True
    assert probes["replica_b_read_after_write"]["checks"]["schema_hash_matches"] is True
    assert report["artifact_type"] == "schema_registry_storage_smoke_report.v1"
    assert report["summary"]["storage_backend"] == "postgresql"
    assert report["summary"]["registry_replica_count"] == 2
    assert report["summary"]["secret_env_files_persisted"] is False
    assert report["registry"]["storage"]["secret_env_files_persisted"] is False
    assert report["summary"]["cross_replica_read_after_write_passed"] is True
    assert "managed_ha_postgres_or_database_cluster" in report["runtime_scope"]["not_covered"]


class FakeSharedRegistryServer:
    def __init__(self, store: dict[str, dict]) -> None:
        parent = self
        self.store = store

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/apis/registry/v2/system/info":
                    self._write_json(200, {"name": "apicurio-registry", "version": "2.6.5.Final"})
                    return
                subject = extract_subject(self.path)
                if subject not in parent.store:
                    self._write_json(404, {"error": "not found"})
                    return
                item = parent.store[subject]
                if self.path.endswith("/versions/latest/schema"):
                    body = item["schema"].encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if "/versions/latest" in self.path:
                    self._write_json(200, {"id": item["id"], "subject": subject, "version": 1, "schemaType": "JSON"})
                    return
                if "/config/" in self.path:
                    self._write_json(200, {"compatibilityLevel": item.get("compatibility")})
                    return
                self._write_json(404, {"error": "not found"})

            def do_POST(self) -> None:  # noqa: N802
                subject = extract_subject(self.path)
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or "0")).decode("utf-8"))
                parent.store[subject] = {
                    "id": str(len(parent.store) + 1),
                    "schema": payload["schema"],
                    "schema_hash": hash_bytes(payload["schema"].encode("utf-8")),
                    "compatibility": None,
                }
                self._write_json(200, {"id": parent.store[subject]["id"]})

            def do_PUT(self) -> None:  # noqa: N802
                subject = extract_subject(self.path)
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or "0")).decode("utf-8"))
                parent.store.setdefault(subject, {"id": "1", "schema": "{}", "compatibility": None})
                parent.store[subject]["compatibility"] = payload.get("compatibility")
                self._write_json(200, {"compatibility": payload.get("compatibility")})

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


def extract_subject(path: str) -> str:
    marker = "/subjects/"
    if marker not in path:
        return ""
    suffix = path.split(marker, 1)[1]
    return suffix.split("/", 1)[0]

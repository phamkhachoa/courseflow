from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request

import enterprise_dp.schema_registry_runtime_smoke as smoke
from enterprise_dp.event_backbone_smoke import CommandResult


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-01-15T09:15:20Z"
TOPIC = "finance.benefit_settled.v1"
SUBJECT = f"{TOPIC}-value"


def test_schema_registry_runtime_smoke_publishes_and_reads_back_subject(monkeypatch, tmp_path: Path) -> None:
    fake_http = FakeApicurioCcompat()
    monkeypatch.setattr(smoke, "urlopen", fake_http)

    result = smoke.write_schema_registry_runtime_smoke_report(
        ROOT,
        tmp_path / "schema-registry-runtime-smoke-report.json",
        output_dir=tmp_path / "run",
        topic_name=TOPIC,
        release_id="schema-runtime-test",
        generated_at=GENERATED_AT,
        command_runner=fake_runner,
        wait_interval_seconds=0,
    )
    report = json.loads(result.output_path.read_text(encoding="utf-8"))

    assert report == result.report
    assert report["artifact_type"] == "schema_registry_runtime_smoke_report.v1"
    assert report["passed"] is True
    assert report["registry"]["api"] == "confluent_compatible_v7"
    assert report["summary"]["subject_count"] == 1
    assert report["summary"]["published_subject_count"] == 1
    assert report["summary"]["readback_passed_count"] == 1
    assert report["summary"]["hash_match_count"] == 1
    assert report["publication_manifest"]["artifact_type"] == "schema_registry_publication_manifest.v1"
    subject = report["subjects"][0]
    assert subject["subject"] == SUBJECT
    assert subject["schema_id"] == "42"
    assert subject["version"] == 1
    assert subject["compatibility"] == "BACKWARD_TRANSITIVE"
    assert subject["compatibility_configured"] is True
    assert subject["payload_schema_hash_matches"] is True
    assert fake_http.paths.count(f"/apis/ccompat/v7/subjects/{SUBJECT}/versions") == 1


def test_schema_registry_runtime_smoke_fails_when_readback_hash_differs(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(smoke, "urlopen", FakeApicurioCcompat(schema_override=b"{}"))

    result = smoke.write_schema_registry_runtime_smoke_report(
        ROOT,
        tmp_path / "schema-registry-runtime-smoke-report.json",
        output_dir=tmp_path / "run",
        topic_name=TOPIC,
        release_id="schema-runtime-fail",
        generated_at=GENERATED_AT,
        command_runner=fake_runner,
        wait_interval_seconds=0,
    )

    assert result.report["passed"] is False
    assert result.report["summary"]["hash_match_count"] == 0
    assert any(item["check"] == "subject_readback_hash_matches" for item in result.report["summary"]["failed_checks"])


def fake_runner(args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
    assert "schema-registry" in args
    return CommandResult(tuple(args), 0, "started", "")


class FakeApicurioCcompat:
    def __init__(self, *, schema_override: bytes | None = None) -> None:
        self.schema = schema_override or (ROOT / "contracts/events/finance.benefit_settled.v1.schema.json").read_bytes()
        self.paths: list[str] = []

    def __call__(self, request: Request, timeout: int):
        path = request.full_url.split("http://fake.local", 1)[-1]
        if path.startswith("http://"):
            path = "/" + path.split("/", 3)[3]
        self.paths.append(path)
        method = request.get_method()
        if method == "GET" and path == "/apis/registry/v2/system/info":
            return FakeResponse(200, {"name": "apicurio-registry", "version": "2.6.5.Final"})
        if method == "POST" and path == f"/apis/ccompat/v7/subjects/{SUBJECT}/versions":
            return FakeResponse(200, {"id": 42})
        if method == "PUT" and path == f"/apis/ccompat/v7/config/{SUBJECT}":
            return FakeResponse(200, {"compatibility": "BACKWARD_TRANSITIVE"})
        if method == "GET" and path == f"/apis/ccompat/v7/config/{SUBJECT}":
            return FakeResponse(200, {"compatibilityLevel": "BACKWARD_TRANSITIVE"})
        if method == "GET" and path == f"/apis/ccompat/v7/subjects/{SUBJECT}/versions/latest":
            return FakeResponse(200, {"id": 42, "subject": SUBJECT, "version": 1, "schemaType": "JSON"})
        if method == "GET" and path == f"/apis/ccompat/v7/subjects/{SUBJECT}/versions/latest/schema":
            return FakeResponse(200, self.schema, raw=True)
        raise AssertionError(f"unexpected request: {method} {path}")


class FakeResponse:
    def __init__(self, status: int, payload, *, raw: bool = False) -> None:
        self.status = status
        self.payload = payload if raw else json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def read(self) -> bytes:
        return self.payload

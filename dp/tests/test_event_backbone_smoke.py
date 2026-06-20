from __future__ import annotations

import json
from pathlib import Path

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.contracts import load_yaml
from enterprise_dp.event_backbone_smoke import CommandResult, write_event_backbone_smoke_report


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "finance" / "benefit_settled.jsonl"


def write_schema_registry_runtime_report(path: Path) -> Path:
    registry = load_yaml(ROOT / "platform" / "ingestion" / "source-registry.yaml")
    subjects: list[dict[str, object]] = []
    seen: set[str] = set()
    for source in registry["sources"]:
        if source.get("priority") != "P0":
            continue
        canonical = source["canonical"]
        subject = canonical["schemaSubject"]
        if subject in seen:
            continue
        seen.add(subject)
        topic = canonical["topic"]
        topic_contract = load_yaml(ROOT / "contracts" / "topics" / f"{topic}.yaml")
        payload_schema_path = ROOT / topic_contract["schema"]["payloadSchema"]
        subjects.append(
            {
                "subject": subject,
                "topic": topic,
                "registered": True,
                "schema_id": f"local-schema-{len(subjects) + 1}",
                "version": 1,
                "registry_uri": "http://localhost:18082",
                "payload_schema_hash": hash_file(payload_schema_path),
            }
        )
    report = {
        "artifact_type": "schema_registry_runtime_smoke_report.v1",
        "passed": True,
        "summary": {"subject_count": len(subjects)},
        "subjects": subjects,
    }
    path.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return path


def test_event_backbone_smoke_round_trips_records_and_runs_data_plane(tmp_path: Path) -> None:
    calls: list[list[str]] = []
    produced_by_topic: dict[str, str] = {}

    def fake_runner(args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        calls.append(args)
        if args[-1] == "redpanda":
            return CommandResult(tuple(args), 0, "started", "")
        if "create" in args:
            return CommandResult(tuple(args), 0, "created", "")
        if "produce" in args:
            assert input_text is not None
            topic = args[-1]
            produced_by_topic[topic] = input_text
            return CommandResult(tuple(args), 0, "produced", "")
        if "consume" in args:
            topic = args[args.index("consume") + 1]
            return CommandResult(tuple(args), 0, produced_by_topic[topic], "")
        if "group" in args and "describe" in args:
            group = args[-1]
            topic = group.removesuffix(".group")
            return CommandResult(tuple(args), 0, fake_group_describe(topic), "")
        raise AssertionError(f"unexpected command: {args}")

    result = write_event_backbone_smoke_report(
        ROOT,
        tmp_path / "event-backbone-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="event-backbone-smoke-test",
        generated_at="2026-01-15T09:15:20Z",
        ingested_at="2026-01-15T09:15:05Z",
        built_at="2026-01-15T09:15:10Z",
        evaluation_time="2026-01-15T09:15:15Z",
        schema_registry_runtime_report_path=write_schema_registry_runtime_report(
            tmp_path / "schema-registry-runtime-smoke-report.json"
        ),
        command_runner=fake_runner,
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))

    assert report == result.report
    assert report["artifact_type"] == "event_backbone_smoke_report.v1"
    assert report["passed"] is True
    assert report["summary"]["source_record_count"] == 4
    assert report["summary"]["consumed_record_count"] == 4
    assert report["summary"]["p0_source_round_trip_count"] == 8
    assert report["summary"]["source_round_trip_failed_count"] == 0
    assert report["summary"]["sink_schema_validation_passed"] is True
    assert report["summary"]["sink_schema_validated_source_count"] == 8
    assert report["summary"]["sink_schema_validation_failed_count"] == 0
    assert report["summary"]["producer_schema_id_guard_passed"] is True
    assert report["summary"]["producer_schema_id_guarded_source_count"] == 8
    assert report["summary"]["producer_schema_id_guard_failed_count"] == 0
    assert report["summary"]["multi_partition_rebalance_passed"] is True
    assert report["summary"]["multi_partition_topic_partition_count"] == 3
    assert report["summary"]["multi_partition_consumed_partition_count"] == 3
    assert report["summary"]["multi_partition_group_total_lag"] == 0
    assert report["summary"]["data_plane_smoke_passed"] is True
    assert report["summary"]["ingestion_runtime_report_passed"] is True
    assert report["multi_partition_probe"]["passed"] is True
    assert report["multi_partition_probe"]["produced_partition_counts"] == {"0": 2, "1": 2, "2": 2}
    assert report["multi_partition_probe"]["consumed_partition_counts"] == {"0": 2, "1": 2, "2": 2}
    assert "multi_partition_rebalance" not in report["runtime_scope"]["not_covered"]
    assert len(report["source_round_trips"]) == 8
    assert all(item["schema_validation"]["passed"] is True for item in report["source_round_trips"])
    assert all(item["producer_schema_id_guard"]["passed"] is True for item in report["source_round_trips"])
    assert all(item["producer_schema_id_guard"]["schema_id"] for item in report["source_round_trips"])
    assert all(
        "schemaId" in json.loads(text.splitlines()[0])["headers"]
        for text in produced_by_topic.values()
        if text.strip() and text.lstrip().startswith("{")
    )
    assert any(item["normalization"]["required"] is True for item in report["source_round_trips"])
    assert report["data_plane_smoke"]["exists"] is True
    assert report["ingestion_runtime"]["exists"] is True
    assert report["ingestion_runtime"]["passed"] is True
    assert report["ingestion_runtime"]["mode"] == "runtime_evidence"
    assert Path(report["ingestion_runtime"]["path"]).is_file()
    assert len(report["commands"]) == 29
    assert any("produce" in command for command in calls)
    assert any("consume" in command for command in calls)


def test_event_backbone_smoke_recreates_existing_topic(tmp_path: Path) -> None:
    create_attempts = 0
    produced_by_topic: dict[str, str] = {}

    def fake_runner(args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        nonlocal create_attempts
        if args[-1] == "redpanda":
            return CommandResult(tuple(args), 0, "started", "")
        if "create" in args:
            create_attempts += 1
            if create_attempts == 1:
                return CommandResult(tuple(args), 1, "TOPIC_ALREADY_EXISTS: The topic has already been created", "")
            return CommandResult(tuple(args), 0, "created", "")
        if "delete" in args:
            return CommandResult(tuple(args), 0, "deleted", "")
        if "produce" in args:
            assert input_text is not None
            produced_by_topic[args[-1]] = input_text
            return CommandResult(tuple(args), 0, "produced", "")
        if "consume" in args:
            topic = args[args.index("consume") + 1]
            return CommandResult(tuple(args), 0, produced_by_topic[topic], "")
        if "group" in args and "describe" in args:
            group = args[-1]
            topic = group.removesuffix(".group")
            return CommandResult(tuple(args), 0, fake_group_describe(topic), "")
        raise AssertionError(f"unexpected command: {args}")

    result = write_event_backbone_smoke_report(
        ROOT,
        tmp_path / "event-backbone-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="event-backbone-smoke-existing-topic",
        generated_at="2026-01-15T09:15:20Z",
        command_runner=fake_runner,
    )

    steps = [command["step"] for command in result.report["commands"]]

    assert result.report["passed"] is True
    assert create_attempts == 10
    assert "topic_delete_existing" in steps
    assert "topic_create_retry" in steps
    assert result.report["summary"]["consumed_record_count"] == 4
    assert result.report["summary"]["p0_source_round_trip_count"] == 8
    assert result.report["summary"]["sink_schema_validation_passed"] is True
    assert result.report["summary"]["multi_partition_rebalance_passed"] is True
    assert result.report["summary"]["ingestion_runtime_report_passed"] is True


def test_event_backbone_smoke_writes_failed_report_when_redpanda_unavailable(tmp_path: Path) -> None:
    def failing_runner(args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        return CommandResult(tuple(args), 1, "", "Cannot connect to the Docker daemon")

    result = write_event_backbone_smoke_report(
        ROOT,
        tmp_path / "failed-event-backbone-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="event-backbone-smoke-fail",
        generated_at="2026-01-15T09:15:20Z",
        command_runner=failing_runner,
    )

    assert result.report["passed"] is False
    assert result.report["summary"]["failed_check_count"] == 1
    assert result.report["summary"]["consumed_record_count"] == 0
    assert result.report["summary"]["ingestion_runtime_report_passed"] is False
    assert result.report["ingestion_runtime"]["exists"] is False
    assert result.output_path.is_file()


def fake_group_describe(topic: str) -> str:
    return f"""GROUP        fake-group
COORDINATOR  0
STATE        Empty
BALANCER
MEMBERS      0
TOTAL-LAG    0

TOPIC  PARTITION  CURRENT-OFFSET  LOG-START-OFFSET  LOG-END-OFFSET  LAG   MEMBER-ID  CLIENT-ID  HOST
{topic}  0          2               0                 2               0
{topic}  1          2               0                 2               0
{topic}  2          2               0                 2               0
"""

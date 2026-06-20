from __future__ import annotations

import json
from pathlib import Path

from enterprise_dp.catalog import canonical_json
from enterprise_dp.event_backbone_smoke import CommandResult, read_jsonl
from enterprise_dp.transactional_outbox_smoke import write_transactional_outbox_smoke_report


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RECORDS = read_jsonl(ROOT / "samples" / "finance" / "benefit_settled.jsonl")


class TransactionalOutboxFakeRunner:
    def __init__(self, query_records: list[dict] | None = None) -> None:
        self.query_records = query_records if query_records is not None else SOURCE_RECORDS
        self.produced_by_topic: dict[str, str] = {}
        self.seed_sql = ""

    def __call__(self, args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        if "up" in args and "iceberg-postgres" in args and "redpanda" in args:
            return CommandResult(tuple(args), 0, "started", "")
        if "psql" in args and input_text is not None:
            self.seed_sql = input_text
            return CommandResult(tuple(args), 0, "seeded", "")
        if "psql" in args and "-c" in args:
            rows = "\n".join(
                f"{index}\t{canonical_json(record)}" for index, record in enumerate(self.query_records, start=1)
            )
            return CommandResult(tuple(args), 0, f"{rows}\n", "")
        if "create" in args:
            return CommandResult(tuple(args), 0, "created", "")
        if "produce" in args:
            assert input_text is not None
            self.produced_by_topic[args[-1]] = input_text
            return CommandResult(tuple(args), 0, "produced", "")
        if "consume" in args:
            topic = args[args.index("consume") + 1]
            return CommandResult(tuple(args), 0, self.produced_by_topic[topic], "")
        raise AssertionError(f"unexpected command: {args}")


def test_transactional_outbox_smoke_writes_postgres_to_redpanda_to_bronze_report(tmp_path: Path) -> None:
    runner = TransactionalOutboxFakeRunner()

    result = write_transactional_outbox_smoke_report(
        ROOT,
        tmp_path / "transactional-outbox-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="transactional-outbox-smoke-pass",
        generated_at="2026-01-15T09:15:20Z",
        ingested_at="2026-01-15T09:15:05Z",
        schema_id="registry:finance.benefit_settled.v1:1",
        command_runner=runner,
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    steps = [item["step"] for item in report["commands"]]

    assert report == result.report
    assert report["artifact_type"] == "transactional_outbox_smoke_report.v1"
    assert report["passed"] is True
    assert report["runtime_scope"]["mode"] == "local_postgres_transactional_outbox_to_redpanda_to_bronze"
    assert report["source"]["source_id"] == "enterprise-commerce-benefit-settled-outbox"
    assert report["source"]["source_type"] == "transactional_outbox"
    assert report["summary"]["transactional_outbox_to_bronze_passed"] is True
    assert report["summary"]["outbox_row_count"] == 4
    assert report["summary"]["connector_record_count"] == 4
    assert report["summary"]["consumed_record_count"] == 4
    assert report["summary"]["bronze_approved_new_row_count"] == 4
    assert report["summary"]["bronze_quarantine_row_count"] == 0
    assert report["summary"]["failed_check_count"] == 0
    assert "production_debezium_connector_runtime" in report["runtime_scope"]["not_covered"]
    assert "CREATE TABLE" in runner.seed_sql
    assert "postgres_seed_transactional_outbox" in steps
    assert "connector_poll_outbox_rows" in steps
    assert "transactional_outbox_topic_produce" in steps
    assert Path(report["connector_output"]["path"]).is_file()
    assert Path(report["event_backbone"]["consumed_path"]).is_file()
    assert (tmp_path / "run" / "bronze-ingestion" / "bronze" / "events_benefit_settled.jsonl").is_file()


def test_transactional_outbox_smoke_fails_when_connector_drops_outbox_rows(tmp_path: Path) -> None:
    runner = TransactionalOutboxFakeRunner(query_records=SOURCE_RECORDS[:1])

    result = write_transactional_outbox_smoke_report(
        ROOT,
        tmp_path / "transactional-outbox-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="transactional-outbox-smoke-fail",
        generated_at="2026-01-15T09:15:20Z",
        ingested_at="2026-01-15T09:15:05Z",
        command_runner=runner,
    )

    assert result.report["passed"] is False
    assert result.report["summary"]["connector_record_count"] == 1
    assert result.report["summary"]["failed_check_count"] > 0
    assert any(
        item["check"] == "transactional_outbox_connector_records_match_source"
        for item in result.report["summary"]["failed_checks"]
    )

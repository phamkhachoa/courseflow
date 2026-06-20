from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.catalog import write_catalog_bundle
from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.openlineage import (
    build_openlineage_events,
    validate_openlineage_events,
    write_openlineage_events,
)
from enterprise_dp.pipelines import run_recommendation_pipeline_from_bronze


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "recommendation" / "tracking.jsonl"
INGESTED_AT = "2026-01-15T11:00:05Z"
BUILT_AT = "2026-01-15T11:00:10Z"


def test_openlineage_export_builds_runtime_events_without_raw_payloads(tmp_path: Path) -> None:
    catalog_path = build_catalog_with_recommendation_run(tmp_path)
    bundle = json.loads(catalog_path.read_text(encoding="utf-8"))

    events = build_openlineage_events(
        bundle,
        namespace="enterprise-dp://test",
        producer="https://enterprise-dp.local/test-openlineage",
    )
    validation = validate_openlineage_events(events)

    assert validation.errors == []
    assert validation.checked_count == 2
    assert [event["eventType"] for event in events] == ["COMPLETE", "COMPLETE"]

    ingestion_event = next(event for event in events if event["job"]["name"] == "bronze_ingestion.local_jsonl.v1")
    assert ingestion_event["inputs"][0]["namespace"] == "enterprise-dp://test/topics"
    assert ingestion_event["inputs"][0]["name"] == "recommendation.tracking.v1"
    assert ingestion_event["outputs"][0]["name"] == "bronze.events_recommendation_tracking"
    assert ingestion_event["run"]["facets"]["enterpriseDp_run"]["sourcePositions"]

    pipeline_event = next(event for event in events if event["job"]["name"] == "recommendation.from_approved_bronze.v1")
    assert [dataset["name"] for dataset in pipeline_event["inputs"]] == ["bronze.events_recommendation_tracking"]
    assert [dataset["name"] for dataset in pipeline_event["outputs"]] == [
        "silver.learner_activity",
        "gold.recsys_interactions",
    ]
    gold_output = next(dataset for dataset in pipeline_event["outputs"] if dataset["name"] == "gold.recsys_interactions")
    fields = gold_output["facets"]["schema"]["fields"]
    assert any(field["name"] == "learner_id_hash" for field in fields)
    serialized = json.dumps(events, sort_keys=True)
    assert "raw_payload" not in serialized
    assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" not in serialized


def test_write_openlineage_events_and_cli_export(tmp_path: Path) -> None:
    catalog_path = build_catalog_with_recommendation_run(tmp_path)
    output_path = tmp_path / "lineage" / "openlineage.jsonl"

    result = write_openlineage_events(
        catalog_path,
        output_path,
        namespace="enterprise-dp://local-test",
        producer="https://enterprise-dp.local/test-openlineage",
    )
    records = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert result["event_count"] == 2
    assert len(records) == 2
    assert result["content_hash"].startswith("sha256:")
    assert records[0]["producer"] == "https://enterprise-dp.local/test-openlineage"

    cli_output = tmp_path / "lineage" / "cli-openlineage.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "openlineage-export",
            "--catalog",
            str(catalog_path),
            "--output",
            str(cli_output),
            "--namespace",
            "enterprise-dp://cli-test",
            "--producer",
            "https://enterprise-dp.local/cli-openlineage",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["event_count"] == 2
    assert summary["output"] == str(cli_output)
    assert cli_output.is_file()


def test_openlineage_validation_rejects_malformed_event() -> None:
    result = validate_openlineage_events(
        [
            {
                "eventType": "COMPLETE",
                "eventTime": "not-a-time",
                "producer": "",
                "schemaURL": "https://openlineage.io/spec/OpenLineage.json",
                "run": {"runId": ""},
                "job": {"namespace": "enterprise-dp://test", "name": "bad-job"},
                "inputs": [{}],
                "outputs": [],
            }
        ]
    )

    assert any("eventTime must be an ISO-8601 timestamp" in error for error in result.errors)
    assert any("producer must be a non-empty string" in error for error in result.errors)
    assert any("run.runId must be a non-empty string" in error for error in result.errors)
    assert any("inputs[0].namespace must be a non-empty string" in error for error in result.errors)


def build_catalog_with_recommendation_run(tmp_path: Path) -> Path:
    ingestion = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        SAMPLE_INPUT,
        tmp_path / "ingestion",
        ingested_at=INGESTED_AT,
        ingest_run_id="openlineage-ingest-run",
    )
    recommendation = run_recommendation_pipeline_from_bronze(
        ingestion.approved_path,
        tmp_path / "pipeline",
        upstream_manifest_path=ingestion.manifest_path,
        snapshot_id="openlineage-recsys-snapshot",
        built_at=BUILT_AT,
    )
    catalog_path = tmp_path / "catalog" / "catalog-bundle.json"
    write_catalog_bundle(
        ROOT,
        catalog_path,
        manifest_paths=[ingestion.manifest_path, recommendation.manifest_path],
        generated_at="2026-01-15T11:00:20Z",
    )
    return catalog_path

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.orchestration import run_use_case
from enterprise_dp.pipelines import PipelineRunRequest, default_pipeline_registry


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "identity" / "identity_subject_changed.jsonl"
INGESTED_AT = "2026-01-15T08:12:00Z"
BUILT_AT = "2026-01-15T08:12:05Z"
EVALUATION_TIME = "2026-01-15T08:12:10Z"


def test_identity_access_governance_pipeline_from_bronze(tmp_path: Path) -> None:
    ingestion = run_bronze_ingestion(
        ROOT,
        "compliance.identity_subject.changed.v1",
        SAMPLE_INPUT,
        tmp_path / "ingestion",
        ingested_at=INGESTED_AT,
        ingest_run_id="identity-access-ingest",
    )

    result = default_pipeline_registry().run(
        "identity.access_governance.from_approved_bronze.v1",
        PipelineRunRequest(
            input_path=ingestion.approved_path,
            output_dir=tmp_path / "pipeline",
            options={
                "upstream_manifest_path": ingestion.manifest_path,
                "snapshot_id": "identity-access-snapshot",
                "built_at": BUILT_AT,
            },
        ),
    )

    gold_rows = read_jsonl(result.gold_path)
    risk_by_subject = {row["subject_id_hash"]: row["risk_status"] for row in gold_rows}

    assert ingestion.manifest["quality_passed"] is True
    assert ingestion.manifest["approved"]["row_count"] == 3
    assert result.snapshot_id == "identity-access-snapshot"
    assert result.manifest["quality_passed"] is True
    assert result.manifest["row_count"] == 3
    assert result.manifest["layers"]["silver.identity_subject"]["row_count"] == 3
    assert result.manifest["layers"]["gold.access_risk_daily"]["row_count"] == 3
    assert result.manifest["lineage_edges"] == [
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "bronze.events_identity_subject_changed",
            "target": "silver.identity_subject",
        },
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "silver.identity_subject",
            "target": "gold.access_risk_daily",
        },
    ]
    assert risk_by_subject["aa11bb22cc33dd44ee55ff6677889900"] == "OK"
    assert risk_by_subject["bb22cc33dd44ee55ff6677889900aa11"] == "REVIEW"
    assert risk_by_subject["cc33dd44ee55ff6677889900aa11bb22"] == "CRITICAL"
    assert all(row["quality_passed"] is True for row in gold_rows)
    assert all("subject_id_hash" in row for row in gold_rows)
    assert all("email" not in row for row in gold_rows)
    assert all("user_id" not in row for row in gold_rows)


def test_run_use_case_orchestrates_identity_access_governance(tmp_path: Path) -> None:
    result = run_use_case(
        ROOT,
        SAMPLE_INPUT,
        tmp_path,
        use_case_id="identity-access-governance",
        release_id="local-identity-access-test",
        environment="local",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
        snapshot_id="identity-access-use-case-snapshot",
    )
    gates = gates_by_id(result.evidence)

    assert result.evidence["release_passed"] is True
    assert result.runner_id == "identity.access_governance.from_approved_bronze.v1"
    assert result.topic == "compliance.identity_subject.changed.v1"
    assert result.primary_output == "gold.access_risk_daily"
    assert result.evidence["input_data_products"] == ["bronze.events_identity_subject_changed"]
    assert result.evidence["output_data_products"] == ["silver.identity_subject", "gold.access_risk_daily"]
    assert result.evidence["quality_profile_id"] == "p0-identity-access-governance"
    assert gates["P0-PIPELINE-QUALITY"]["passed"] is True
    assert gates["P0-QUALITY-PROFILE"]["passed"] is True
    assert gates["P0-ACCESS-GRANT-EVIDENCE"]["passed"] is True
    assert gates["P0-RETENTION-ERASURE"]["passed"] is True
    assert gates["P0-OUTPUT-EVIDENCE"]["passed"] is True
    assert gates["P0-CATALOG-LINEAGE"]["passed"] is True
    assert result.ingestion is not None
    assert result.ingestion.manifest_path.is_file()
    assert result.pipeline.manifest_path.is_file()
    assert result.catalog_bundle_path.is_file()


def test_cli_runs_identity_access_use_case(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "run-use-case",
            "--root",
            str(ROOT),
            "--use-case-id",
            "identity-access-governance",
            "--input",
            str(SAMPLE_INPUT),
            "--output-dir",
            str(tmp_path),
            "--release-id",
            "cli-identity-access-test",
            "--environment",
            "local",
            "--ingested-at",
            INGESTED_AT,
            "--built-at",
            BUILT_AT,
            "--evaluation-time",
            EVALUATION_TIME,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["use_case_id"] == "identity-access-governance"
    assert output["runner_id"] == "identity.access_governance.from_approved_bronze.v1"
    assert output["topic"] == "compliance.identity_subject.changed.v1"
    assert output["primary_output"] == "gold.access_risk_daily"
    assert output["release_passed"] is True
    assert output["gates"]["P0-ACCESS-GRANT-EVIDENCE"] is True
    assert Path(output["evidence_path"]).is_file()


def test_identity_access_blocks_missing_subject_hash(tmp_path: Path) -> None:
    broken_input = write_mutated_sample(
        tmp_path,
        "missing-subject-hash.jsonl",
        lambda event: event["payload"].pop("subjectIdHash"),
    )

    result = run_use_case(
        ROOT,
        broken_input,
        tmp_path / "run",
        use_case_id="identity-access-governance",
        release_id="local-identity-missing-subject",
        environment="local",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
    )
    gates = gates_by_id(result.evidence)

    assert result.evidence["release_passed"] is False
    assert result.ingestion is not None
    assert result.ingestion.manifest["quality_passed"] is False
    assert result.ingestion.manifest["quarantine"]["reason_counts"]["SCHEMA_INVALID"] == 1
    assert gates["P0-PIPELINE-QUALITY"]["passed"] is False


def test_identity_access_blocks_missing_tenant_id(tmp_path: Path) -> None:
    broken_input = write_mutated_sample(
        tmp_path,
        "missing-tenant.jsonl",
        lambda event: event.pop("tenantId"),
    )

    result = run_use_case(
        ROOT,
        broken_input,
        tmp_path / "run",
        use_case_id="identity-access-governance",
        release_id="local-identity-missing-tenant",
        environment="local",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
    )
    gates = gates_by_id(result.evidence)

    assert result.evidence["release_passed"] is False
    assert result.ingestion is not None
    assert result.ingestion.manifest["quality_passed"] is True
    assert gates["P0-PIPELINE-QUALITY"]["passed"] is False
    bronze_errors = result.pipeline.manifest["layers"]["bronze.events_identity_subject_changed"]["quality_errors"]
    assert any("tenant_id_not_null" in error for error in bronze_errors)


def write_mutated_sample(tmp_path: Path, name: str, mutate) -> Path:
    events = read_jsonl(SAMPLE_INPUT)
    mutate(events[0])
    output = tmp_path / name
    output.write_text("".join(f"{json.dumps(event, sort_keys=True)}\n" for event in events), encoding="utf-8")
    return output


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def gates_by_id(evidence: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(gate["gate_id"]): gate
        for gate in evidence["gates"]
        if isinstance(gate, dict)
    }

from __future__ import annotations

import json
from pathlib import Path

from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.pipelines import PipelineRunRequest, default_pipeline_registry


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "finance" / "benefit_settled.jsonl"
INGESTED_AT = "2026-01-15T09:16:00Z"
BUILT_AT = "2026-01-15T09:16:05Z"


def test_finance_benefit_reconciliation_pipeline_from_bronze(tmp_path: Path) -> None:
    ingestion = run_bronze_ingestion(
        ROOT,
        "finance.benefit_settled.v1",
        SAMPLE_INPUT,
        tmp_path / "ingestion",
        ingested_at=INGESTED_AT,
        ingest_run_id="finance-pipeline-ingest",
    )

    result = default_pipeline_registry().run(
        "finance.benefit_reconciliation.from_approved_bronze.v1",
        PipelineRunRequest(
            input_path=ingestion.approved_path,
            output_dir=tmp_path / "pipeline",
            options={
                "upstream_manifest_path": ingestion.manifest_path,
                "snapshot_id": "finance-pipeline-snapshot",
                "built_at": BUILT_AT,
            },
        ),
    )

    gold_rows = read_jsonl(result.gold_path)
    reason_codes = {row["reconciliation_key"]: row["reason_code"] for row in gold_rows}

    assert ingestion.manifest["quality_passed"] is True
    assert ingestion.manifest["approved"]["row_count"] == 4
    assert result.snapshot_id == "finance-pipeline-snapshot"
    assert result.manifest["quality_passed"] is True
    assert result.manifest["row_count"] == 4
    assert result.manifest["layers"]["silver.finance_benefit_transactions"]["row_count"] == 4
    assert result.manifest["layers"]["gold.finance_benefit_reconciliation"]["row_count"] == 4
    assert result.manifest["lineage_edges"] == [
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "bronze.events_benefit_settled",
            "target": "silver.finance_benefit_transactions",
        },
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "silver.finance_benefit_transactions",
            "target": "gold.finance_benefit_reconciliation",
        },
    ]
    assert reason_codes["order-20260115-0001"] == "MATCHED"
    assert reason_codes["order-20260115-0002"] == "AMOUNT_MISMATCH"
    assert reason_codes["order-20260115-0003"] == "POINTS_MISMATCH"
    assert reason_codes["order-20260115-0004"] == "MISSING_REVERSE"
    assert all(row["quality_passed"] is True for row in gold_rows)
    assert all("beneficiary_id_hash" in row for row in gold_rows)
    assert all("entitlement_id" in row for row in gold_rows)
    assert all("item_id" in row for row in gold_rows)
    assert all("learner_id_hash" not in row for row in gold_rows)
    assert all("enrollment_id" not in row for row in gold_rows)
    assert all("course_id" not in row for row in gold_rows)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

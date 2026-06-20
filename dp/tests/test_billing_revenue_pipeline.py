from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.orchestration import run_use_case
from enterprise_dp.pipelines import PipelineRunRequest, default_pipeline_registry


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "billing" / "billing_transaction_settled.jsonl"
INGESTED_AT = "2026-01-15T10:16:00Z"
BUILT_AT = "2026-01-15T10:16:05Z"
EVALUATION_TIME = "2026-01-15T10:16:10Z"


def test_billing_revenue_pipeline_from_bronze(tmp_path: Path) -> None:
    ingestion = run_bronze_ingestion(
        ROOT,
        "finance.billing_transaction.settled.v1",
        SAMPLE_INPUT,
        tmp_path / "ingestion",
        ingested_at=INGESTED_AT,
        ingest_run_id="billing-revenue-ingest",
    )

    result = default_pipeline_registry().run(
        "billing.revenue_daily.from_approved_bronze.v1",
        PipelineRunRequest(
            input_path=ingestion.approved_path,
            output_dir=tmp_path / "pipeline",
            options={
                "upstream_manifest_path": ingestion.manifest_path,
                "snapshot_id": "billing-revenue-snapshot",
                "built_at": BUILT_AT,
            },
        ),
    )

    gold_rows = read_jsonl(result.gold_path)
    by_product_line = {row["product_line"]: row for row in gold_rows}

    assert ingestion.manifest["quality_passed"] is True
    assert ingestion.manifest["approved"]["row_count"] == 4
    assert result.snapshot_id == "billing-revenue-snapshot"
    assert result.manifest["quality_passed"] is True
    assert result.manifest["row_count"] == 2
    assert result.manifest["layers"]["silver.finance_billing_transactions"]["row_count"] == 4
    assert result.manifest["layers"]["gold.finance_revenue_daily"]["row_count"] == 2
    assert result.manifest["lineage_edges"] == [
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "bronze.events_billing_transaction_settled",
            "target": "silver.finance_billing_transactions",
        },
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "silver.finance_billing_transactions",
            "target": "gold.finance_revenue_daily",
        },
    ]
    assert by_product_line["subscription"]["transaction_count"] == 3
    assert by_product_line["subscription"]["invoice_count"] == 2
    assert by_product_line["subscription"]["gross_amount_cents"] == 30000
    assert by_product_line["subscription"]["discount_amount_cents"] == 1000
    assert by_product_line["subscription"]["refund_amount_cents"] == 2500
    assert by_product_line["subscription"]["net_revenue_cents"] == 26500
    assert by_product_line["subscription"]["recognized_revenue_cents"] == 11500
    assert by_product_line["subscription"]["deferred_revenue_cents"] == 15000
    assert by_product_line["subscription"]["revenue_status"] == "CLOSED"
    assert by_product_line["services"]["pending_transaction_count"] == 1
    assert by_product_line["services"]["revenue_status"] == "PENDING_SOURCE"
    assert all(row["quality_passed"] is True for row in gold_rows)
    assert all("customer_id_hash" not in row for row in gold_rows)
    assert all("account_id" not in row for row in gold_rows)
    assert all("email" not in row for row in gold_rows)
    assert all("phone" not in row for row in gold_rows)


def test_run_use_case_orchestrates_enterprise_revenue(tmp_path: Path) -> None:
    result = run_use_case(
        ROOT,
        SAMPLE_INPUT,
        tmp_path,
        use_case_id="enterprise-revenue-intelligence",
        release_id="local-billing-revenue-test",
        environment="local",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
        snapshot_id="billing-revenue-use-case-snapshot",
    )
    gates = gates_by_id(result.evidence)

    assert result.evidence["release_passed"] is True
    assert result.runner_id == "billing.revenue_daily.from_approved_bronze.v1"
    assert result.topic == "finance.billing_transaction.settled.v1"
    assert result.primary_output == "gold.finance_revenue_daily"
    assert result.evidence["input_data_products"] == ["bronze.events_billing_transaction_settled"]
    assert result.evidence["output_data_products"] == [
        "silver.finance_billing_transactions",
        "gold.finance_revenue_daily",
    ]
    assert result.evidence["quality_profile_id"] == "p0-enterprise-revenue-intelligence"
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


def test_cli_runs_enterprise_revenue_use_case(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "run-use-case",
            "--root",
            str(ROOT),
            "--use-case-id",
            "enterprise-revenue-intelligence",
            "--input",
            str(SAMPLE_INPUT),
            "--output-dir",
            str(tmp_path),
            "--release-id",
            "cli-billing-revenue-test",
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
    assert output["use_case_id"] == "enterprise-revenue-intelligence"
    assert output["runner_id"] == "billing.revenue_daily.from_approved_bronze.v1"
    assert output["topic"] == "finance.billing_transaction.settled.v1"
    assert output["primary_output"] == "gold.finance_revenue_daily"
    assert output["release_passed"] is True
    assert output["gates"]["P0-ACCESS-GRANT-EVIDENCE"] is True
    assert Path(output["evidence_path"]).is_file()


def test_enterprise_revenue_blocks_missing_customer_subject(tmp_path: Path) -> None:
    broken_input = write_mutated_sample(
        tmp_path,
        "missing-customer-subject.jsonl",
        lambda event: event["payload"].pop("customerIdHash"),
    )

    result = run_use_case(
        ROOT,
        broken_input,
        tmp_path / "run",
        use_case_id="enterprise-revenue-intelligence",
        release_id="local-billing-revenue-missing-subject",
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


def test_enterprise_revenue_blocks_direct_identifier_payload(tmp_path: Path) -> None:
    broken_input = write_mutated_sample(
        tmp_path,
        "direct-identifier.jsonl",
        lambda event: event["payload"].update({"email": "blocked@example.test"}),
    )

    result = run_use_case(
        ROOT,
        broken_input,
        tmp_path / "run",
        use_case_id="enterprise-revenue-intelligence",
        release_id="local-billing-revenue-direct-id",
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
    assert result.ingestion.manifest["quarantine"]["reason_counts"]["PII_POLICY_VIOLATION"] == 1
    assert gates["P0-PIPELINE-QUALITY"]["passed"] is False


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

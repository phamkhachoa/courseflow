from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.semantic_views import (
    build_semantic_view_manifest,
    validate_semantic_view_manifest,
    write_semantic_view_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


def test_semantic_view_manifest_builds_trino_and_dremio_views() -> None:
    manifest = build_semantic_view_manifest(ROOT, generated_at="2026-01-15T10:00:00Z")

    assert manifest["artifact_type"] == "semantic_views_manifest.v1"
    assert manifest["generated_at"] == "2026-01-15T10:00:00Z"
    assert manifest["summary"]["metric_count"] >= 9
    assert manifest["summary"]["view_count"] == manifest["summary"]["metric_count"] * 2
    assert set(manifest["summary"]["engines"]) == {"dremio", "trino"}

    revenue_view = next(
        view
        for view in manifest["views"]
        if view["metric_id"] == "revenue_net" and view["engine"] == "trino"
    )
    assert revenue_view["view_name"] == "semantic.enterprise_metrics.revenue_net"
    assert revenue_view["source_data_product"] == "gold.finance_revenue_daily"
    assert "SUM(net_revenue_cents) / 100.0 AS metric_value" in revenue_view["sql"]
    assert "WHERE quality_passed = TRUE" in revenue_view["sql"]
    assert "GROUP BY report_date, accounting_date, product_id, source_product_id, org_id, product_line, currency" in revenue_view["sql"]

    access_risk_view = next(
        view
        for view in manifest["views"]
        if view["metric_id"] == "critical_access_risk_subject_count" and view["engine"] == "dremio"
    )
    assert access_risk_view["view_name"] == "semantic.enterprise_metrics.critical_access_risk_subject_count"
    assert access_risk_view["source_data_product"] == "gold.access_risk_daily"
    assert "SUM(CASE WHEN risk_status = 'CRITICAL' THEN 1 ELSE 0 END) AS metric_value" in access_risk_view["sql"]
    assert "GROUP BY report_date, product_id, org_id" in access_risk_view["sql"]

    customer_view = next(
        view
        for view in manifest["views"]
        if view["metric_id"] == "at_risk_customer_account_count" and view["engine"] == "trino"
    )
    assert customer_view["view_name"] == "semantic.enterprise_metrics.at_risk_customer_account_count"
    assert customer_view["source_data_product"] == "gold.customer_360_profile"
    assert "SUM(CASE WHEN profile_status = 'RISK' THEN 1 ELSE 0 END) AS metric_value" in customer_view["sql"]
    assert "GROUP BY report_date, product_id, org_id" in customer_view["sql"]

    support_view = next(
        view
        for view in manifest["views"]
        if view["metric_id"] == "support_case_count" and view["engine"] == "dremio"
    )
    assert support_view["view_name"] == "semantic.enterprise_metrics.support_case_count"
    assert support_view["source_data_product"] == "gold.support_sla_daily"
    assert "SUM(case_count) AS metric_value" in support_view["sql"]
    assert "GROUP BY report_date, product_id, org_id, channel, priority" in support_view["sql"]


def test_semantic_view_manifest_can_filter_engine_and_write_file(tmp_path: Path) -> None:
    output_path = tmp_path / "serving" / "semantic-views.json"

    manifest = write_semantic_view_manifest(
        ROOT,
        output_path,
        engine="trino",
        generated_at="2026-01-15T10:00:00Z",
    )
    written = json.loads(output_path.read_text(encoding="utf-8"))

    assert written == manifest
    assert manifest["engine"] == "trino"
    assert manifest["summary"]["engines"] == ["trino"]
    assert {view["engine"] for view in manifest["views"]} == {"trino"}


def test_semantic_view_manifest_validation_rejects_bad_sql_and_duplicate_view() -> None:
    manifest = build_semantic_view_manifest(ROOT, engine="trino", generated_at="2026-01-15T10:00:00Z")
    manifest["views"].append({**manifest["views"][0]})
    manifest["views"][0]["sql"] = "SELECT 1"

    result = validate_semantic_view_manifest(manifest)

    assert any("sql must contain CREATE OR REPLACE VIEW" in error for error in result.errors)
    assert any("duplicate view" in error for error in result.errors)


def test_semantic_views_cli_export(tmp_path: Path) -> None:
    output_path = tmp_path / "cli" / "semantic-views.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "semantic-views-export",
            "--root",
            str(ROOT),
            "--output",
            str(output_path),
            "--engine",
            "dremio",
            "--generated-at",
            "2026-01-15T10:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["engine"] == "dremio"
    assert summary["view_count"] == manifest["summary"]["view_count"]
    assert {view["engine"] for view in manifest["views"]} == {"dremio"}

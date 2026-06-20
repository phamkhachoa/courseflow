from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path
import shutil
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file, load_json, write_catalog_bundle
from enterprise_dp.catalog_lineage_ops import write_catalog_lineage_ops_report
from enterprise_dp.control_tower import write_data_product_control_tower_report
from enterprise_dp.ingestion import BronzeIngestionResult, run_bronze_ingestion
from enterprise_dp.openlineage import write_openlineage_events
from enterprise_dp.orchestration import UseCaseRunResult, run_use_case
from enterprise_dp.quality_slo_ops import write_quality_slo_ops_report
from enterprise_dp.source_activation_ledger import (
    SourceActivationManifestResult,
    SourceActivationOpsReportResult,
    write_source_activation_manifest_from_bundle,
    write_source_activation_ops_report,
)
from enterprise_dp.source_bridge import SourceBridgeResult, run_source_bridge_preflight
from enterprise_dp.source_readiness_bundle import SourceReadinessBundleResult, run_source_readiness_bundle


REPORT_VERSION = 1
DEFAULT_GENERATED_AT = "2026-06-16T12:10:00Z"


@dataclass(frozen=True)
class PortfolioReleaseSpec:
    use_case_id: str
    input_path: str | Path
    release_id: str
    built_at: str
    evaluation_time: str
    ingested_at: str | None = None
    snapshot_id: str | None = None


@dataclass(frozen=True)
class PortfolioReleaseSmokeResult:
    output_path: Path
    output_dir: Path
    report: dict[str, Any]


@dataclass(frozen=True)
class SourceBridgeBronzeSpec:
    source_id: str
    topic: str
    input_path: str | Path
    bridge_run_id: str
    ingest_run_id: str
    normalized_at: str
    ingested_at: str


@dataclass(frozen=True)
class SourceBridgeBronzeResult:
    spec: SourceBridgeBronzeSpec
    bridge: SourceBridgeResult
    ingestion: BronzeIngestionResult


@dataclass(frozen=True)
class SourceActivationSpec:
    source_id: str
    input_path: str | Path
    change_request_id: str
    requested_by: str
    bundle_id: str
    generated_at: str
    ingested_at: str
    replayed_at: str
    activated_at: str
    expires_at: str


@dataclass(frozen=True)
class SourceActivationSmokeResult:
    spec: SourceActivationSpec
    bundle: SourceReadinessBundleResult
    activation: SourceActivationManifestResult


DEFAULT_RELEASE_SPECS: tuple[PortfolioReleaseSpec, ...] = (
    PortfolioReleaseSpec(
        use_case_id="customer-support-experience-intelligence",
        input_path="samples/support/support_case_changed.jsonl",
        release_id="portfolio-support-sla-local",
        ingested_at="2026-01-15T06:12:00Z",
        built_at="2026-01-15T06:12:05Z",
        evaluation_time="2026-01-15T06:12:10Z",
        snapshot_id="portfolio-support-sla-local",
    ),
    PortfolioReleaseSpec(
        use_case_id="customer-account-health",
        input_path="samples/customer/account_changed.jsonl",
        release_id="portfolio-customer-account-health-local",
        ingested_at="2026-01-15T07:12:00Z",
        built_at="2026-01-15T07:12:05Z",
        evaluation_time="2026-01-15T07:12:10Z",
        snapshot_id="portfolio-customer-account-health-local",
    ),
    PortfolioReleaseSpec(
        use_case_id="identity-access-governance",
        input_path="samples/identity/identity_subject_changed.jsonl",
        release_id="portfolio-identity-access-local",
        ingested_at="2026-01-15T08:12:00Z",
        built_at="2026-01-15T08:12:05Z",
        evaluation_time="2026-01-15T08:12:10Z",
        snapshot_id="portfolio-identity-access-local",
    ),
    PortfolioReleaseSpec(
        use_case_id="finance-benefit-reconciliation",
        input_path="samples/finance/benefit_settled.jsonl",
        release_id="portfolio-finance-benefit-local",
        ingested_at="2026-01-15T09:15:05Z",
        built_at="2026-01-15T09:15:10Z",
        evaluation_time="2026-01-15T09:15:15Z",
        snapshot_id="portfolio-finance-benefit-local",
    ),
    PortfolioReleaseSpec(
        use_case_id="ml-feature-governance",
        input_path="samples/recommendation/tracking.jsonl",
        release_id="portfolio-ml-feature-local",
        ingested_at="2026-01-15T10:10:00Z",
        built_at="2026-01-15T10:10:05Z",
        evaluation_time="2026-01-15T10:10:10Z",
        snapshot_id="portfolio-ml-feature-local",
    ),
    PortfolioReleaseSpec(
        use_case_id="enterprise-revenue-intelligence",
        input_path="samples/billing/billing_transaction_settled.jsonl",
        release_id="portfolio-enterprise-revenue-local",
        ingested_at="2026-01-15T10:16:00Z",
        built_at="2026-01-15T10:16:05Z",
        evaluation_time="2026-01-15T10:16:10Z",
        snapshot_id="portfolio-enterprise-revenue-local",
    ),
    PortfolioReleaseSpec(
        use_case_id="enterprise-kpi-scorecard",
        input_path="samples/enterprise-reporting/semantic_metric_snapshot.json",
        release_id="portfolio-enterprise-kpi-local",
        built_at="2026-01-15T11:00:00Z",
        evaluation_time="2026-01-15T11:00:05Z",
        snapshot_id="portfolio-enterprise-kpi-local",
    ),
)

SOURCE_BRIDGE_BRONZE_SPECS: tuple[SourceBridgeBronzeSpec, ...] = (
    SourceBridgeBronzeSpec(
        source_id="lms-courseflow-course-published-outbox",
        topic="course.published.v1",
        input_path="samples/source-bridge/lms_course_published_raw.jsonl",
        bridge_run_id="portfolio-lms-course-published-bridge",
        ingest_run_id="portfolio-lms-course-published-ingest",
        normalized_at="2026-01-15T08:55:00Z",
        ingested_at="2026-01-15T08:55:05Z",
    ),
    SourceBridgeBronzeSpec(
        source_id="lms-courseflow-enrollment-completed-outbox",
        topic="enrollment.completed.v1",
        input_path="samples/source-bridge/lms_enrollment_completed_raw.jsonl",
        bridge_run_id="portfolio-lms-enrollment-completed-bridge",
        ingest_run_id="portfolio-lms-enrollment-completed-ingest",
        normalized_at="2026-01-15T09:05:00Z",
        ingested_at="2026-01-15T09:05:05Z",
    ),
    SourceBridgeBronzeSpec(
        source_id="lms-courseflow-gradebook-final-grade-outbox",
        topic="gradebook.final_grade.updated.v1",
        input_path="samples/source-bridge/lms_gradebook_final_grade_raw.jsonl",
        bridge_run_id="portfolio-lms-gradebook-final-grade-bridge",
        ingest_run_id="portfolio-lms-gradebook-final-grade-ingest",
        normalized_at="2026-01-15T09:10:00Z",
        ingested_at="2026-01-15T09:10:05Z",
    ),
)

SOURCE_ACTIVATION_SPECS: tuple[SourceActivationSpec, ...] = (
    SourceActivationSpec(
        source_id="enterprise-commerce-benefit-settled-outbox",
        input_path="samples/finance/benefit_settled.jsonl",
        change_request_id="onboard_enterprise_commerce_source_local_preflight",
        requested_by="finance-platform-lead",
        bundle_id="portfolio-enterprise-commerce-benefit-source-local",
        generated_at="2026-01-19T10:00:00Z",
        ingested_at="2026-01-19T10:00:05Z",
        replayed_at="2026-01-19T10:05:05Z",
        activated_at="2026-01-19T10:10:00Z",
        expires_at="2026-07-19T10:10:00Z",
    ),
    SourceActivationSpec(
        source_id="crm-sales-account-changed-outbox",
        input_path="samples/customer/account_changed.jsonl",
        change_request_id="onboard_crm_sales_source_local_preflight",
        requested_by="customer-success-analytics-lead",
        bundle_id="portfolio-crm-sales-account-source-local",
        generated_at="2026-01-19T10:10:00Z",
        ingested_at="2026-01-19T10:10:05Z",
        replayed_at="2026-01-19T10:15:05Z",
        activated_at="2026-01-19T10:20:00Z",
        expires_at="2026-07-19T10:20:00Z",
    ),
    SourceActivationSpec(
        source_id="identity-platform-subject-changed-outbox",
        input_path="samples/identity/identity_subject_changed.jsonl",
        change_request_id="onboard_identity_platform_source_local_preflight",
        requested_by="security-compliance-lead",
        bundle_id="portfolio-identity-subject-source-local",
        generated_at="2026-01-19T10:20:00Z",
        ingested_at="2026-01-19T10:20:05Z",
        replayed_at="2026-01-19T10:25:05Z",
        activated_at="2026-01-19T10:30:00Z",
        expires_at="2026-07-19T10:30:00Z",
    ),
    SourceActivationSpec(
        source_id="lms-courseflow-course-published-outbox",
        input_path="samples/source-bridge/lms_course_published_raw.jsonl",
        change_request_id="onboard_lms_courseflow_workforce_sources_local_preflight",
        requested_by="learning-platform-sa",
        bundle_id="portfolio-lms-course-published-source-local",
        generated_at="2026-01-19T10:30:00Z",
        ingested_at="2026-01-19T10:30:05Z",
        replayed_at="2026-01-19T10:35:05Z",
        activated_at="2026-01-19T10:40:00Z",
        expires_at="2026-07-19T10:40:00Z",
    ),
    SourceActivationSpec(
        source_id="lms-courseflow-enrollment-completed-outbox",
        input_path="samples/source-bridge/lms_enrollment_completed_raw.jsonl",
        change_request_id="onboard_lms_courseflow_workforce_sources_local_preflight",
        requested_by="learning-platform-sa",
        bundle_id="portfolio-lms-enrollment-completed-source-local",
        generated_at="2026-01-19T10:40:00Z",
        ingested_at="2026-01-19T10:40:05Z",
        replayed_at="2026-01-19T10:45:05Z",
        activated_at="2026-01-19T10:50:00Z",
        expires_at="2026-07-19T10:50:00Z",
    ),
    SourceActivationSpec(
        source_id="lms-courseflow-gradebook-final-grade-outbox",
        input_path="samples/source-bridge/lms_gradebook_final_grade_raw.jsonl",
        change_request_id="onboard_lms_courseflow_workforce_sources_local_preflight",
        requested_by="learning-platform-sa",
        bundle_id="portfolio-lms-gradebook-final-grade-source-local",
        generated_at="2026-01-19T10:50:00Z",
        ingested_at="2026-01-19T10:50:05Z",
        replayed_at="2026-01-19T10:55:05Z",
        activated_at="2026-01-19T11:00:00Z",
        expires_at="2026-07-19T11:00:00Z",
    ),
    SourceActivationSpec(
        source_id="lms-courseflow-recommendation-tracking-collector",
        input_path="samples/source-bridge/lms_recommendation_tracking_raw.jsonl",
        change_request_id="onboard_lms_courseflow_recommendation_source_local_preflight",
        requested_by="ml-ai-platform-owner",
        bundle_id="portfolio-lms-recommendation-tracking-source-local",
        generated_at="2026-01-19T11:00:00Z",
        ingested_at="2026-01-19T11:00:05Z",
        replayed_at="2026-01-19T11:05:05Z",
        activated_at="2026-01-19T11:10:00Z",
        expires_at="2026-07-19T11:10:00Z",
    ),
)

CONTROL_TOWER_SPEC = PortfolioReleaseSpec(
    use_case_id="data-product-control-tower",
    input_path="__generated_control_tower__",
    release_id="portfolio-data-product-control-tower-local",
    built_at="2026-06-16T12:00:00Z",
    evaluation_time="2026-06-16T12:00:05Z",
    snapshot_id="portfolio-data-product-control-tower-local",
)


def write_portfolio_release_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    environment: str = "local",
    generated_at: str | None = None,
) -> PortfolioReleaseSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    generated = generated_at or DEFAULT_GENERATED_AT

    business_runs = [
        run_portfolio_spec(platform_root, target_dir, spec, environment=environment)
        for spec in DEFAULT_RELEASE_SPECS
    ]
    source_bridge_runs = run_source_bridge_bronze_preflights(platform_root, target_dir)
    source_activation = write_portfolio_source_activation_ops(
        platform_root,
        target_dir / "source-activation",
        environment=environment,
        generated_at=generated,
    )
    interim = write_consolidated_control_artifacts(
        platform_root,
        target_dir / "interim",
        business_runs,
        source_bridge_runs=source_bridge_runs,
        source_activation_ops_report_path=source_activation["ops_report"].output_path,
        environment=environment,
        generated_at=generated,
    )
    control_run = run_portfolio_spec(
        platform_root,
        target_dir,
        CONTROL_TOWER_SPEC,
        environment=environment,
        input_override=Path(interim["control_tower"]["uri"]),
    )
    all_runs = business_runs + [control_run]
    final = write_consolidated_control_artifacts(
        platform_root,
        target_dir / "final",
        all_runs,
        source_bridge_runs=source_bridge_runs,
        source_activation_ops_report_path=source_activation["ops_report"].output_path,
        environment=environment,
        generated_at=generated,
    )
    report = build_portfolio_release_smoke_report(
        output_dir=target_dir,
        generated_at=generated,
        environment=environment,
        runs=all_runs,
        source_bridge_runs=source_bridge_runs,
        source_activation=source_activation,
        interim_artifacts=interim,
        final_artifacts=final,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return PortfolioReleaseSmokeResult(output_path=target, output_dir=target_dir, report=report)


def run_portfolio_spec(
    root: Path,
    output_dir: Path,
    spec: PortfolioReleaseSpec,
    *,
    environment: str,
    input_override: Path | None = None,
) -> UseCaseRunResult:
    input_path = input_override or root / spec.input_path
    return run_use_case(
        root,
        input_path,
        output_dir / "runs" / spec.use_case_id,
        use_case_id=spec.use_case_id,
        release_id=spec.release_id,
        environment=environment,
        ingested_at=spec.ingested_at,
        built_at=spec.built_at,
        evaluation_time=spec.evaluation_time,
        snapshot_id=spec.snapshot_id,
        approver="data-platform-release-bot",
    )


def run_source_bridge_bronze_preflights(
    root: Path,
    output_dir: Path,
    specs: tuple[SourceBridgeBronzeSpec, ...] = SOURCE_BRIDGE_BRONZE_SPECS,
) -> list[SourceBridgeBronzeResult]:
    results: list[SourceBridgeBronzeResult] = []
    for spec in specs:
        bridge = run_source_bridge_preflight(
            root,
            spec.source_id,
            root / spec.input_path,
            output_dir / "source-bridge" / spec.source_id,
            normalized_at=spec.normalized_at,
            bridge_run_id=spec.bridge_run_id,
        )
        ingestion = run_bronze_ingestion(
            root,
            spec.topic,
            bridge.normalized_path,
            output_dir / "source-bridge-bronze" / spec.source_id,
            ingested_at=spec.ingested_at,
            ingest_run_id=spec.ingest_run_id,
        )
        results.append(SourceBridgeBronzeResult(spec=spec, bridge=bridge, ingestion=ingestion))
    return results


def write_portfolio_source_activation_ops(
    root: Path,
    output_dir: Path,
    *,
    environment: str,
    generated_at: str,
    specs: tuple[SourceActivationSpec, ...] = SOURCE_ACTIVATION_SPECS,
) -> dict[str, Any]:
    ledger_path = output_dir / "governance" / "source-activations.yaml"
    pointer_dir = output_dir / "governance" / "source-active-pointers"
    copy_source_activation_baseline(root, ledger_path, pointer_dir)
    activation_results: list[SourceActivationSmokeResult] = []
    for spec in specs:
        bundle = run_source_readiness_bundle(
            root,
            spec.source_id,
            root / spec.input_path,
            output_dir / "readiness-bundles" / spec.source_id,
            environment=environment,
            bundle_id=spec.bundle_id,
            generated_at=spec.generated_at,
            ingested_at=spec.ingested_at,
            replayed_at=spec.replayed_at,
            change_request_id=spec.change_request_id,
        )
        activation = write_source_activation_manifest_from_bundle(
            root,
            bundle.summary_path,
            output_dir / "manifests" / f"{spec.source_id}.source-activation.json",
            requested_by=spec.requested_by,
            approved_by="data-platform-lead",
            change_request_id=spec.change_request_id,
            ledger_path=ledger_path,
            active_state_path=pointer_dir / f"{spec.source_id}.{environment}.json",
            generated_at=spec.activated_at,
            expires_at=spec.expires_at,
            reason="Activate local source preflight after source-to-Bronze readiness evidence passed.",
        )
        if activation.manifest.get("passed") is not True:
            failed = [failure.get("check") for failure in activation.manifest.get("failures", []) if isinstance(failure, dict)]
            raise ValueError(f"{spec.source_id}: source activation failed checks {failed}")
        activation_results.append(SourceActivationSmokeResult(spec=spec, bundle=bundle, activation=activation))
    ops_report = write_source_activation_ops_report(
        root,
        output_dir / "source-activation-ops.json",
        environment=environment,
        ledger_path=ledger_path,
        active_pointer_dir=pointer_dir,
        generated_at=generated_at,
    )
    return {
        "ledger_path": ledger_path,
        "active_pointer_dir": pointer_dir,
        "activations": activation_results,
        "ops_report": ops_report,
    }


def copy_source_activation_baseline(root: Path, ledger_path: Path, pointer_dir: Path) -> None:
    source_ledger = root / "governance" / "source-activations.yaml"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_ledger, ledger_path)
    source_pointer_dir = root / "governance" / "source-active-pointers"
    pointer_dir.mkdir(parents=True, exist_ok=True)
    if not source_pointer_dir.is_dir():
        return
    for pointer_path in source_pointer_dir.glob("*.json"):
        shutil.copy2(pointer_path, pointer_dir / pointer_path.name)


def write_consolidated_control_artifacts(
    root: Path,
    output_dir: Path,
    runs: list[UseCaseRunResult],
    *,
    source_bridge_runs: list[SourceBridgeBronzeResult] | None = None,
    source_activation_ops_report_path: str | Path | None = None,
    environment: str,
    generated_at: str,
) -> dict[str, Any]:
    release_paths = [run.evidence_path for run in runs]
    manifest_paths = [
        path
        for run in runs
        for path in (
            run.ingestion.manifest_path if run.ingestion else None,
            run.pipeline.manifest_path,
        )
        if path is not None
    ]
    source_bridge_manifest_paths = [
        path
        for run in source_bridge_runs or []
        for path in (run.bridge.manifest_path, run.ingestion.manifest_path)
    ]
    catalog_bundle_path = output_dir / "catalog" / "catalog-bundle.json"
    write_catalog_bundle(
        root,
        catalog_bundle_path,
        manifest_paths=[*source_bridge_manifest_paths, *manifest_paths],
        generated_at=generated_at,
    )
    openlineage_path = output_dir / "lineage" / "openlineage-events.jsonl"
    openlineage_result = write_openlineage_events(catalog_bundle_path, openlineage_path)
    quality_slo_result = write_quality_slo_ops_report(
        root,
        output_dir / "quality" / "quality-slo-ops.json",
        environment=environment,
        catalog_bundle_path=catalog_bundle_path,
        release_evidence_paths=release_paths,
        generated_at=generated_at,
    )
    catalog_lineage_result = write_catalog_lineage_ops_report(
        root,
        output_dir / "catalog-lineage" / "catalog-lineage-ops.json",
        environment=environment,
        catalog_bundle_path=catalog_bundle_path,
        openlineage_events_path=openlineage_path,
        generated_at=generated_at,
    )
    control_tower_result = write_data_product_control_tower_report(
        root,
        output_dir / "control-tower" / "control-tower-with-portfolio-release.json",
        catalog_bundle_path=catalog_bundle_path,
        catalog_lineage_ops_report_path=catalog_lineage_result.output_path,
        quality_slo_ops_report_path=quality_slo_result.output_path,
        source_activation_ops_report_path=source_activation_ops_report_path,
        release_evidence_paths=release_paths,
        environment=environment,
        generated_at=generated_at,
    )
    return {
        "catalog_bundle": artifact_ref(catalog_bundle_path, load_json(catalog_bundle_path)),
        "openlineage_events": {
            "uri": openlineage_path.as_posix(),
            "hash": hash_file(openlineage_path),
            "event_count": openlineage_result["event_count"],
            "catalog_bundle_hash": openlineage_result["catalog_bundle_hash"],
        },
        "quality_slo_ops": artifact_ref(quality_slo_result.output_path, quality_slo_result.report),
        "catalog_lineage_ops": artifact_ref(catalog_lineage_result.output_path, catalog_lineage_result.report),
        "source_activation_ops": artifact_ref(source_activation_ops_report_path, load_json(source_activation_ops_report_path))
        if source_activation_ops_report_path
        else {"attached": False},
        "control_tower": artifact_ref(control_tower_result.output_path, control_tower_result.report),
    }


def build_portfolio_release_smoke_report(
    *,
    output_dir: Path,
    generated_at: str,
    environment: str,
    runs: list[UseCaseRunResult],
    source_bridge_runs: list[SourceBridgeBronzeResult],
    source_activation: dict[str, Any],
    interim_artifacts: dict[str, Any],
    final_artifacts: dict[str, Any],
) -> dict[str, Any]:
    release_artifacts = [release_artifact(run) for run in runs]
    source_bridge_artifacts = [source_bridge_artifact(run) for run in source_bridge_runs]
    source_activation_artifacts = [
        source_activation_artifact(item)
        for item in source_activation.get("activations", [])
        if isinstance(item, SourceActivationSmokeResult)
    ]
    final_control = load_json(Path(final_artifacts["control_tower"]["uri"]))
    final_summary = final_control.get("summary") if isinstance(final_control.get("summary"), dict) else {}
    coverage = final_summary.get("gold_release_coverage") if isinstance(final_summary.get("gold_release_coverage"), dict) else {}
    failed = [artifact for artifact in release_artifacts if artifact.get("release_passed") is not True]
    report = {
        "artifact_type": "portfolio_release_smoke_report.v1",
        "report_version": REPORT_VERSION,
        "generated_at": generated_at,
        "environment": environment,
        "output_dir": output_dir.as_posix(),
        "runtime_scope": {
            "mode": "local_portfolio_release_smoke",
            "covered": [
                "multi_use_case_release_evidence",
                "consolidated_catalog_bundle",
                "openlineage_events_from_run_manifests",
                "quality_slo_ops_with_release_evidence",
                "control_tower_with_portfolio_release_evidence",
            ],
            "not_covered": [
                "live_orchestrator_run_history",
                "iceberg_table_commit",
                "production_catalog_publish_receipt",
                "production_runtime_quality_observability",
            ],
        },
        "release_evidence": release_artifacts,
        "source_bridge_bronze_evidence": source_bridge_artifacts,
        "source_activation_evidence": source_activation_artifacts,
        "artifacts": {
            "source_activation_ops": artifact_ref(
                source_activation["ops_report"].output_path,
                source_activation["ops_report"].report,
            ),
            "interim": interim_artifacts,
            "final": final_artifacts,
        },
        "summary": {
            "use_case_count": len(runs),
            "release_evidence_count": len(release_artifacts),
            "source_bridge_preflight_count": len(source_bridge_artifacts),
            "source_bridge_preflight_passed_count": sum(1 for artifact in source_bridge_artifacts if artifact.get("bridge_quality_passed") is True),
            "source_bridge_bronze_ingestion_passed_count": sum(1 for artifact in source_bridge_artifacts if artifact.get("bronze_quality_passed") is True),
            "source_activation_count": len(source_activation_artifacts),
            "source_activation_passed_count": sum(1 for artifact in source_activation_artifacts if artifact.get("activation_passed") is True),
            "source_activation_ops_passed": source_activation["ops_report"].report.get("passed"),
            "passed_release_count": len(release_artifacts) - len(failed),
            "failed_release_count": len(failed),
            "covered_gold_count": coverage.get("covered_count", 0),
            "gold_count": coverage.get("gold_count", 0),
            "missing_gold_outputs": coverage.get("missing", []),
            "final_control_tower_blocker_count": final_summary.get("blocker_count", 0),
            "final_runtime_lineage_blocker_count": count_blockers(final_control, "runtime_lineage_evidence_present"),
            "final_gold_release_blocker_count": count_blockers(final_control, "gold_release_evidence_passed"),
            "final_source_activation_blocker_count": count_blockers(final_control, "source_activation_ops_p0_clear"),
            "final_contract_active_blocker_count": count_blockers(final_control, "contract_active"),
        },
    }
    report["passed"] = (
        not failed
        and all(artifact.get("bridge_quality_passed") is True for artifact in source_bridge_artifacts)
        and all(artifact.get("bronze_quality_passed") is True for artifact in source_bridge_artifacts)
        and all(artifact.get("activation_passed") is True for artifact in source_activation_artifacts)
        and source_activation["ops_report"].report.get("passed") is True
        and int(report["summary"]["covered_gold_count"]) == int(report["summary"]["gold_count"])
        and not report["summary"]["missing_gold_outputs"]
    )
    report["report_id"] = stable_id(
        "portfolio-release-smoke",
        environment,
        generated_at,
        report["summary"],
        report["release_evidence"],
        report["artifacts"]["final"],
    )
    return report


def release_artifact(run: UseCaseRunResult) -> dict[str, Any]:
    evidence = run.evidence
    return {
        "uri": run.evidence_path.as_posix(),
        "hash": hash_file(run.evidence_path),
        "release_id": run.release_id,
        "use_case_id": run.use_case_id,
        "runner_id": run.runner_id,
        "topic": run.topic,
        "primary_output": run.primary_output,
        "output_data_products": evidence.get("output_data_products", []),
        "release_passed": evidence.get("release_passed"),
        "gate_count": len(evidence.get("gates", [])) if isinstance(evidence.get("gates"), list) else 0,
        "failed_gates": [
            gate.get("gate_id")
            for gate in evidence.get("gates", [])
            if isinstance(gate, dict) and gate.get("passed") is not True
        ]
        if isinstance(evidence.get("gates"), list)
        else [],
        "pipeline_manifest_path": run.pipeline.manifest_path.as_posix(),
        "ingestion_manifest_path": run.ingestion.manifest_path.as_posix() if run.ingestion else None,
    }


def source_bridge_artifact(run: SourceBridgeBronzeResult) -> dict[str, Any]:
    return {
        "source_id": run.spec.source_id,
        "topic": run.spec.topic,
        "bronze_target": run.ingestion.manifest.get("bronze_target"),
        "bridge_manifest_path": run.bridge.manifest_path.as_posix(),
        "bridge_manifest_hash": hash_file(run.bridge.manifest_path),
        "bronze_manifest_path": run.ingestion.manifest_path.as_posix(),
        "bronze_manifest_hash": hash_file(run.ingestion.manifest_path),
        "bridge_quality_passed": run.bridge.manifest.get("quality_passed"),
        "bronze_quality_passed": run.ingestion.manifest.get("quality_passed"),
        "normalized_row_count": run.bridge.manifest.get("normalized", {}).get("row_count"),
        "bronze_new_row_count": run.ingestion.manifest.get("approved", {}).get("new_row_count"),
    }


def source_activation_artifact(run: SourceActivationSmokeResult) -> dict[str, Any]:
    return {
        "source_id": run.spec.source_id,
        "change_request_id": run.spec.change_request_id,
        "source_readiness_bundle_path": run.bundle.summary_path.as_posix(),
        "source_readiness_bundle_hash": hash_file(run.bundle.summary_path),
        "source_readiness_passed": run.bundle.summary.get("passed"),
        "activation_manifest_path": run.activation.output_path.as_posix(),
        "activation_manifest_hash": hash_file(run.activation.output_path),
        "activation_id": run.activation.manifest.get("activation_id"),
        "activation_passed": run.activation.manifest.get("passed"),
        "active_state_path": run.activation.manifest.get("active_state_path"),
    }


def artifact_ref(path: Path | str, payload: dict[str, Any]) -> dict[str, Any]:
    resolved = Path(path)
    return {
        "uri": resolved.as_posix(),
        "hash": hash_file(resolved),
        "artifact_type": payload.get("artifact_type"),
        "generated_at": payload.get("generated_at"),
        "environment": payload.get("environment"),
        "passed": payload.get("passed"),
        "readiness_state": payload.get("readiness_state"),
        "summary": payload.get("summary", {}),
    }


def count_blockers(report: dict[str, Any], gate: str) -> int:
    return sum(
        1
        for blocker in report.get("blockers", [])
        if isinstance(blocker, dict) and blocker.get("gate") == gate
    )


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

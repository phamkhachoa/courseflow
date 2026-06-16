from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from enterprise_df.catalog import hash_file, load_json
from enterprise_df.change_requests import load_reference_sets, maker_checker_separated
from enterprise_df.contracts import DATA_PRODUCT_NAME, PRODUCT_CODE, ValidationResult, load_yaml, require_int, require_mapping, require_string


REQUEST_ID = re.compile(r"^[a-z][a-z0-9_]*$")
VALID_BACKFILL_TYPES = {"backfill_replay", "historical_backfill", "replay_repair", "correction_rebuild", "privacy_erasure_rebuild"}
VALID_OPERATION_TYPES = {"backfill", "replay", "correction"}
VALID_STATUSES = {"draft", "submitted", "in_review", "approved", "executed", "cancelled", "rejected"}
VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}
VALID_ENVIRONMENTS = {"local", "staging", "prod"}
VALID_APPROVER_ROLES = {
    "data_steward",
    "domain_owner",
    "enterprise_data_council",
    "finance_controller",
    "ml_governance",
    "platform_owner",
    "privacy_owner",
    "product_owner",
    "security_owner",
}
VALID_APPROVAL_DECISIONS = {"approved", "rejected", "needs_changes", "pending"}
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}
FINAL_APPROVED_STATUSES = {"approved", "executed"}
REPORT_VERSION = 1


@dataclass(frozen=True)
class BackfillReadinessResult:
    output_path: Path
    report: dict[str, Any]


def validate_backfill_request_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = backfill_request_registry_path(root)
    if not registry_path.is_file():
        result.error(registry_path, "governance/backfill-requests.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(registry_path)
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "registry_scope")
    requests = registry.get("backfill_requests")
    if not isinstance(requests, list) or not requests:
        result.error(registry_path, "backfill_requests must be a non-empty list")
        return result

    references = load_reference_sets(root)
    seen_ids: set[str] = set()
    for index, request in enumerate(requests):
        validate_backfill_request(registry_path, request, index, seen_ids, references, result)
    return result


def validate_backfill_request(
    registry_path: Path,
    request: object,
    index: int,
    seen_ids: set[str],
    references: dict[str, set[str]],
    result: ValidationResult,
) -> None:
    prefix = f"backfill_requests[{index}]"
    if not isinstance(request, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return

    request_id = require_string(registry_path, result, request, "id", prefix)
    if request_id:
        if not REQUEST_ID.fullmatch(request_id):
            result.error(registry_path, f"{prefix}.id must be snake_case")
        if request_id in seen_ids:
            result.error(registry_path, f"{prefix}.id duplicates request {request_id!r}")
        seen_ids.add(request_id)
    request_type = require_string(registry_path, result, request, "type", prefix)
    if request_type and request_type not in VALID_BACKFILL_TYPES:
        result.error(registry_path, f"{prefix}.type must be one of {sorted(VALID_BACKFILL_TYPES)}")
    operation_type = require_string(registry_path, result, request, "operationType", prefix)
    if operation_type and operation_type not in VALID_OPERATION_TYPES:
        result.error(registry_path, f"{prefix}.operationType must be one of {sorted(VALID_OPERATION_TYPES)}")
    status = require_string(registry_path, result, request, "status", prefix)
    if status and status not in VALID_STATUSES:
        result.error(registry_path, f"{prefix}.status must be one of {sorted(VALID_STATUSES)}")
    risk_level = require_string(registry_path, result, request, "riskLevel", prefix)
    if risk_level and risk_level not in VALID_RISK_LEVELS:
        result.error(registry_path, f"{prefix}.riskLevel must be one of {sorted(VALID_RISK_LEVELS)}")
    environment = require_string(registry_path, result, request, "targetEnvironment", prefix)
    if environment and environment not in VALID_ENVIRONMENTS:
        result.error(registry_path, f"{prefix}.targetEnvironment must be one of {sorted(VALID_ENVIRONMENTS)}")

    validate_optional_reference(registry_path, result, request, "product", prefix, references["products"], PRODUCT_CODE, "product code")
    validate_optional_reference(registry_path, result, request, "domain", prefix, references["domains"], PRODUCT_CODE, "domain code")
    validate_optional_reference(registry_path, result, request, "useCase", prefix, references["use_cases"], None, "use-case id")
    validate_optional_reference(registry_path, result, request, "primaryOutput", prefix, references["data_products"], DATA_PRODUCT_NAME, "data product name")

    requester = require_string(registry_path, result, request, "requester", prefix)
    for key in ("requestedAt", "businessJustification", "changeTicket", "runnerId"):
        require_string(registry_path, result, request, key, prefix)
    validate_window(registry_path, result, require_mapping(registry_path, result, request, "window"), prefix)
    validate_source_ids(registry_path, result, request.get("sourceIds"), prefix)
    validate_tenant_scope(registry_path, result, require_mapping(registry_path, result, request, "tenantScope"), prefix)
    validate_input_bindings(registry_path, result, request.get("inputBindings"), prefix, references)
    validate_output_products(registry_path, result, request.get("outputDataProducts"), prefix, references)
    validate_plan(registry_path, result, require_mapping(registry_path, result, request, "plan"), prefix)
    validate_baseline(registry_path, result, require_mapping(registry_path, result, request, "baseline"), prefix)
    validate_execution(registry_path, result, require_mapping(registry_path, result, request, "execution"), prefix)
    validate_evidence(registry_path, result, require_mapping(registry_path, result, request, "evidence"), prefix)
    validate_controls(registry_path, result, require_mapping(registry_path, result, request, "controls"), prefix)

    approvals = request.get("approvals")
    if not isinstance(approvals, list) or not approvals:
        result.error(registry_path, f"{prefix}.approvals must be a non-empty list")
        return
    for approval_index, approval in enumerate(approvals):
        validate_approval(registry_path, approval, f"{prefix}.approvals[{approval_index}]", requester, result)


def write_backfill_readiness_report(
    root: str | Path,
    output_path: str | Path,
    *,
    request_id: str,
    environment: str,
    dry_run_report_path: str | Path | None = None,
    quality_report_path: str | Path | None = None,
    data_diff_report_path: str | Path | None = None,
    source_offset_ledger_path: str | Path | None = None,
    snapshot_evidence_path: str | Path | None = None,
    release_evidence_path: str | Path | None = None,
    change_control_evidence_path: str | Path | None = None,
    backfill_plan_path: str | Path | None = None,
    active_state_path: str | Path | None = None,
    generated_at: str | None = None,
) -> BackfillReadinessResult:
    report = build_backfill_readiness_report(
        root,
        request_id=request_id,
        environment=environment,
        dry_run_report_path=dry_run_report_path,
        quality_report_path=quality_report_path,
        data_diff_report_path=data_diff_report_path,
        source_offset_ledger_path=source_offset_ledger_path,
        snapshot_evidence_path=snapshot_evidence_path,
        release_evidence_path=release_evidence_path,
        change_control_evidence_path=change_control_evidence_path,
        backfill_plan_path=backfill_plan_path,
        active_state_path=active_state_path,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return BackfillReadinessResult(output_path=target, report=report)


def build_backfill_readiness_report(
    root: str | Path,
    *,
    request_id: str,
    environment: str,
    dry_run_report_path: str | Path | None = None,
    quality_report_path: str | Path | None = None,
    data_diff_report_path: str | Path | None = None,
    source_offset_ledger_path: str | Path | None = None,
    snapshot_evidence_path: str | Path | None = None,
    release_evidence_path: str | Path | None = None,
    change_control_evidence_path: str | Path | None = None,
    backfill_plan_path: str | Path | None = None,
    active_state_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    registry_path = backfill_request_registry_path(platform_root)
    request = find_backfill_request(platform_root, request_id)
    references = load_reference_sets(platform_root)
    generated = generated_at or utc_now()
    if request is None:
        checks = [check("request_exists", False, {"request_id": request_id})]
        return report_payload(
            registry_path,
            request_id=request_id,
            environment=environment,
            generated_at=generated,
            request=None,
            checks=checks,
        )

    evidence = request.get("evidence") if isinstance(request.get("evidence"), dict) else {}
    plan = request.get("plan") if isinstance(request.get("plan"), dict) else {}
    baseline = request.get("baseline") if isinstance(request.get("baseline"), dict) else {}
    backfill_plan_ref = plan_reference(plan, backfill_plan_path)
    active_pointer_ref = active_pointer_reference(baseline, active_state_path)
    dry_run_ref = evidence_reference(evidence, "dryRunReport", dry_run_report_path)
    quality_ref = evidence_reference(evidence, "qualityReport", quality_report_path)
    data_diff_ref = evidence_reference(evidence, "dataDiffReport", data_diff_report_path)
    source_offset_ref = evidence_reference(evidence, "sourceOffsetLedger", source_offset_ledger_path)
    snapshot_ref = evidence_reference(evidence, "snapshotEvidence", snapshot_evidence_path)
    release_ref = evidence_reference(evidence, "releaseEvidence", release_evidence_path)
    change_control_ref = evidence_reference(evidence, "changeControlEvidence", change_control_evidence_path)
    backfill_plan_report = load_json_if_local(backfill_plan_ref)
    dry_run_report = load_json_if_local(dry_run_ref)
    quality_report = load_json_if_local(quality_ref)
    data_diff_report = load_json_if_local(data_diff_ref)
    source_offset_report = load_json_if_local(source_offset_ref)
    snapshot_report = load_json_if_local(snapshot_ref)
    release_report = load_json_if_local(release_ref)
    change_control_report = load_json_if_local(change_control_ref)
    active_pointer_report = load_json_if_local(active_pointer_ref)
    checks = backfill_readiness_checks(
        request,
        environment=environment,
        references=references,
        backfill_plan_ref=backfill_plan_ref,
        active_pointer_ref=active_pointer_ref,
        dry_run_ref=dry_run_ref,
        quality_ref=quality_ref,
        data_diff_ref=data_diff_ref,
        source_offset_ref=source_offset_ref,
        snapshot_ref=snapshot_ref,
        release_ref=release_ref,
        change_control_ref=change_control_ref,
        backfill_plan_report=backfill_plan_report,
        active_pointer_report=active_pointer_report,
        dry_run_report=dry_run_report,
        quality_report=quality_report,
        data_diff_report=data_diff_report,
        source_offset_report=source_offset_report,
        snapshot_report=snapshot_report,
        release_report=release_report,
        change_control_report=change_control_report,
    )
    return report_payload(
        registry_path,
        request_id=request_id,
        environment=environment,
        generated_at=generated,
        request=request,
        checks=checks,
        evidence={
            "backfill_plan": backfill_plan_ref,
            "active_pointer": active_pointer_ref,
            "dry_run": dry_run_ref,
            "quality": quality_ref,
            "data_diff": data_diff_ref,
            "source_offset_ledger": source_offset_ref,
            "snapshot": snapshot_ref,
            "release": release_ref,
            "change_control": change_control_ref,
        },
    )


def backfill_readiness_checks(
    request: dict[str, Any],
    *,
    environment: str,
    references: dict[str, set[str]],
    backfill_plan_ref: dict[str, Any],
    active_pointer_ref: dict[str, Any],
    dry_run_ref: dict[str, Any],
    quality_ref: dict[str, Any],
    data_diff_ref: dict[str, Any],
    source_offset_ref: dict[str, Any],
    snapshot_ref: dict[str, Any],
    release_ref: dict[str, Any],
    change_control_ref: dict[str, Any],
    backfill_plan_report: dict[str, Any] | None,
    active_pointer_report: dict[str, Any] | None,
    dry_run_report: dict[str, Any] | None,
    quality_report: dict[str, Any] | None,
    data_diff_report: dict[str, Any] | None,
    source_offset_report: dict[str, Any] | None,
    snapshot_report: dict[str, Any] | None,
    release_report: dict[str, Any] | None,
    change_control_report: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    request_environment = request.get("targetEnvironment")
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS or request_environment in PRODUCTION_LIKE_ENVIRONMENTS
    approvals = [approval for approval in request.get("approvals", []) if isinstance(approval, dict)]
    approvers = [str(approval.get("approver")) for approval in approvals if approval.get("decision") == "approved" and isinstance(approval.get("approver"), str)]
    approved_roles = {str(approval.get("role")) for approval in approvals if approval.get("decision") == "approved" and isinstance(approval.get("role"), str)}
    output_products = string_list(request.get("outputDataProducts"))
    controls = request.get("controls") if isinstance(request.get("controls"), dict) else {}
    execution = request.get("execution") if isinstance(request.get("execution"), dict) else {}
    plan = request.get("plan") if isinstance(request.get("plan"), dict) else {}
    baseline = request.get("baseline") if isinstance(request.get("baseline"), dict) else {}
    window = request.get("window") if isinstance(request.get("window"), dict) else {}
    evidence = request.get("evidence") if isinstance(request.get("evidence"), dict) else {}
    primary_output = request.get("primaryOutput")
    return [
        check("request_type_supported", request.get("type") in VALID_BACKFILL_TYPES, {"type": request.get("type")}),
        check("operation_type_supported", request.get("operationType") in VALID_OPERATION_TYPES, {"operation_type": request.get("operationType")}),
        check("environment_supported", environment in VALID_ENVIRONMENTS, {"environment": environment}),
        check("request_environment_matches_report", request_environment == environment, {"request_environment": request_environment, "report_environment": environment}),
        check("status_approved_for_execution", request.get("status") in FINAL_APPROVED_STATUSES if production_like else request.get("status") not in {"cancelled", "rejected"}, {"status": request.get("status")}),
        check("business_justification_present", non_empty(request.get("businessJustification")), {}),
        check("change_ticket_present", non_empty(request.get("changeTicket")), {"change_ticket": request.get("changeTicket")}),
        check("maker_checker_separated", maker_checker_separated(request.get("requester"), approvers), {"requester": request.get("requester"), "approvers": approvers}),
        check("minimum_approved_roles", len(approved_roles) >= (3 if production_like else 1), {"approved_roles": sorted(approved_roles)}),
        check("data_steward_approved", "data_steward" in approved_roles, {"approved_roles": sorted(approved_roles)}),
        check("platform_owner_approved", "platform_owner" in approved_roles if production_like else True, {"approved_roles": sorted(approved_roles)}),
        check("window_valid", valid_window(window), {"window": window}),
        check("window_within_policy", window_within_policy(window), {"window": window}),
        check("tenant_scope_declared", tenant_scope_declared(request.get("tenantScope")), {"tenant_scope": request.get("tenantScope")}),
        check("source_ids_declared", bool(string_list(request.get("sourceIds"))), {"source_ids": request.get("sourceIds")}),
        check("input_bindings_bounded", input_bindings_bounded(request.get("inputBindings")), {"input_bindings": request.get("inputBindings")}),
        check("output_products_registered", all(item in references["data_products"] for item in output_products) and bool(output_products), {"output_data_products": output_products}),
        check("primary_output_in_outputs", isinstance(primary_output, str) and primary_output in output_products, {"primary_output": primary_output, "output_data_products": output_products}),
        check("runner_declared", non_empty(request.get("runnerId")), {"runner_id": request.get("runnerId")}),
        check("plan_identity_present", plan_identity_present(plan), {"plan": plan}),
        check("row_delta_within_tolerance", row_delta_within_tolerance(plan), {"plan": plan}),
        check("rollback_strategy_declared", non_empty(plan.get("rollbackStrategy")), {"rollback_strategy": plan.get("rollbackStrategy")}),
        check("concurrency_lock_declared", non_empty(plan.get("concurrencyLockId")), {"concurrency_lock_id": plan.get("concurrencyLockId")}),
        check("baseline_identity_present", baseline_identity_present(baseline) if production_like else True, {"baseline": baseline}),
        check("code_commit_sha_present", not production_like or non_empty(execution.get("codeCommitSha")), {"code_commit_sha": execution.get("codeCommitSha")}),
        check("idempotency_key_present", non_empty(execution.get("idempotencyKey")), {"idempotency_key": execution.get("idempotencyKey")}),
        check("dry_run_required", execution.get("dryRunRequired") is True if production_like else True, {"dry_run_required": execution.get("dryRunRequired")}),
        check("rollback_control_present", controls.get("rollbackRequired") is True if production_like else True, controls),
        check("impact_assessment_control_present", controls.get("impactAssessmentRequired") is True if production_like else True, controls),
        check("communication_control_present", controls.get("communicationRequired") is True if environment == "prod" else True, controls),
        evidence_check("backfill_plan_evidence", backfill_plan_ref, required=production_like),
        evidence_check("active_pointer_evidence", active_pointer_ref, required=production_like),
        evidence_check("dry_run_evidence", dry_run_ref, required=production_like),
        evidence_check("quality_evidence", quality_ref, required=production_like),
        evidence_check("data_diff_evidence", data_diff_ref, required=production_like),
        evidence_check("source_offset_ledger_evidence", source_offset_ref, required=production_like),
        evidence_check("snapshot_evidence", snapshot_ref, required=production_like),
        evidence_check("release_evidence", release_ref, required=production_like),
        evidence_check("change_control_evidence", change_control_ref, required=production_like),
        evidence_key_check("rollback_plan", evidence, "rollbackPlanUri", required=production_like),
        evidence_key_check("impact_assessment", evidence, "impactAssessmentUri", required=production_like),
        evidence_key_check("communication_plan", evidence, "communicationPlanUri", required=environment == "prod"),
        local_report_passed_check("backfill_plan_report_passed", backfill_plan_report),
        active_pointer_hash_matches_baseline(active_pointer_report, active_pointer_ref=active_pointer_ref, baseline=baseline),
        active_pointer_matches_baseline(active_pointer_report, request=request, environment=environment),
        rollback_target_matches_active_pointer(active_pointer_report, baseline=baseline),
        local_report_passed_check("dry_run_report_passed", dry_run_report),
        local_report_passed_check("quality_report_passed", quality_report),
        local_report_passed_check("data_diff_report_passed", data_diff_report),
        source_offset_report_passed(source_offset_report, environment=environment),
        snapshot_report_matches(snapshot_report, environment=environment, output_products=output_products),
        release_report_passed(release_report, environment=environment),
        change_control_report_passed(change_control_report, environment=environment),
    ]


def report_payload(
    registry_path: Path,
    *,
    request_id: str,
    environment: str,
    generated_at: str,
    request: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    passed = all(item["passed"] is True for item in checks)
    return {
        "artifact_type": "backfill_readiness_report.v1",
        "report_version": REPORT_VERSION,
        "readiness_id": stable_id("backfill-readiness", request_id, environment, registry_path, generated_at),
        "generated_at": generated_at,
        "environment": environment,
        "request_id": request_id,
        "readiness_state": "ready" if passed else "blocked",
        "registry_uri": registry_path.as_posix(),
        "registry_hash": hash_file(registry_path),
        "request": request_summary(request),
        "scope": scope_summary(request),
        "plan": request.get("plan") if isinstance(request, dict) and isinstance(request.get("plan"), dict) else {},
        "baseline": request.get("baseline") if isinstance(request, dict) and isinstance(request.get("baseline"), dict) else {},
        "evidence": evidence or {},
        "checks": checks,
        "failures": [
            {"check": item["name"], "details": item.get("details", {})}
            for item in checks
            if item.get("passed") is not True
        ],
        "passed": passed,
    }


def validate_optional_reference(
    registry_path: Path,
    result: ValidationResult,
    request: dict[str, Any],
    key: str,
    prefix: str,
    known_values: set[str],
    pattern: re.Pattern[str] | None,
    label: str,
) -> None:
    value = request.get(key)
    if value in (None, ""):
        return
    if not isinstance(value, str):
        result.error(registry_path, f"{prefix}.{key} must be a string")
        return
    if pattern is not None and not pattern.fullmatch(value):
        result.error(registry_path, f"{prefix}.{key} must be a {label}")
    if known_values and value not in known_values:
        result.error(registry_path, f"{prefix}.{key} references unknown {label} {value!r}")


def validate_window(registry_path: Path, result: ValidationResult, window: dict[str, Any] | None, prefix: str) -> None:
    if not window:
        return
    for key in ("eventTimeStart", "eventTimeEnd", "timezone"):
        require_string(registry_path, result, window, key, f"{prefix}.window")
    max_days = window.get("maxWindowDays")
    if not isinstance(max_days, int) or max_days < 1:
        result.error(registry_path, f"{prefix}.window.maxWindowDays must be an integer >= 1")


def validate_input_bindings(registry_path: Path, result: ValidationResult, value: object, prefix: str, references: dict[str, set[str]]) -> None:
    if not isinstance(value, list) or not value:
        result.error(registry_path, f"{prefix}.inputBindings must be a non-empty list")
        return
    for index, binding in enumerate(value):
        binding_prefix = f"{prefix}.inputBindings[{index}]"
        if not isinstance(binding, dict):
            result.error(registry_path, f"{binding_prefix} must be an object")
            continue
        data_product = require_string(registry_path, result, binding, "dataProduct", binding_prefix)
        if data_product and (not DATA_PRODUCT_NAME.fullmatch(data_product) or data_product not in references["data_products"]):
            result.error(registry_path, f"{binding_prefix}.dataProduct references unknown data product {data_product!r}")
        if not non_empty(binding.get("snapshotId")) and not isinstance(binding.get("offsetRanges"), list):
            result.error(registry_path, f"{binding_prefix} must define snapshotId or offsetRanges")


def validate_output_products(registry_path: Path, result: ValidationResult, value: object, prefix: str, references: dict[str, set[str]]) -> None:
    products = string_list(value)
    if not products:
        result.error(registry_path, f"{prefix}.outputDataProducts must be a non-empty list")
        return
    for product in products:
        if not DATA_PRODUCT_NAME.fullmatch(product) or product not in references["data_products"]:
            result.error(registry_path, f"{prefix}.outputDataProducts references unknown data product {product!r}")


def validate_source_ids(registry_path: Path, result: ValidationResult, value: object, prefix: str) -> None:
    if not string_list(value):
        result.error(registry_path, f"{prefix}.sourceIds must be a non-empty list")


def validate_tenant_scope(registry_path: Path, result: ValidationResult, tenant_scope: dict[str, Any] | None, prefix: str) -> None:
    if not tenant_scope:
        return
    mode = require_string(registry_path, result, tenant_scope, "mode", f"{prefix}.tenantScope")
    if mode and mode not in {"all", "org_allowlist", "tenant_allowlist"}:
        result.error(registry_path, f"{prefix}.tenantScope.mode must be all, org_allowlist or tenant_allowlist")
    org_ids = tenant_scope.get("orgIds")
    if org_ids is not None and not isinstance(org_ids, list):
        result.error(registry_path, f"{prefix}.tenantScope.orgIds must be a list")


def validate_plan(registry_path: Path, result: ValidationResult, plan: dict[str, Any] | None, prefix: str) -> None:
    if not plan:
        return
    for key in (
        "backfillPlanUri",
        "backfillPlanHash",
        "runId",
        "idempotencyStrategy",
        "materializationStrategy",
        "concurrencyLockId",
        "maintenanceWindow",
        "rollbackStrategy",
    ):
        require_string(registry_path, result, plan, key, f"{prefix}.plan")
    for key in ("expectedRowDelta", "maxAllowedRowDelta"):
        value = plan.get(key)
        if not isinstance(value, int) or value < 0:
            result.error(registry_path, f"{prefix}.plan.{key} must be an integer >= 0")
    if not string_list(plan.get("partitionScope")):
        result.error(registry_path, f"{prefix}.plan.partitionScope must be a non-empty list")


def validate_baseline(registry_path: Path, result: ValidationResult, baseline: dict[str, Any] | None, prefix: str) -> None:
    if not baseline:
        return
    for key in (
        "previousReleaseId",
        "previousSnapshotId",
        "previousContentHash",
        "activePointerUri",
        "activePointerHash",
        "rollbackTarget",
    ):
        require_string(registry_path, result, baseline, key, f"{prefix}.baseline")


def validate_execution(registry_path: Path, result: ValidationResult, execution: dict[str, Any] | None, prefix: str) -> None:
    if not execution:
        return
    for key in ("codeCommitSha", "idempotencyKey"):
        require_string(registry_path, result, execution, key, f"{prefix}.execution")
    if not isinstance(execution.get("dryRunRequired"), bool):
        result.error(registry_path, f"{prefix}.execution.dryRunRequired must be a boolean")
    expected_max_rows = execution.get("expectedMaxRows")
    if not isinstance(expected_max_rows, int) or expected_max_rows < 1:
        result.error(registry_path, f"{prefix}.execution.expectedMaxRows must be an integer >= 1")


def validate_evidence(registry_path: Path, result: ValidationResult, evidence: dict[str, Any] | None, prefix: str) -> None:
    if not evidence:
        return
    for key in (
        "dryRunReportUri",
        "dryRunReportHash",
        "qualityReportUri",
        "qualityReportHash",
        "dataDiffReportUri",
        "dataDiffReportHash",
        "snapshotEvidenceUri",
        "snapshotEvidenceHash",
        "releaseEvidenceUri",
        "releaseEvidenceHash",
        "sourceOffsetLedgerUri",
        "sourceOffsetLedgerHash",
        "changeControlEvidenceUri",
        "rollbackPlanUri",
        "impactAssessmentUri",
        "communicationPlanUri",
    ):
        require_string(registry_path, result, evidence, key, f"{prefix}.evidence")


def validate_controls(registry_path: Path, result: ValidationResult, controls: dict[str, Any] | None, prefix: str) -> None:
    if not controls:
        return
    for key in ("makerCheckerRequired", "rollbackRequired", "impactAssessmentRequired", "communicationRequired", "consumerFreezeRequired"):
        if not isinstance(controls.get(key), bool):
            result.error(registry_path, f"{prefix}.controls.{key} must be a boolean")
    if not isinstance(controls.get("slaHours"), int) or controls.get("slaHours") < 1:
        result.error(registry_path, f"{prefix}.controls.slaHours must be an integer >= 1")


def validate_approval(registry_path: Path, approval: object, prefix: str, requester: str | None, result: ValidationResult) -> None:
    if not isinstance(approval, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return
    role = require_string(registry_path, result, approval, "role", prefix)
    if role and role not in VALID_APPROVER_ROLES:
        result.error(registry_path, f"{prefix}.role must be one of {sorted(VALID_APPROVER_ROLES)}")
    approver = require_string(registry_path, result, approval, "approver", prefix)
    decision = require_string(registry_path, result, approval, "decision", prefix)
    if decision and decision not in VALID_APPROVAL_DECISIONS:
        result.error(registry_path, f"{prefix}.decision must be one of {sorted(VALID_APPROVAL_DECISIONS)}")
    require_string(registry_path, result, approval, "decidedAt", prefix)
    if requester and approver and requester == approver and decision == "approved":
        result.error(registry_path, f"{prefix}.approver must be different from requester for approved decisions")


def find_backfill_request(root: Path, request_id: str) -> dict[str, Any] | None:
    registry = load_yaml(backfill_request_registry_path(root))
    requests = registry.get("backfill_requests")
    if not isinstance(requests, list):
        return None
    for request in requests:
        if isinstance(request, dict) and request.get("id") == request_id:
            return request
    return None


def evidence_reference(evidence: dict[str, Any], prefix: str, override_path: str | Path | None) -> dict[str, Any]:
    uri_key = f"{prefix}Uri"
    hash_key = f"{prefix}Hash"
    uri = Path(override_path).as_posix() if override_path else evidence.get(uri_key)
    evidence_hash = hash_file(override_path) if override_path else evidence.get(hash_key)
    local = Path(str(uri)).is_file() if isinstance(uri, str) else False
    return {
        "uri": uri,
        "hash": evidence_hash,
        "local": local,
        "override": override_path is not None,
    }


def plan_reference(plan: dict[str, Any], override_path: str | Path | None) -> dict[str, Any]:
    uri = Path(override_path).as_posix() if override_path else plan.get("backfillPlanUri")
    evidence_hash = hash_file(override_path) if override_path else plan.get("backfillPlanHash")
    local = Path(str(uri)).is_file() if isinstance(uri, str) else False
    return {
        "uri": uri,
        "hash": evidence_hash,
        "local": local,
        "override": override_path is not None,
    }


def active_pointer_reference(baseline: dict[str, Any], override_path: str | Path | None) -> dict[str, Any]:
    uri = Path(override_path).as_posix() if override_path else baseline.get("activePointerUri")
    evidence_hash = hash_file(override_path) if override_path else baseline.get("activePointerHash")
    local = Path(str(uri)).is_file() if isinstance(uri, str) else False
    return {
        "uri": uri,
        "hash": evidence_hash,
        "local": local,
        "override": override_path is not None,
    }


def evidence_check(name: str, reference: dict[str, Any], *, required: bool) -> dict[str, Any]:
    uri = reference.get("uri")
    evidence_hash = reference.get("hash")
    passed = (not required) or (non_empty(uri) and is_hash(evidence_hash))
    if passed and reference.get("local") and is_hash(evidence_hash):
        passed = evidence_hash == hash_file(str(uri))
    return check(name, passed, reference)


def evidence_key_check(name: str, evidence: dict[str, Any], key: str, *, required: bool) -> dict[str, Any]:
    return check(name, (not required) or non_empty(evidence.get(key)), {key: evidence.get(key)})


def load_json_if_local(reference: dict[str, Any]) -> dict[str, Any] | None:
    uri = reference.get("uri")
    if isinstance(uri, str) and Path(uri).is_file():
        data = load_json(Path(uri))
        return data if isinstance(data, dict) else None
    return None


def local_report_passed_check(name: str, report: dict[str, Any] | None) -> dict[str, Any]:
    if report is None:
        return check(name, True, {"not_applicable": True})
    return check(name, report.get("passed") is True, {"artifact_type": report.get("artifact_type"), "passed": report.get("passed")})


def source_offset_report_passed(report: dict[str, Any] | None, *, environment: str) -> dict[str, Any]:
    if report is None:
        return check("source_offset_ledger_report_passed", True, {"not_applicable": True})
    required = {
        "artifact_type": report.get("artifact_type") == "source_offset_ledger.v1",
        "passed": report.get("passed") is True,
        "environment": report.get("environment") == environment,
    }
    return check("source_offset_ledger_report_passed", all(required.values()), {"required": required})


def snapshot_report_matches(report: dict[str, Any] | None, *, environment: str, output_products: list[str]) -> dict[str, Any]:
    if report is None:
        return check("snapshot_report_matches_request", True, {"not_applicable": True})
    layers = report.get("layers") if isinstance(report.get("layers"), dict) else {}
    missing_outputs = [product for product in output_products if product not in layers]
    required = {
        "artifact_type": report.get("artifact_type") == "lakehouse_snapshot_evidence.v1",
        "passed": report.get("passed") is True,
        "environment": report.get("environment") == environment,
        "outputs_present": not missing_outputs,
    }
    return check("snapshot_report_matches_request", all(required.values()), {"required": required, "missing_outputs": missing_outputs})


def release_report_passed(report: dict[str, Any] | None, *, environment: str) -> dict[str, Any]:
    if report is None:
        return check("release_report_passed", True, {"not_applicable": True})
    gates = [
        gate
        for gate in report.get("gates", [])
        if isinstance(gate, dict)
    ]
    gate_results = {gate.get("gate_id"): gate.get("passed") for gate in gates}
    required = {
        "release_passed": report.get("release_passed") is True,
        "environment": report.get("environment") == environment,
        "snapshot_gate": gate_results.get("P0-LAKEHOUSE-SNAPSHOT-EVIDENCE") is True,
        "production_evidence_gate": True if environment in {"local", "dev"} else gate_results.get("P0-PRODUCTION-EVIDENCE") is True,
    }
    return check("release_report_passed", all(required.values()), {"required": required})


def change_control_report_passed(report: dict[str, Any] | None, *, environment: str) -> dict[str, Any]:
    if report is None:
        return check("change_control_report_passed", True, {"not_applicable": True})
    required = {
        "artifact_type": report.get("artifact_type") == "change_control_evidence.v1",
        "passed": report.get("passed") is True,
        "environment": report.get("environment") == environment,
    }
    return check("change_control_report_passed", all(required.values()), {"required": required})


def active_pointer_hash_matches_baseline(
    report: dict[str, Any] | None,
    *,
    active_pointer_ref: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    if report is None:
        return check("active_pointer_hash_matches_baseline", True, {"not_applicable": True})
    expected = baseline.get("activePointerHash")
    actual = active_pointer_ref.get("hash")
    return check(
        "active_pointer_hash_matches_baseline",
        is_hash(expected) and expected == actual,
        {"expected": expected, "actual": actual, "active_pointer_uri": active_pointer_ref.get("uri")},
    )


def active_pointer_matches_baseline(
    report: dict[str, Any] | None,
    *,
    request: dict[str, Any],
    environment: str,
) -> dict[str, Any]:
    if report is None:
        return check("active_pointer_matches_baseline", True, {"not_applicable": True})
    baseline = request.get("baseline") if isinstance(request.get("baseline"), dict) else {}
    required = {
        "artifact_type": report.get("artifact_type") == "release_active_pointer.v1",
        "environment": report.get("environment") == environment,
        "data_product": report.get("data_product") == request.get("primaryOutput"),
        "release_id": report.get("release_id") == baseline.get("previousReleaseId"),
        "dataset_snapshot_id": report.get("dataset_snapshot_id") == baseline.get("previousSnapshotId"),
        "content_hash": report.get("content_hash") == baseline.get("previousContentHash"),
    }
    return check(
        "active_pointer_matches_baseline",
        all(required.values()),
        {"required": required, "active_pointer": active_pointer_summary(report), "baseline": baseline},
    )


def rollback_target_matches_active_pointer(report: dict[str, Any] | None, *, baseline: dict[str, Any]) -> dict[str, Any]:
    if report is None:
        return check("rollback_target_matches_active_pointer", True, {"not_applicable": True})
    return check(
        "rollback_target_matches_active_pointer",
        baseline.get("rollbackTarget") == report.get("dataset_snapshot_id"),
        {
            "rollback_target": baseline.get("rollbackTarget"),
            "active_dataset_snapshot_id": report.get("dataset_snapshot_id"),
        },
    )


def tenant_scope_declared(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    mode = value.get("mode")
    if mode == "all":
        return True
    if mode in {"org_allowlist", "tenant_allowlist"}:
        ids = value.get("orgIds")
        return isinstance(ids, list) and bool(ids)
    return False


def plan_identity_present(plan: dict[str, Any]) -> bool:
    return all(
        non_empty(plan.get(key))
        for key in ("runId", "idempotencyStrategy", "materializationStrategy", "concurrencyLockId")
    ) and bool(string_list(plan.get("partitionScope")))


def baseline_identity_present(baseline: dict[str, Any]) -> bool:
    return all(
        non_empty(baseline.get(key))
        for key in (
            "previousReleaseId",
            "previousSnapshotId",
            "previousContentHash",
            "activePointerUri",
            "activePointerHash",
            "rollbackTarget",
        )
    ) and is_hash(baseline.get("previousContentHash")) and is_hash(baseline.get("activePointerHash"))


def row_delta_within_tolerance(plan: dict[str, Any]) -> bool:
    expected = plan.get("expectedRowDelta")
    maximum = plan.get("maxAllowedRowDelta")
    return isinstance(expected, int) and isinstance(maximum, int) and expected <= maximum


def valid_window(window: dict[str, Any]) -> bool:
    start = parse_time(window.get("eventTimeStart"))
    end = parse_time(window.get("eventTimeEnd"))
    return start is not None and end is not None and start < end and window.get("timezone") == "UTC"


def window_within_policy(window: dict[str, Any]) -> bool:
    start = parse_time(window.get("eventTimeStart"))
    end = parse_time(window.get("eventTimeEnd"))
    max_days = window.get("maxWindowDays")
    if start is None or end is None or not isinstance(max_days, int):
        return False
    return (end - start).total_seconds() <= max_days * 24 * 60 * 60


def input_bindings_bounded(value: object) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for binding in value:
        if not isinstance(binding, dict):
            return False
        if non_empty(binding.get("snapshotId")):
            continue
        ranges = binding.get("offsetRanges")
        if not isinstance(ranges, list) or not ranges:
            return False
    return True


def request_summary(request: dict[str, Any] | None) -> dict[str, Any] | None:
    if request is None:
        return None
    return {
        "id": request.get("id"),
        "type": request.get("type"),
        "operation_type": request.get("operationType"),
        "status": request.get("status"),
        "risk_level": request.get("riskLevel"),
        "target_environment": request.get("targetEnvironment"),
        "product": request.get("product"),
        "domain": request.get("domain"),
        "use_case": request.get("useCase"),
        "primary_output": request.get("primaryOutput"),
        "source_ids": request.get("sourceIds"),
        "runner_id": request.get("runnerId"),
        "window": request.get("window"),
        "input_bindings": request.get("inputBindings"),
        "output_data_products": request.get("outputDataProducts"),
        "change_ticket": request.get("changeTicket"),
    }


def scope_summary(request: dict[str, Any] | None) -> dict[str, Any]:
    if request is None:
        return {}
    return {
        "product": request.get("product"),
        "domain": request.get("domain"),
        "use_case_id": request.get("useCase"),
        "runner_id": request.get("runnerId"),
        "operation_type": request.get("operationType"),
        "primary_output": request.get("primaryOutput"),
        "affected_data_products": request.get("outputDataProducts", []),
        "source_ids": request.get("sourceIds", []),
        "tenant_scope": request.get("tenantScope", {}),
        "event_time_window": request.get("window", {}),
        "source_position_ranges": request.get("inputBindings", []),
    }


def active_pointer_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "environment": report.get("environment"),
        "release_id": report.get("release_id"),
        "data_product": report.get("data_product"),
        "dataset_snapshot_id": report.get("dataset_snapshot_id"),
        "content_hash": report.get("content_hash"),
        "activation_id": report.get("activation_id"),
    }


def string_list(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_hash(value: object) -> bool:
    return isinstance(value, str) and value.startswith("sha256:")


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def backfill_request_registry_path(root: Path) -> Path:
    return root / "governance" / "backfill-requests.yaml"


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

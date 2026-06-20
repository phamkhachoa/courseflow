from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, load_json
from enterprise_dp.pipelines.base import PipelineRunRequest, PipelineSpec


PIPELINE_NAME = "control_tower.materialize_gold.from_report.v1"
PRODUCT_ID = "enterprise-data-platform"
DOMAIN = "enterprise-reporting"
ORG_ID = "00000000-0000-0000-0000-000000000000"
OUTPUT_DATA_PRODUCTS = (
    "gold.data_product_inventory",
    "gold.contract_compliance_daily",
    "gold.quality_sla_daily",
    "gold.lineage_coverage_daily",
)
ALLOWED_LIFECYCLE_STATES = {
    "DRAFT_CONTRACT",
    "CANDIDATE",
    "CERTIFIED",
    "ACTIVE",
    "DEGRADED",
    "FROZEN",
    "WITHDRAWN",
    "DEPRECATED",
}
ALLOWED_STATUS = {"GREEN", "AMBER", "RED", "UNKNOWN"}


@dataclass(frozen=True)
class LayerSnapshot:
    name: str
    path: Path
    row_count: int
    content_hash: str
    quality_passed: bool
    quality_errors: tuple[str, ...]

    def as_manifest_entry(self, output_dir: Path) -> dict[str, Any]:
        try:
            relative_path = self.path.relative_to(output_dir).as_posix()
        except ValueError:
            relative_path = self.path.as_posix()
        return {
            "path": relative_path,
            "row_count": self.row_count,
            "content_hash": self.content_hash,
            "quality_passed": self.quality_passed,
            "quality_errors": list(self.quality_errors),
        }


@dataclass(frozen=True)
class ControlTowerPipelineResult:
    snapshot_id: str
    report_path: Path
    inventory_path: Path
    contract_compliance_path: Path
    quality_sla_path: Path
    lineage_coverage_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


class ControlTowerGoldMaterializationRunner:
    spec = PipelineSpec(
        runner_id=PIPELINE_NAME,
        name="Control Tower Gold materialization from report",
        product=PRODUCT_ID,
        domain=DOMAIN,
        use_cases=("data-product-control-tower",),
        input_kind="data_product_snapshot",
        output_data_products=OUTPUT_DATA_PRODUCTS,
        description="Materialize Data Product Control Tower report into four operational Gold datasets.",
        primary_output="gold.data_product_inventory",
        evidence_capabilities=(
            "catalog_lineage",
            "quality_slo",
            "access_privacy",
            "release_gates",
            "capability_maturity",
        ),
        optional_options=("snapshot_id", "built_at"),
    )

    def run(self, request: PipelineRunRequest) -> ControlTowerPipelineResult:
        return run_control_tower_gold_materialization(
            request.input_path,
            request.output_dir,
            snapshot_id=request.options.get("snapshot_id"),
            built_at=request.options.get("built_at"),
        )


def run_control_tower_gold_materialization(
    report_path: str | Path,
    output_dir: str | Path,
    *,
    snapshot_id: str | None = None,
    built_at: str | None = None,
) -> ControlTowerPipelineResult:
    source_path = Path(report_path)
    target_dir = Path(output_dir)
    build_time = built_at or _utc_now()
    resolved_snapshot_id = snapshot_id or f"control-tower-{_compact_timestamp(build_time)}"
    report = load_json(source_path)
    validate_control_tower_input(source_path, report)

    inventory_rows = build_inventory_rows(report, snapshot_id=resolved_snapshot_id, built_at=build_time)
    contract_rows = build_contract_compliance_rows(report, built_at=build_time)
    quality_rows = build_quality_sla_rows(report, built_at=build_time)
    lineage_rows = build_lineage_coverage_rows(report, built_at=build_time)

    inventory_snapshot = write_layer_snapshot(
        "gold.data_product_inventory",
        target_dir / "gold" / "data_product_inventory.jsonl",
        inventory_rows,
        quality_errors=validate_inventory_rows(inventory_rows),
    )
    contract_snapshot = write_layer_snapshot(
        "gold.contract_compliance_daily",
        target_dir / "gold" / "contract_compliance_daily.jsonl",
        contract_rows,
        quality_errors=validate_contract_rows(contract_rows),
    )
    quality_snapshot = write_layer_snapshot(
        "gold.quality_sla_daily",
        target_dir / "gold" / "quality_sla_daily.jsonl",
        quality_rows,
        quality_errors=validate_quality_rows(quality_rows),
    )
    lineage_snapshot = write_layer_snapshot(
        "gold.lineage_coverage_daily",
        target_dir / "gold" / "lineage_coverage_daily.jsonl",
        lineage_rows,
        quality_errors=validate_lineage_rows(lineage_rows),
    )

    layer_snapshots = (inventory_snapshot, contract_snapshot, quality_snapshot, lineage_snapshot)
    manifest = build_manifest(
        snapshot_id=resolved_snapshot_id,
        generated_at=build_time,
        input_path=source_path,
        report=report,
        output_dir=target_dir,
        layer_snapshots=layer_snapshots,
    )
    manifest_path = target_dir / "manifests" / f"control_tower.{resolved_snapshot_id}.json"
    write_manifest(manifest_path, manifest)

    return ControlTowerPipelineResult(
        snapshot_id=resolved_snapshot_id,
        report_path=source_path,
        inventory_path=inventory_snapshot.path,
        contract_compliance_path=contract_snapshot.path,
        quality_sla_path=quality_snapshot.path,
        lineage_coverage_path=lineage_snapshot.path,
        manifest_path=manifest_path,
        manifest=manifest,
    )


def build_inventory_rows(report: dict[str, Any], *, snapshot_id: str, built_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for product in data_products(report):
        quality_profile_id = first_quality_profile_id(product)
        release = latest_release(product)
        top_blocker = first_blocker(product)
        contract = product.get("contract") if isinstance(product.get("contract"), dict) else {}
        rows.append(
            {
                "org_id": ORG_ID,
                "report_date": report_date(report, built_at),
                "data_product_name": product.get("name"),
                "product_id": product.get("product"),
                "domain_id": product.get("domain"),
                "layer": product.get("layer"),
                "contract_version": int_value(contract.get("contract_version")),
                "contract_status": product.get("status"),
                "environment": report.get("environment"),
                "owner_team": owner(product, "owner_team"),
                "business_owner": owner(product, "business_owner"),
                "technical_owner": owner(product, "technical_owner"),
                "data_steward": owner(product, "data_steward"),
                "classification": nested(product, "privacy", "classification"),
                "contains_pii": bool(nested(product, "privacy", "contains_pii")),
                "access_policy": nested(product, "access", "access_policy"),
                "consumer_contract": nested(product, "access", "consumer_contract"),
                "freshness_slo_minutes": int_value(nested(product, "quality", "freshness_slo_minutes")),
                "quality_profile_id": quality_profile_id,
                "top_blocker_gate": top_blocker.get("gate") if top_blocker else None,
                "last_successful_release_id": release.get("release_id") if release and release.get("release_passed") is True else None,
                "active_snapshot_id": snapshot_id,
                "lifecycle_state": lifecycle_state(product),
                "readiness_state": product.get("readiness_state"),
                "blocker_count": len(product.get("blockers", [])) if isinstance(product.get("blockers"), list) else 0,
                "generated_at": built_at,
            }
        )
    return rows


def build_contract_compliance_rows(report: dict[str, Any], *, built_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for product in data_products(report):
        contract = product.get("contract") if isinstance(product.get("contract"), dict) else {}
        blockers = product.get("blockers") if isinstance(product.get("blockers"), list) else []
        failed_gate_count = len(blockers)
        registry = registry_evidence(product)
        rows.append(
            {
                "org_id": ORG_ID,
                "report_date": report_date(report, built_at),
                "data_product_name": product.get("name"),
                "contract_hash": product.get("contract_hash"),
                "contract_valid": contract.get("valid") is True,
                "contract_status": product.get("status"),
                "schema_column_count": int_value(contract.get("schema_column_count")),
                "quality_check_count": int_value(nested(product, "quality", "check_count")),
                "access_policy_passed": nested(product, "access", "access_policy_passed") is True,
                "consumer_contract_passed": nested(product, "access", "consumer_contract_passed") is True,
                "compatibility_status": "NOT_ATTACHED" if not registry.get("uri") else "PASSED",
                "breaking_change_risk": "HIGH" if contract.get("valid") is not True else "LOW",
                "registry_report_uri": registry.get("uri"),
                "registry_report_hash": registry.get("hash"),
                "retention_policy_passed": not has_failed_gate(product, "retention"),
                "privacy_policy_passed": nested(product, "access", "access_policy_passed") is True,
                "highest_severity": highest_severity(blockers),
                "failed_gate_count": failed_gate_count,
                "blocker_details": blockers,
                "last_checked_at": built_at,
                "generated_at": built_at,
            }
        )
    return rows


def build_quality_sla_rows(report: dict[str, Any], *, built_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for product in data_products(report):
        release = latest_release(product)
        release_passed = nested(product, "release_evidence", "passed") is True
        release_covered = nested(product, "release_evidence", "covered") is True
        quality_ops = nested(product, "quality", "quality_slo_ops")
        quality_ops = quality_ops if isinstance(quality_ops, dict) else {}
        runtime_quality = quality_ops.get("runtime_quality") if isinstance(quality_ops.get("runtime_quality"), dict) else {}
        quality_profile_id = first_quality_profile_id(product)
        failed_count = count_failed_quality_gates(product)
        layer = str(product.get("layer") or "")
        output = release_output(product)
        sla_status = quality_sla_status(product, release_passed=release_passed, release_covered=release_covered)
        observed_age_minutes = age_minutes(runtime_quality.get("age_seconds"))
        runtime_freshness_status = runtime_quality.get("freshness_status")
        quality_ops_release = quality_ops.get("release") if isinstance(quality_ops.get("release"), dict) else {}
        freshness_status = (
            str(runtime_freshness_status)
            if runtime_freshness_status in {"GREEN", "AMBER", "RED", "UNKNOWN"}
            else ("UNKNOWN" if not release_covered else ("GREEN" if release_passed else "RED"))
        )
        release_gate_status = (
            "PASSED"
            if quality_ops.get("passed") is True and quality_ops_release.get("attached") is True
            else (
                "FAILED"
                if quality_ops.get("passed") is False and quality_ops_release.get("attached") is True
                else ("PASSED" if release_passed else ("FAILED" if release_covered else "MISSING"))
            )
        )
        rows.append(
            {
                "org_id": ORG_ID,
                "report_date": report_date(report, built_at),
                "data_product_name": product.get("name"),
                "layer": layer,
                "freshness_slo_minutes": int_value(nested(product, "quality", "freshness_slo_minutes")),
                "observed_age_minutes": observed_age_minutes,
                "freshness_status": freshness_status,
                "ingestion_lag_minutes": None,
                "ingestion_lag_status": "UNKNOWN",
                "quality_check_count": int_value(nested(product, "quality", "check_count")),
                "quality_failed_count": failed_count,
                "quarantine_row_count": int_value(runtime_quality.get("quarantine_row_count")),
                "output_row_count": output.get("row_count"),
                "output_hash": output.get("content_hash"),
                "quality_profile_id": quality_profile_id,
                "release_evidence_passed": release_passed,
                "release_id": release.get("release_id") if release else None,
                "release_gate_status": release_gate_status,
                "runtime_lineage_present": nested(product, "lineage", "runtime_lineage_present") is True,
                "sla_status": sla_status,
                "incident_id": incident_id(product, sla_status),
                "assignee": owner(product, "owner_team") if sla_status == "RED" else None,
                "sla_age_minutes": 0,
                "generated_at": built_at,
            }
        )
    return rows


def build_lineage_coverage_rows(report: dict[str, Any], *, built_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for product in data_products(report):
        lineage = product.get("lineage") if isinstance(product.get("lineage"), dict) else {}
        runtime_present = lineage.get("runtime_lineage_present") is True
        static_present = lineage.get("static_lineage_present") is True
        missing_reason = None
        if lineage.get("lineage_required") is True and not static_present:
            missing_reason = "STATIC_LINEAGE_MISSING"
        elif lineage.get("lineage_required") is True and not runtime_present:
            missing_reason = "RUNTIME_LINEAGE_MISSING"
        rows.append(
            {
                "org_id": ORG_ID,
                "report_date": report_date(report, built_at),
                "data_product_name": product.get("name"),
                "upstream_count": len(lineage.get("upstream", [])) if isinstance(lineage.get("upstream"), list) else 0,
                "static_edge_count": int_value(lineage.get("static_edge_count")),
                "runtime_edge_count": int_value(lineage.get("runtime_edge_count")),
                "runtime_run_count": int_value(lineage.get("runtime_run_count")),
                "catalog_system": lineage.get("catalog") or "UNKNOWN",
                "catalog_publish_status": lineage.get("catalog_publish_status") or "NOT_ATTACHED",
                "openlineage_event_count": int_value(lineage.get("openlineage_event_count")),
                "lineage_required": lineage.get("lineage_required") is True,
                "static_lineage_present": static_present,
                "runtime_lineage_present": runtime_present,
                "missing_lineage_reason": missing_reason,
                "last_runtime_run_id": lineage.get("last_runtime_run_id"),
                "last_runtime_run_at": lineage.get("last_runtime_run_at"),
                "downstream_impact_count": downstream_impact_count(report, str(product.get("name"))),
                "downstream_p0_count": downstream_p0_count(report, str(product.get("name"))),
                "impact_severity": "P0" if downstream_p0_count(report, str(product.get("name"))) > 0 else ("P1" if missing_reason else "NONE"),
                "owner_action_required": missing_reason is not None,
                "generated_at": built_at,
            }
        )
    return rows


def build_manifest(
    *,
    snapshot_id: str,
    generated_at: str,
    input_path: Path,
    report: dict[str, Any],
    output_dir: Path,
    layer_snapshots: tuple[LayerSnapshot, ...],
) -> dict[str, Any]:
    layers = {snapshot.name: snapshot.as_manifest_entry(output_dir) for snapshot in layer_snapshots}
    quality_passed = all(snapshot.quality_passed for snapshot in layer_snapshots)
    inventory = layers["gold.data_product_inventory"]
    return {
        "pipeline": PIPELINE_NAME,
        "product_id": PRODUCT_ID,
        "snapshot_id": snapshot_id,
        "generated_at": generated_at,
        "input": {
            "path": input_path.as_posix(),
            "content_hash": hash_file(input_path),
            "artifact_type": report.get("artifact_type"),
            "report_id": report.get("report_id"),
            "readiness_state": report.get("readiness_state"),
            "p0_ready": report.get("p0_ready"),
        },
        "layers": layers,
        "lineage_edges": control_tower_lineage_edges(),
        "source_positions": [],
        "upstream_quality_passed": report.get("artifact_type") == "data_product_control_tower_report.v1",
        "row_count": inventory["row_count"],
        "content_hash": combined_layer_hash(layer_snapshots),
        "quality_passed": quality_passed,
    }


def control_tower_lineage_edges() -> list[dict[str, str]]:
    return [
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "gold.data_product_inventory",
            "target": "gold.contract_compliance_daily",
        },
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "gold.data_product_inventory",
            "target": "gold.quality_sla_daily",
        },
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "gold.contract_compliance_daily",
            "target": "gold.quality_sla_daily",
        },
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "gold.data_product_inventory",
            "target": "gold.lineage_coverage_daily",
        },
    ]


def write_layer_snapshot(
    name: str,
    path: Path,
    rows: list[dict[str, Any]],
    *,
    quality_errors: tuple[str, ...],
) -> LayerSnapshot:
    write_jsonl(path, rows)
    return LayerSnapshot(
        name=name,
        path=path,
        row_count=len(rows),
        content_hash=hash_file(path),
        quality_passed=not quality_errors,
        quality_errors=quality_errors,
    )


def validate_control_tower_input(path: Path, report: dict[str, Any]) -> None:
    if report.get("artifact_type") != "data_product_control_tower_report.v1":
        raise ValueError(f"{path}: expected artifact_type=data_product_control_tower_report.v1")
    if not isinstance(report.get("data_products"), list) or not report["data_products"]:
        raise ValueError(f"{path}: data_products must be a non-empty list")


def validate_inventory_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors = []
    if not rows:
        errors.append("inventory_rows_empty")
    for index, row in enumerate(rows):
        if not row.get("data_product_name"):
            errors.append(f"inventory[{index}].data_product_name_missing")
        if row.get("readiness_state") not in {"ready_for_production_signoff", "blocked"}:
            errors.append(f"inventory[{index}].readiness_state_invalid")
        if row.get("lifecycle_state") not in ALLOWED_LIFECYCLE_STATES:
            errors.append(f"inventory[{index}].lifecycle_state_invalid")
    return tuple(errors)


def validate_contract_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors = []
    if not rows:
        errors.append("contract_rows_empty")
    for index, row in enumerate(rows):
        if row.get("compatibility_status") not in {"PASSED", "FAILED", "NOT_ATTACHED", "UNKNOWN"}:
            errors.append(f"contract[{index}].compatibility_status_invalid")
        if not isinstance(row.get("blocker_details"), list):
            errors.append(f"contract[{index}].blocker_details_not_list")
    return tuple(errors)


def validate_quality_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors = []
    if not rows:
        errors.append("quality_rows_empty")
    for index, row in enumerate(rows):
        for key in ("freshness_status", "ingestion_lag_status", "sla_status"):
            if row.get(key) not in ALLOWED_STATUS:
                errors.append(f"quality[{index}].{key}_invalid")
        if row.get("release_gate_status") not in {"PASSED", "FAILED", "MISSING"}:
            errors.append(f"quality[{index}].release_gate_status_invalid")
    return tuple(errors)


def validate_lineage_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors = []
    if not rows:
        errors.append("lineage_rows_empty")
    for index, row in enumerate(rows):
        if row.get("catalog_publish_status") not in {"READY", "BLOCKED", "NOT_ATTACHED", "UNKNOWN"}:
            errors.append(f"lineage[{index}].catalog_publish_status_invalid")
        if row.get("impact_severity") not in {"P0", "P1", "P2", "P3", "NONE"}:
            errors.append(f"lineage[{index}].impact_severity_invalid")
    return tuple(errors)


def data_products(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in report.get("data_products", []) if isinstance(item, dict)]


def first_quality_profile_id(product: dict[str, Any]) -> str | None:
    profiles = nested(product, "quality", "quality_profiles")
    if not isinstance(profiles, list) or not profiles:
        return None
    first = profiles[0]
    return first.get("id") if isinstance(first, dict) else None


def latest_release(product: dict[str, Any]) -> dict[str, Any] | None:
    releases = nested(product, "release_evidence", "releases")
    if not isinstance(releases, list) or not releases:
        return None
    candidates = [item for item in releases if isinstance(item, dict)]
    passed = [item for item in candidates if item.get("release_passed") is True]
    return (passed or candidates)[-1] if candidates else None


def release_output(product: dict[str, Any]) -> dict[str, Any]:
    release = latest_release(product)
    if not release:
        return {}
    return {
        "row_count": release.get("row_count"),
        "content_hash": release.get("content_hash") or release.get("evidence_hash"),
    }


def first_blocker(product: dict[str, Any]) -> dict[str, Any] | None:
    blockers = product.get("blockers")
    if not isinstance(blockers, list):
        return None
    for blocker in blockers:
        if isinstance(blocker, dict):
            return blocker
    return None


def lifecycle_state(product: dict[str, Any]) -> str:
    status = product.get("status")
    if status == "DEPRECATED":
        return "DEPRECATED"
    if product.get("readiness_state") == "ready_for_production_signoff":
        return "CERTIFIED"
    if status == "ACTIVE":
        return "ACTIVE"
    if status == "DRAFT":
        return "DRAFT_CONTRACT"
    return "CANDIDATE"


def quality_sla_status(product: dict[str, Any], *, release_passed: bool, release_covered: bool) -> str:
    quality_gates = {
        "freshness_slo_declared",
        "quality_checks_declared",
        "gold_quality_profile_attached",
        "gold_release_evidence_passed",
        "runtime_lineage_evidence_present",
    }
    blockers = product.get("blockers") if isinstance(product.get("blockers"), list) else []
    if any(isinstance(blocker, dict) and blocker.get("gate") in quality_gates for blocker in blockers):
        return "RED"
    if release_covered and release_passed:
        return "GREEN"
    return "UNKNOWN"


def count_failed_quality_gates(product: dict[str, Any]) -> int:
    quality_gates = {
        "freshness_slo_declared",
        "quality_checks_declared",
        "gold_quality_profile_attached",
        "gold_release_evidence_passed",
        "runtime_lineage_evidence_present",
    }
    blockers = product.get("blockers") if isinstance(product.get("blockers"), list) else []
    return sum(1 for blocker in blockers if isinstance(blocker, dict) and blocker.get("gate") in quality_gates)


def incident_id(product: dict[str, Any], status: str) -> str | None:
    if status != "RED":
        return None
    return stable_id("control-tower-incident", product.get("name"), first_blocker(product))


def downstream_impact_count(report: dict[str, Any], data_product_name: str) -> int:
    return sum(
        1
        for row in report.get("gate_matrix", [])
        if isinstance(row, dict) and row.get("data_product") == data_product_name
    )


def downstream_p0_count(report: dict[str, Any], data_product_name: str) -> int:
    return sum(
        1
        for row in report.get("gate_matrix", [])
        if isinstance(row, dict) and row.get("data_product") == data_product_name and row.get("severity") == "P0"
    )


def registry_evidence(product: dict[str, Any]) -> dict[str, Any]:
    checks = product.get("checks") if isinstance(product.get("checks"), list) else []
    for check in checks:
        if not isinstance(check, dict):
            continue
        details = check.get("details")
        if isinstance(details, dict):
            evaluation = details.get("evaluation")
            if isinstance(evaluation, dict) and evaluation.get("registry_report_uri"):
                return {
                    "uri": evaluation.get("registry_report_uri"),
                    "hash": evaluation.get("registry_report_hash"),
                }
    return {}


def has_failed_gate(product: dict[str, Any], pattern: str) -> bool:
    blockers = product.get("blockers") if isinstance(product.get("blockers"), list) else []
    return any(isinstance(blocker, dict) and pattern in str(blocker.get("gate")) for blocker in blockers)


def highest_severity(blockers: list[Any]) -> str:
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    values = [
        str(blocker.get("severity"))
        for blocker in blockers
        if isinstance(blocker, dict) and blocker.get("severity") in order
    ]
    return sorted(values, key=lambda value: order[value])[0] if values else "NONE"


def owner(product: dict[str, Any], key: str) -> str | None:
    owners = product.get("owners")
    if isinstance(owners, dict):
        value = owners.get(key)
        return str(value) if value is not None else None
    return None


def nested(mapping: dict[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def report_date(report: dict[str, Any], fallback: str) -> str:
    timestamp = str(report.get("generated_at") or fallback)
    return timestamp[:10]


def int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def age_minutes(value: object) -> int | None:
    if isinstance(value, int | float):
        return int(value // 60)
    return None


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{canonical_json(row)}\n" for row in rows), encoding="utf-8")


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def combined_layer_hash(layer_snapshots: tuple[LayerSnapshot, ...]) -> str:
    return stable_id("control-tower-layers", [(snapshot.name, snapshot.content_hash) for snapshot in layer_snapshots])


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _compact_timestamp(value: str) -> str:
    return value.replace("-", "").replace(":", "").replace("T", "").replace("Z", "")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

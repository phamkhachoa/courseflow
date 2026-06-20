from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import build_catalog_bundle, canonical_json, hash_file, load_json
from enterprise_dp.catalog_publish import validate_catalog_publish_manifest
from enterprise_dp.openlineage import validate_openlineage_events


REPORT_VERSION = 1
SUPPORTED_ENVIRONMENTS = {"local", "staging", "prod"}
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}


@dataclass(frozen=True)
class CatalogLineageOpsReportResult:
    output_path: Path
    report: dict[str, Any]


def write_catalog_lineage_ops_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str = "local",
    catalog_bundle_path: str | Path | None = None,
    catalog_bundle: dict[str, Any] | None = None,
    catalog_publish_manifest_path: str | Path | None = None,
    openlineage_events_path: str | Path | None = None,
    publish_receipt_path: str | Path | None = None,
    generated_at: str | None = None,
) -> CatalogLineageOpsReportResult:
    report = build_catalog_lineage_ops_report(
        root,
        environment=environment,
        catalog_bundle_path=catalog_bundle_path,
        catalog_bundle=catalog_bundle,
        catalog_publish_manifest_path=catalog_publish_manifest_path,
        openlineage_events_path=openlineage_events_path,
        publish_receipt_path=publish_receipt_path,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return CatalogLineageOpsReportResult(output_path=target, report=report)


def build_catalog_lineage_ops_report(
    root: str | Path,
    *,
    environment: str = "local",
    catalog_bundle_path: str | Path | None = None,
    catalog_bundle: dict[str, Any] | None = None,
    catalog_publish_manifest_path: str | Path | None = None,
    openlineage_events_path: str | Path | None = None,
    publish_receipt_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or utc_now()
    catalog_ref, catalog = load_or_build_catalog_bundle(
        root,
        catalog_bundle_path=catalog_bundle_path,
        catalog_bundle=catalog_bundle,
        generated_at=generated,
    )
    publish_ref, publish_manifest = load_optional_json(catalog_publish_manifest_path)
    openlineage_ref, openlineage_events = load_openlineage_events(openlineage_events_path)
    receipt_ref, publish_receipt = load_optional_json(publish_receipt_path)
    publish_validation = validate_catalog_publish_manifest(publish_manifest) if publish_manifest else None
    openlineage_validation = validate_openlineage_events(openlineage_events) if openlineage_events else None
    product_rows = [
        catalog_lineage_product_row(
            product,
            catalog,
            openlineage_events,
            publish_manifest,
            publish_receipt,
            environment=environment,
        )
        for product in sorted(catalog.get("data_products", []), key=lambda item: str(item.get("name")))
        if isinstance(product, dict)
    ]
    global_checks = catalog_lineage_global_checks(
        environment=environment,
        catalog_ref=catalog_ref,
        publish_ref=publish_ref,
        publish_manifest=publish_manifest,
        publish_validation=publish_validation,
        openlineage_ref=openlineage_ref,
        openlineage_events=openlineage_events,
        openlineage_validation=openlineage_validation,
        receipt_ref=receipt_ref,
        publish_receipt=publish_receipt,
    )
    failed_global = [check for check in global_checks if check.get("passed") is not True]
    failed_products = [row for row in product_rows if row.get("passed") is not True]
    passed = not failed_global and not failed_products
    readiness_state = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    return {
        "artifact_type": "catalog_lineage_ops_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id(
            "catalog-lineage-ops",
            environment,
            generated,
            catalog_ref,
            publish_ref,
            openlineage_ref,
            receipt_ref,
        ),
        "generated_at": generated,
        "environment": environment,
        "capability_id": "catalog-lineage-control-plane",
        "readiness_state": readiness_state,
        "mode": "runtime_attested" if receipt_ref.get("attached") is True else "local_preflight",
        "inputs": {
            "catalog_bundle": catalog_ref,
            "catalog_publish_manifest": publish_ref,
            "openlineage_events": openlineage_ref,
            "publish_receipt": receipt_ref,
        },
        "checks": global_checks,
        "data_products": product_rows,
        "decision_board": {
            "failed_products": [compact_product_row(row) for row in failed_products[:30]],
            "page_now": [
                action
                for row in failed_products
                for action in row.get("next_actions", [])
                if isinstance(action, dict) and action.get("priority") == "P0"
            ][:30],
        },
        "summary": catalog_lineage_summary(
            product_rows,
            failed_global,
            catalog_ref,
            publish_ref,
            openlineage_ref,
            receipt_ref,
        ),
        "passed": passed,
    }


def load_or_build_catalog_bundle(
    root: str | Path,
    *,
    catalog_bundle_path: str | Path | None,
    catalog_bundle: dict[str, Any] | None,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if catalog_bundle_path:
        path = Path(catalog_bundle_path)
        payload = load_json(path)
        return catalog_ref(payload, source="artifact", path=path), payload
    payload = catalog_bundle if isinstance(catalog_bundle, dict) else build_catalog_bundle(root, generated_at=generated_at)
    return catalog_ref(payload, source="generated_from_root", path=None), payload


def catalog_ref(payload: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {
        "attached": True,
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(payload),
        "generated_at": payload.get("generated_at"),
        "product_count": summary.get("product_count", 0),
        "data_product_count": summary.get("data_product_count", 0),
        "lineage_edge_count": summary.get("lineage_edge_count", 0),
        "run_evidence_count": summary.get("run_evidence_count", 0),
    }


def load_optional_json(path_value: str | Path | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if path_value is None:
        return {"attached": False}, None
    path = Path(path_value)
    if not path.is_file():
        return {"attached": False, "uri": path.as_posix(), "missing": True}, None
    payload = load_json(path)
    return {
        "attached": True,
        "uri": path.as_posix(),
        "hash": hash_file(path),
        "artifact_type": payload.get("artifact_type"),
        "generated_at": payload.get("generated_at"),
        "environment": payload.get("environment") or mapping(payload, "target").get("environment"),
        "passed": payload.get("passed"),
    }, payload


def load_openlineage_events(path_value: str | Path | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if path_value is None:
        return {"attached": False}, []
    path = Path(path_value)
    if not path.is_file():
        return {"attached": False, "uri": path.as_posix(), "missing": True}, []
    events: list[dict[str, Any]] = []
    parse_errors = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            parse_errors.append(f"line {index}: {exc.msg}")
            continue
        if isinstance(payload, dict):
            events.append(payload)
        else:
            parse_errors.append(f"line {index}: event must be a JSON object")
    namespaces = sorted(
        {
            str(mapping(event, "job").get("namespace"))
            for event in events
            if mapping(event, "job").get("namespace")
        }
    )
    producers = sorted({str(event.get("producer")) for event in events if event.get("producer")})
    return {
        "attached": True,
        "uri": path.as_posix(),
        "hash": hash_file(path),
        "event_count": len(events),
        "parse_errors": parse_errors,
        "namespaces": namespaces,
        "producers": producers,
    }, events


def catalog_lineage_global_checks(
    *,
    environment: str,
    catalog_ref: dict[str, Any],
    publish_ref: dict[str, Any],
    publish_manifest: dict[str, Any] | None,
    publish_validation: Any,
    openlineage_ref: dict[str, Any],
    openlineage_events: list[dict[str, Any]],
    openlineage_validation: Any,
    receipt_ref: dict[str, Any],
    publish_receipt: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    target = mapping(publish_manifest or {}, "target")
    publish_catalog = mapping(publish_manifest or {}, "catalog_bundle")
    publish_lineage = mapping(publish_manifest or {}, "openlineage")
    receipt_target = mapping(publish_receipt or {}, "target")
    validation_errors = list(getattr(openlineage_validation, "errors", [])) if openlineage_validation else []
    return [
        check("environment_supported", environment in SUPPORTED_ENVIRONMENTS, {"environment": environment}),
        check("catalog_bundle_attached", catalog_ref.get("attached") is True, catalog_ref),
        check(
            "catalog_publish_manifest_attached_for_production_like",
            not production_like or publish_ref.get("attached") is True,
            publish_ref,
        ),
        check(
            "catalog_publish_manifest_artifact_type_valid",
            publish_manifest is None or publish_manifest.get("artifact_type") == "catalog_publish_manifest.v1",
            {"artifact_type": publish_manifest.get("artifact_type") if isinstance(publish_manifest, dict) else None},
        ),
        check(
            "catalog_publish_manifest_passed",
            publish_manifest is None or publish_manifest.get("passed") is True,
            {"passed": publish_manifest.get("passed") if isinstance(publish_manifest, dict) else None},
        ),
        check(
            "catalog_publish_manifest_validation_passed",
            publish_validation is None or publish_validation.get("passed") is True,
            {"failures": publish_validation.get("failures", []) if isinstance(publish_validation, dict) else []},
        ),
        check(
            "catalog_hash_matches_publish_manifest",
            publish_manifest is None or publish_catalog.get("hash") == catalog_ref.get("hash"),
            {"catalog_hash": catalog_ref.get("hash"), "publish_catalog_hash": publish_catalog.get("hash")},
        ),
        check(
            "catalog_publish_environment_matches",
            publish_manifest is None or target.get("environment") == environment,
            {"expected": environment, "actual": target.get("environment")},
        ),
        check(
            "production_publish_endpoint_declared",
            not production_like or non_empty(target.get("endpoint")),
            {"endpoint": target.get("endpoint")},
        ),
        check(
            "production_requested_by_declared",
            not production_like or non_empty((publish_manifest or {}).get("requested_by")),
            {"requested_by": (publish_manifest or {}).get("requested_by")},
        ),
        check(
            "production_change_ticket_declared",
            not production_like or non_empty((publish_manifest or {}).get("change_ticket")),
            {"change_ticket": (publish_manifest or {}).get("change_ticket")},
        ),
        check(
            "openlineage_attached_for_production_like",
            not production_like or openlineage_ref.get("attached") is True,
            openlineage_ref,
        ),
        check(
            "openlineage_jsonl_parse_passed",
            not openlineage_ref.get("parse_errors"),
            {"parse_errors": openlineage_ref.get("parse_errors", [])},
        ),
        check(
            "openlineage_events_valid",
            not openlineage_events or openlineage_validation.ok,
            {"errors": validation_errors},
        ),
        check(
            "openlineage_events_non_empty_for_production_like",
            not production_like or int_value(openlineage_ref.get("event_count")) > 0,
            {"event_count": openlineage_ref.get("event_count", 0)},
        ),
        check(
            "openlineage_hash_matches_publish_manifest",
            publish_manifest is None
            or publish_lineage.get("attached") is not True
            or publish_lineage.get("hash") == openlineage_ref.get("hash"),
            {"openlineage_hash": openlineage_ref.get("hash"), "publish_openlineage_hash": publish_lineage.get("hash")},
        ),
        check(
            "production_openlineage_namespace_not_local",
            not production_like or not local_namespace_used(openlineage_ref.get("namespaces", [])),
            {"namespaces": openlineage_ref.get("namespaces", [])},
        ),
        check(
            "production_openlineage_producer_not_local",
            not production_like or not local_producer_used(openlineage_ref.get("producers", [])),
            {"producers": openlineage_ref.get("producers", [])},
        ),
        check(
            "publish_receipt_attached_for_production_like",
            not production_like or receipt_ref.get("attached") is True,
            receipt_ref,
        ),
        check(
            "publish_receipt_artifact_type_valid",
            publish_receipt is None or publish_receipt.get("artifact_type") == "catalog_publish_receipt.v1",
            {"artifact_type": publish_receipt.get("artifact_type") if isinstance(publish_receipt, dict) else None},
        ),
        check(
            "publish_receipt_environment_matches",
            publish_receipt is None or publish_receipt.get("environment") == environment,
            {"expected": environment, "actual": publish_receipt.get("environment") if isinstance(publish_receipt, dict) else None},
        ),
        check(
            "publish_receipt_status_succeeded",
            publish_receipt is None or publish_receipt.get("status") == "succeeded",
            {"status": publish_receipt.get("status") if isinstance(publish_receipt, dict) else None},
        ),
        check(
            "publish_receipt_catalog_hash_matches",
            publish_receipt is None or publish_receipt.get("catalog_bundle_hash") == catalog_ref.get("hash"),
            {"catalog_hash": catalog_ref.get("hash"), "receipt_catalog_hash": publish_receipt.get("catalog_bundle_hash") if isinstance(publish_receipt, dict) else None},
        ),
        check(
            "publish_receipt_manifest_hash_matches",
            publish_receipt is None
            or not publish_ref.get("hash")
            or publish_receipt.get("catalog_publish_manifest_hash") == publish_ref.get("hash"),
            {"publish_manifest_hash": publish_ref.get("hash"), "receipt_manifest_hash": publish_receipt.get("catalog_publish_manifest_hash") if isinstance(publish_receipt, dict) else None},
        ),
        check(
            "publish_receipt_openlineage_hash_matches",
            publish_receipt is None
            or not openlineage_ref.get("hash")
            or publish_receipt.get("openlineage_hash") == openlineage_ref.get("hash"),
            {
                "openlineage_hash": openlineage_ref.get("hash"),
                "receipt_openlineage_hash": publish_receipt.get("openlineage_hash") if isinstance(publish_receipt, dict) else None,
            },
        ),
        check(
            "publish_receipt_target_matches",
            publish_receipt is None
            or target.get("system") is None
            or (
                receipt_target.get("system") == target.get("system")
                and receipt_target.get("endpoint") == target.get("endpoint")
            ),
            {"target": target, "receipt_target": receipt_target},
        ),
    ]


def catalog_lineage_product_row(
    product: dict[str, Any],
    catalog: dict[str, Any],
    openlineage_events: list[dict[str, Any]],
    publish_manifest: dict[str, Any] | None,
    publish_receipt: dict[str, Any] | None,
    *,
    environment: str,
) -> dict[str, Any]:
    name = str(product.get("name"))
    lineage = mapping(product, "lineage")
    lineage_required = lineage.get("lineage_required") is True
    static_edge_count = static_edge_count_for_product(catalog, name)
    runtime = runtime_lineage_for_product(openlineage_events, name)
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    checks = [
        check("owner_team_declared", non_empty(product.get("owner_team")), {"owner_team": product.get("owner_team")}),
        check("data_steward_declared", non_empty(product.get("data_steward")), {"data_steward": product.get("data_steward")}),
        check("static_lineage_present", not lineage_required or static_edge_count > 0, {"static_edge_count": static_edge_count}),
        check(
            "runtime_lineage_present_for_production_like",
            not (production_like and lineage_required) or runtime["event_count"] > 0,
            {"event_count": runtime["event_count"], "last_run_id": runtime.get("last_run_id")},
        ),
    ]
    issues = catalog_lineage_product_issues(checks)
    publish_status = catalog_publish_status(publish_manifest, publish_receipt, environment=environment)
    return {
        "data_product": name,
        "layer": product.get("layer"),
        "domain": product.get("domain"),
        "product": product.get("product"),
        "catalog_system": lineage.get("catalog") or target_system(publish_manifest),
        "catalog_publish_status": publish_status,
        "lineage_required": lineage_required,
        "static_edge_count": static_edge_count,
        "runtime_event_count": runtime["event_count"],
        "runtime_lineage_present": runtime["event_count"] > 0,
        "last_runtime_run_id": runtime.get("last_run_id"),
        "last_runtime_run_at": runtime.get("last_run_at"),
        "checks": checks,
        "issues": issues,
        "risk_state": issues[0] if issues else "ok",
        "next_actions": catalog_lineage_next_actions(issues, name),
        "passed": not issues,
    }


def static_edge_count_for_product(catalog: dict[str, Any], data_product_name: str) -> int:
    urn = f"urn:enterprise-dp:data-product:{data_product_name}"
    return sum(
        1
        for edge in catalog.get("lineage_edges", [])
        if isinstance(edge, dict)
        and edge.get("type") != "RUN_LAYER_TRANSFORM"
        and (edge.get("source") == urn or edge.get("target") == urn)
    )


def runtime_lineage_for_product(openlineage_events: list[dict[str, Any]], data_product_name: str) -> dict[str, Any]:
    matched = []
    for event in openlineage_events:
        datasets = list_value(event.get("inputs")) + list_value(event.get("outputs"))
        if any(isinstance(dataset, dict) and dataset.get("name") == data_product_name for dataset in datasets):
            matched.append(event)
    matched.sort(key=lambda item: str(item.get("eventTime") or ""))
    if not matched:
        return {"event_count": 0}
    latest = matched[-1]
    return {
        "event_count": len(matched),
        "last_run_id": mapping(latest, "run").get("runId"),
        "last_run_at": latest.get("eventTime"),
    }


def catalog_lineage_product_issues(checks: list[dict[str, Any]]) -> list[str]:
    issue_map = {
        "owner_team_declared": "owner_missing",
        "data_steward_declared": "steward_missing",
        "static_lineage_present": "static_lineage_missing",
        "runtime_lineage_present_for_production_like": "runtime_lineage_missing",
    }
    return [
        issue_map[check["name"]]
        for check in checks
        if check.get("passed") is not True and check.get("name") in issue_map
    ]


def catalog_lineage_next_actions(issues: list[str], data_product: str) -> list[dict[str, Any]]:
    actions = []
    if "owner_missing" in issues or "steward_missing" in issues:
        actions.append({"priority": "P0", "action": "repair_catalog_ownership", "owner": "data-platform-team"})
    if "static_lineage_missing" in issues:
        actions.append({"priority": "P0", "action": "repair_catalog_lineage", "owner": "data-platform-team"})
    if "runtime_lineage_missing" in issues:
        actions.append({"priority": "P0", "action": "attach_openlineage_runtime_events", "owner": "data-platform-team"})
    return actions or [{"priority": "P3", "action": "no_action", "owner": data_product}]


def catalog_lineage_summary(
    rows: list[dict[str, Any]],
    failed_global_checks: list[dict[str, Any]],
    catalog_ref: dict[str, Any],
    publish_ref: dict[str, Any],
    openlineage_ref: dict[str, Any],
    receipt_ref: dict[str, Any],
) -> dict[str, Any]:
    failed_products = [row for row in rows if row.get("passed") is not True]
    publish_statuses = {str(row.get("catalog_publish_status")) for row in rows}
    status = "UNKNOWN"
    if publish_statuses == {"READY"}:
        status = "READY"
    elif "BLOCKED" in publish_statuses:
        status = "BLOCKED"
    elif publish_statuses == {"NOT_ATTACHED"}:
        status = "NOT_ATTACHED"
    return {
        "data_product_count": len(rows),
        "failed_product_count": len(failed_products),
        "global_failed_check_count": len(failed_global_checks),
        "catalog_hash": catalog_ref.get("hash"),
        "catalog_publish_status": status,
        "catalog_publish_manifest_attached": publish_ref.get("attached") is True,
        "openlineage_attached": openlineage_ref.get("attached") is True,
        "openlineage_event_count": openlineage_ref.get("event_count", 0),
        "publish_receipt_attached": receipt_ref.get("attached") is True,
        "owner_steward_gap_count": sum(
            1
            for row in rows
            if "owner_missing" in row.get("issues", []) or "steward_missing" in row.get("issues", [])
        ),
        "static_lineage_gap_count": sum(1 for row in rows if "static_lineage_missing" in row.get("issues", [])),
        "runtime_lineage_gap_count": sum(1 for row in rows if "runtime_lineage_missing" in row.get("issues", [])),
        "by_risk_state": count_by(rows, "risk_state"),
    }


def catalog_publish_status(
    publish_manifest: dict[str, Any] | None,
    publish_receipt: dict[str, Any] | None,
    *,
    environment: str,
) -> str:
    if publish_manifest is None:
        return "NOT_ATTACHED"
    if publish_manifest.get("passed") is not True:
        return "BLOCKED"
    if environment in PRODUCTION_LIKE_ENVIRONMENTS and (
        publish_receipt is None or publish_receipt.get("status") != "succeeded"
    ):
        return "BLOCKED"
    return "READY"


def target_system(publish_manifest: dict[str, Any] | None) -> str | None:
    if not isinstance(publish_manifest, dict):
        return None
    return mapping(publish_manifest, "target").get("system")


def compact_product_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "data_product": row.get("data_product"),
        "risk_state": row.get("risk_state"),
        "issues": row.get("issues", []),
        "next_actions": row.get("next_actions", []),
    }


def local_namespace_used(namespaces: object) -> bool:
    return any(str(namespace).startswith("enterprise-dp://local") for namespace in list_value(namespaces))


def local_producer_used(producers: object) -> bool:
    return any("enterprise-dp.local" in str(producer) for producer in list_value(producers))


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def mapping(record: dict[str, Any], key: str) -> dict[str, Any]:
    value = record.get(key)
    return value if isinstance(value, dict) else {}


def list_value(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def content_hash(value: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()}"


def stable_id(*parts: Any) -> str:
    return hashlib.sha256(canonical_json(parts).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

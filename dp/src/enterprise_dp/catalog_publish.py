from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file, load_json


SUPPORTED_TARGETS = {"datahub", "openmetadata"}
SUPPORTED_ENVIRONMENTS = {"local", "staging", "prod"}


@dataclass(frozen=True)
class CatalogPublishManifestResult:
    output_path: Path
    manifest: dict[str, Any]


def write_catalog_publish_manifest(
    catalog_bundle_path: str | Path,
    output_path: str | Path,
    *,
    target_system: str,
    environment: str,
    endpoint: str | None = None,
    openlineage_events_path: str | Path | None = None,
    semantic_views_manifest_path: str | Path | None = None,
    requested_by: str | None = None,
    change_ticket: str | None = None,
    generated_at: str | None = None,
) -> CatalogPublishManifestResult:
    manifest = build_catalog_publish_manifest(
        catalog_bundle_path,
        target_system=target_system,
        environment=environment,
        endpoint=endpoint,
        openlineage_events_path=openlineage_events_path,
        semantic_views_manifest_path=semantic_views_manifest_path,
        requested_by=requested_by,
        change_ticket=change_ticket,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    return CatalogPublishManifestResult(output_path=target, manifest=manifest)


def build_catalog_publish_manifest(
    catalog_bundle_path: str | Path,
    *,
    target_system: str,
    environment: str,
    endpoint: str | None = None,
    openlineage_events_path: str | Path | None = None,
    semantic_views_manifest_path: str | Path | None = None,
    requested_by: str | None = None,
    change_ticket: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    catalog_path = Path(catalog_bundle_path)
    catalog_bundle = load_json(catalog_path)
    openlineage_path = Path(openlineage_events_path) if openlineage_events_path else None
    semantic_views_path = Path(semantic_views_manifest_path) if semantic_views_manifest_path else None
    openlineage_summary = summarize_openlineage(openlineage_path)
    semantic_views_summary = summarize_semantic_views(semantic_views_path)
    summary = catalog_bundle.get("summary") if isinstance(catalog_bundle.get("summary"), dict) else {}
    checks = catalog_publish_checks(
        catalog_bundle,
        catalog_path=catalog_path,
        target_system=target_system,
        environment=environment,
        endpoint=endpoint,
        openlineage_summary=openlineage_summary,
        semantic_views_summary=semantic_views_summary,
        requested_by=requested_by,
        change_ticket=change_ticket,
    )
    passed = all(item["passed"] is True for item in checks)
    return {
        "artifact_type": "catalog_publish_manifest.v1",
        "manifest_version": 1,
        "generated_at": generated_at or utc_now(),
        "publish_state": "ready_for_publish" if passed else "blocked",
        "target": {
            "system": target_system,
            "environment": environment,
            "endpoint": endpoint,
        },
        "requested_by": requested_by,
        "change_ticket": change_ticket,
        "catalog_bundle": {
            "uri": catalog_path.as_posix(),
            "hash": hash_file(catalog_path),
            "generated_at": catalog_bundle.get("generated_at"),
            "target": catalog_bundle.get("catalog_target"),
            "summary": summary,
        },
        "openlineage": openlineage_summary,
        "semantic_views": semantic_views_summary,
        "publish_payload": {
            "products": summary.get("product_count", 0),
            "domains": summary.get("domain_count", 0),
            "topics": summary.get("topic_count", 0),
            "data_products": summary.get("data_product_count", 0),
            "use_cases": summary.get("use_case_count", 0),
            "lineage_edges": summary.get("lineage_edge_count", 0),
            "semantic_views": semantic_views_summary.get("view_count", 0),
            "openlineage_events": openlineage_summary.get("event_count", 0),
        },
        "checks": checks,
        "failures": [
            {"check": item["name"], "details": item.get("details", {})}
            for item in checks
            if item.get("passed") is not True
        ],
        "passed": passed,
    }


def validate_catalog_publish_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    checks = [
        check("artifact_type", manifest.get("artifact_type") == "catalog_publish_manifest.v1", {"artifact_type": manifest.get("artifact_type")}),
        check("manifest_version", manifest.get("manifest_version") == 1, {"manifest_version": manifest.get("manifest_version")}),
        check("target_declared", isinstance(manifest.get("target"), dict), {"target": manifest.get("target")}),
        check("catalog_bundle_declared", isinstance(manifest.get("catalog_bundle"), dict), {"catalog_bundle": manifest.get("catalog_bundle")}),
        check("checks_declared", isinstance(manifest.get("checks"), list) and bool(manifest.get("checks")), {"checks": manifest.get("checks")}),
    ]
    if isinstance(manifest.get("checks"), list):
        checks.extend(item for item in manifest["checks"] if isinstance(item, dict))
    passed = all(item.get("passed") is True for item in checks)
    return {
        "passed": passed,
        "failures": [
            {"check": item.get("name"), "details": item.get("details", {})}
            for item in checks
            if item.get("passed") is not True
        ],
    }


def catalog_publish_checks(
    catalog_bundle: dict[str, Any],
    *,
    catalog_path: Path,
    target_system: str,
    environment: str,
    endpoint: str | None,
    openlineage_summary: dict[str, Any],
    semantic_views_summary: dict[str, Any],
    requested_by: str | None,
    change_ticket: str | None,
) -> list[dict[str, Any]]:
    summary = catalog_bundle.get("summary") if isinstance(catalog_bundle.get("summary"), dict) else {}
    production_like = environment != "local"
    return [
        check("catalog_bundle_file_exists", catalog_path.is_file(), {"uri": catalog_path.as_posix()}),
        check("target_system_supported", target_system in SUPPORTED_TARGETS, {"target_system": target_system}),
        check("environment_supported", environment in SUPPORTED_ENVIRONMENTS, {"environment": environment}),
        check("production_endpoint_declared", not production_like or non_empty(endpoint), {"endpoint": endpoint}),
        check("requested_by_declared", not production_like or non_empty(requested_by), {"requested_by": requested_by}),
        check("change_ticket_declared", not production_like or non_empty(change_ticket), {"change_ticket": change_ticket}),
        check("catalog_has_products", int_value(summary.get("product_count")) > 0, {"product_count": summary.get("product_count")}),
        check("catalog_has_domains", int_value(summary.get("domain_count")) > 0, {"domain_count": summary.get("domain_count")}),
        check("catalog_has_topics", int_value(summary.get("topic_count")) > 0, {"topic_count": summary.get("topic_count")}),
        check("catalog_has_data_products", int_value(summary.get("data_product_count")) > 0, {"data_product_count": summary.get("data_product_count")}),
        check("catalog_has_lineage_edges", int_value(summary.get("lineage_edge_count")) > 0, {"lineage_edge_count": summary.get("lineage_edge_count")}),
        check("production_openlineage_attached", not production_like or openlineage_summary.get("attached") is True, openlineage_summary),
        check("openlineage_events_valid", openlineage_summary.get("attached") is not True or int_value(openlineage_summary.get("event_count")) >= 0, openlineage_summary),
        check("production_semantic_views_attached", not production_like or semantic_views_summary.get("attached") is True, semantic_views_summary),
        check("semantic_views_valid", semantic_views_summary.get("attached") is not True or int_value(semantic_views_summary.get("view_count")) > 0, semantic_views_summary),
    ]


def summarize_openlineage(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"attached": False}
    if not path.is_file():
        return {"attached": False, "uri": path.as_posix(), "missing": True}
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        "attached": True,
        "uri": path.as_posix(),
        "hash": hash_file(path),
        "event_count": len(lines),
    }


def summarize_semantic_views(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"attached": False}
    if not path.is_file():
        return {"attached": False, "uri": path.as_posix(), "missing": True}
    manifest = load_json(path)
    summary = manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {}
    return {
        "attached": True,
        "uri": path.as_posix(),
        "hash": hash_file(path),
        "artifact_type": manifest.get("artifact_type"),
        "engine": manifest.get("engine"),
        "view_count": summary.get("view_count", 0),
        "metric_count": summary.get("metric_count", 0),
    }


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import build_catalog_bundle, canonical_json, hash_file, load_json
from enterprise_dp.contracts import ValidationResult
from enterprise_dp.schema_registry import build_schema_registry_report


REPORT_VERSION = 1
DATA_PRODUCT_PREFIX = "urn:enterprise-dp:data-product:"
TOPIC_PREFIX = "urn:enterprise-dp:topic:"
USE_CASE_PREFIX = "urn:enterprise-dp:use-case:"


@dataclass(frozen=True)
class ContractImpactReportResult:
    output_path: Path
    report: dict[str, Any]


def write_contract_impact_report(
    root: str | Path,
    output_path: str | Path,
    *,
    topic_name: str,
    schema_registry_report_path: str | Path | None = None,
    generated_at: str | None = None,
) -> ContractImpactReportResult:
    report = build_contract_impact_report(
        root,
        topic_name=topic_name,
        schema_registry_report_path=schema_registry_report_path,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return ContractImpactReportResult(output_path=target, report=report)


def build_contract_impact_report(
    root: str | Path,
    *,
    topic_name: str,
    schema_registry_report_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    schema_report, schema_ref = resolve_schema_report(
        platform_root,
        topic_name=topic_name,
        schema_registry_report_path=schema_registry_report_path,
        generated_at=generated,
    )
    subject = subject_for_topic(schema_report, topic_name)
    catalog = build_catalog_bundle(platform_root, generated_at=generated)
    topic = topic_entry(catalog, topic_name)
    downstream_products = downstream_data_products(catalog, topic_name)
    affected_use_cases = use_cases_for_impact(catalog, topic_name, downstream_products)
    access_grants = grants_for_products(catalog, downstream_products)
    breaking_changes = compatibility_violations(subject)
    risk = risk_level(subject, affected_use_cases, downstream_products)
    release_decision = "blocked" if not subject.get("compatibility_passed") else ("review_required" if affected_use_cases else "allowed")
    report = {
        "artifact_type": "contract_impact_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id("contract-impact", topic_name, schema_ref, generated),
        "generated_at": generated,
        "topic": {
            "name": topic_name,
            "urn": f"{TOPIC_PREFIX}{topic_name}",
            "contract_path": topic.get("contract_path") if topic else subject.get("contract_path"),
            "contract_hash": topic.get("contract_hash") if topic else subject.get("contract_hash"),
            "product": topic.get("product") if topic else subject.get("product"),
            "domain": topic.get("domain") if topic else subject.get("domain"),
            "owner_team": topic.get("owner_team") if topic else None,
            "data_steward": topic.get("data_steward") if topic else None,
            "compatibility": subject.get("compatibility"),
        },
        "inputs": {
            "schema_registry_report": schema_ref,
            "catalog_bundle": {
                "source": "generated_from_root",
                "hash": content_hash(catalog),
                "summary": catalog.get("summary", {}),
            },
        },
        "compatibility": {
            "passed": subject.get("compatibility_passed") is True,
            "breaking_change_count": len(breaking_changes),
            "breaking_changes": breaking_changes,
            "prior_versions_checked": subject.get("prior_versions_checked", []),
        },
        "impact": {
            "risk_level": risk,
            "release_decision": release_decision,
            "affected_data_product_count": len(downstream_products),
            "affected_gold_count": sum(1 for product in downstream_products if product.get("layer") == "GOLD"),
            "affected_use_case_count": len(affected_use_cases),
            "affected_p0_use_case_count": sum(1 for use_case in affected_use_cases if use_case.get("priority") == "P0"),
            "active_access_grant_count": len(access_grants),
        },
        "required_approvals": required_approvals(topic, affected_use_cases, downstream_products),
        "affected_data_products": downstream_products,
        "affected_use_cases": affected_use_cases,
        "affected_access_grants": access_grants,
        "lineage": lineage_summary(catalog, topic_name, downstream_products),
        "passed": release_decision != "blocked",
    }
    validation = validate_contract_impact_report(report)
    if not validation.ok:
        raise ValueError("; ".join(validation.errors))
    return report


def validate_contract_impact_report(report: dict[str, Any]) -> ValidationResult:
    result = ValidationResult(checked_count=1)
    if report.get("artifact_type") != "contract_impact_report.v1":
        result.error(Path("contract_impact_report"), "artifact_type must be contract_impact_report.v1")
    if report.get("report_version") != REPORT_VERSION:
        result.error(Path("contract_impact_report"), f"report_version must be {REPORT_VERSION}")
    if not isinstance(report.get("topic"), dict):
        result.error(Path("contract_impact_report"), "topic must be an object")
    if not isinstance(report.get("compatibility"), dict):
        result.error(Path("contract_impact_report"), "compatibility must be an object")
    if not isinstance(report.get("impact"), dict):
        result.error(Path("contract_impact_report"), "impact must be an object")
    if not isinstance(report.get("affected_data_products"), list):
        result.error(Path("contract_impact_report"), "affected_data_products must be a list")
    if not isinstance(report.get("affected_use_cases"), list):
        result.error(Path("contract_impact_report"), "affected_use_cases must be a list")
    if report.get("passed") is True and report.get("compatibility", {}).get("passed") is False:
        result.error(Path("contract_impact_report"), "passed cannot be true when compatibility failed")
    return result


def resolve_schema_report(
    root: Path,
    *,
    topic_name: str,
    schema_registry_report_path: str | Path | None,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if schema_registry_report_path:
        path = Path(schema_registry_report_path)
        report = load_json(path)
        return report, {
            "source": "artifact",
            "uri": path.as_posix(),
            "hash": hash_file(path),
            "compatibility_passed": report.get("compatibility_passed"),
            "subject_count": report.get("subject_count"),
        }
    report = build_schema_registry_report(root, topic_name=topic_name, generated_at=generated_at)
    return report, {
        "source": "generated_from_root",
        "uri": None,
        "hash": content_hash(report),
        "compatibility_passed": report.get("compatibility_passed"),
        "subject_count": report.get("subject_count"),
    }


def subject_for_topic(report: dict[str, Any], topic_name: str) -> dict[str, Any]:
    for subject in report.get("subjects", []):
        if isinstance(subject, dict) and subject.get("topic") == topic_name:
            return subject
    raise ValueError(f"schema registry report does not contain topic {topic_name}")


def topic_entry(catalog: dict[str, Any], topic_name: str) -> dict[str, Any] | None:
    for topic in catalog.get("topics", []):
        if isinstance(topic, dict) and topic.get("name") == topic_name:
            return topic
    return None


def downstream_data_products(catalog: dict[str, Any], topic_name: str) -> list[dict[str, Any]]:
    data_products = {
        item.get("name"): item
        for item in catalog.get("data_products", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    graph: dict[str, set[str]] = {}
    for edge in catalog.get("lineage_edges", []):
        if not isinstance(edge, dict):
            continue
        source = edge.get("source")
        target = edge.get("target")
        if isinstance(source, str) and isinstance(target, str):
            graph.setdefault(source, set()).add(target)

    start = f"{TOPIC_PREFIX}{topic_name}"
    visited: set[str] = set()
    queue = [start]
    affected: set[str] = set()
    while queue:
        current = queue.pop(0)
        for target in sorted(graph.get(current, set())):
            if target in visited:
                continue
            visited.add(target)
            queue.append(target)
            if target.startswith(DATA_PRODUCT_PREFIX):
                affected.add(target.removeprefix(DATA_PRODUCT_PREFIX))
    return [
        data_product_summary(data_products[name])
        for name in sorted(affected)
        if name in data_products
    ]


def use_cases_for_impact(catalog: dict[str, Any], topic_name: str, products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    affected_products = {str(product.get("name")) for product in products}
    affected: list[dict[str, Any]] = []
    for use_case in catalog.get("use_cases", []):
        if not isinstance(use_case, dict):
            continue
        summary = use_case.get("implementation_summary") if isinstance(use_case.get("implementation_summary"), dict) else {}
        declared_products = {
            item.get("name")
            for item in use_case.get("data_products", [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        declared_products.update(summary.get("input_data_products", []) if isinstance(summary.get("input_data_products"), list) else [])
        declared_products.update(summary.get("output_data_products", []) if isinstance(summary.get("output_data_products"), list) else [])
        declared_topics = set(summary.get("input_topics", []) if isinstance(summary.get("input_topics"), list) else [])
        if topic_name in declared_topics or affected_products.intersection(declared_products):
            affected.append(
                {
                    "id": use_case.get("id"),
                    "name": use_case.get("name"),
                    "priority": use_case.get("priority"),
                    "status": use_case.get("status"),
                    "domain": use_case.get("domain"),
                    "owner": use_case.get("owner"),
                    "matched_topic": topic_name in declared_topics,
                    "matched_data_products": sorted(affected_products.intersection(declared_products)),
                }
            )
    return sorted(affected, key=lambda item: (priority_rank(str(item.get("priority"))), str(item.get("id"))))


def grants_for_products(catalog: dict[str, Any], products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    affected_products = {str(product.get("name")) for product in products}
    grants = []
    for grant in catalog.get("access_grants", []):
        if not isinstance(grant, dict) or grant.get("data_product") not in affected_products:
            continue
        grants.append(
            {
                "id": grant.get("id"),
                "status": grant.get("status"),
                "data_product": grant.get("data_product"),
                "consumer": grant.get("consumer"),
                "persona": grant.get("persona"),
                "expires_at": grant.get("expires_at"),
            }
        )
    return sorted(grants, key=lambda item: (str(item.get("data_product")), str(item.get("id"))))


def compatibility_violations(subject: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for check in subject.get("checks", []):
        if not isinstance(check, dict):
            continue
        details = check.get("details")
        if isinstance(details, dict) and isinstance(details.get("violations"), list):
            violations.extend(str(item) for item in details["violations"])
    return sorted(set(violations))


def required_approvals(
    topic: dict[str, Any] | None,
    use_cases: list[dict[str, Any]],
    products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    approvals: dict[tuple[str, str], dict[str, Any]] = {}
    if topic:
        add_approval(approvals, "topic_owner", topic.get("owner_team"), topic.get("name"))
        add_approval(approvals, "data_steward", topic.get("data_steward"), topic.get("name"))
        add_approval(approvals, "domain_owner", topic.get("domain_owner"), topic.get("name"))
    for product in products:
        add_approval(approvals, "data_product_owner", product.get("owner_team"), product.get("name"))
        add_approval(approvals, "data_product_steward", product.get("data_steward"), product.get("name"))
    for use_case in use_cases:
        add_approval(approvals, "use_case_owner", use_case.get("owner"), use_case.get("id"))
    return sorted(approvals.values(), key=lambda item: (item["role"], item["owner"]))


def add_approval(approvals: dict[tuple[str, str], dict[str, Any]], role: str, owner: object, subject: object) -> None:
    if not isinstance(owner, str) or not owner.strip():
        return
    key = (role, owner)
    entry = approvals.setdefault(key, {"role": role, "owner": owner, "subjects": []})
    if isinstance(subject, str) and subject not in entry["subjects"]:
        entry["subjects"].append(subject)
        entry["subjects"].sort()


def lineage_summary(catalog: dict[str, Any], topic_name: str, products: list[dict[str, Any]]) -> dict[str, Any]:
    affected_urns = {f"{DATA_PRODUCT_PREFIX}{product.get('name')}" for product in products}
    topic_urn = f"{TOPIC_PREFIX}{topic_name}"
    edges = [
        edge
        for edge in catalog.get("lineage_edges", [])
        if isinstance(edge, dict) and (edge.get("source") == topic_urn or edge.get("source") in affected_urns or edge.get("target") in affected_urns)
    ]
    return {
        "topic_urn": topic_urn,
        "affected_edge_count": len(edges),
        "edge_types": sorted({str(edge.get("type")) for edge in edges}),
    }


def data_product_summary(data_product: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": data_product.get("name"),
        "layer": data_product.get("layer"),
        "product": data_product.get("product"),
        "domain": data_product.get("domain"),
        "status": data_product.get("status"),
        "owner_team": data_product.get("owner_team"),
        "business_owner": data_product.get("business_owner"),
        "technical_owner": data_product.get("technical_owner"),
        "data_steward": data_product.get("data_steward"),
        "classification": data_product.get("privacy", {}).get("classification") if isinstance(data_product.get("privacy"), dict) else None,
        "contains_pii": data_product.get("privacy", {}).get("contains_pii") if isinstance(data_product.get("privacy"), dict) else None,
    }


def risk_level(subject: dict[str, Any], use_cases: list[dict[str, Any]], products: list[dict[str, Any]]) -> str:
    if subject.get("compatibility_passed") is True:
        return "P1" if any(use_case.get("priority") == "P0" for use_case in use_cases) else "P2"
    if any(use_case.get("priority") == "P0" for use_case in use_cases):
        return "P0"
    if any(product.get("layer") == "GOLD" for product in products):
        return "P1"
    return "P2"


def priority_rank(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(priority, 9)


def content_hash(value: dict[str, Any]) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()}"


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

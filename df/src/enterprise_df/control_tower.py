from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_df.access_grants import evaluate_access_grants
from enterprise_df.access_governance import evaluate_consumer_contract_reference
from enterprise_df.access_policies import evaluate_access_policy_contract
from enterprise_df.capabilities import build_capability_maturity_report
from enterprise_df.catalog import build_catalog_bundle, canonical_json, hash_file, load_json
from enterprise_df.contracts import ValidationResult, load_yaml, validate_data_product_contract
from enterprise_df.quality_profiles import list_quality_profiles


REPORT_VERSION = 1
P0 = "P0"
P1 = "P1"


@dataclass(frozen=True)
class ControlTowerReportResult:
    output_path: Path
    report: dict[str, Any]


def write_data_product_control_tower_report(
    root: str | Path,
    output_path: str | Path,
    *,
    catalog_bundle_path: str | Path | None = None,
    release_evidence_paths: list[str | Path] | None = None,
    capability_maturity_report_path: str | Path | None = None,
    environment: str = "local",
    generated_at: str | None = None,
) -> ControlTowerReportResult:
    report = build_data_product_control_tower_report(
        root,
        catalog_bundle_path=catalog_bundle_path,
        release_evidence_paths=release_evidence_paths,
        capability_maturity_report_path=capability_maturity_report_path,
        environment=environment,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return ControlTowerReportResult(output_path=target, report=report)


def build_data_product_control_tower_report(
    root: str | Path,
    *,
    catalog_bundle_path: str | Path | None = None,
    release_evidence_paths: list[str | Path] | None = None,
    capability_maturity_report_path: str | Path | None = None,
    environment: str = "local",
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    catalog_bundle, catalog_ref = resolve_catalog_bundle(
        platform_root,
        catalog_bundle_path=catalog_bundle_path,
        generated_at=generated,
    )
    release_evidences = [load_json(Path(path)) for path in release_evidence_paths or []]
    capability_report, capability_ref = resolve_capability_report(
        platform_root,
        capability_maturity_report_path=capability_maturity_report_path,
        generated_at=generated,
    )
    quality_profiles = list_quality_profiles(platform_root)
    lineage_index = build_lineage_index(catalog_bundle)
    release_index = build_release_index(release_evidences, release_evidence_paths or [])
    products = [
        data_product_control_entry(
            platform_root,
            data_product,
            quality_profiles=quality_profiles,
            lineage_index=lineage_index,
            release_index=release_index,
            generated_at=generated,
        )
        for data_product in sorted(catalog_bundle.get("data_products", []), key=lambda item: str(item.get("name")))
        if isinstance(data_product, dict)
    ]
    capability_blockers = capability_blocker_entries(capability_report)
    product_blockers = [
        blocker
        for product in products
        for blocker in product["blockers"]
    ]
    p0_ready = not product_blockers and not capability_blockers
    report = {
        "artifact_type": "data_product_control_tower_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id("data-product-control-tower", catalog_ref, capability_ref, release_index, generated),
        "generated_at": generated,
        "environment": environment,
        "scope": control_tower_scope(catalog_bundle),
        "readiness_state": "production_ready" if p0_ready else "not_ready",
        "p0_ready": p0_ready,
        "passed": p0_ready,
        "inputs": {
            "catalog_bundle": catalog_ref,
            "capability_maturity_report": capability_ref,
            "release_evidence": release_evidence_summary(release_index),
        },
        "catalog": catalog_ref,
        "capability_maturity": capability_ref,
        "release_evidence": release_evidence_summary(release_index),
        "summary": control_tower_summary(products, capability_blockers),
        "escalations": escalation_summary(product_blockers, capability_blockers),
        "gate_matrix": gate_matrix(products),
        "blockers": product_blockers + capability_blockers,
        "data_products": products,
    }
    validation = validate_data_product_control_tower_report(report)
    if not validation.ok:
        raise ValueError("; ".join(validation.errors))
    return report


def data_product_control_entry(
    root: Path,
    data_product: dict[str, Any],
    *,
    quality_profiles: list[dict[str, Any]],
    lineage_index: dict[str, dict[str, Any]],
    release_index: dict[str, list[dict[str, Any]]],
    generated_at: str,
) -> dict[str, Any]:
    name = str(data_product.get("name"))
    contract_path = root / str(data_product.get("contract_path"))
    contract = load_yaml(contract_path)
    contract_result = ValidationResult(checked_count=1)
    validate_data_product_contract(contract_path, contract, contract_result, root=root)
    contract_meta = contract.get("dataProduct", {}) if isinstance(contract.get("dataProduct"), dict) else {}
    quality = data_product.get("quality") if isinstance(data_product.get("quality"), dict) else {}
    serving = data_product.get("serving") if isinstance(data_product.get("serving"), dict) else {}
    privacy = data_product.get("privacy") if isinstance(data_product.get("privacy"), dict) else {}
    schema = contract.get("schema", {}) if isinstance(contract.get("schema"), dict) else {}
    columns = [column for column in schema.get("columns", []) if isinstance(column, dict)]
    access_policy = evaluate_safely(
        lambda: evaluate_access_policy_contract(
            root,
            data_product_name=name,
            layer=str(data_product.get("layer")),
            privacy=contract.get("privacy", {}) if isinstance(contract.get("privacy"), dict) else {},
            serving=contract.get("serving", {}) if isinstance(contract.get("serving"), dict) else {},
            columns=columns,
        ),
        fallback={"passed": False, "checks": [], "error": "access_policy_evaluation_failed"},
    )
    consumer_contract = evaluate_safely(
        lambda: evaluate_consumer_contract_reference(
            root,
            data_product_name=name,
            layer=str(data_product.get("layer")),
            privacy=contract.get("privacy", {}) if isinstance(contract.get("privacy"), dict) else {},
            serving=contract.get("serving", {}) if isinstance(contract.get("serving"), dict) else {},
        ),
        fallback={"passed": False, "checks": [], "error": "consumer_contract_evaluation_failed"},
    )
    access_grants = evaluate_safely(
        lambda: evaluate_access_grants(
            root,
            data_product_name=name,
            serving=contract.get("serving", {}) if isinstance(contract.get("serving"), dict) else {},
            evaluation_time=generated_at,
        ),
        fallback={"passed": False, "checks": [], "active_grant_count": 0, "error": "access_grant_evaluation_failed"},
    )
    profiles = quality_profiles_for_data_product(name, quality_profiles)
    lineage = lineage_index.get(name, empty_lineage_coverage(name))
    releases = release_index.get(name, [])
    release_passed = any(release.get("release_passed") is True for release in releases)
    layer = str(data_product.get("layer") or "")
    checks = product_checks(
        data_product=data_product,
        contract_result=contract_result,
        quality=quality,
        serving=serving,
        privacy=privacy,
        profiles=profiles,
        lineage=lineage,
        access_policy=access_policy,
        consumer_contract=consumer_contract,
        access_grants=access_grants,
        release_count=len(releases),
        release_passed=release_passed,
    )
    blockers = [
        blocker_entry(name, data_product, check)
        for check in checks
        if check["severity"] == P0 and check["passed"] is not True
    ]
    return {
        "name": name,
        "urn": data_product.get("urn"),
        "contract_urn": data_product.get("contract_urn"),
        "contract_path": data_product.get("contract_path"),
        "contract_hash": data_product.get("contract_hash"),
        "contract": {
            "contract_version": contract.get("contractVersion"),
            "valid": not contract_result.errors,
            "validation_errors": contract_result.errors,
            "schema_column_count": len(columns),
        },
        "layer": layer,
        "product": data_product.get("product"),
        "domain": data_product.get("domain"),
        "status": data_product.get("status"),
        "owners": {
            "domain_owner": data_product.get("domain_owner"),
            "owner_team": data_product.get("owner_team"),
            "business_owner": data_product.get("business_owner"),
            "technical_owner": data_product.get("technical_owner"),
            "data_steward": data_product.get("data_steward"),
        },
        "privacy": {
            "classification": privacy.get("classification"),
            "contains_pii": privacy.get("contains_pii"),
            "tenant_isolation": privacy.get("tenant_isolation"),
            "retention_days": privacy.get("retention_days"),
        },
        "quality": {
            "freshness_slo_minutes": quality.get("freshness_slo_minutes"),
            "check_count": len(quality.get("checks", [])) if isinstance(quality.get("checks"), list) else 0,
            "quality_profiles": [profile_summary(profile) for profile in profiles],
        },
        "access": {
            "access_policy": serving.get("access_policy"),
            "access_policy_passed": access_policy.get("passed") is True,
            "consumer_contract": serving.get("consumer_contract"),
            "consumer_contract_passed": consumer_contract.get("passed") is True,
            "access_personas": serving.get("access_personas", []),
            "active_grant_count": access_grants.get("active_grant_count", 0),
            "active_personas": access_grants.get("active_personas", []),
        },
        "lineage": lineage,
        "release_evidence": {
            "covered": bool(releases),
            "passed": release_passed,
            "release_count": len(releases),
            "releases": [
                {
                    "release_id": release.get("release_id"),
                    "use_case_id": release.get("use_case_id"),
                    "release_passed": release.get("release_passed"),
                    "evidence_uri": release.get("evidence_uri"),
                    "evidence_hash": release.get("evidence_hash"),
                }
                for release in releases
            ],
        },
        "checks": checks,
        "blockers": blockers,
        "readiness_state": "ready_for_production_signoff" if not blockers else "blocked",
    }


def product_checks(
    *,
    data_product: dict[str, Any],
    contract_result: ValidationResult,
    quality: dict[str, Any],
    serving: dict[str, Any],
    privacy: dict[str, Any],
    profiles: list[dict[str, Any]],
    lineage: dict[str, Any],
    access_policy: dict[str, Any],
    consumer_contract: dict[str, Any],
    access_grants: dict[str, Any],
    release_count: int,
    release_passed: bool,
) -> list[dict[str, Any]]:
    layer = str(data_product.get("layer") or "")
    lineage_required = bool(lineage.get("lineage_required"))
    is_gold = layer == "GOLD"
    is_serving_layer = layer in {"SILVER", "GOLD"}
    return [
        check("contract_valid", not contract_result.errors, P0, {"errors": contract_result.errors}),
        check("contract_active", data_product.get("status") == "ACTIVE", P0, {"status": data_product.get("status")}),
        check("owner_team_declared", non_empty(data_product.get("owner_team")), P0, {"owner_team": data_product.get("owner_team")}),
        check("data_steward_declared", non_empty(data_product.get("data_steward")), P0, {"data_steward": data_product.get("data_steward")}),
        check(
            "freshness_slo_declared",
            isinstance(quality.get("freshness_slo_minutes"), int) and quality.get("freshness_slo_minutes") > 0,
            P0,
            {"freshness_slo_minutes": quality.get("freshness_slo_minutes")},
        ),
        check(
            "quality_checks_declared",
            isinstance(quality.get("checks"), list) and bool(quality.get("checks")),
            P0,
            {"check_count": len(quality.get("checks", [])) if isinstance(quality.get("checks"), list) else 0},
        ),
        check(
            "gold_quality_profile_attached",
            not is_gold or bool(profiles),
            P0,
            {"profile_ids": [profile.get("id") for profile in profiles]},
        ),
        check(
            "catalog_lineage_declared",
            not lineage_required or lineage.get("static_lineage_present") is True,
            P0,
            lineage,
        ),
        check(
            "runtime_lineage_evidence_present",
            not lineage_required or lineage.get("runtime_lineage_present") is True,
            P0,
            lineage,
        ),
        check(
            "access_policy_passed",
            not is_serving_layer or access_policy.get("passed") is True,
            P0,
            {"access_policy": serving.get("access_policy"), "evaluation": compact_evaluation(access_policy)},
        ),
        check(
            "consumer_contract_passed",
            not is_serving_layer or consumer_contract.get("passed") is True,
            P0,
            {"consumer_contract": serving.get("consumer_contract"), "evaluation": compact_evaluation(consumer_contract)},
        ),
        check(
            "gold_access_grants_active",
            not is_gold or int_value(access_grants.get("active_grant_count")) > 0,
            P0,
            {
                "active_grant_count": access_grants.get("active_grant_count", 0),
                "active_personas": access_grants.get("active_personas", []),
            },
        ),
        check(
            "gold_release_evidence_passed",
            not is_gold or release_passed,
            P0,
            {"release_count": release_count, "release_passed": release_passed},
        ),
        check(
            "tenant_isolation_declared",
            privacy.get("tenant_isolation") == "REQUIRED",
            P1,
            {"tenant_isolation": privacy.get("tenant_isolation")},
        ),
    ]


def resolve_catalog_bundle(
    root: Path,
    *,
    catalog_bundle_path: str | Path | None,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if catalog_bundle_path:
        path = Path(catalog_bundle_path)
        bundle = load_json(path)
        return bundle, {
            "source": "artifact",
            "uri": path.as_posix(),
            "hash": hash_file(path),
            "generated_at": bundle.get("generated_at"),
            "summary": bundle.get("summary", {}),
        }
    bundle = build_catalog_bundle(root, generated_at=generated_at)
    return bundle, {
        "source": "generated_from_root",
        "uri": None,
        "hash": content_hash(bundle),
        "generated_at": bundle.get("generated_at"),
        "summary": bundle.get("summary", {}),
    }


def resolve_capability_report(
    root: Path,
    *,
    capability_maturity_report_path: str | Path | None,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if capability_maturity_report_path:
        path = Path(capability_maturity_report_path)
        report = load_json(path)
        return report, {
            "source": "artifact",
            "uri": path.as_posix(),
            "hash": hash_file(path),
            "readiness_state": report.get("readiness_state"),
            "p0_ready": report.get("p0_ready"),
            "blocker_count": len(report.get("blockers", [])) if isinstance(report.get("blockers"), list) else 0,
            "summary": report.get("summary", {}),
        }
    report = build_capability_maturity_report(root, phase="P0", generated_at=generated_at)
    return report, {
        "source": "generated_from_root",
        "uri": None,
        "hash": content_hash(report),
        "readiness_state": report.get("readiness_state"),
        "p0_ready": report.get("p0_ready"),
        "blocker_count": len(report.get("blockers", [])) if isinstance(report.get("blockers"), list) else 0,
        "summary": report.get("summary", {}),
    }


def build_lineage_index(catalog_bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    data_products = {
        item.get("name"): item
        for item in catalog_bundle.get("data_products", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    edges = [edge for edge in catalog_bundle.get("lineage_edges", []) if isinstance(edge, dict)]
    runs = [run for run in catalog_bundle.get("run_evidence", []) if isinstance(run, dict)]
    index: dict[str, dict[str, Any]] = {}
    for name, data_product in data_products.items():
        urn = f"urn:enterprise-df:data-product:{name}"
        static_edges = [
            edge
            for edge in edges
            if edge.get("type") != "RUN_LAYER_TRANSFORM"
            and (edge.get("source") == urn or edge.get("target") == urn)
        ]
        runtime_edges = [
            edge
            for edge in edges
            if edge.get("type", "").startswith("RUN_")
            and (edge.get("source") == urn or edge.get("target") == urn)
        ]
        runtime_runs = [
            run
            for run in runs
            if run.get("bronze_target") == name
            or name in (run.get("layers", {}) if isinstance(run.get("layers"), dict) else {})
        ]
        lineage = data_product.get("lineage") if isinstance(data_product.get("lineage"), dict) else {}
        index[name] = {
            "lineage_required": lineage.get("lineage_required") is True,
            "catalog": lineage.get("catalog"),
            "static_lineage_present": bool(static_edges),
            "runtime_lineage_present": bool(runtime_edges or runtime_runs),
            "static_edge_count": len(static_edges),
            "runtime_edge_count": len(runtime_edges),
            "runtime_run_count": len(runtime_runs),
            "upstream": lineage.get("upstream", []),
        }
    return index


def build_release_index(releases: list[dict[str, Any]], paths: list[str | Path]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for release, path_value in zip(releases, paths):
        path = Path(path_value)
        covered = set()
        primary_output = release.get("primary_output")
        if isinstance(primary_output, str):
            covered.add(primary_output)
        outputs = release.get("output_data_products")
        if isinstance(outputs, list):
            covered.update(item for item in outputs if isinstance(item, str))
        entry = {
            "release_id": release.get("release_id"),
            "use_case_id": release.get("use_case_id"),
            "release_passed": release.get("release_passed"),
            "primary_output": primary_output,
            "output_data_products": sorted(covered),
            "evidence_uri": path.as_posix(),
            "evidence_hash": hash_file(path) if path.is_file() else None,
        }
        for data_product_name in covered:
            index.setdefault(data_product_name, []).append(entry)
    return index


def release_evidence_summary(release_index: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    releases = {
        str(release.get("release_id"))
        for entries in release_index.values()
        for release in entries
        if release.get("release_id")
    }
    return {
        "release_count": len(releases),
        "covered_data_product_count": len(release_index),
        "covered_data_products": sorted(release_index),
    }


def quality_profiles_for_data_product(name: str, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matched = []
    for profile in profiles:
        applies_to = profile.get("appliesTo") if isinstance(profile.get("appliesTo"), dict) else {}
        required_columns = profile.get("requiredColumns") if isinstance(profile.get("requiredColumns"), dict) else {}
        covered = set(profile.get("requiredOutputDataProducts", []) if isinstance(profile.get("requiredOutputDataProducts"), list) else [])
        covered.update(applies_to.get("primaryOutputs", []) if isinstance(applies_to.get("primaryOutputs"), list) else [])
        covered.update(key for key in required_columns if isinstance(key, str))
        if name in covered:
            matched.append(profile)
    return matched


def capability_blocker_entries(capability_report: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = []
    for blocker in capability_report.get("blockers", []):
        if not isinstance(blocker, dict):
            continue
        blockers.append(
            {
                "scope": "platform_capability",
                "data_product": None,
                "capability_id": blocker.get("capability_id"),
                "gate": "p0_capability_target_met",
                "severity": P0 if blocker.get("phase") == P0 else str(blocker.get("phase") or "P1"),
                "owner_team": "data-platform-team",
                "domain": "platform",
                "message": f"{blocker.get('capability_id')} is {blocker.get('current_level')} below target {blocker.get('target_level')}",
                "details": {
                    "missing_level_count": blocker.get("missing_level_count"),
                    "gaps": blocker.get("gaps", []),
                    "next_milestones": blocker.get("next_milestones", []),
                },
            }
        )
    return blockers


def control_tower_summary(products: list[dict[str, Any]], capability_blockers: list[dict[str, Any]]) -> dict[str, Any]:
    data_product_blocker_count = sum(len(product.get("blockers", [])) for product in products)
    return {
        "overall_state": "ready" if data_product_blocker_count == 0 and not capability_blockers else "blocked",
        "data_product_count": len(products),
        "by_layer": count_by(products, "layer"),
        "by_status": count_by(products, "status"),
        "by_domain": count_by(products, "domain"),
        "by_product": count_by(products, "product"),
        "by_readiness_state": count_by(products, "readiness_state"),
        "blocker_count": data_product_blocker_count + len(capability_blockers),
        "data_product_blocker_count": data_product_blocker_count,
        "capability_blocker_count": len(capability_blockers),
        "gold_release_coverage": gold_release_coverage(products),
    }


def gold_release_coverage(products: list[dict[str, Any]]) -> dict[str, Any]:
    gold = [product for product in products if product.get("layer") == "GOLD"]
    covered = [product for product in gold if product.get("release_evidence", {}).get("covered") is True]
    passed = [product for product in gold if product.get("release_evidence", {}).get("passed") is True]
    return {
        "gold_count": len(gold),
        "covered_count": len(covered),
        "passed_count": len(passed),
        "missing": sorted(str(product.get("name")) for product in gold if product not in covered),
    }


def escalation_summary(product_blockers: list[dict[str, Any]], capability_blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for blocker in product_blockers + capability_blockers:
        key = (str(blocker.get("owner_team") or "unknown"), str(blocker.get("domain") or "unknown"))
        item = grouped.setdefault(
            key,
            {
                "owner_team": key[0],
                "domain": key[1],
                "p0_blocker_count": 0,
                "gates": {},
                "data_products": set(),
            },
        )
        if blocker.get("severity") == P0:
            item["p0_blocker_count"] += 1
        gate = str(blocker.get("gate") or "unknown")
        item["gates"][gate] = item["gates"].get(gate, 0) + 1
        data_product = blocker.get("data_product")
        if data_product:
            item["data_products"].add(data_product)
    return [
        {
            **item,
            "gates": dict(sorted(item["gates"].items())),
            "data_products": sorted(item["data_products"]),
        }
        for item in sorted(grouped.values(), key=lambda value: (-value["p0_blocker_count"], value["owner_team"], value["domain"]))
    ]


def validate_data_product_control_tower_report(report: dict[str, Any]) -> ValidationResult:
    result = ValidationResult(checked_count=1)
    if report.get("artifact_type") != "data_product_control_tower_report.v1":
        result.error(Path("control_tower_report"), "artifact_type must be data_product_control_tower_report.v1")
    if report.get("report_version") != REPORT_VERSION:
        result.error(Path("control_tower_report"), f"report_version must be {REPORT_VERSION}")
    if not isinstance(report.get("summary"), dict):
        result.error(Path("control_tower_report"), "summary must be an object")
    if not isinstance(report.get("scope"), dict):
        result.error(Path("control_tower_report"), "scope must be an object")
    if not isinstance(report.get("inputs"), dict):
        result.error(Path("control_tower_report"), "inputs must be an object")
    if not isinstance(report.get("gate_matrix"), list):
        result.error(Path("control_tower_report"), "gate_matrix must be a list")
    if not isinstance(report.get("data_products"), list):
        result.error(Path("control_tower_report"), "data_products must be a list")
    if not isinstance(report.get("blockers"), list):
        result.error(Path("control_tower_report"), "blockers must be a list")
    if report.get("p0_ready") is True and report.get("blockers"):
        result.error(Path("control_tower_report"), "p0_ready cannot be true while blockers are present")
    return result


def blocker_entry(data_product_name: str, data_product: dict[str, Any], check_item: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope": "data_product",
        "data_product": data_product_name,
        "capability_id": None,
        "gate": check_item["name"],
        "severity": check_item["severity"],
        "owner_team": data_product.get("owner_team"),
        "domain": data_product.get("domain"),
        "message": f"{data_product_name} failed {check_item['name']}",
        "details": check_item.get("details", {}),
    }


def check(name: str, passed: bool, severity: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "severity": severity,
        "details": details,
    }


def compact_evaluation(evaluation: dict[str, Any]) -> dict[str, Any]:
    checks = evaluation.get("checks")
    return {
        "passed": evaluation.get("passed"),
        "failed_checks": [
            item.get("name")
            for item in checks
            if isinstance(item, dict) and item.get("passed") is not True
        ] if isinstance(checks, list) else [],
        "error": evaluation.get("error"),
    }


def control_tower_scope(catalog_bundle: dict[str, Any]) -> dict[str, Any]:
    products = sorted(
        str(product.get("code"))
        for product in catalog_bundle.get("products", [])
        if isinstance(product, dict) and product.get("code")
    )
    domains = sorted(
        str(domain.get("code"))
        for domain in catalog_bundle.get("domains", [])
        if isinstance(domain, dict) and domain.get("code")
    )
    use_cases = sorted(
        str(use_case.get("id"))
        for use_case in catalog_bundle.get("use_cases", [])
        if isinstance(use_case, dict) and use_case.get("id")
    )
    return {
        "products": products,
        "domains": domains,
        "use_cases": use_cases,
    }


def gate_matrix(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for product in products:
        for check_item in product.get("checks", []):
            if not isinstance(check_item, dict):
                continue
            rows.append(
                {
                    "data_product": product.get("name"),
                    "product": product.get("product"),
                    "domain": product.get("domain"),
                    "layer": product.get("layer"),
                    "gate": check_item.get("name"),
                    "severity": check_item.get("severity"),
                    "passed": check_item.get("passed"),
                }
            )
    return rows


def evaluate_safely(callback, *, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        value = callback()
    except (KeyError, ValueError):
        return fallback
    return value if isinstance(value, dict) else fallback


def empty_lineage_coverage(name: str) -> dict[str, Any]:
    return {
        "lineage_required": True,
        "catalog": None,
        "static_lineage_present": False,
        "runtime_lineage_present": False,
        "static_edge_count": 0,
        "runtime_edge_count": 0,
        "runtime_run_count": 0,
        "upstream": [],
        "name": name,
    }


def profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": profile.get("id"),
        "owner": profile.get("owner"),
        "severity": profile.get("severity"),
    }


def count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def content_hash(value: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()}"


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

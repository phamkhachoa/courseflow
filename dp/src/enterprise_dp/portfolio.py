from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json
from enterprise_dp.contracts import DATA_PRODUCT_NAME, TOPIC_NAME, ValidationResult, load_yaml
from enterprise_dp.source_activation_ledger import (
    activation_state_counts,
    build_source_activation_index,
    source_activation_summary,
    source_effective_status,
)
from enterprise_dp.usecases import list_use_cases


REPORT_VERSION = 1
P0 = "P0"


@dataclass(frozen=True)
class PortfolioReadinessReportResult:
    output_path: Path
    report: dict[str, Any]


def write_enterprise_portfolio_readiness_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str = "local",
    generated_at: str | None = None,
    source_activation_ledger_path: str | Path | None = None,
) -> PortfolioReadinessReportResult:
    report = build_enterprise_portfolio_readiness_report(
        root,
        environment=environment,
        generated_at=generated_at,
        source_activation_ledger_path=source_activation_ledger_path,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return PortfolioReadinessReportResult(output_path=target, report=report)


def build_enterprise_portfolio_readiness_report(
    root: str | Path,
    *,
    environment: str = "local",
    generated_at: str | None = None,
    source_activation_ledger_path: str | Path | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    products = load_product_onboardings(platform_root)
    use_cases = list_use_cases(platform_root)
    sources = load_source_registry(platform_root)
    activation_index = (
        build_source_activation_index(
            platform_root,
            environment=environment,
            as_of=generated,
            ledger_path=source_activation_ledger_path,
        )
        if source_activation_ledger_path is not None
        else {}
    )
    source_index = index_sources_by_product(sources)
    topic_names = load_topic_names(platform_root)
    data_product_names = load_data_product_names(platform_root)
    p0_use_case_ids_by_product = p0_use_case_requirements_by_product(use_cases)

    product_matrix = [
        product_portfolio_entry(
            platform_root,
            code,
            onboarding,
            source_index=source_index,
            topic_names=topic_names,
            data_product_names=data_product_names,
            p0_use_case_ids=p0_use_case_ids_by_product.get(code, []),
            activation_index=activation_index,
        )
        for code, onboarding in sorted(products.items())
    ]
    use_case_matrix = [
        use_case_portfolio_entry(
            use_case,
            products=products,
            source_index=source_index,
            data_product_names=data_product_names,
            activation_index=activation_index,
        )
        for use_case in sorted(use_cases, key=lambda item: (str(item.get("priority")), str(item.get("id"))))
    ]
    domain_matrix = build_domain_matrix(platform_root, product_matrix, use_case_matrix)
    blockers = sorted(
        [
            blocker
            for item in product_matrix + use_case_matrix
            for blocker in item.get("blockers", [])
            if isinstance(blocker, dict)
        ],
        key=lambda item: (item.get("severity") != P0, str(item.get("scope")), str(item.get("id")), str(item.get("gate"))),
    )
    p0_ready = not any(blocker.get("severity") == P0 for blocker in blockers)
    report = {
        "artifact_type": "enterprise_portfolio_readiness_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id(
            "enterprise-portfolio",
            environment,
            generated,
            products_fingerprint(products),
            sources_fingerprint(sources, activation_index),
            use_cases,
        ),
        "generated_at": generated,
        "environment": environment,
        "source_activation_ledger": {
            "enabled": source_activation_ledger_path is not None,
            "path": str(source_activation_ledger_path) if source_activation_ledger_path is not None else None,
            "covered_source_count": len(activation_index),
            "by_state": activation_state_counts(activation_index),
        },
        "portfolio_scope": load_portfolio_scope(platform_root),
        "readiness_state": "production_ready" if p0_ready else "not_ready",
        "p0_ready": p0_ready,
        "passed": p0_ready,
        "summary": portfolio_summary(product_matrix, use_case_matrix, blockers, sources, activation_index),
        "decision_board": decision_board(product_matrix, use_case_matrix, blockers),
        "domain_matrix": domain_matrix,
        "product_matrix": product_matrix,
        "use_case_matrix": use_case_matrix,
        "source_summary": source_summary(sources, activation_index),
        "blockers": blockers,
    }
    validation = validate_enterprise_portfolio_readiness_report(report)
    if not validation.ok:
        raise ValueError("; ".join(validation.errors))
    return report


def product_portfolio_entry(
    root: Path,
    code: str,
    onboarding: dict[str, Any],
    *,
    source_index: dict[str, list[dict[str, Any]]],
    topic_names: set[str],
    data_product_names: set[str],
    p0_use_case_ids: list[str],
    activation_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    product = as_mapping(onboarding.get("product"))
    governance = as_mapping(onboarding.get("governance"))
    first_slice = as_mapping(onboarding.get("firstSlice"))
    domains = string_list(onboarding.get("domains"))
    first_topics = string_list(first_slice.get("topics"))
    first_data_products = string_list(first_slice.get("dataProducts"))
    contract_status = str(first_slice.get("contractStatus") or "existing")
    existing_topics = [topic for topic in first_topics if topic in topic_names]
    missing_topics = [topic for topic in first_topics if topic not in topic_names and TOPIC_NAME.fullmatch(topic)]
    existing_data_products = [name for name in first_data_products if name in data_product_names]
    missing_data_products = [
        name for name in first_data_products if name not in data_product_names and DATA_PRODUCT_NAME.fullmatch(name)
    ]
    product_sources = source_index.get(code, [])
    static_source_gaps = [
        source_gap_summary(source, activation_index)
        for source in product_sources
        if source.get("priority") == P0 and source.get("status") != "production_ready"
    ]
    source_gaps = [
        source_gap_summary(source, activation_index)
        for source in product_sources
        if source.get("priority") == P0 and source_effective_status(source, activation_index) != "production_ready"
    ]
    source_activations = [
        activation
        for activation in (source_activation_summary(source.get("sourceId"), activation_index) for source in product_sources)
        if activation is not None
    ]
    required_by_p0 = bool(p0_use_case_ids)
    blockers = []
    if required_by_p0 and product.get("status") == "draft":
        blockers.append(
            blocker(
                scope="product",
                item_id=code,
                gate="product_onboarding_promoted",
                severity=P0,
                owner=product.get("productOwner"),
                message=f"{code} is required by P0 use cases but remains draft.",
                details={"required_by_p0_use_cases": p0_use_case_ids, "status": product.get("status")},
            )
        )
    if required_by_p0 and contract_status == "planned":
        blockers.append(
            blocker(
                scope="product",
                item_id=code,
                gate="first_slice_contracts_existing",
                severity=P0,
                owner=product.get("technicalOwner"),
                message=f"{code} first slice contracts are still planned.",
                details={
                    "topics": first_topics,
                    "data_products": first_data_products,
                    "required_by_p0_use_cases": p0_use_case_ids,
                },
            )
        )
    if contract_status == "existing" and (missing_topics or missing_data_products):
        blockers.append(
            blocker(
                scope="product",
                item_id=code,
                gate="declared_contracts_present",
                severity=P0,
                owner=product.get("technicalOwner"),
                message=f"{code} declares existing first-slice contracts that are missing.",
                details={"missing_topics": missing_topics, "missing_data_products": missing_data_products},
            )
        )
    if required_by_p0 and source_gaps:
        blockers.append(
            blocker(
                scope="product",
                item_id=code,
                gate="p0_sources_production_ready",
                severity=P0,
                owner=product.get("technicalOwner"),
                message=f"{code} has P0 source onboarding gaps.",
                details={"source_gaps": source_gaps},
            )
        )

    return {
        "product_code": code,
        "name": product.get("name"),
        "status": product.get("status"),
        "domains": domains,
        "owners": {
            "business_sponsor": product.get("businessSponsor"),
            "product_owner": product.get("productOwner"),
            "technical_owner": product.get("technicalOwner"),
            "data_steward": product.get("dataSteward"),
        },
        "governance": {
            "classification": governance.get("classification"),
            "contains_pii": governance.get("containsPii"),
            "tenant_isolation": governance.get("tenantIsolation"),
            "retention_policy": governance.get("defaultRetentionPolicy"),
            "consumer_contract": governance.get("consumerContract"),
            "release_evidence_profile": governance.get("releaseEvidenceProfile"),
            "lineage_required": governance.get("lineageRequired"),
            "catalog_registration_required": governance.get("catalogRegistrationRequired"),
        },
        "first_slice": {
            "contract_status": contract_status,
            "topic_count": len(first_topics),
            "existing_topic_count": len(existing_topics),
            "missing_topics": missing_topics,
            "data_product_count": len(first_data_products),
            "existing_data_product_count": len(existing_data_products),
            "missing_data_products": missing_data_products,
        },
        "source_readiness": {
            "registered_source_count": len(product_sources),
            "p0_static_source_gap_count": len(static_source_gaps),
            "p0_source_gap_count": len(source_gaps),
            "p0_effective_source_gap_count": len(source_gaps),
            "p0_source_gaps": source_gaps,
            "activation_covered_count": len(source_activations),
            "activations": source_activations,
        },
        "required_by_p0_use_cases": p0_use_case_ids,
        "next_actions": product_next_actions(
            contract_status,
            required_by_p0,
            missing_topics,
            missing_data_products,
            source_gaps,
            product,
        ),
        "blockers": blockers,
        "readiness_state": "ready_for_p0_use_case" if not blockers else "blocked",
        "contract_path": relative_path(root, root / "products" / code / "onboarding.yaml"),
    }


def use_case_portfolio_entry(
    use_case: dict[str, Any],
    *,
    products: dict[str, dict[str, Any]],
    source_index: dict[str, list[dict[str, Any]]],
    data_product_names: set[str],
    activation_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    use_case_id = str(use_case.get("id"))
    priority = str(use_case.get("priority") or "")
    source_products = string_list(use_case.get("sourceProducts"))
    data_products = [
        item for item in use_case.get("dataProducts", []) if isinstance(item, dict)
    ] if isinstance(use_case.get("dataProducts"), list) else []
    planned_contracts = [
        str(item.get("name"))
        for item in data_products
        if item.get("contractStatus") == "planned" and isinstance(item.get("name"), str)
    ]
    missing_existing_contracts = [
        str(item.get("name"))
        for item in data_products
        if item.get("contractStatus") == "existing"
        and isinstance(item.get("name"), str)
        and item.get("name") not in data_product_names
    ]
    onboarded_source_products = [code for code in source_products if code in products]
    missing_source_products = [code for code in source_products if code not in products]
    draft_source_products = [
        code
        for code in onboarded_source_products
        if as_mapping(products[code].get("product")).get("status") == "draft"
    ]
    source_gaps = [
        {"product": code, **gap}
        for code in onboarded_source_products
        for gap in [
            source_gap_summary(source, activation_index)
            for source in source_index.get(code, [])
            if source.get("priority") == P0 and source_effective_status(source, activation_index) != "production_ready"
        ]
    ]
    implementation = as_mapping(use_case.get("implementation"))
    pipelines = [pipeline for pipeline in implementation.get("pipelines", []) if isinstance(pipeline, dict)] if implementation else []
    pipeline_runners = string_list(use_case.get("pipelineRunners"))
    blockers = []
    severity = P0 if priority == P0 else "P1"
    if priority == P0 and missing_source_products:
        blockers.append(
            blocker(
                scope="use_case",
                item_id=use_case_id,
                gate="source_products_onboarded",
                severity=P0,
                owner=use_case.get("owner"),
                message=f"{use_case_id} references source products that are not onboarded.",
                details={"missing_source_products": missing_source_products},
            )
        )
    if priority == P0 and draft_source_products:
        blockers.append(
            blocker(
                scope="use_case",
                item_id=use_case_id,
                gate="source_products_promoted",
                severity=P0,
                owner=use_case.get("owner"),
                message=f"{use_case_id} depends on draft source products.",
                details={"draft_source_products": draft_source_products},
            )
        )
    if planned_contracts:
        blockers.append(
            blocker(
                scope="use_case",
                item_id=use_case_id,
                gate="data_product_contracts_existing",
                severity=severity,
                owner=use_case.get("owner"),
                message=f"{use_case_id} still has planned data product contracts.",
                details={"planned_contracts": planned_contracts},
            )
        )
    if missing_existing_contracts:
        blockers.append(
            blocker(
                scope="use_case",
                item_id=use_case_id,
                gate="existing_contracts_present",
                severity=P0,
                owner=use_case.get("owner"),
                message=f"{use_case_id} declares existing contracts that are missing.",
                details={"missing_existing_contracts": missing_existing_contracts},
            )
        )
    if priority == P0 and not pipelines:
        blockers.append(
            blocker(
                scope="use_case",
                item_id=use_case_id,
                gate="implementation_pipeline_declared",
                severity=P0,
                owner=use_case.get("owner"),
                message=f"{use_case_id} has no implementation pipeline metadata.",
                details={"pipeline_runners": pipeline_runners},
            )
        )
    if priority == P0 and source_gaps:
        blockers.append(
            blocker(
                scope="use_case",
                item_id=use_case_id,
                gate="p0_source_readiness",
                severity=P0,
                owner=use_case.get("owner"),
                message=f"{use_case_id} depends on P0 sources that are not production-ready.",
                details={"source_gaps": source_gaps},
            )
        )
    return {
        "use_case_id": use_case_id,
        "name": use_case.get("name"),
        "priority": priority,
        "status": use_case.get("status"),
        "domain": use_case.get("domain"),
        "owner": use_case.get("owner"),
        "business_outcome": use_case.get("businessOutcome"),
        "primary_consumers": string_list(use_case.get("primaryConsumers")),
        "source_products": source_products,
        "onboarded_source_products": onboarded_source_products,
        "missing_source_products": missing_source_products,
        "draft_source_products": draft_source_products,
        "data_product_contracts": {
            "declared_count": len(data_products),
            "planned": planned_contracts,
            "missing_existing": missing_existing_contracts,
        },
        "implementation": {
            "pipeline_runner_count": len(pipeline_runners),
            "pipeline_count": len(pipelines),
            "pipeline_runners": pipeline_runners,
        },
        "source_readiness": {
            "p0_source_gap_count": len(source_gaps),
            "p0_effective_source_gap_count": len(source_gaps),
            "p0_source_gaps": source_gaps,
        },
        "next_actions": use_case_next_actions(planned_contracts, missing_existing_contracts, missing_source_products, draft_source_products, source_gaps, pipelines, priority),
        "blockers": blockers,
        "readiness_state": "ready_for_p0_execution" if not blockers else "blocked",
    }


def build_domain_matrix(root: Path, product_matrix: list[dict[str, Any]], use_case_matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry = load_yaml(root / "domains" / "registry.yaml")
    domains = registry.get("domains")
    domain_codes = [
        str(domain.get("code"))
        for domain in domains
        if isinstance(domains, list) and isinstance(domain, dict) and isinstance(domain.get("code"), str)
    ] if isinstance(domains, list) else []
    rows = []
    for code in sorted(domain_codes):
        products = [product for product in product_matrix if code in product.get("domains", [])]
        use_cases = [use_case for use_case in use_case_matrix if use_case.get("domain") == code]
        p0_use_cases = [use_case for use_case in use_cases if use_case.get("priority") == P0]
        p0_blockers = [
            blocker
            for item in products + use_cases
            for blocker in item.get("blockers", [])
            if blocker.get("severity") == P0
        ]
        rows.append(
            {
                "domain": code,
                "product_count": len(products),
                "use_case_count": len(use_cases),
                "p0_use_case_count": len(p0_use_cases),
                "p0_blocker_count": len(p0_blockers),
                "readiness_state": "ready" if not p0_blockers else "blocked",
            }
        )
    return rows


def portfolio_summary(
    product_matrix: list[dict[str, Any]],
    use_case_matrix: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    activation_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    p0_blockers = [blocker for blocker in blockers if blocker.get("severity") == P0]
    p0_static_source_gap_count = sum(
        1 for source in sources if source.get("priority") == P0 and source.get("status") != "production_ready"
    )
    p0_effective_source_gap_count = sum(
        1
        for source in sources
        if source.get("priority") == P0 and source_effective_status(source, activation_index) != "production_ready"
    )
    effective_source_rows = [
        {"effective_status": source_effective_status(source, activation_index)}
        for source in sources
    ]
    return {
        "product_count": len(product_matrix),
        "use_case_count": len(use_case_matrix),
        "p0_use_case_count": sum(1 for item in use_case_matrix if item.get("priority") == P0),
        "blocked_product_count": sum(1 for item in product_matrix if item.get("blockers")),
        "blocked_use_case_count": sum(1 for item in use_case_matrix if item.get("blockers")),
        "blocker_count": len(blockers),
        "p0_blocker_count": len(p0_blockers),
        "product_status": count_by(product_matrix, "status"),
        "use_case_status": count_by(use_case_matrix, "status"),
        "use_case_priority": count_by(use_case_matrix, "priority"),
        "source_status": count_by(sources, "status"),
        "source_effective_status": count_by(effective_source_rows, "effective_status"),
        "source_activation_state": activation_state_counts(activation_index),
        "p0_static_source_gap_count": p0_static_source_gap_count,
        "p0_source_gap_count": p0_effective_source_gap_count,
        "p0_effective_source_gap_count": p0_effective_source_gap_count,
        "p0_activation_covered_count": sum(
            1 for source in sources if source.get("priority") == P0 and source.get("sourceId") in activation_index
        ),
    }


def decision_board(
    product_matrix: list[dict[str, Any]],
    use_case_matrix: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "top_p0_blockers": [compact_blocker(blocker) for blocker in blockers if blocker.get("severity") == P0][:10],
        "ready_p0_use_cases": [
            item["use_case_id"]
            for item in use_case_matrix
            if item.get("priority") == P0 and item.get("readiness_state") == "ready_for_p0_execution"
        ],
        "blocked_p0_use_cases": [
            item["use_case_id"]
            for item in use_case_matrix
            if item.get("priority") == P0 and item.get("readiness_state") == "blocked"
        ],
        "products_required_by_p0": [
            item["product_code"]
            for item in product_matrix
            if item.get("required_by_p0_use_cases")
        ],
        "next_actions": top_next_actions(product_matrix, use_case_matrix),
    }


def top_next_actions(product_matrix: list[dict[str, Any]], use_case_matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions = []
    for item in product_matrix:
        for action in item.get("next_actions", []):
            actions.append({"scope": "product", "id": item.get("product_code"), **action})
    for item in use_case_matrix:
        for action in item.get("next_actions", []):
            actions.append({"scope": "use_case", "id": item.get("use_case_id"), **action})
    return sorted(actions, key=lambda item: (item.get("priority") != P0, str(item.get("scope")), str(item.get("id")), str(item.get("action"))))[:20]


def product_next_actions(
    contract_status: str,
    required_by_p0: bool,
    missing_topics: list[str],
    missing_data_products: list[str],
    source_gaps: list[dict[str, Any]],
    product: dict[str, Any],
) -> list[dict[str, Any]]:
    actions = []
    priority = P0 if required_by_p0 else "P1"
    if product.get("status") == "draft" and required_by_p0:
        actions.append({"priority": P0, "action": "promote_product_onboarding", "owner": product.get("productOwner")})
    if contract_status == "planned":
        actions.append({"priority": priority, "action": "create_first_slice_contracts", "owner": product.get("technicalOwner")})
    if contract_status == "existing" and (missing_topics or missing_data_products):
        actions.append({"priority": P0, "action": "repair_missing_declared_contracts", "owner": product.get("technicalOwner")})
    if source_gaps:
        actions.append({"priority": priority, "action": "complete_source_registry_bridge_and_evidence", "owner": product.get("technicalOwner")})
    return actions


def use_case_next_actions(
    planned_contracts: list[str],
    missing_existing_contracts: list[str],
    missing_source_products: list[str],
    draft_source_products: list[str],
    source_gaps: list[dict[str, Any]],
    pipelines: list[dict[str, Any]],
    priority: str,
) -> list[dict[str, Any]]:
    actions = []
    action_priority = P0 if priority == P0 else "P1"
    if missing_source_products:
        actions.append({"priority": action_priority, "action": "onboard_missing_source_products"})
    if draft_source_products:
        actions.append({"priority": action_priority, "action": "promote_required_source_products"})
    if planned_contracts:
        actions.append({"priority": action_priority, "action": "create_planned_data_product_contracts"})
    if missing_existing_contracts:
        actions.append({"priority": P0, "action": "repair_missing_existing_contracts"})
    if priority == P0 and not pipelines:
        actions.append({"priority": P0, "action": "declare_and_register_implementation_pipeline"})
    if source_gaps:
        actions.append({"priority": action_priority, "action": "clear_p0_source_readiness_gaps"})
    return actions


def source_summary(sources: list[dict[str, Any]], activation_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "source_count": len(sources),
        "by_status": count_by(sources, "status"),
        "by_effective_status": count_by(
            [{"effective_status": source_effective_status(source, activation_index)} for source in sources],
            "effective_status",
        ),
        "by_priority": count_by(sources, "priority"),
        "activation_covered_count": len(activation_index),
        "activation_state": activation_state_counts(activation_index),
        "p0_not_ready": [
            source_gap_summary(source, activation_index)
            for source in sources
            if source.get("priority") == P0 and source_effective_status(source, activation_index) != "production_ready"
        ],
    }


def source_gap_summary(source: dict[str, Any], activation_index: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    bridge = as_mapping(source.get("bridge"))
    canonical = as_mapping(source.get("canonical"))
    activation = source_activation_summary(source.get("sourceId"), activation_index)
    summary = {
        "source_id": source.get("sourceId"),
        "product": source.get("product"),
        "domain": source.get("domain"),
        "status": source.get("status"),
        "static_status": source.get("status"),
        "effective_status": source_effective_status(source, activation_index),
        "bridge_status": bridge.get("status"),
        "canonical_topic": canonical.get("topic"),
        "bronze_target": canonical.get("bronzeTarget"),
    }
    if activation:
        summary.update(
            {
                "activation_id": activation.get("activation_id"),
                "activation_state": activation.get("activation_state"),
                "activation_environment": activation.get("environment"),
                "activation_business_readiness": activation.get("business_readiness"),
                "activation_expires_at": activation.get("expires_at"),
                "activation_block_reason": activation.get("block_reason"),
                "readiness_id": activation.get("readiness_id"),
                "gate_badges": activation.get("gate_badges", {}),
                "impacted_use_cases": activation.get("impacted_use_cases", []),
            }
        )
    return summary


def p0_use_case_requirements_by_product(use_cases: list[dict[str, Any]]) -> dict[str, list[str]]:
    required: dict[str, list[str]] = {}
    for use_case in use_cases:
        if use_case.get("priority") != P0:
            continue
        use_case_id = str(use_case.get("id"))
        for product_code in string_list(use_case.get("sourceProducts")):
            required.setdefault(product_code, []).append(use_case_id)
    return {code: sorted(ids) for code, ids in required.items()}


def load_product_onboardings(root: Path) -> dict[str, dict[str, Any]]:
    products: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "products").glob("*/onboarding.yaml")):
        onboarding = load_yaml(path)
        product = onboarding.get("product")
        if isinstance(product, dict) and isinstance(product.get("code"), str):
            products[product["code"]] = onboarding
    return products


def load_source_registry(root: Path) -> list[dict[str, Any]]:
    path = root / "platform" / "ingestion" / "source-registry.yaml"
    if not path.is_file():
        return []
    registry = load_yaml(path)
    sources = registry.get("sources")
    return [source for source in sources if isinstance(source, dict)] if isinstance(sources, list) else []


def index_sources_by_product(sources: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for source in sources:
        product = source.get("product")
        if isinstance(product, str):
            index.setdefault(product, []).append(source)
    return index


def load_topic_names(root: Path) -> set[str]:
    names = set()
    for path in sorted((root / "contracts" / "topics").glob("*.yaml")):
        topic = load_yaml(path).get("topic")
        if isinstance(topic, dict) and isinstance(topic.get("name"), str):
            names.add(topic["name"])
    return names


def load_data_product_names(root: Path) -> set[str]:
    names = set()
    for path in sorted((root / "contracts" / "data-products").glob("*.yaml")):
        data_product = load_yaml(path).get("dataProduct")
        if isinstance(data_product, dict) and isinstance(data_product.get("name"), str):
            names.add(data_product["name"])
    return names


def load_portfolio_scope(root: Path) -> str:
    registry_path = root / "use-cases" / "registry.yaml"
    if not registry_path.is_file():
        return "unknown"
    registry = load_yaml(registry_path)
    return str(registry.get("portfolio_scope") or registry.get("portfolioScope") or "unknown")


def validate_enterprise_portfolio_readiness_report(report: dict[str, Any]) -> ValidationResult:
    result = ValidationResult(checked_count=1)
    if report.get("artifact_type") != "enterprise_portfolio_readiness_report.v1":
        result.error(Path("portfolio_readiness_report"), "artifact_type must be enterprise_portfolio_readiness_report.v1")
    if report.get("report_version") != REPORT_VERSION:
        result.error(Path("portfolio_readiness_report"), f"report_version must be {REPORT_VERSION}")
    for key in ("summary", "decision_board", "source_summary"):
        if not isinstance(report.get(key), dict):
            result.error(Path("portfolio_readiness_report"), f"{key} must be an object")
    for key in ("domain_matrix", "product_matrix", "use_case_matrix", "blockers"):
        if not isinstance(report.get(key), list):
            result.error(Path("portfolio_readiness_report"), f"{key} must be a list")
    if report.get("p0_ready") is True:
        blockers = report.get("blockers")
        if isinstance(blockers, list) and any(isinstance(blocker, dict) and blocker.get("severity") == P0 for blocker in blockers):
            result.error(Path("portfolio_readiness_report"), "p0_ready cannot be true while P0 blockers are present")
    return result


def blocker(
    *,
    scope: str,
    item_id: str,
    gate: str,
    severity: str,
    owner: object,
    message: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "scope": scope,
        "id": item_id,
        "gate": gate,
        "severity": severity,
        "owner": owner,
        "message": message,
        "details": details,
    }


def compact_blocker(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope": item.get("scope"),
        "id": item.get("id"),
        "gate": item.get("gate"),
        "owner": item.get("owner"),
        "message": item.get("message"),
    }


def products_fingerprint(products: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        code: {
            "status": as_mapping(product.get("product")).get("status"),
            "domains": product.get("domains", []),
            "first_slice": product.get("firstSlice", {}),
        }
        for code, product in sorted(products.items())
    }


def sources_fingerprint(sources: list[dict[str, Any]], activation_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        str(source.get("sourceId")): {
            "static_status": source.get("status"),
            "effective_status": source_effective_status(source, activation_index),
            "activation_id": activation_index.get(str(source.get("sourceId") or ""), {}).get("activation_id"),
        }
        for source in sorted(sources, key=lambda item: str(item.get("sourceId") or ""))
    }


def count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def string_list(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def as_mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def stable_id(*parts: object) -> str:
    payload = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

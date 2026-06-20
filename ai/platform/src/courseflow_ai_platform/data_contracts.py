from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str


@dataclass(frozen=True, slots=True)
class DataContractDefinition:
    contract_id: str
    name: str
    status: str
    product: str
    path: str
    use_cases: tuple[str, ...]
    data_domains: tuple[str, ...]
    owner_role: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "contractId": self.contract_id,
            "dataDomains": list(self.data_domains),
            "name": self.name,
            "ownerRole": self.owner_role,
            "path": self.path,
            "product": self.product,
            "status": self.status,
            "useCases": list(self.use_cases),
        }


@dataclass(frozen=True, slots=True)
class DataContractCoverageItem:
    request_id: str
    product: str
    use_case_id: str
    status: str
    is_non_lms: bool
    data_domains: tuple[str, ...]
    mapped_domains: tuple[str, ...]
    missing_domains: tuple[str, ...]
    contract_ids: tuple[str, ...]
    contract_statuses: tuple[str, ...]
    design_ready: bool
    production_ready: bool
    privacy_gated: bool
    simulator_gated: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "contractIds": list(self.contract_ids),
            "contractStatuses": list(self.contract_statuses),
            "dataDomains": list(self.data_domains),
            "designReady": self.design_ready,
            "isNonLms": self.is_non_lms,
            "mappedDomains": list(self.mapped_domains),
            "missingDomains": list(self.missing_domains),
            "privacyGated": self.privacy_gated,
            "product": self.product,
            "productionReady": self.production_ready,
            "requestId": self.request_id,
            "simulatorGated": self.simulator_gated,
            "status": self.status,
            "useCaseId": self.use_case_id,
        }


@dataclass(frozen=True, slots=True)
class DataContractCoverageReport:
    contract_count: int
    active_contract_count: int
    draft_contract_count: int
    privacy_gated_contract_count: int
    simulator_gated_contract_count: int
    request_count: int
    design_ready_request_count: int
    production_ready_request_count: int
    missing_request_count: int
    privacy_gated_request_count: int
    simulator_gated_request_count: int
    non_lms_request_count: int
    domain_count: int
    mapped_domain_count: int
    missing_domain_count: int
    contracts: tuple[DataContractDefinition, ...]
    items: tuple[DataContractCoverageItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionQueue": build_action_queue(self.items),
            "activeContractCount": self.active_contract_count,
            "contractCount": self.contract_count,
            "contracts": [contract.to_dict() for contract in self.contracts],
            "designReadyRequestCount": self.design_ready_request_count,
            "domainCount": self.domain_count,
            "draftContractCount": self.draft_contract_count,
            "items": [item.to_dict() for item in self.items],
            "mappedDomainCount": self.mapped_domain_count,
            "missingDomainCount": self.missing_domain_count,
            "missingRequestCount": self.missing_request_count,
            "nonLmsRequestCount": self.non_lms_request_count,
            "privacyGatedContractCount": self.privacy_gated_contract_count,
            "privacyGatedRequestCount": self.privacy_gated_request_count,
            "productionReadyRequestCount": self.production_ready_request_count,
            "requestCount": self.request_count,
            "simulatorGatedContractCount": self.simulator_gated_contract_count,
            "simulatorGatedRequestCount": self.simulator_gated_request_count,
        }

    def to_snapshot_dict(
        self,
        *,
        generated_at: str,
        source_registry: str = "platform/data-contracts/registry.yaml",
    ) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "data-contract-coverage-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "source_registry": source_registry,
            "summary": {
                "contract_count": self.contract_count,
                "active_contract_count": self.active_contract_count,
                "draft_contract_count": self.draft_contract_count,
                "privacy_gated_contract_count": self.privacy_gated_contract_count,
                "simulator_gated_contract_count": self.simulator_gated_contract_count,
                "request_count": self.request_count,
                "design_ready_request_count": self.design_ready_request_count,
                "production_ready_request_count": self.production_ready_request_count,
                "missing_request_count": self.missing_request_count,
                "privacy_gated_request_count": self.privacy_gated_request_count,
                "simulator_gated_request_count": self.simulator_gated_request_count,
                "non_lms_request_count": self.non_lms_request_count,
                "domain_count": self.domain_count,
                "mapped_domain_count": self.mapped_domain_count,
                "missing_domain_count": self.missing_domain_count,
            },
            "action_queue": build_snapshot_action_queue(self.items),
            "contracts": [contract_to_snapshot_dict(contract) for contract in self.contracts],
            "items": [coverage_item_to_snapshot_dict(item) for item in self.items],
        }


def build_data_contract_coverage_report(ai_root: Path | str) -> DataContractCoverageReport:
    root = Path(ai_root)
    registry = load_yaml(root / "platform" / "data-contracts" / "registry.yaml")
    intake = load_yaml(root / "platform" / "intake" / "use-case-requests.yaml")
    products = collect_products(load_yaml(root / "products" / "registry.yaml"))
    use_cases = collect_use_cases(load_yaml(root / "use-cases" / "registry.yaml"))

    policy = registry.get("policy")
    if not isinstance(policy, dict):
        raise RegistryValidationError("data contract registry must define policy")
    allowed_statuses = require_string_set(policy, "allowed_statuses", "data contract policy")
    design_ready_statuses = require_string_set(
        policy,
        "design_ready_statuses",
        "data contract policy",
    )
    production_ready_statuses = require_string_set(
        policy,
        "production_ready_statuses",
        "data contract policy",
    )
    if not design_ready_statuses <= allowed_statuses:
        raise RegistryValidationError("data contract design_ready_statuses must be allowed")
    if not production_ready_statuses <= allowed_statuses:
        raise RegistryValidationError("data contract production_ready_statuses must be allowed")

    contracts = tuple(
        build_data_contract_definition(root, row, products, use_cases, allowed_statuses)
        for row in require_mapping_list(registry, "contracts", "data contract registry")
    )
    if not contracts:
        raise RegistryValidationError("data contract registry must define contracts")

    domain_index = build_domain_index(contracts)
    request_rows = require_mapping_list(intake, "requests", "use-case intake registry")
    items = tuple(
        build_coverage_item(
            row,
            use_cases,
            domain_index,
            design_ready_statuses,
            production_ready_statuses,
        )
        for row in request_rows
    )

    return DataContractCoverageReport(
        contract_count=len(contracts),
        active_contract_count=count_contract_status(contracts, "active"),
        draft_contract_count=count_contract_status(contracts, "draft"),
        privacy_gated_contract_count=count_contract_status(contracts, "privacy_gated"),
        simulator_gated_contract_count=count_contract_status(contracts, "simulator_gated"),
        request_count=len(items),
        design_ready_request_count=sum(1 for item in items if item.design_ready),
        production_ready_request_count=sum(1 for item in items if item.production_ready),
        missing_request_count=sum(1 for item in items if item.missing_domains),
        privacy_gated_request_count=sum(1 for item in items if item.privacy_gated),
        simulator_gated_request_count=sum(1 for item in items if item.simulator_gated),
        non_lms_request_count=sum(1 for item in items if item.is_non_lms),
        domain_count=sum(len(item.data_domains) for item in items),
        mapped_domain_count=sum(len(item.mapped_domains) for item in items),
        missing_domain_count=sum(len(item.missing_domains) for item in items),
        contracts=contracts,
        items=items,
    )


def build_data_contract_coverage_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_data_contract_coverage_report(ai_root).to_snapshot_dict(
        generated_at=report_date
    )


def write_data_contract_coverage_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            build_data_contract_coverage_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def build_data_contract_definition(
    root: Path,
    row: dict[str, Any],
    products: set[str],
    use_cases: dict[str, dict[str, Any]],
    allowed_statuses: set[str],
) -> DataContractDefinition:
    contract_id = require_str(row, "contract_id", "data contract")
    owner = f"data contract {contract_id}"
    name = require_str(row, "name", owner)
    status = require_str(row, "status", owner)
    product = require_str(row, "product", owner)
    path = require_str(row, "path", owner)
    owner_role = require_str(row, "owner_role", owner)
    use_case_ids = tuple(require_string_list(row, "use_cases", owner))
    data_domains = tuple(require_string_list(row, "data_domains", owner))

    if status not in allowed_statuses:
        raise RegistryValidationError(f"{owner} has unsupported status: {status}")
    if product not in products:
        raise RegistryValidationError(f"{owner} references unknown product: {product}")
    if not use_case_ids:
        raise RegistryValidationError(f"{owner} must reference at least one use case")
    if not data_domains:
        raise RegistryValidationError(f"{owner} must reference at least one data domain")

    for use_case_id in use_case_ids:
        use_case = use_cases.get(use_case_id)
        if use_case is None:
            raise RegistryValidationError(f"{owner} references unknown use case: {use_case_id}")
        use_case_product = require_str(use_case, "product", f"use case {use_case_id}")
        if use_case_product != product:
            raise RegistryValidationError(
                f"{owner} product does not match use case {use_case_id}: "
                f"{product} != {use_case_product}"
            )

    contract_path = root / path
    contract_payload = load_yaml(contract_path)
    if require_str(contract_payload, "product", f"contract file {path}") != product:
        raise RegistryValidationError(f"{owner} product does not match contract file")
    require_str(contract_payload, "contract", f"contract file {path}")
    require_str(contract_payload, "owner", f"contract file {path}")
    require_str(contract_payload, "producer", f"contract file {path}")
    require_str(contract_payload, "consumer", f"contract file {path}")
    require_mapping(contract_payload, "entities", f"contract file {path}")
    require_mapping(contract_payload, "feature_groups", f"contract file {path}")
    require_mapping(contract_payload, "privacy", f"contract file {path}")
    require_mapping(contract_payload, "quality", f"contract file {path}")

    return DataContractDefinition(
        contract_id=contract_id,
        name=name,
        status=status,
        product=product,
        path=path,
        use_cases=use_case_ids,
        data_domains=data_domains,
        owner_role=owner_role,
    )


def build_coverage_item(
    row: dict[str, Any],
    use_cases: dict[str, dict[str, Any]],
    domain_index: dict[str, list[DataContractDefinition]],
    design_ready_statuses: set[str],
    production_ready_statuses: set[str],
) -> DataContractCoverageItem:
    request_id = require_str(row, "request_id", "use-case intake request")
    product = require_str(row, "product", f"use-case intake request {request_id}")
    use_case_id = require_str(row, "use_case_id", f"use-case intake request {request_id}")
    status = require_str(row, "status", f"use-case intake request {request_id}")
    data_domains = tuple(
        require_string_list(row, "data_domains", f"use-case intake request {request_id}")
    )
    use_case = use_cases.get(use_case_id)
    if use_case is None:
        raise RegistryValidationError(
            f"use-case intake request {request_id} references unknown use case: {use_case_id}"
        )
    use_case_product = require_str(use_case, "product", f"use case {use_case_id}")
    if use_case_product != product:
        raise RegistryValidationError(
            f"use-case intake request {request_id} product does not match use case"
        )

    mapped_domains: list[str] = []
    missing_domains: list[str] = []
    contract_ids: list[str] = []
    contract_statuses: list[str] = []
    for domain in data_domains:
        contracts = [
            contract
            for contract in domain_index.get(domain, [])
            if contract.product == product and use_case_id in contract.use_cases
        ]
        if not contracts:
            missing_domains.append(domain)
            continue
        mapped_domains.append(domain)
        for contract in contracts:
            if contract.contract_id not in contract_ids:
                contract_ids.append(contract.contract_id)
            if contract.status not in contract_statuses:
                contract_statuses.append(contract.status)

    all_statuses = set(contract_statuses)
    design_ready = (
        not missing_domains
        and bool(contract_ids)
        and all_statuses <= design_ready_statuses
    )
    production_ready = (
        not missing_domains
        and bool(contract_ids)
        and all_statuses <= production_ready_statuses
    )
    return DataContractCoverageItem(
        request_id=request_id,
        product=product,
        use_case_id=use_case_id,
        status=status,
        is_non_lms=product != "lms-courseflow",
        data_domains=data_domains,
        mapped_domains=tuple(mapped_domains),
        missing_domains=tuple(missing_domains),
        contract_ids=tuple(contract_ids),
        contract_statuses=tuple(contract_statuses),
        design_ready=design_ready,
        production_ready=production_ready,
        privacy_gated="privacy_gated" in all_statuses,
        simulator_gated="simulator_gated" in all_statuses,
    )


def build_domain_index(
    contracts: tuple[DataContractDefinition, ...],
) -> dict[str, list[DataContractDefinition]]:
    domain_index: dict[str, list[DataContractDefinition]] = {}
    seen_contract_ids: set[str] = set()
    for contract in contracts:
        if contract.contract_id in seen_contract_ids:
            raise RegistryValidationError(
                f"data contract registry has duplicate id: {contract.contract_id}"
            )
        seen_contract_ids.add(contract.contract_id)
        for domain in contract.data_domains:
            domain_index.setdefault(domain, []).append(contract)
    return domain_index


def build_action_queue(
    items: tuple[DataContractCoverageItem, ...],
) -> dict[str, list[str]]:
    return {
        "designReady": [item.request_id for item in items if item.design_ready],
        "missingContract": [item.request_id for item in items if item.missing_domains],
        "needsPrivacyReview": [item.request_id for item in items if item.privacy_gated],
        "needsProductionHardening": [
            item.request_id
            for item in items
            if item.design_ready and not item.production_ready
        ],
        "needsSimulator": [item.request_id for item in items if item.simulator_gated],
        "productionReady": [item.request_id for item in items if item.production_ready],
    }


def build_snapshot_action_queue(
    items: tuple[DataContractCoverageItem, ...],
) -> dict[str, list[str]]:
    queue = build_action_queue(items)
    return {
        "design_ready": queue["designReady"],
        "missing_contract": queue["missingContract"],
        "needs_privacy_review": queue["needsPrivacyReview"],
        "needs_production_hardening": queue["needsProductionHardening"],
        "needs_simulator": queue["needsSimulator"],
        "production_ready": queue["productionReady"],
    }


def contract_to_snapshot_dict(contract: DataContractDefinition) -> dict[str, Any]:
    return {
        "contract_id": contract.contract_id,
        "name": contract.name,
        "status": contract.status,
        "product": contract.product,
        "path": contract.path,
        "use_cases": list(contract.use_cases),
        "data_domains": list(contract.data_domains),
        "owner_role": contract.owner_role,
    }


def coverage_item_to_snapshot_dict(item: DataContractCoverageItem) -> dict[str, Any]:
    return {
        "request_id": item.request_id,
        "product": item.product,
        "use_case_id": item.use_case_id,
        "status": item.status,
        "is_non_lms": item.is_non_lms,
        "data_domains": list(item.data_domains),
        "mapped_domains": list(item.mapped_domains),
        "missing_domains": list(item.missing_domains),
        "contract_ids": list(item.contract_ids),
        "contract_statuses": list(item.contract_statuses),
        "design_ready": item.design_ready,
        "production_ready": item.production_ready,
        "privacy_gated": item.privacy_gated,
        "simulator_gated": item.simulator_gated,
    }


def collect_products(registry: dict[str, Any]) -> set[str]:
    return {
        require_str(row, "id", "products registry")
        for row in require_mapping_list(registry, "products", "products registry")
    }


def collect_use_cases(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        require_str(row, "id", "use-case registry"): row
        for row in require_mapping_list(registry, "use_cases", "use-case registry")
    }


def count_contract_status(
    contracts: tuple[DataContractDefinition, ...],
    status: str,
) -> int:
    return sum(1 for contract in contracts if contract.status == status)


def require_mapping(row: dict[str, Any], key: str, owner: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict) or not value:
        raise RegistryValidationError(f"{owner} must define non-empty mapping field {key}")
    return value


def require_mapping_list(row: dict[str, Any], key: str, owner: str) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a mapping")
        result.append(item)
    return result


def require_string_list(row: dict[str, Any], key: str, owner: str) -> list[str]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a string")
        result.append(item.strip())
    return result


def require_string_set(row: dict[str, Any], key: str, owner: str) -> set[str]:
    return set(require_string_list(row, key, owner))


def default_snapshot_path(root: Path) -> Path:
    return root / "platform" / "data-contracts" / "reports" / "data-contract-coverage-v1.yaml"

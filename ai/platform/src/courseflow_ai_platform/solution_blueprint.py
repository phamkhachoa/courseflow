from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

EXECUTABLE_COVERAGE_STATUSES = frozenset({"implemented_baseline", "executable_gate"})
ROADMAP_COVERAGE_STATUS = "registered_roadmap"
PRIVACY_COVERAGE_STATUS = "privacy_gated"
SIMULATOR_COVERAGE_STATUS = "simulator_required"

READY_STATUS = "ready_for_solution_design"
CLOSED_STATUSES = frozenset({"rejected", "withdrawn"})


@dataclass(frozen=True, slots=True)
class BlueprintModulePlan:
    module_id: str
    taxonomy_area: str
    coverage_status: str
    model_family_count: int
    evaluation_gate_count: int
    business_capabilities: tuple[str, ...]

    @property
    def executable(self) -> bool:
        return self.coverage_status in EXECUTABLE_COVERAGE_STATUSES

    def to_dict(self) -> dict[str, Any]:
        return {
            "businessCapabilities": list(self.business_capabilities),
            "coverageStatus": self.coverage_status,
            "evaluationGateCount": self.evaluation_gate_count,
            "executable": self.executable,
            "modelFamilyCount": self.model_family_count,
            "moduleId": self.module_id,
            "taxonomyArea": self.taxonomy_area,
        }


@dataclass(frozen=True, slots=True)
class UseCaseSolutionBlueprint:
    request_id: str
    product: str
    use_case_id: str
    use_case_name: str
    status: str
    priority: str
    submitted_by: str
    business_owner: str
    submitted_at: str
    objective: str
    is_non_lms: bool
    target_modules: tuple[BlueprintModulePlan, ...]
    requested_capabilities: tuple[str, ...]
    expected_business_kpis: tuple[str, ...]
    data_domains: tuple[str, ...]
    constraints: tuple[str, ...]
    blueprint_status: str
    workstreams: tuple[str, ...]
    blocking_reasons: tuple[str, ...]

    @property
    def target_module_count(self) -> int:
        return len(self.target_modules)

    @property
    def executable_module_count(self) -> int:
        return sum(1 for module in self.target_modules if module.executable)

    @property
    def roadmap_module_count(self) -> int:
        return sum(
            1
            for module in self.target_modules
            if module.coverage_status == ROADMAP_COVERAGE_STATUS
        )

    @property
    def privacy_gated_module_count(self) -> int:
        return sum(
            1
            for module in self.target_modules
            if module.coverage_status == PRIVACY_COVERAGE_STATUS
        )

    @property
    def simulator_required_module_count(self) -> int:
        return sum(
            1
            for module in self.target_modules
            if module.coverage_status == SIMULATOR_COVERAGE_STATUS
        )

    @property
    def evaluation_gate_count(self) -> int:
        return sum(module.evaluation_gate_count for module in self.target_modules)

    @property
    def ready_for_solution_design(self) -> bool:
        return self.blueprint_status == READY_STATUS and not self.blocking_reasons

    def to_dict(self) -> dict[str, Any]:
        return {
            "blockingReasons": list(self.blocking_reasons),
            "blueprintStatus": self.blueprint_status,
            "businessOwner": self.business_owner,
            "constraints": list(self.constraints),
            "dataDomains": list(self.data_domains),
            "evaluationGateCount": self.evaluation_gate_count,
            "executableModuleCount": self.executable_module_count,
            "expectedBusinessKpis": list(self.expected_business_kpis),
            "isNonLms": self.is_non_lms,
            "objective": self.objective,
            "priority": self.priority,
            "product": self.product,
            "readyForSolutionDesign": self.ready_for_solution_design,
            "requestId": self.request_id,
            "requestedCapabilities": list(self.requested_capabilities),
            "roadmapModuleCount": self.roadmap_module_count,
            "status": self.status,
            "submittedAt": self.submitted_at,
            "submittedBy": self.submitted_by,
            "targetModuleCount": self.target_module_count,
            "targetModules": [module.to_dict() for module in self.target_modules],
            "useCaseId": self.use_case_id,
            "useCaseName": self.use_case_name,
            "workstreams": list(self.workstreams),
        }


@dataclass(frozen=True, slots=True)
class SolutionBlueprintReport:
    request_count: int
    ready_count: int
    waiting_count: int
    non_lms_count: int
    data_contract_gap_count: int
    evaluation_strategy_gap_count: int
    privacy_review_count: int
    simulator_required_count: int
    platform_build_gap_count: int
    target_module_count: int
    executable_module_count: int
    coverage_module_count: int
    by_status: dict[str, int]
    blueprints: tuple[UseCaseSolutionBlueprint, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionQueue": build_action_queue(self.blueprints),
            "blueprints": [blueprint.to_dict() for blueprint in self.blueprints],
            "byStatus": self.by_status,
            "coverageModuleCount": self.coverage_module_count,
            "dataContractGapCount": self.data_contract_gap_count,
            "evaluationStrategyGapCount": self.evaluation_strategy_gap_count,
            "executableModuleCount": self.executable_module_count,
            "nonLmsCount": self.non_lms_count,
            "platformBuildGapCount": self.platform_build_gap_count,
            "privacyReviewCount": self.privacy_review_count,
            "readyCount": self.ready_count,
            "requestCount": self.request_count,
            "simulatorRequiredCount": self.simulator_required_count,
            "targetModuleCount": self.target_module_count,
            "waitingCount": self.waiting_count,
        }

    def to_snapshot_dict(
        self,
        *,
        generated_at: str,
        source_registry: str = "platform/intake/use-case-requests.yaml",
    ) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "use-case-solution-blueprints-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "source_registry": source_registry,
            "summary": {
                "request_count": self.request_count,
                "ready_count": self.ready_count,
                "waiting_count": self.waiting_count,
                "non_lms_count": self.non_lms_count,
                "data_contract_gap_count": self.data_contract_gap_count,
                "evaluation_strategy_gap_count": self.evaluation_strategy_gap_count,
                "privacy_review_count": self.privacy_review_count,
                "simulator_required_count": self.simulator_required_count,
                "platform_build_gap_count": self.platform_build_gap_count,
                "target_module_count": self.target_module_count,
                "executable_module_count": self.executable_module_count,
                "coverage_module_count": self.coverage_module_count,
            },
            "by_status": self.by_status,
            "action_queue": build_snapshot_action_queue(self.blueprints),
            "blueprints": [
                solution_blueprint_to_snapshot_dict(blueprint)
                for blueprint in self.blueprints
            ],
        }


def build_solution_blueprint_report(ai_root: Path | str) -> SolutionBlueprintReport:
    root = Path(ai_root)
    registry = load_yaml(root / "platform" / "intake" / "use-case-requests.yaml")
    products = collect_products(load_yaml(root / "products" / "registry.yaml"))
    use_cases = collect_use_cases(load_yaml(root / "use-cases" / "registry.yaml"))
    coverage_modules = collect_coverage_modules(
        load_yaml(root / "platform" / "coverage" / "business-capability-coverage.yaml")
    )

    policy = registry.get("policy")
    if not isinstance(policy, dict):
        raise RegistryValidationError("use-case intake registry must define policy")
    allowed_statuses = require_string_set(policy, "allowed_statuses", "use-case intake policy")
    allowed_priorities = require_string_set(
        policy, "allowed_priorities", "use-case intake policy"
    )
    required_roles = require_string_set(policy, "required_roles", "use-case intake policy")
    for role in ("po_ba", "sa_ai_platform", "sa_ai_engineer"):
        if role not in required_roles:
            raise RegistryValidationError(
                f"use-case intake policy must require role: {role}"
            )

    rows = require_mapping_list(registry, "requests", "use-case intake registry")
    if not rows:
        raise RegistryValidationError("use-case intake registry must define requests")

    blueprints: list[UseCaseSolutionBlueprint] = []
    seen_ids: set[str] = set()
    for row in rows:
        blueprint = build_solution_blueprint(
            row,
            products,
            use_cases,
            coverage_modules,
            allowed_statuses,
            allowed_priorities,
        )
        if blueprint.request_id in seen_ids:
            raise RegistryValidationError(
                f"use-case intake registry has duplicate id: {blueprint.request_id}"
            )
        seen_ids.add(blueprint.request_id)
        blueprints.append(blueprint)

    by_status = {status: 0 for status in sorted(allowed_statuses)}
    for blueprint in blueprints:
        by_status[blueprint.status] = by_status.get(blueprint.status, 0) + 1

    all_target_modules = {
        module.module_id for blueprint in blueprints for module in blueprint.target_modules
    }
    return SolutionBlueprintReport(
        request_count=len(blueprints),
        ready_count=sum(1 for blueprint in blueprints if blueprint.ready_for_solution_design),
        waiting_count=sum(1 for blueprint in blueprints if blueprint.status.startswith("waiting_")),
        non_lms_count=sum(1 for blueprint in blueprints if blueprint.is_non_lms),
        data_contract_gap_count=count_blocker(blueprints, "data_contract_missing"),
        evaluation_strategy_gap_count=count_blocker(
            blueprints,
            "evaluation_strategy_missing",
        ),
        privacy_review_count=count_blocker(blueprints, "privacy_review_required"),
        simulator_required_count=count_any_blocker(
            blueprints,
            {"simulator_missing", "simulator_required"},
        ),
        platform_build_gap_count=count_blocker(
            blueprints,
            "platform_module_not_executable",
        ),
        target_module_count=sum(blueprint.target_module_count for blueprint in blueprints),
        executable_module_count=sum(
            blueprint.executable_module_count for blueprint in blueprints
        ),
        coverage_module_count=len(all_target_modules),
        by_status=by_status,
        blueprints=tuple(blueprints),
    )


def build_solution_blueprint_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_solution_blueprint_report(ai_root).to_snapshot_dict(
        generated_at=report_date
    )


def write_solution_blueprint_snapshot(
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
            build_solution_blueprint_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def build_solution_blueprint(
    row: dict[str, Any],
    products: set[str],
    use_cases: dict[str, dict[str, Any]],
    coverage_modules: dict[str, dict[str, Any]],
    allowed_statuses: set[str],
    allowed_priorities: set[str],
) -> UseCaseSolutionBlueprint:
    request_id = require_str(row, "request_id", "use-case intake request")
    owner = f"use-case intake request {request_id}"
    product = require_str(row, "product", owner)
    use_case_id = require_str(row, "use_case_id", owner)
    status = require_str(row, "status", owner)
    priority = require_str(row, "priority", owner)
    submitted_by = require_str(row, "submitted_by", owner)
    business_owner = require_str(row, "business_owner", owner)
    submitted_at = require_str(row, "submitted_at", owner)
    objective = require_str(row, "objective", owner)
    date.fromisoformat(submitted_at)

    if product not in products:
        raise RegistryValidationError(f"{owner} references unknown product: {product}")
    use_case = use_cases.get(use_case_id)
    if use_case is None:
        raise RegistryValidationError(f"{owner} references unknown use case: {use_case_id}")
    use_case_product = require_str(use_case, "product", f"use case {use_case_id}")
    if use_case_product != product:
        raise RegistryValidationError(
            f"{owner} product does not match use case product: {product} != {use_case_product}"
        )
    if status not in allowed_statuses:
        raise RegistryValidationError(f"{owner} has unsupported status: {status}")
    if priority not in allowed_priorities:
        raise RegistryValidationError(f"{owner} has unsupported priority: {priority}")

    requested_capabilities = require_string_list(row, "requested_capabilities", owner)
    expected_business_kpis = require_string_list(row, "expected_business_kpis", owner)
    data_domains = require_string_list(row, "data_domains", owner)
    constraints = require_string_list(row, "constraints", owner)
    target_module_ids = require_string_list(row, "target_modules", owner)
    if not target_module_ids:
        raise RegistryValidationError(f"{owner} must target at least one platform module")

    target_modules: list[BlueprintModulePlan] = []
    for module_id in target_module_ids:
        module = coverage_modules.get(module_id)
        if module is None:
            raise RegistryValidationError(f"{owner} references unknown module: {module_id}")
        validate_module_supports_use_case(module, module_id, use_case_id, owner)
        target_modules.append(
            BlueprintModulePlan(
                module_id=module_id,
                taxonomy_area=require_str(module, "taxonomy_area", f"module {module_id}"),
                coverage_status=require_str(module, "coverage_status", f"module {module_id}"),
                model_family_count=len(
                    require_string_list(module, "model_families", f"module {module_id}")
                ),
                evaluation_gate_count=len(
                    require_string_list(module, "evaluation_gate_ids", f"module {module_id}")
                ),
                business_capabilities=tuple(
                    require_string_list(
                        module,
                        "business_capabilities",
                        f"module {module_id}",
                    )
                ),
            )
        )

    blocking_reasons = derive_blocking_reasons(status, target_modules)
    blueprint_status = derive_blueprint_status(status, blocking_reasons)
    workstreams = derive_workstreams(blocking_reasons)

    return UseCaseSolutionBlueprint(
        request_id=request_id,
        product=product,
        use_case_id=use_case_id,
        use_case_name=require_str(use_case, "name", f"use case {use_case_id}"),
        status=status,
        priority=priority,
        submitted_by=submitted_by,
        business_owner=business_owner,
        submitted_at=submitted_at,
        objective=objective,
        is_non_lms=product != "lms-courseflow",
        target_modules=tuple(target_modules),
        requested_capabilities=tuple(requested_capabilities),
        expected_business_kpis=tuple(expected_business_kpis),
        data_domains=tuple(data_domains),
        constraints=tuple(constraints),
        blueprint_status=blueprint_status,
        workstreams=workstreams,
        blocking_reasons=blocking_reasons,
    )


def derive_blocking_reasons(
    status: str,
    target_modules: list[BlueprintModulePlan],
) -> tuple[str, ...]:
    if status in CLOSED_STATUSES:
        return ()

    blockers: list[str] = []
    if status == "waiting_for_data_contract":
        blockers.append("data_contract_missing")
    if status == "waiting_for_evaluation_strategy":
        blockers.append("evaluation_strategy_missing")
    if status == "waiting_for_privacy_review":
        blockers.append("privacy_review_required")
    if status == "waiting_for_simulator":
        blockers.append("simulator_missing")

    for module in target_modules:
        if module.coverage_status == PRIVACY_COVERAGE_STATUS:
            blockers.append("privacy_review_required")
        if module.coverage_status == SIMULATOR_COVERAGE_STATUS:
            blockers.append("simulator_required")
        if module.coverage_status == ROADMAP_COVERAGE_STATUS:
            blockers.append("platform_module_not_executable")
        if module.evaluation_gate_count == 0 and module.executable:
            blockers.append("evaluation_gate_missing")

    return tuple(dict.fromkeys(blockers))


def derive_blueprint_status(status: str, blocking_reasons: tuple[str, ...]) -> str:
    if status in CLOSED_STATUSES:
        return "closed"
    if not blocking_reasons:
        return READY_STATUS
    if "privacy_review_required" in blocking_reasons:
        return "needs_privacy_review"
    if "simulator_missing" in blocking_reasons or "simulator_required" in blocking_reasons:
        return "needs_simulator"
    if "data_contract_missing" in blocking_reasons:
        return "needs_data_contract"
    if "evaluation_strategy_missing" in blocking_reasons:
        return "needs_evaluation_strategy"
    if "platform_module_not_executable" in blocking_reasons:
        return "needs_platform_build"
    return "blocked"


def derive_workstreams(blocking_reasons: tuple[str, ...]) -> tuple[str, ...]:
    if not blocking_reasons:
        return (
            "po_ba_confirm_business_value_and_acceptance_metrics",
            "sa_ai_platform_publish_solution_architecture",
            "sa_ai_engineer_prepare_baseline_artifact_and_eval_plan",
        )

    workstreams: list[str] = []
    if "data_contract_missing" in blocking_reasons:
        workstreams.append("po_ba_define_feature_and_training_data_contract")
    if (
        "evaluation_strategy_missing" in blocking_reasons
        or "evaluation_gate_missing" in blocking_reasons
    ):
        workstreams.append("sa_ai_engineer_design_offline_and_shadow_evaluation_gates")
    if "privacy_review_required" in blocking_reasons:
        workstreams.append("sa_ai_platform_complete_privacy_and_retention_review")
    if "simulator_missing" in blocking_reasons or "simulator_required" in blocking_reasons:
        workstreams.append("sa_ai_engineer_build_simulator_or_offline_policy_evaluation")
    if "platform_module_not_executable" in blocking_reasons:
        workstreams.append("sa_ai_platform_plan_runtime_artifact_for_roadmap_module")
    return tuple(dict.fromkeys(workstreams))


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


def collect_coverage_modules(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        require_str(row, "id", "business capability coverage"): row
        for row in require_mapping_list(
            registry,
            "modules",
            "business capability coverage",
        )
    }


def validate_module_supports_use_case(
    module: dict[str, Any],
    module_id: str,
    use_case_id: str,
    owner: str,
) -> None:
    supported_use_cases = set(
        require_string_list(module, "lms_use_cases", f"module {module_id}")
        + require_string_list(module, "enterprise_use_cases", f"module {module_id}")
    )
    if use_case_id not in supported_use_cases:
        raise RegistryValidationError(
            f"{owner} targets module {module_id}, but it does not cover {use_case_id}"
        )


def build_action_queue(
    blueprints: tuple[UseCaseSolutionBlueprint, ...],
) -> dict[str, list[str]]:
    return {
        "closed": [
            blueprint.request_id
            for blueprint in blueprints
            if blueprint.blueprint_status == "closed"
        ],
        "needsDataContract": [
            blueprint.request_id
            for blueprint in blueprints
            if "data_contract_missing" in blueprint.blocking_reasons
        ],
        "needsEvaluationStrategy": [
            blueprint.request_id
            for blueprint in blueprints
            if "evaluation_strategy_missing" in blueprint.blocking_reasons
            or "evaluation_gate_missing" in blueprint.blocking_reasons
        ],
        "needsPlatformBuild": [
            blueprint.request_id
            for blueprint in blueprints
            if "platform_module_not_executable" in blueprint.blocking_reasons
        ],
        "needsPrivacyReview": [
            blueprint.request_id
            for blueprint in blueprints
            if "privacy_review_required" in blueprint.blocking_reasons
        ],
        "needsSimulator": [
            blueprint.request_id
            for blueprint in blueprints
            if "simulator_missing" in blueprint.blocking_reasons
            or "simulator_required" in blueprint.blocking_reasons
        ],
        "readyForSolutionDesign": [
            blueprint.request_id
            for blueprint in blueprints
            if blueprint.ready_for_solution_design
        ],
    }


def build_snapshot_action_queue(
    blueprints: tuple[UseCaseSolutionBlueprint, ...],
) -> dict[str, list[str]]:
    queue = build_action_queue(blueprints)
    return {
        "closed": queue["closed"],
        "needs_data_contract": queue["needsDataContract"],
        "needs_evaluation_strategy": queue["needsEvaluationStrategy"],
        "needs_platform_build": queue["needsPlatformBuild"],
        "needs_privacy_review": queue["needsPrivacyReview"],
        "needs_simulator": queue["needsSimulator"],
        "ready_for_solution_design": queue["readyForSolutionDesign"],
    }


def solution_blueprint_to_snapshot_dict(
    blueprint: UseCaseSolutionBlueprint,
) -> dict[str, Any]:
    return {
        "request_id": blueprint.request_id,
        "product": blueprint.product,
        "use_case_id": blueprint.use_case_id,
        "use_case_name": blueprint.use_case_name,
        "status": blueprint.status,
        "priority": blueprint.priority,
        "submitted_by": blueprint.submitted_by,
        "business_owner": blueprint.business_owner,
        "submitted_at": blueprint.submitted_at,
        "is_non_lms": blueprint.is_non_lms,
        "blueprint_status": blueprint.blueprint_status,
        "ready_for_solution_design": blueprint.ready_for_solution_design,
        "target_module_count": blueprint.target_module_count,
        "executable_module_count": blueprint.executable_module_count,
        "roadmap_module_count": blueprint.roadmap_module_count,
        "privacy_gated_module_count": blueprint.privacy_gated_module_count,
        "simulator_required_module_count": blueprint.simulator_required_module_count,
        "evaluation_gate_count": blueprint.evaluation_gate_count,
        "blocking_reasons": list(blueprint.blocking_reasons),
        "workstreams": list(blueprint.workstreams),
        "target_modules": [
            {
                "module_id": module.module_id,
                "taxonomy_area": module.taxonomy_area,
                "coverage_status": module.coverage_status,
                "executable": module.executable,
                "evaluation_gate_count": module.evaluation_gate_count,
                "business_capabilities": list(module.business_capabilities),
            }
            for module in blueprint.target_modules
        ],
    }


def count_blocker(
    blueprints: tuple[UseCaseSolutionBlueprint, ...],
    blocker: str,
) -> int:
    return sum(1 for blueprint in blueprints if blocker in blueprint.blocking_reasons)


def count_any_blocker(
    blueprints: tuple[UseCaseSolutionBlueprint, ...],
    blockers: set[str],
) -> int:
    return sum(
        1
        for blueprint in blueprints
        if any(blocker in blueprint.blocking_reasons for blocker in blockers)
    )


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
    return root / "platform" / "intake" / "reports" / "use-case-blueprints-v1.yaml"

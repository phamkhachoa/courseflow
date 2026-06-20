from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml
from courseflow_ai_platform.solution_blueprint import (
    build_solution_blueprint_report,
    build_solution_blueprint_snapshot,
)


def test_solution_blueprints_project_enterprise_front_door() -> None:
    report = build_solution_blueprint_report(Path(__file__).resolve().parents[2])
    payload = report.to_dict()

    assert payload["requestCount"] == 6
    assert payload["readyCount"] == 6
    assert payload["waitingCount"] == 0
    assert payload["nonLmsCount"] == 5
    assert payload["coverageModuleCount"] == 9
    assert payload["actionQueue"]["readyForSolutionDesign"] == [
        "enterprise-knowledge-assistant-discovery",
        "lms-at-risk-prediction-baseline",
        "support-sla-risk-discovery",
        "finance-document-intelligence-discovery",
        "operations-routing-optimization-simulator",
        "finance-payment-fraud-scoring-discovery",
    ]
    assert payload["actionQueue"]["needsDataContract"] == []
    assert payload["actionQueue"]["needsPrivacyReview"] == []
    assert payload["actionQueue"]["needsSimulator"] == []
    assert payload["actionQueue"]["needsEvaluationStrategy"] == []


def test_solution_blueprint_items_expose_role_workstreams_and_blockers() -> None:
    report = build_solution_blueprint_report(Path(__file__).resolve().parents[2])
    blueprints = {blueprint.request_id: blueprint for blueprint in report.blueprints}

    enterprise_knowledge = blueprints["enterprise-knowledge-assistant-discovery"]
    assert enterprise_knowledge.ready_for_solution_design is True
    assert enterprise_knowledge.blocking_reasons == ()
    assert enterprise_knowledge.executable_module_count == 3
    assert "sa_ai_platform_publish_solution_architecture" in (
        enterprise_knowledge.workstreams
    )

    finance_doc = blueprints["finance-document-intelligence-discovery"]
    assert finance_doc.blueprint_status == "ready_for_solution_design"
    assert finance_doc.ready_for_solution_design is True
    assert finance_doc.blocking_reasons == ()
    assert finance_doc.executable_module_count == 2

    support_sla = blueprints["support-sla-risk-discovery"]
    assert support_sla.blueprint_status == "ready_for_solution_design"
    assert support_sla.blocking_reasons == ()
    assert support_sla.executable_module_count == 2

    operations_routing = blueprints["operations-routing-optimization-simulator"]
    assert operations_routing.blueprint_status == "ready_for_solution_design"
    assert operations_routing.ready_for_solution_design is True
    assert operations_routing.blocking_reasons == ()
    assert operations_routing.executable_module_count == 1

    finance_fraud = blueprints["finance-payment-fraud-scoring-discovery"]
    assert finance_fraud.blueprint_status == "ready_for_solution_design"
    assert finance_fraud.ready_for_solution_design is True
    assert finance_fraud.blocking_reasons == ()
    assert finance_fraud.executable_module_count == 3
    assert finance_fraud.evaluation_gate_count == 5


def test_solution_blueprint_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root / "platform" / "intake" / "reports" / "use-case-blueprints-v1.yaml"
    )
    generated = build_solution_blueprint_snapshot(ai_root, generated_at="2026-06-17")

    assert checked_in["summary"] == generated["summary"]
    assert checked_in["action_queue"] == generated["action_queue"]
    assert checked_in["blueprints"] == generated["blueprints"]


def test_solution_blueprint_rejects_module_that_does_not_cover_use_case(
    tmp_path: Path,
) -> None:
    write_minimal_solution_blueprint_tree(tmp_path)

    with pytest.raises(RegistryValidationError, match="does not cover"):
        build_solution_blueprint_report(tmp_path)


def write_minimal_solution_blueprint_tree(root: Path) -> None:
    (root / "products").mkdir(parents=True)
    (root / "use-cases").mkdir(parents=True)
    (root / "platform" / "coverage").mkdir(parents=True)
    (root / "platform" / "intake").mkdir(parents=True)

    (root / "products" / "registry.yaml").write_text(
        """
version: 1
owner: ai-platform
platform_product: p1
products:
  - id: p1
    name: Product
    type: product
    status: candidate
    owner: product-owner
    ai_use_cases:
      - u1
""",
        encoding="utf-8",
    )
    (root / "use-cases" / "registry.yaml").write_text(
        """
version: 1
owner: ai-platform
platform_product: p1
use_cases:
  - id: u1
    name: Use Case
    status: proposed
    product: p1
""",
        encoding="utf-8",
    )
    (root / "platform" / "coverage" / "business-capability-coverage.yaml").write_text(
        """
version: 1
owner: ai-platform
coverage_statuses:
  - executable_gate
modules:
  - id: m1
    name: Module
    taxonomy_area: nlp_transformers
    coverage_status: executable_gate
    model_families:
      - nlp
    lms_use_cases: []
    enterprise_use_cases:
      - other-use-case
    evidence_artifacts: []
    evaluation_gate_ids:
      - gate-1
    business_capabilities:
      - semantic_understanding
""",
        encoding="utf-8",
    )
    (root / "platform" / "intake" / "use-case-requests.yaml").write_text(
        """
version: 1
owner: ai-platform
policy:
  allowed_statuses:
    - ready_for_solution_design
  allowed_priorities:
    - p1
  required_roles:
    - po_ba
    - sa_ai_platform
    - sa_ai_engineer
requests:
  - request_id: r1
    product: p1
    use_case_id: u1
    submitted_at: "2026-06-16"
    submitted_by: product-owner
    business_owner: product-owner
    priority: p1
    status: ready_for_solution_design
    objective: Ship a validated capability.
    target_modules:
      - m1
    requested_capabilities:
      - semantic_understanding
    expected_business_kpis:
      - cycle_time
    data_domains:
      - events
    constraints:
      - human_review
""",
        encoding="utf-8",
    )

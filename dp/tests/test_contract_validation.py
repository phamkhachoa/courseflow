from __future__ import annotations

from pathlib import Path

import yaml

from enterprise_dp.contracts import (
    ValidationResult,
    validate_contract_tree,
    validate_data_product_contract,
    validate_topic_contract,
)
from enterprise_dp.domains import validate_domain_registry
from enterprise_dp.products import validate_product_onboarding, validate_product_onboarding_tree
from enterprise_dp.products import scaffold_product_onboarding
from enterprise_dp.scope_guardrails import validate_scope_guardrails
from enterprise_dp.structure import validate_project_structure
from enterprise_dp.usecases import validate_use_case_registry


ROOT = Path(__file__).resolve().parents[1]


def test_repository_data_product_contracts_are_valid() -> None:
    result = validate_contract_tree(ROOT)

    assert result.errors == []
    assert result.checked_count >= 10
    for relative_path in (
        "contracts/topics/recommendation.tracking.v1.yaml",
        "contracts/data-products/bronze.events_recommendation_tracking.v1.yaml",
        "contracts/data-products/silver.learner_activity.v1.yaml",
        "contracts/data-products/gold.recsys_interactions.v1.yaml",
    ):
        assert (ROOT / relative_path).exists()


def test_repository_structure_is_enterprise_ready() -> None:
    result = validate_project_structure(ROOT)

    assert result.errors == []


def test_repository_product_onboarding_is_valid() -> None:
    result = validate_product_onboarding_tree(ROOT)

    assert result.errors == []
    assert result.checked_count >= 1


def test_repository_domain_registry_is_valid() -> None:
    result = validate_domain_registry(ROOT)

    assert result.errors == []
    assert result.checked_count == 1


def test_repository_use_case_registry_is_valid() -> None:
    result = validate_use_case_registry(ROOT)

    assert result.errors == []
    assert result.checked_count == 1


def test_repository_scope_guardrails_are_valid() -> None:
    result = validate_scope_guardrails(ROOT)

    assert result.errors == []
    assert result.checked_count >= 1


def test_gold_contract_requires_quality_gate() -> None:
    path = ROOT / "contracts" / "data-products" / "gold.recsys_interactions.v1.yaml"
    contract = yaml.safe_load(path.read_text())
    contract["serving"]["publicationGate"] = "manual_review_only"
    result = ValidationResult()

    validate_data_product_contract(path, contract, result)

    assert any("Gold data products must use publicationGate" in error for error in result.errors)


def test_pii_columns_require_contract_privacy_flag() -> None:
    path = ROOT / "contracts" / "data-products" / "silver.learner_activity.v1.yaml"
    contract = yaml.safe_load(path.read_text())
    contract["privacy"]["containsPii"] = False
    result = ValidationResult()

    validate_data_product_contract(path, contract, result)

    assert any("privacy.containsPii must be true" in error for error in result.errors)


def test_subject_key_columns_must_be_pii_tagged() -> None:
    path = ROOT / "contracts" / "data-products" / "gold.recsys_interactions.v1.yaml"
    contract = yaml.safe_load(path.read_text())
    for column in contract["schema"]["columns"]:
        if column["name"] == "learner_id_hash":
            column["pii"] = False
    result = ValidationResult()

    validate_data_product_contract(path, contract, result)

    assert any("privacy.subjectKeys[].column must reference pii=true columns" in error for error in result.errors)


def test_pii_bronze_raw_payload_must_be_pii_tagged() -> None:
    path = ROOT / "contracts" / "data-products" / "bronze.events_recommendation_tracking.v1.yaml"
    contract = yaml.safe_load(path.read_text())
    for column in contract["schema"]["columns"]:
        if column["name"] == "raw_payload":
            column["pii"] = False
    result = ValidationResult()

    validate_data_product_contract(path, contract, result)

    assert any("PII raw_payload columns must be tagged pii=true" in error for error in result.errors)


def test_topic_subject_key_path_must_exist_in_payload_schema() -> None:
    path = ROOT / "contracts" / "topics" / "recommendation.tracking.v1.yaml"
    contract = yaml.safe_load(path.read_text())
    contract["privacy"]["subjectKeys"][0]["topicPath"] = "$.payload.missingLearnerIdHash"
    result = ValidationResult()

    validate_topic_contract(ROOT, path, contract, result)

    assert any("topicPath does not exist in payload schema" in error for error in result.errors)


def test_data_product_contract_requires_enterprise_product_metadata() -> None:
    path = ROOT / "contracts" / "data-products" / "gold.recsys_interactions.v1.yaml"
    contract = yaml.safe_load(path.read_text())
    del contract["dataProduct"]["product"]
    result = ValidationResult()

    validate_data_product_contract(path, contract, result)

    assert any("product must be a non-empty string" in error for error in result.errors)


def test_bronze_event_contract_requires_platform_lineage_columns() -> None:
    path = ROOT / "contracts" / "data-products" / "bronze.events_recommendation_tracking.v1.yaml"
    contract = yaml.safe_load(path.read_text())
    contract["schema"]["columns"] = [
        column
        for column in contract["schema"]["columns"]
        if column["name"] != "schema_id"
    ]
    result = ValidationResult()

    validate_data_product_contract(path, contract, result)

    assert any("Bronze event data products must declare required platform columns" in error for error in result.errors)
    assert any("schema_id" in error for error in result.errors)


def test_topic_contract_filename_must_match_topic_name() -> None:
    path = ROOT / "contracts" / "topics" / "gradebook.final_grade.updated.v1.yaml"
    contract = yaml.safe_load(path.read_text())
    contract["topic"]["name"] = "gradebook.final-grade.updated.v1"
    result = ValidationResult()

    validate_topic_contract(ROOT, path, contract, result)

    assert any("topic contract filename must match topic.name" in error for error in result.errors)


def test_product_onboarding_requires_folder_matching_product_code() -> None:
    path = ROOT / "products" / "lms-courseflow" / "onboarding.yaml"
    onboarding = yaml.safe_load(path.read_text())
    onboarding["product"]["code"] = "another-product"
    result = ValidationResult()

    validate_product_onboarding(ROOT, path, onboarding, result)

    assert any("product.code must match product folder name" in error for error in result.errors)


def test_product_onboarding_requires_governance_controls() -> None:
    path = ROOT / "products" / "lms-courseflow" / "onboarding.yaml"
    onboarding = yaml.safe_load(path.read_text())
    del onboarding["governance"]
    result = ValidationResult()

    validate_product_onboarding(ROOT, path, onboarding, result)

    assert any("governance must be an object" in error for error in result.errors)


def test_product_onboarding_rejects_unknown_governance_references() -> None:
    path = ROOT / "products" / "lms-courseflow" / "onboarding.yaml"
    onboarding = yaml.safe_load(path.read_text())
    onboarding["governance"]["defaultAccessPersonas"] = ["MissingPersona"]
    onboarding["governance"]["consumerContract"] = "missing_contract"
    onboarding["governance"]["defaultRetentionPolicy"] = "missing_policy"
    onboarding["governance"]["releaseEvidenceProfile"] = "missing.v1"
    result = ValidationResult()

    validate_product_onboarding(ROOT, path, onboarding, result)

    assert any("references unknown persona" in error for error in result.errors)
    assert any("references unknown contract" in error for error in result.errors)
    assert any("references unknown policy" in error for error in result.errors)
    assert any("references unknown profile" in error for error in result.errors)


def test_product_onboarding_requires_existing_first_slice_contracts() -> None:
    path = ROOT / "products" / "lms-courseflow" / "onboarding.yaml"
    onboarding = yaml.safe_load(path.read_text())
    onboarding["firstSlice"]["topics"].append("missing.topic.v1")
    onboarding["firstSlice"]["dataProducts"].append("gold.missing_dataset")
    result = ValidationResult()

    validate_product_onboarding(ROOT, path, onboarding, result)

    assert any("topic contract does not exist" in error for error in result.errors)
    assert any("data product contract does not exist" in error for error in result.errors)


def test_planned_product_onboarding_allows_future_first_slice_contracts() -> None:
    path = ROOT / "products" / "lms-courseflow" / "onboarding.yaml"
    onboarding = yaml.safe_load(path.read_text())
    onboarding["firstSlice"]["contractStatus"] = "planned"
    onboarding["firstSlice"]["topics"] = ["learning.future_entity.changed.v1"]
    onboarding["firstSlice"]["dataProducts"] = ["bronze.events_future_entity_changed", "gold.future_entity_daily"]
    result = ValidationResult()

    validate_product_onboarding(ROOT, path, onboarding, result)

    assert result.errors == []


def test_product_scaffold_creates_planned_onboarding_pack(tmp_path: Path) -> None:
    output = scaffold_product_onboarding(
        tmp_path,
        product_code="crm-sales",
        name="CRM Sales",
        domains=["customer"],
        business_sponsor="customer-growth-lead",
        product_owner="crm-sales-po",
        technical_owner="crm-sales-sa",
    )
    onboarding_path = Path(output["onboarding_path"])
    onboarding = yaml.safe_load(onboarding_path.read_text(encoding="utf-8"))
    result = ValidationResult()

    validate_product_onboarding(tmp_path, onboarding_path, onboarding, result)

    assert result.errors == []
    assert onboarding["product"]["code"] == "crm-sales"
    assert onboarding["governance"]["consumerContract"] == "catalog_registered_access_request_required"
    assert onboarding["firstSlice"]["contractStatus"] == "planned"
    assert Path(output["readme_path"]).is_file()
    assert Path(output["domain_readme_path"]).is_file()
    assert Path(output["use_case_readme_path"]).is_file()


def test_product_onboarding_rejects_orphan_contract_products_and_domains(tmp_path: Path) -> None:
    products_dir = tmp_path / "products" / "example-product"
    topics_dir = tmp_path / "contracts" / "topics"
    data_products_dir = tmp_path / "contracts" / "data-products"
    domains_dir = tmp_path / "domains"
    products_dir.mkdir(parents=True)
    topics_dir.mkdir(parents=True)
    data_products_dir.mkdir(parents=True)
    domains_dir.mkdir(parents=True)
    (domains_dir / "registry.yaml").write_text(
        """
domains:
  - code: finance
""".lstrip(),
        encoding="utf-8",
    )
    (products_dir / "onboarding.yaml").write_text(
        """
product:
  code: example-product
  name: Example Product
  status: pilot
  businessSponsor: sponsor
  productOwner: po
  technicalOwner: sa
  dataSteward: steward
  defaultDataResidency: REGION_CONTROLLED
  tenantModel:
    enterpriseTenantKey: tenant_id
    productOrgKey: org_id
domains:
  - finance
sourceSystems:
  - domain: finance
    services: [billing-service]
    publicationModes: [transactional_outbox]
firstSlice:
  topics: [example.changed.v1]
  dataProducts: [bronze.events_example_changed]
consumers: [BI]
""".lstrip(),
        encoding="utf-8",
    )
    (topics_dir / "example.changed.v1.yaml").write_text(
        """
topic:
  name: example.changed.v1
  product: example-product
  domain: finance
""".lstrip(),
        encoding="utf-8",
    )
    (data_products_dir / "bronze.events_example_changed.v1.yaml").write_text(
        """
dataProduct:
  name: bronze.events_example_changed
  product: example-product
  domain: finance
""".lstrip(),
        encoding="utf-8",
    )
    (topics_dir / "orphan.changed.v1.yaml").write_text(
        """
topic:
  name: orphan.changed.v1
  product: unknown-product
  domain: finance
""".lstrip(),
        encoding="utf-8",
    )
    (data_products_dir / "bronze.events_customer_changed.v1.yaml").write_text(
        """
dataProduct:
  name: bronze.events_customer_changed
  product: example-product
  domain: customer
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_product_onboarding_tree(tmp_path)

    assert any("must have products/unknown-product/onboarding.yaml" in error for error in result.errors)
    assert any("domain 'customer' must be listed in domains/registry.yaml" in error for error in result.errors)


def test_domain_registry_requires_domain_readme(tmp_path: Path) -> None:
    root = tmp_path
    registry_dir = root / "domains"
    registry_dir.mkdir()
    (root / "products" / "lms-courseflow").mkdir(parents=True)
    (root / "products" / "lms-courseflow" / "onboarding.yaml").write_text("product: {}\n")
    (registry_dir / "registry.yaml").write_text(
        """
version: 1
registry_scope: test
first_product_pilot: lms-courseflow
domains:
  - code: missing-domain
    name: Missing Domain
    status: planned
    business_capability: Missing domain capability.
    first_data_products:
      - gold.missing_daily
    first_consumers:
      - enterprise-reporting
    pilot_product_contribution: None yet.
    future_onboarding_products:
      - future-product
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_domain_registry(root)

    assert any("must have domains/missing-domain/README.md" in error for error in result.errors)


def test_scope_guardrail_rejects_unreviewed_product_identity_in_platform(tmp_path: Path) -> None:
    (tmp_path / "governance").mkdir()
    (tmp_path / "platform").mkdir()
    (tmp_path / "governance" / "scope-guardrails.yaml").write_text(
        """
version: 1
policy:
  protected_paths:
    - platform/**
guardrails:
  - id: no_pilot_identity
    status: active
    owner: enterprise-data-platform-architect
    severity: error
    rationale: Product pilot identity must not leak into shared platform areas.
    patterns:
      - '(?i)\\bcourseflow\\b'
    allowed_paths:
      - platform/explicit-pilot-note.md
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "platform" / "README.md").write_text(
        "This shared platform depends on CourseFlow internals.\n",
        encoding="utf-8",
    )
    (tmp_path / "platform" / "explicit-pilot-note.md").write_text(
        "CourseFlow is intentionally referenced here as a pilot note.\n",
        encoding="utf-8",
    )

    result = validate_scope_guardrails(tmp_path)

    assert any("scope guardrail no_pilot_identity" in error for error in result.errors)
    assert any("platform/README.md" in error for error in result.errors)
    assert all("explicit-pilot-note" not in error for error in result.errors)


def test_use_case_registry_rejects_unknown_domain_and_missing_existing_contract(tmp_path: Path) -> None:
    (tmp_path / "domains").mkdir()
    (tmp_path / "products" / "example-product").mkdir(parents=True)
    (tmp_path / "contracts" / "data-products").mkdir(parents=True)
    (tmp_path / "domains" / "registry.yaml").write_text(
        """
domains:
  - code: finance
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "products" / "example-product" / "onboarding.yaml").write_text(
        """
product:
  code: example-product
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "use-cases").mkdir()
    (tmp_path / "use-cases" / "registry.yaml").write_text(
        """
version: 1
portfolio_scope: test
useCases:
  - id: bad-use-case
    name: Bad Use Case
    domain: unknown-domain
    priority: P0
    status: planned
    owner: owner
    businessOutcome: outcome
    primaryConsumers: [finance]
    sourceProducts: [example-product]
    sourceSystems: [billing-service]
    dataProducts:
      - name: gold.missing_existing
        layer: GOLD
        contractStatus: existing
    kpis: [metric_one]
    accessPersonas: [ApprovedBIConsumer]
    governance:
      classification: CONFIDENTIAL
      dataResidency: REGION_CONTROLLED
      containsPii: true
      tenantIsolation: REQUIRED
    platformCapabilities: [catalog]
    releaseGates: [quality_checks_must_pass]
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_use_case_registry(tmp_path)

    assert any("domain must be listed in domains/registry.yaml" in error for error in result.errors)
    assert any("contractStatus=existing but contract does not exist" in error for error in result.errors)


def test_use_case_registry_rejects_unregistered_pipeline_runner(tmp_path: Path) -> None:
    (tmp_path / "domains").mkdir()
    (tmp_path / "products" / "example-product").mkdir(parents=True)
    (tmp_path / "contracts" / "data-products").mkdir(parents=True)
    (tmp_path / "domains" / "registry.yaml").write_text(
        """
domains:
  - code: finance
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "products" / "example-product" / "onboarding.yaml").write_text(
        """
product:
  code: example-product
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "use-cases").mkdir()
    (tmp_path / "use-cases" / "registry.yaml").write_text(
        """
version: 1
portfolio_scope: test
useCases:
  - id: bad-runner
    name: Bad Runner
    domain: finance
    priority: P0
    status: planned
    owner: owner
    businessOutcome: outcome
    primaryConsumers: [finance]
    sourceProducts: [example-product]
    sourceSystems: [billing-service]
    dataProducts:
      - name: gold.future_metric
        layer: GOLD
        contractStatus: planned
    kpis: [metric_one]
    accessPersonas: [ApprovedBIConsumer]
    governance:
      classification: CONFIDENTIAL
      dataResidency: REGION_CONTROLLED
      containsPii: true
      tenantIsolation: REQUIRED
    platformCapabilities: [catalog]
    pipelineRunners: [missing.runner.v1]
    releaseGates: [quality_checks_must_pass]
""".lstrip(),
        encoding="utf-8",
    )

    result = validate_use_case_registry(tmp_path)

    assert any("pipelineRunners contains unregistered runner" in error for error in result.errors)

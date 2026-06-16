from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import yaml


VALID_LAYERS = {"BRONZE", "SILVER", "GOLD"}
VALID_STATUSES = {"DRAFT", "ACTIVE", "DEPRECATED"}
VALID_CLASSIFICATIONS = {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "PII", "SENSITIVE"}
VALID_INGESTION_MODES = {"streaming", "batch", "cdc", "manual"}
VALID_COLUMN_TYPES = {
    "boolean",
    "date",
    "decimal",
    "double",
    "int",
    "json",
    "long",
    "string",
    "timestamp",
    "uuid",
}
VALID_CHECK_TYPES = {
    "accepted_values",
    "expression",
    "freshness",
    "not_null",
    "no_sensitive_payload",
    "unique",
    "volume",
}
VALID_SCHEMA_FORMATS = {"JSON_SCHEMA", "AVRO", "PROTOBUF"}
VALID_COMPATIBILITY_MODES = {"BACKWARD", "BACKWARD_TRANSITIVE", "FULL", "FULL_TRANSITIVE"}
VALID_ERASURE_MODES = {"NONE", "SUBJECT_DELETE", "REGULATED_SUBJECT_DELETE"}
VALID_LEGAL_HOLD_POLICIES = {"none", "standard_legal_hold_check", "regulated_legal_hold_check"}
VALID_RAW_PAYLOAD_POLICIES = {
    "NO_RAW_PAYLOAD",
    "NON_PERSONAL_RAW_PAYLOAD",
    "SECURE_RAW_PAYLOAD_WITH_SUBJECT_ERASURE",
}
VALID_SUBJECT_KEY_TYPES = {"tokenized_subject_id", "natural_subject_id", "organization_subject_id"}
BRONZE_EVENT_REQUIRED_COLUMNS = {
    "product_id",
    "domain_id",
    "event_id",
    "event_type",
    "event_version",
    "source_service",
    "tenant_id",
    "occurred_at",
    "published_at",
    "ingested_at",
    "source_system",
    "source_topic",
    "source_partition",
    "source_offset",
    "source_snapshot_id",
    "source_record_key",
    "source_record_hash_sha256",
    "payload_hash_sha256",
    "schema_subject",
    "schema_id",
    "raw_headers",
    "raw_payload",
    "ingest_run_id",
    "event_date",
    "ingest_date",
}
DATA_PRODUCT_NAME = re.compile(r"^(bronze|silver|gold)\.[a-z][a-z0-9_]*$")
COLUMN_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
PRODUCT_CODE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
TOPIC_NAME = re.compile(r"^[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)*\.v[0-9]+$")


@dataclass
class ValidationResult:
    checked_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, path: Path, message: str) -> None:
        self.errors.append(f"{path}: {message}")

    def warn(self, path: Path, message: str) -> None:
        self.warnings.append(f"{path}: {message}")

    def extend(self, other: ValidationResult) -> None:
        self.checked_count += other.checked_count
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def validate_contract_tree(root: Path) -> ValidationResult:
    result = ValidationResult()
    data_products = root / "contracts" / "data-products"
    topics = root / "contracts" / "topics"
    if not data_products.exists():
        result.error(data_products, "contracts/data-products directory is required")
    if not topics.exists():
        result.error(topics, "contracts/topics directory is required")
    if result.errors:
        return result

    data_product_files = sorted(data_products.glob("*.yaml"))
    topic_files = sorted(topics.glob("*.yaml"))
    if not data_product_files:
        result.error(data_products, "at least one data product contract is required")
    if not topic_files:
        result.error(topics, "at least one topic contract is required")
    if result.errors:
        return result

    for path in data_product_files:
        result.checked_count += 1
        validate_data_product_contract(path, load_yaml(path), result, root=root)
    for path in topic_files:
        result.checked_count += 1
        validate_topic_contract(root, path, load_yaml(path), result)
    return result


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML object")
    return data


def validate_data_product_contract(
    path: Path,
    contract: dict[str, Any],
    result: ValidationResult,
    root: Path | None = None,
) -> None:
    contract_version = require_int(path, result, contract, "contractVersion", minimum=1)
    product = require_mapping(path, result, contract, "dataProduct")
    source = require_mapping(path, result, contract, "source")
    schema = require_mapping(path, result, contract, "schema")
    quality = require_mapping(path, result, contract, "quality")
    privacy = require_mapping(path, result, contract, "privacy")
    serving = require_mapping(path, result, contract, "serving")
    lineage = require_mapping(path, result, contract, "lineage")

    if not all([product, source, schema, quality, privacy, serving, lineage]):
        return

    name = require_string(path, result, product, "name")
    layer = require_string(path, result, product, "layer")
    if name and not DATA_PRODUCT_NAME.fullmatch(name):
        result.error(path, "dataProduct.name must look like bronze|silver|gold.dataset_name")
    if layer and layer not in VALID_LAYERS:
        result.error(path, f"dataProduct.layer must be one of {sorted(VALID_LAYERS)}")
    if name and layer and not name.startswith(f"{layer.lower()}."):
        result.error(path, "dataProduct.layer must match the dataset name prefix")
    if name and contract_version and path.name != f"{name}.v{contract_version}.yaml":
        result.error(path, "data product contract filename must match dataProduct.name and contractVersion")

    product_code = require_string(path, result, product, "product")
    if product_code and not PRODUCT_CODE.fullmatch(product_code):
        result.error(path, "dataProduct.product must be a product code like example-product")
    for key in (
        "domain",
        "domainOwner",
        "ownerTeam",
        "businessOwner",
        "technicalOwner",
        "dataSteward",
        "description",
        "deprecationPolicy",
    ):
        require_string(path, result, product, key)
    status = require_string(path, result, product, "status")
    if status and status not in VALID_STATUSES:
        result.error(path, f"dataProduct.status must be one of {sorted(VALID_STATUSES)}")

    validate_source(path, result, source, layer)
    contains_pii = validate_privacy(path, result, privacy)
    validate_schema(path, result, schema, contains_pii)
    validate_schema_privacy_controls(path, result, schema, privacy, contains_pii)
    validate_bronze_event_columns(path, result, product, schema)
    validate_quality(path, result, quality, layer)
    validate_serving(path, result, serving, layer)
    if root is not None:
        validate_access_policy_contract_reference(root, path, result, product, privacy, serving, schema)
        validate_retention_contract_reference(root, path, result, product, privacy, artifact_type="data_product")
    validate_lineage(path, result, lineage)


def validate_access_policy_contract_reference(
    root: Path,
    path: Path,
    result: ValidationResult,
    product: dict[str, Any],
    privacy: dict[str, Any],
    serving: dict[str, Any],
    schema: dict[str, Any],
) -> None:
    from enterprise_df.access_policies import evaluate_access_policy_contract
    from enterprise_df.access_governance import evaluate_consumer_contract_reference

    policy_id = serving.get("accessPolicy")
    try:
        evaluation = evaluate_access_policy_contract(
            root,
            data_product_name=str(product.get("name")),
            layer=str(product.get("layer")),
            privacy=privacy,
            serving=serving,
            columns=[column for column in schema.get("columns", []) if isinstance(column, dict)],
        )
    except KeyError:
        result.error(path, f"serving.accessPolicy references unregistered policy {policy_id!r}")
        return
    if not evaluation.get("passed"):
        failed = [
            check.get("name")
            for check in evaluation.get("checks", [])
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        result.error(path, f"serving.accessPolicy {policy_id!r} failed policy checks: {failed}")

    consumer_contract_id = serving.get("consumerContract")
    try:
        contract_evaluation = evaluate_consumer_contract_reference(
            root,
            data_product_name=str(product.get("name")),
            layer=str(product.get("layer")),
            privacy=privacy,
            serving=serving,
        )
    except KeyError:
        result.error(path, f"serving.consumerContract references unregistered contract {consumer_contract_id!r}")
        return
    if not contract_evaluation.get("passed"):
        failed = [
            check.get("name")
            for check in contract_evaluation.get("checks", [])
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        result.error(path, f"serving.consumerContract {consumer_contract_id!r} failed contract checks: {failed}")


def validate_retention_contract_reference(
    root: Path,
    path: Path,
    result: ValidationResult,
    artifact: dict[str, Any],
    privacy: dict[str, Any],
    *,
    artifact_type: str,
) -> None:
    from enterprise_df.retention import evaluate_retention_contract

    artifact_name = str(artifact.get("name"))
    try:
        evaluation = evaluate_retention_contract(
            root,
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            layer=str(artifact.get("layer") or "BRONZE"),
            domain=str(artifact.get("domain")),
            product=str(artifact.get("product")),
            privacy=privacy,
        )
    except KeyError as exc:
        result.error(path, f"privacy retention policy could not be resolved for {artifact_name!r}: {exc}")
        return
    if not evaluation.get("passed"):
        failed = [
            check.get("name")
            for check in evaluation.get("checks", [])
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        result.error(path, f"privacy retention policy {evaluation.get('policy_id')!r} failed checks: {failed}")


def validate_source(
    path: Path,
    result: ValidationResult,
    source: dict[str, Any],
    layer: str | None,
) -> None:
    upstream = source.get("upstream")
    if not isinstance(upstream, list):
        result.error(path, "source.upstream must be a list")
    elif layer in {"SILVER", "GOLD"} and not upstream:
        result.error(path, "source.upstream is required for Silver and Gold products")
    elif upstream:
        for index, item in enumerate(upstream):
            if not isinstance(item, dict):
                result.error(path, f"source.upstream[{index}] must be an object")
                continue
            upstream_name = require_string(path, result, item, "name", f"source.upstream[{index}]")
            require_string(path, result, item, "type", f"source.upstream[{index}]")
            if upstream_name and not DATA_PRODUCT_NAME.fullmatch(upstream_name):
                result.error(path, f"source.upstream[{index}].name is not a data product name")

    ingestion_mode = require_string(path, result, source, "ingestionMode")
    if ingestion_mode and ingestion_mode not in VALID_INGESTION_MODES:
        result.error(path, f"source.ingestionMode must be one of {sorted(VALID_INGESTION_MODES)}")
    require_string(path, result, source, "eventTimeColumn")


def validate_schema(
    path: Path,
    result: ValidationResult,
    schema: dict[str, Any],
    contains_pii: bool,
) -> None:
    columns = schema.get("columns")
    if not isinstance(columns, list) or not columns:
        result.error(path, "schema.columns must be a non-empty list")
        return

    seen: set[str] = set()
    has_pii_column = False
    for index, column in enumerate(columns):
        prefix = f"schema.columns[{index}]"
        if not isinstance(column, dict):
            result.error(path, f"{prefix} must be an object")
            continue
        name = require_string(path, result, column, "name", prefix)
        column_type = require_string(path, result, column, "type", prefix)
        if name:
            if not COLUMN_NAME.fullmatch(name):
                result.error(path, f"{prefix}.name must be snake_case")
            if name in seen:
                result.error(path, f"{prefix}.name duplicates column {name}")
            seen.add(name)
        if column_type and column_type not in VALID_COLUMN_TYPES:
            result.error(path, f"{prefix}.type must be one of {sorted(VALID_COLUMN_TYPES)}")
        require_bool(path, result, column, "nullable", prefix)
        pii = require_bool(path, result, column, "pii", prefix)
        if pii is True:
            has_pii_column = True
        require_string(path, result, column, "description", prefix)

    if has_pii_column and not contains_pii:
        result.error(path, "privacy.containsPii must be true when any schema column is pii=true")
    if contains_pii and not has_pii_column:
        result.warn(path, "privacy.containsPii=true but no column is marked pii=true")


def validate_bronze_event_columns(
    path: Path,
    result: ValidationResult,
    product: dict[str, Any],
    schema: dict[str, Any],
) -> None:
    name = product.get("name")
    layer = product.get("layer")
    if layer != "BRONZE" or not isinstance(name, str) or not name.startswith("bronze.events_"):
        return
    columns = schema.get("columns")
    if not isinstance(columns, list):
        return
    column_names = {
        column.get("name")
        for column in columns
        if isinstance(column, dict) and isinstance(column.get("name"), str)
    }
    missing = sorted(BRONZE_EVENT_REQUIRED_COLUMNS - column_names)
    if missing:
        result.error(path, f"Bronze event data products must declare required platform columns: {missing}")


def validate_schema_privacy_controls(
    path: Path,
    result: ValidationResult,
    schema: dict[str, Any],
    privacy: dict[str, Any],
    contains_pii: bool,
) -> None:
    columns = schema.get("columns")
    if not isinstance(columns, list):
        return
    column_names = {
        column.get("name")
        for column in columns
        if isinstance(column, dict) and isinstance(column.get("name"), str)
    }
    subject_keys = subject_key_specs(privacy)
    normalized_subject_keys = [
        spec.get("column")
        for spec in subject_keys
        if isinstance(spec.get("column"), str)
    ]
    missing_subject_keys = sorted(set(normalized_subject_keys) - column_names)
    if missing_subject_keys:
        result.error(path, f"privacy.subjectKeys[].column must exist in schema.columns: {missing_subject_keys}")
    pii_by_column = {
        column.get("name"): column.get("pii")
        for column in columns
        if isinstance(column, dict) and isinstance(column.get("name"), str)
    }
    untagged_subject_keys = sorted(
        column
        for column in normalized_subject_keys
        if pii_by_column.get(column) is not True
    )
    if untagged_subject_keys:
        result.error(path, f"privacy.subjectKeys[].column must reference pii=true columns: {untagged_subject_keys}")
    has_raw_payload = "raw_payload" in column_names
    raw_payload_policy = privacy.get("rawPayloadPolicy")
    if has_raw_payload and contains_pii and raw_payload_policy != "SECURE_RAW_PAYLOAD_WITH_SUBJECT_ERASURE":
        result.error(path, "PII raw_payload columns require rawPayloadPolicy=SECURE_RAW_PAYLOAD_WITH_SUBJECT_ERASURE")
    if has_raw_payload and contains_pii and pii_by_column.get("raw_payload") is not True:
        result.error(path, "PII raw_payload columns must be tagged pii=true")
    if has_raw_payload and not contains_pii and raw_payload_policy != "NON_PERSONAL_RAW_PAYLOAD":
        result.error(path, "non-PII raw_payload columns require rawPayloadPolicy=NON_PERSONAL_RAW_PAYLOAD")
    if not has_raw_payload and raw_payload_policy != "NO_RAW_PAYLOAD":
        result.error(path, "datasets without raw_payload require rawPayloadPolicy=NO_RAW_PAYLOAD")


def validate_quality(
    path: Path,
    result: ValidationResult,
    quality: dict[str, Any],
    layer: str | None,
) -> None:
    require_int(path, result, quality, "freshnessSloMinutes", minimum=1)
    checks = quality.get("checks")
    if not isinstance(checks, list) or not checks:
        result.error(path, "quality.checks must be a non-empty list")
        return
    for index, check in enumerate(checks):
        prefix = f"quality.checks[{index}]"
        if not isinstance(check, dict):
            result.error(path, f"{prefix} must be an object")
            continue
        require_string(path, result, check, "name", prefix)
        check_type = require_string(path, result, check, "type", prefix)
        if check_type and check_type not in VALID_CHECK_TYPES:
            result.error(path, f"{prefix}.type must be one of {sorted(VALID_CHECK_TYPES)}")
    if layer == "GOLD" and not any(check.get("type") == "freshness" for check in checks if isinstance(check, dict)):
        result.error(path, "Gold data products must define a freshness quality check")


def validate_privacy(path: Path, result: ValidationResult, privacy: dict[str, Any]) -> bool:
    classification = require_string(path, result, privacy, "classification")
    if classification and classification not in VALID_CLASSIFICATIONS:
        result.error(path, f"privacy.classification must be one of {sorted(VALID_CLASSIFICATIONS)}")
    contains_pii = require_bool(path, result, privacy, "containsPii")
    tenant_isolation = require_string(path, result, privacy, "tenantIsolation")
    require_string(path, result, privacy, "dataResidency")
    require_int(path, result, privacy, "retentionDays", minimum=1)
    erasure_supported = require_bool(path, result, privacy, "erasureSupported")
    subject_keys = validate_subject_key_specs(path, result, privacy)
    erasure_mode = require_string(path, result, privacy, "erasureMode")
    if erasure_mode and erasure_mode not in VALID_ERASURE_MODES:
        result.error(path, f"privacy.erasureMode must be one of {sorted(VALID_ERASURE_MODES)}")
    legal_hold_policy = require_string(path, result, privacy, "legalHoldPolicy")
    if legal_hold_policy and legal_hold_policy not in VALID_LEGAL_HOLD_POLICIES:
        result.error(path, f"privacy.legalHoldPolicy must be one of {sorted(VALID_LEGAL_HOLD_POLICIES)}")
    raw_payload_policy = require_string(path, result, privacy, "rawPayloadPolicy")
    if raw_payload_policy and raw_payload_policy not in VALID_RAW_PAYLOAD_POLICIES:
        result.error(path, f"privacy.rawPayloadPolicy must be one of {sorted(VALID_RAW_PAYLOAD_POLICIES)}")
    if contains_pii and tenant_isolation != "REQUIRED":
        result.error(path, "privacy.tenantIsolation must be REQUIRED when containsPii=true")
    if contains_pii and not subject_keys:
        result.error(path, "privacy.subjectKeys must be non-empty when containsPii=true")
    if not contains_pii and subject_keys:
        result.error(path, "privacy.subjectKeys must be empty when containsPii=false")
    if contains_pii and erasure_supported is True and erasure_mode == "NONE":
        result.error(path, "privacy.erasureMode cannot be NONE when PII erasure is supported")
    if not contains_pii and erasure_mode != "NONE":
        result.error(path, "privacy.erasureMode must be NONE when containsPii=false")
    if erasure_mode == "REGULATED_SUBJECT_DELETE" and legal_hold_policy != "regulated_legal_hold_check":
        result.error(path, "REGULATED_SUBJECT_DELETE requires legalHoldPolicy=regulated_legal_hold_check")
    if erasure_mode == "SUBJECT_DELETE" and legal_hold_policy == "none":
        result.error(path, "SUBJECT_DELETE requires a legal hold check policy")
    return contains_pii is True


def validate_subject_key_specs(path: Path, result: ValidationResult, privacy: dict[str, Any]) -> list[dict[str, Any]]:
    subject_keys_value = privacy.get("subjectKeys")
    if not isinstance(subject_keys_value, list):
        result.error(path, "privacy.subjectKeys must be a list")
        return []
    specs: list[dict[str, Any]] = []
    for index, item in enumerate(subject_keys_value):
        prefix = f"privacy.subjectKeys[{index}]"
        if not isinstance(item, dict):
            result.error(path, f"{prefix} must be an object")
            continue
        name = require_string(path, result, item, "name", prefix)
        if name and not COLUMN_NAME.fullmatch(name):
            result.error(path, f"{prefix}.name must be snake_case")
        subject_type = require_string(path, result, item, "type", prefix)
        if subject_type and subject_type not in VALID_SUBJECT_KEY_TYPES:
            result.error(path, f"{prefix}.type must be one of {sorted(VALID_SUBJECT_KEY_TYPES)}")
        require_bool(path, result, item, "required", prefix)
        column = item.get("column")
        topic_path = item.get("topicPath")
        if column is not None:
            if not isinstance(column, str) or not COLUMN_NAME.fullmatch(column):
                result.error(path, f"{prefix}.column must be a snake_case column name")
        if topic_path is not None:
            if not isinstance(topic_path, str) or not topic_path.startswith("$.payload."):
                result.error(path, f"{prefix}.topicPath must start with $.payload.")
        if column is None and topic_path is None:
            result.error(path, f"{prefix} must declare column or topicPath")
        specs.append(item)
    return specs


def subject_key_specs(privacy: dict[str, Any]) -> list[dict[str, Any]]:
    value = privacy.get("subjectKeys")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def validate_topic_subject_keys(
    root: Path,
    path: Path,
    result: ValidationResult,
    schema: dict[str, Any],
    privacy: dict[str, Any],
) -> None:
    specs = subject_key_specs(privacy)
    if not specs:
        return
    payload_schema_ref = schema.get("payloadSchema")
    if not isinstance(payload_schema_ref, str):
        return
    payload_schema_path = root / payload_schema_ref
    if not payload_schema_path.is_file():
        return
    try:
        import json

        payload_schema = json.loads(payload_schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    properties = payload_schema.get("properties")
    if not isinstance(properties, dict):
        return
    for index, spec in enumerate(specs):
        topic_path = spec.get("topicPath")
        if not isinstance(topic_path, str):
            result.error(path, f"privacy.subjectKeys[{index}].topicPath is required for topic contracts")
            continue
        field_name = topic_path.removeprefix("$.payload.")
        if not field_name or "." in field_name:
            result.error(path, f"privacy.subjectKeys[{index}].topicPath must point to a top-level payload field")
        elif field_name not in properties:
            result.error(path, f"privacy.subjectKeys[{index}].topicPath does not exist in payload schema properties: {topic_path}")


def validate_serving(path: Path, result: ValidationResult, serving: dict[str, Any], layer: str | None) -> None:
    consumers = serving.get("consumers")
    if not isinstance(consumers, list) or not consumers:
        result.error(path, "serving.consumers must be a non-empty list")
    elif not all(isinstance(consumer, str) and consumer.strip() for consumer in consumers):
        result.error(path, "serving.consumers must contain non-empty strings")
    require_string(path, result, serving, "accessPolicy")
    require_string(path, result, serving, "consumerContract")
    require_string_list(path, result, serving, "accessPersonas")
    publication_gate = require_string(path, result, serving, "publicationGate")
    if layer == "GOLD" and publication_gate != "quality_checks_must_pass":
        result.error(path, "Gold data products must use publicationGate=quality_checks_must_pass")


def validate_lineage(path: Path, result: ValidationResult, lineage: dict[str, Any]) -> None:
    require_string(path, result, lineage, "catalog")
    require_bool(path, result, lineage, "lineageRequired")


def validate_topic_contract(
    root: Path,
    path: Path,
    contract: dict[str, Any],
    result: ValidationResult,
) -> None:
    contract_version = require_int(path, result, contract, "contractVersion", minimum=1)
    topic = require_mapping(path, result, contract, "topic")
    schema = require_mapping(path, result, contract, "schema")
    privacy = require_mapping(path, result, contract, "privacy")
    ingestion = require_mapping(path, result, contract, "ingestion")
    quality = require_mapping(path, result, contract, "quality")
    if not all([topic, schema, privacy, ingestion, quality]):
        return

    name = require_string(path, result, topic, "name")
    if name and not TOPIC_NAME.fullmatch(name):
        result.error(path, "topic.name must be a versioned topic like domain.entity.event.v1")
    if name and contract_version:
        if path.name != f"{name}.yaml":
            result.error(path, "topic contract filename must match topic.name")
        if not name.endswith(f".v{contract_version}"):
            result.error(path, "topic.name version suffix must match contractVersion")
    product_code = require_string(path, result, topic, "product")
    if product_code and not PRODUCT_CODE.fullmatch(product_code):
        result.error(path, "topic.product must be a product code like example-product")
    for key in ("domain", "domainOwner", "ownerTeam", "dataSteward", "description"):
        require_string(path, result, topic, key)
    status = require_string(path, result, topic, "status")
    if status and status not in VALID_STATUSES:
        result.error(path, f"topic.status must be one of {sorted(VALID_STATUSES)}")
    source_services = topic.get("sourceServices")
    if not isinstance(source_services, list) or not source_services:
        result.error(path, "topic.sourceServices must be a non-empty list")

    schema_format = require_string(path, result, schema, "format")
    if schema_format and schema_format not in VALID_SCHEMA_FORMATS:
        result.error(path, f"schema.format must be one of {sorted(VALID_SCHEMA_FORMATS)}")
    compatibility = require_string(path, result, schema, "compatibility")
    if compatibility and compatibility not in VALID_COMPATIBILITY_MODES:
        result.error(path, f"schema.compatibility must be one of {sorted(VALID_COMPATIBILITY_MODES)}")
    for key in ("envelopeSchema", "payloadSchema"):
        relative = require_string(path, result, schema, key)
        if relative:
            schema_path = root / relative
            if not schema_path.exists():
                result.error(path, f"schema.{key} file does not exist: {relative}")
            elif schema_path.suffix == ".json":
                validate_json_file(schema_path, result, path)

    validate_privacy(path, result, privacy)
    validate_topic_subject_keys(root, path, result, schema, privacy)
    validate_retention_contract_reference(root, path, result, topic, privacy, artifact_type="topic")
    bronze_target = require_string(path, result, ingestion, "bronzeTarget")
    if bronze_target and not DATA_PRODUCT_NAME.fullmatch(bronze_target):
        result.error(path, "ingestion.bronzeTarget must point to a Bronze data product")
    require_string(path, result, ingestion, "partitionStrategy")
    validate_quality(path, result, quality, "BRONZE")


def validate_json_file(schema_path: Path, result: ValidationResult, contract_path: Path) -> None:
    import json

    try:
        json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.error(contract_path, f"{schema_path} is not valid JSON: {exc.msg}")


def require_mapping(
    path: Path,
    result: ValidationResult,
    mapping: dict[str, Any],
    key: str,
) -> dict[str, Any] | None:
    value = mapping.get(key)
    if not isinstance(value, dict):
        result.error(path, f"{key} must be an object")
        return None
    return value


def require_string(
    path: Path,
    result: ValidationResult,
    mapping: dict[str, Any],
    key: str,
    prefix: str | None = None,
) -> str | None:
    value = mapping.get(key)
    field = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, str) or not value.strip():
        result.error(path, f"{field} must be a non-empty string")
        return None
    return value.strip()


def require_bool(
    path: Path,
    result: ValidationResult,
    mapping: dict[str, Any],
    key: str,
    prefix: str | None = None,
) -> bool | None:
    value = mapping.get(key)
    field = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, bool):
        result.error(path, f"{field} must be a boolean")
        return None
    return value


def require_string_list(
    path: Path,
    result: ValidationResult,
    mapping: dict[str, Any],
    key: str,
    prefix: str | None = None,
) -> list[str] | None:
    value = mapping.get(key)
    field = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, list) or not value:
        result.error(path, f"{field} must be a non-empty list")
        return None
    if not all(isinstance(item, str) and item.strip() for item in value):
        result.error(path, f"{field} must contain non-empty strings")
        return None
    return [item.strip() for item in value]


def require_int(
    path: Path,
    result: ValidationResult,
    mapping: dict[str, Any],
    key: str,
    minimum: int,
    prefix: str | None = None,
) -> int | None:
    value = mapping.get(key)
    field = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, int):
        result.error(path, f"{field} must be an integer")
        return None
    if value < minimum:
        result.error(path, f"{field} must be >= {minimum}")
    return value

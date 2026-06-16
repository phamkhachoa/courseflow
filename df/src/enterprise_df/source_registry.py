from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_df.contracts import (
    DATA_PRODUCT_NAME,
    PRODUCT_CODE,
    TOPIC_NAME,
    VALID_COMPATIBILITY_MODES,
    ValidationResult,
    load_yaml,
    require_bool,
    require_int,
    require_mapping,
    require_string,
    require_string_list,
)
from enterprise_df.products import load_enterprise_domain_codes


VALID_PRIORITIES = {"P0", "P1", "P2"}
VALID_STATUSES = {"planned", "mapped_gap", "pilot", "production_ready", "active", "deprecated"}
VALID_SOURCE_TYPES = {"transactional_outbox", "cdc", "http_event_collector", "batch_connector", "saas_connector"}
VALID_BRIDGE_MODES = {
    "direct_canonical",
    "producer_dual_publish_or_normalizer",
    "collector_to_canonical_topic",
    "cdc_to_canonical_topic",
    "batch_to_canonical_topic",
}
VALID_BRIDGE_STATUSES = {"planned", "local_preflight", "ready", "active", "deprecated"}
VALID_PII_HANDLING = {
    "non_personal_payload_verified",
    "tokenized_before_bronze",
    "masked_before_bronze",
    "encrypted_raw_with_subject_erasure",
}
VALID_TENANT_MAPPING = {"org_id_required", "tenant_id_required", "aggregate_only", "not_required"}
VALID_SUBJECT_KEY_STRATEGIES = {"none", "tokenized_subject_id", "organization_subject_id", "natural_subject_id"}
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}
SUPPORTED_ENVIRONMENTS = {"local", "staging", "prod"}
LOCAL_SCHEMA_REGISTRY_URI = "local-json-schema-registry-preflight"
REPORT_VERSION = 1


@dataclass(frozen=True)
class SourceReadinessResult:
    output_path: Path
    report: dict[str, Any]


def validate_source_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = root / "platform" / "ingestion" / "source-registry.yaml"
    if not registry_path.is_file():
        result.error(registry_path, "platform/ingestion/source-registry.yaml is required")
        return result

    registry = load_yaml(registry_path)
    result.checked_count += 1
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "registryScope")
    require_string(registry_path, result, registry, "owner")
    require_string(registry_path, result, registry, "description")
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        result.error(registry_path, "sources must be a non-empty list")
        return result

    context = validation_context(root)
    seen: set[str] = set()
    for index, source in enumerate(sources):
        result.checked_count += 1
        validate_source_entry(root, registry_path, source, index, seen, context, result)
    return result


def validation_context(root: Path) -> dict[str, Any]:
    return {
        "products": onboarded_products(root),
        "domains": load_enterprise_domain_codes(root),
        "topics": topic_contracts(root),
    }


def validate_source_entry(
    root: Path,
    path: Path,
    entry: object,
    index: int,
    seen: set[str],
    context: dict[str, Any],
    result: ValidationResult,
) -> None:
    prefix = f"sources[{index}]"
    if not isinstance(entry, dict):
        result.error(path, f"{prefix} must be an object")
        return

    source_id = require_string(path, result, entry, "sourceId", prefix)
    if source_id:
        if source_id in seen:
            result.error(path, f"{prefix}.sourceId duplicates source {source_id}")
        seen.add(source_id)
    priority = require_string(path, result, entry, "priority", prefix)
    if priority and priority not in VALID_PRIORITIES:
        result.error(path, f"{prefix}.priority must be one of {sorted(VALID_PRIORITIES)}")
    status = require_string(path, result, entry, "status", prefix)
    if status and status not in VALID_STATUSES:
        result.error(path, f"{prefix}.status must be one of {sorted(VALID_STATUSES)}")
    product = require_string(path, result, entry, "product", prefix)
    if product:
        if not PRODUCT_CODE.fullmatch(product):
            result.error(path, f"{prefix}.product must be a product code like example-product")
        elif product not in context["products"]:
            result.error(path, f"{prefix}.product must have products/{product}/onboarding.yaml")
    domain = require_string(path, result, entry, "domain", prefix)
    if domain and domain not in context["domains"]:
        result.error(path, f"{prefix}.domain must be listed in domains/registry.yaml")

    source = require_mapping(path, result, entry, "source")
    canonical = require_mapping(path, result, entry, "canonical")
    bridge = require_mapping(path, result, entry, "bridge")
    privacy = require_mapping(path, result, entry, "privacy")
    evidence = require_mapping(path, result, entry, "evidence")
    if not all([source, canonical, bridge, privacy, evidence]):
        return

    validate_source_block(path, source, prefix, result)
    canonical_topic = validate_canonical_block(path, canonical, prefix, context, result)
    validate_bridge_block(path, bridge, prefix, canonical_topic, result)
    validate_privacy_block(path, privacy, prefix, result)
    validate_evidence_block(path, evidence, prefix, priority, result)
    validate_production_ready_static_controls(path, entry, bridge, prefix, result)
    if canonical_topic:
        validate_topic_alignment(root, path, context["topics"].get(canonical_topic), canonical, product, domain, prefix, result)


def validate_production_ready_static_controls(
    path: Path,
    entry: dict[str, Any],
    bridge: dict[str, Any],
    prefix: str,
    result: ValidationResult,
) -> None:
    if entry.get("status") != "production_ready":
        return
    if entry.get("priority") != "P0":
        result.error(path, f"{prefix}.priority must be P0 when status=production_ready")
    if bridge.get("status") not in {"ready", "active"}:
        result.error(path, f"{prefix}.bridge.status must be ready or active when status=production_ready")
    if bridge.get("preservesSourcePosition") is not True:
        result.error(path, f"{prefix}.bridge.preservesSourcePosition must be true when status=production_ready")


def validate_source_block(path: Path, source: dict[str, Any], prefix: str, result: ValidationResult) -> None:
    source_type = require_string(path, result, source, "type", f"{prefix}.source")
    if source_type and source_type not in VALID_SOURCE_TYPES:
        result.error(path, f"{prefix}.source.type must be one of {sorted(VALID_SOURCE_TYPES)}")
    for key in ("system", "service", "rawTopic"):
        require_string(path, result, source, key, f"{prefix}.source")
    require_string_list(path, result, source, "rawEventTypes", f"{prefix}.source")


def validate_canonical_block(
    path: Path,
    canonical: dict[str, Any],
    prefix: str,
    context: dict[str, Any],
    result: ValidationResult,
) -> str | None:
    topic = require_string(path, result, canonical, "topic", f"{prefix}.canonical")
    if topic:
        if not TOPIC_NAME.fullmatch(topic):
            result.error(path, f"{prefix}.canonical.topic must be a versioned topic name")
        elif topic not in context["topics"]:
            result.error(path, f"{prefix}.canonical.topic contract does not exist: {topic}")
    bronze_target = require_string(path, result, canonical, "bronzeTarget", f"{prefix}.canonical")
    if bronze_target and not DATA_PRODUCT_NAME.fullmatch(bronze_target):
        result.error(path, f"{prefix}.canonical.bronzeTarget must be a Bronze data product")
    schema_subject = require_string(path, result, canonical, "schemaSubject", f"{prefix}.canonical")
    if topic and schema_subject and schema_subject != f"{topic}-value":
        result.error(path, f"{prefix}.canonical.schemaSubject must equal <topic>-value")
    compatibility = require_string(path, result, canonical, "compatibility", f"{prefix}.canonical")
    if compatibility and compatibility not in VALID_COMPATIBILITY_MODES:
        result.error(path, f"{prefix}.canonical.compatibility must be one of {sorted(VALID_COMPATIBILITY_MODES)}")
    return topic


def validate_bridge_block(
    path: Path,
    bridge: dict[str, Any],
    prefix: str,
    canonical_topic: str | None,
    result: ValidationResult,
) -> None:
    required = require_bool(path, result, bridge, "required", f"{prefix}.bridge")
    mode = require_string(path, result, bridge, "mode", f"{prefix}.bridge")
    status = require_string(path, result, bridge, "status", f"{prefix}.bridge")
    normalizer_id = require_string(path, result, bridge, "normalizerId", f"{prefix}.bridge")
    preserves_source_position = require_bool(path, result, bridge, "preservesSourcePosition", f"{prefix}.bridge")
    envelope_required = require_bool(path, result, bridge, "envelopeRequired", f"{prefix}.bridge")
    if mode and mode not in VALID_BRIDGE_MODES:
        result.error(path, f"{prefix}.bridge.mode must be one of {sorted(VALID_BRIDGE_MODES)}")
    if status and status not in VALID_BRIDGE_STATUSES:
        result.error(path, f"{prefix}.bridge.status must be one of {sorted(VALID_BRIDGE_STATUSES)}")
    if required is False and mode != "direct_canonical":
        result.error(path, f"{prefix}.bridge.mode must be direct_canonical when bridge.required=false")
    if required is True and normalizer_id == "none":
        result.error(path, f"{prefix}.bridge.normalizerId must name the approved normalizer when bridge.required=true")
    if envelope_required is not True:
        result.error(path, f"{prefix}.bridge.envelopeRequired must be true for platform Bronze ingestion")
    if canonical_topic and normalizer_id and normalizer_id != "none" and canonical_topic.replace(".", "-").replace("_", "-") not in normalizer_id:
        result.error(path, f"{prefix}.bridge.normalizerId should include the canonical topic for audit searchability")
    if preserves_source_position is False and required is False:
        result.error(path, f"{prefix}.bridge.preservesSourcePosition must be true for direct canonical sources")


def validate_privacy_block(path: Path, privacy: dict[str, Any], prefix: str, result: ValidationResult) -> None:
    pii_handling = require_string(path, result, privacy, "piiHandling", f"{prefix}.privacy")
    if pii_handling and pii_handling not in VALID_PII_HANDLING:
        result.error(path, f"{prefix}.privacy.piiHandling must be one of {sorted(VALID_PII_HANDLING)}")
    tenant_mapping = require_string(path, result, privacy, "tenantMapping", f"{prefix}.privacy")
    if tenant_mapping and tenant_mapping not in VALID_TENANT_MAPPING:
        result.error(path, f"{prefix}.privacy.tenantMapping must be one of {sorted(VALID_TENANT_MAPPING)}")
    subject_key_strategy = require_string(path, result, privacy, "subjectKeyStrategy", f"{prefix}.privacy")
    if subject_key_strategy and subject_key_strategy not in VALID_SUBJECT_KEY_STRATEGIES:
        result.error(path, f"{prefix}.privacy.subjectKeyStrategy must be one of {sorted(VALID_SUBJECT_KEY_STRATEGIES)}")


def validate_evidence_block(
    path: Path,
    evidence: dict[str, Any],
    prefix: str,
    priority: str | None,
    result: ValidationResult,
) -> None:
    for key in (
        "schemaRegistryReportRequired",
        "replayProofRequired",
        "sourceOffsetRequired",
        "productionAttestationRequired",
    ):
        value = require_bool(path, result, evidence, key, f"{prefix}.evidence")
        if priority == "P0" and value is not True:
            result.error(path, f"{prefix}.evidence.{key} must be true for P0 sources")


def validate_topic_alignment(
    root: Path,
    path: Path,
    topic_contract: dict[str, Any] | None,
    canonical: dict[str, Any],
    product: str | None,
    domain: str | None,
    prefix: str,
    result: ValidationResult,
) -> None:
    if topic_contract is None:
        return
    topic = topic_contract.get("topic")
    ingestion = topic_contract.get("ingestion")
    schema = topic_contract.get("schema")
    if not isinstance(topic, dict) or not isinstance(ingestion, dict) or not isinstance(schema, dict):
        result.error(path, f"{prefix}.canonical.topic contract is malformed")
        return
    if product and topic.get("product") != product:
        result.error(path, f"{prefix}.product must match canonical topic product {topic.get('product')!r}")
    if domain and topic.get("domain") != domain:
        result.error(path, f"{prefix}.domain must match canonical topic domain {topic.get('domain')!r}")
    if canonical.get("bronzeTarget") != ingestion.get("bronzeTarget"):
        result.error(path, f"{prefix}.canonical.bronzeTarget must match topic ingestion.bronzeTarget")
    if canonical.get("compatibility") != schema.get("compatibility"):
        result.error(path, f"{prefix}.canonical.compatibility must match topic schema.compatibility")
    bronze_target = canonical.get("bronzeTarget")
    if isinstance(bronze_target, str):
        candidates = sorted((root / "contracts" / "data-products").glob(f"{bronze_target}.v*.yaml"))
        if not candidates:
            result.error(path, f"{prefix}.canonical.bronzeTarget contract does not exist: {bronze_target}")


def onboarded_products(root: Path) -> set[str]:
    products: set[str] = set()
    for path in sorted((root / "products").glob("*/onboarding.yaml")):
        product = load_yaml(path).get("product")
        if isinstance(product, dict) and isinstance(product.get("code"), str):
            products.add(product["code"])
    return products


def topic_contracts(root: Path) -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "contracts" / "topics").glob("*.yaml")):
        contract = load_yaml(path)
        topic = contract.get("topic")
        if isinstance(topic, dict) and isinstance(topic.get("name"), str):
            contracts[topic["name"]] = contract
    return contracts


def write_source_readiness_report(
    root: str | Path,
    output_path: str | Path,
    *,
    source_id: str,
    environment: str,
    ingestion_manifest_path: str | Path,
    bridge_manifest_path: str | Path | None = None,
    replay_manifest_path: str | Path | None = None,
    offset_ledger_path: str | Path | None = None,
    schema_registry_report_path: str | Path | None = None,
    change_control_evidence_path: str | Path | None = None,
    catalog_bundle_path: str | Path | None = None,
    openlineage_events_path: str | Path | None = None,
    generated_at: str | None = None,
) -> SourceReadinessResult:
    report = build_source_readiness_report(
        root,
        source_id=source_id,
        environment=environment,
        ingestion_manifest_path=ingestion_manifest_path,
        bridge_manifest_path=bridge_manifest_path,
        replay_manifest_path=replay_manifest_path,
        offset_ledger_path=offset_ledger_path,
        schema_registry_report_path=schema_registry_report_path,
        change_control_evidence_path=change_control_evidence_path,
        catalog_bundle_path=catalog_bundle_path,
        openlineage_events_path=openlineage_events_path,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SourceReadinessResult(output_path=target, report=report)


def build_source_readiness_report(
    root: str | Path,
    *,
    source_id: str,
    environment: str,
    ingestion_manifest_path: str | Path,
    bridge_manifest_path: str | Path | None = None,
    replay_manifest_path: str | Path | None = None,
    offset_ledger_path: str | Path | None = None,
    schema_registry_report_path: str | Path | None = None,
    change_control_evidence_path: str | Path | None = None,
    catalog_bundle_path: str | Path | None = None,
    openlineage_events_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    source_entry = find_source_entry(platform_root, source_id)
    generated = generated_at or utc_now()
    ingestion_manifest = load_json_file(Path(ingestion_manifest_path))
    bridge_manifest = load_json_file(Path(bridge_manifest_path)) if bridge_manifest_path else None
    replay_manifest = load_json_file(Path(replay_manifest_path)) if replay_manifest_path else None
    offset_ledger = load_json_file(Path(offset_ledger_path)) if offset_ledger_path else None
    schema_report = load_json_file(Path(schema_registry_report_path)) if schema_registry_report_path else None
    change_control = load_json_file(Path(change_control_evidence_path)) if change_control_evidence_path else None
    catalog_bundle = load_json_file(Path(catalog_bundle_path)) if catalog_bundle_path else None
    openlineage_events = read_jsonl(Path(openlineage_events_path)) if openlineage_events_path else None
    checks = source_readiness_checks(
        source_entry,
        environment=environment,
        ingestion_manifest=ingestion_manifest,
        bridge_manifest=bridge_manifest,
        replay_manifest=replay_manifest,
        offset_ledger=offset_ledger,
        schema_report=schema_report,
        change_control=change_control,
        catalog_bundle=catalog_bundle,
        openlineage_events=openlineage_events,
    )
    passed = all(item["passed"] is True for item in checks)
    source_snapshot = source_readiness_snapshot(source_entry)
    return {
        "artifact_type": "source_readiness_report.v1",
        "report_version": REPORT_VERSION,
        "readiness_id": stable_id(
            "source-readiness",
            source_id,
            environment,
            hash_file_if_present(ingestion_manifest_path),
            hash_file_if_present(bridge_manifest_path),
            hash_file_if_present(replay_manifest_path),
            hash_file_if_present(offset_ledger_path),
            hash_file_if_present(schema_registry_report_path),
            hash_file_if_present(change_control_evidence_path),
            hash_file_if_present(catalog_bundle_path),
            hash_file_if_present(openlineage_events_path),
        ),
        "generated_at": generated,
        "environment": environment,
        "source_id": source_id,
        "readiness_state": "production_ready" if passed else "blocked",
        "source": source_snapshot,
        "evidence": {
            "ingestion_manifest_uri": Path(ingestion_manifest_path).as_posix(),
            "ingestion_manifest_hash": hash_file_if_present(ingestion_manifest_path),
            "bridge_manifest_uri": Path(bridge_manifest_path).as_posix() if bridge_manifest_path else None,
            "bridge_manifest_hash": hash_file_if_present(bridge_manifest_path),
            "replay_manifest_uri": Path(replay_manifest_path).as_posix() if replay_manifest_path else None,
            "replay_manifest_hash": hash_file_if_present(replay_manifest_path),
            "offset_ledger_uri": Path(offset_ledger_path).as_posix() if offset_ledger_path else None,
            "offset_ledger_hash": hash_file_if_present(offset_ledger_path),
            "schema_registry_report_uri": Path(schema_registry_report_path).as_posix() if schema_registry_report_path else None,
            "schema_registry_report_hash": hash_file_if_present(schema_registry_report_path),
            "change_control_evidence_uri": Path(change_control_evidence_path).as_posix() if change_control_evidence_path else None,
            "change_control_evidence_hash": hash_file_if_present(change_control_evidence_path),
            "catalog_bundle_uri": Path(catalog_bundle_path).as_posix() if catalog_bundle_path else None,
            "catalog_bundle_hash": hash_file_if_present(catalog_bundle_path),
            "openlineage_events_uri": Path(openlineage_events_path).as_posix() if openlineage_events_path else None,
            "openlineage_events_hash": hash_file_if_present(openlineage_events_path),
        },
        "checks": checks,
        "failures": [
            {"check": item["name"], "details": item.get("details", {})}
            for item in checks
            if item.get("passed") is not True
        ],
        "passed": passed,
    }


def source_readiness_checks(
    source_entry: dict[str, Any] | None,
    *,
    environment: str,
    ingestion_manifest: dict[str, Any],
    bridge_manifest: dict[str, Any] | None,
    replay_manifest: dict[str, Any] | None,
    offset_ledger: dict[str, Any] | None,
    schema_report: dict[str, Any] | None,
    change_control: dict[str, Any] | None,
    catalog_bundle: dict[str, Any] | None,
    openlineage_events: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if source_entry is None:
        return [
            check("source_registered", False, {}),
            check("environment_supported", environment in SUPPORTED_ENVIRONMENTS, {"environment": environment}),
        ]

    source = _mapping(source_entry, "source")
    canonical = _mapping(source_entry, "canonical")
    bridge = _mapping(source_entry, "bridge")
    privacy = _mapping(source_entry, "privacy")
    evidence = _mapping(source_entry, "evidence")
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    checks = [
        check("source_registered", True, {"source_id": source_entry.get("sourceId")}),
        check("environment_supported", environment in SUPPORTED_ENVIRONMENTS, {"environment": environment}),
        check(
            "source_status_allows_readiness",
            source_entry.get("status") in {"pilot", "production_ready", "active"},
            {"status": source_entry.get("status")},
        ),
        check(
            "bridge_ready_for_production",
            bridge.get("status") in {"ready", "active"} if production_like else bridge.get("status") in VALID_BRIDGE_STATUSES,
            {"bridge_status": bridge.get("status")},
        ),
        check(
            "source_position_preserved",
            bridge.get("preservesSourcePosition") is True,
            {"preservesSourcePosition": bridge.get("preservesSourcePosition")},
        ),
        check(
            "envelope_required",
            bridge.get("envelopeRequired") is True,
            {"envelopeRequired": bridge.get("envelopeRequired")},
        ),
        check(
            "privacy_handling_production_safe",
            privacy.get("piiHandling") in VALID_PII_HANDLING and privacy.get("piiHandling") != "encrypted_raw_with_subject_erasure",
            {"piiHandling": privacy.get("piiHandling")},
        ),
        check(
            "tenant_mapping_declared",
            privacy.get("tenantMapping") in {"org_id_required", "tenant_id_required", "aggregate_only"},
            {"tenantMapping": privacy.get("tenantMapping")},
        ),
        *schema_report_checks(schema_report, canonical=canonical, production_like=production_like, evidence=evidence),
        *bridge_manifest_checks(
            bridge_manifest,
            source_entry=source_entry,
            canonical=canonical,
            bridge=bridge,
            ingestion_manifest=ingestion_manifest,
        ),
        *ingestion_manifest_checks(ingestion_manifest, source_entry=source_entry, canonical=canonical, source=source, evidence=evidence),
        *replay_manifest_checks(replay_manifest, ingestion_manifest=ingestion_manifest, evidence=evidence),
        *offset_ledger_checks(offset_ledger, source_entry=source_entry, canonical=canonical, environment=environment, ingestion_manifest=ingestion_manifest, production_like=production_like),
        *change_control_checks(change_control, source_entry=source_entry, environment=environment, production_like=production_like),
        *catalog_bundle_checks(catalog_bundle, canonical=canonical, production_like=production_like),
        *openlineage_checks(openlineage_events, canonical=canonical, production_like=production_like),
    ]
    return checks


def schema_report_checks(
    schema_report: dict[str, Any] | None,
    *,
    canonical: dict[str, Any],
    production_like: bool,
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    if schema_report is None:
        return [
            check(
                "schema_registry_report_attached",
                evidence.get("schemaRegistryReportRequired") is not True,
                {"required": evidence.get("schemaRegistryReportRequired")},
            )
        ]
    subject = next(
        (
            item
            for item in schema_report.get("subjects", [])
            if isinstance(item, dict) and item.get("subject") == canonical.get("schemaSubject")
        ),
        None,
    )
    registry_uri = schema_report.get("registry_uri")
    return [
        check("schema_registry_report_attached", True, {"registry_uri": registry_uri}),
        check("schema_registry_report_passed", schema_report.get("compatibility_passed") is True, {"compatibility_passed": schema_report.get("compatibility_passed")}),
        check("schema_subject_covered", subject is not None, {"schema_subject": canonical.get("schemaSubject")}),
        check(
            "schema_subject_compatibility_matches_source",
            subject is not None and subject.get("compatibility") == canonical.get("compatibility"),
            {"subject_compatibility": subject.get("compatibility") if subject else None, "source_compatibility": canonical.get("compatibility")},
        ),
        check(
            "production_schema_registry_uri_declared",
            not production_like or (isinstance(registry_uri, str) and registry_uri.strip() and registry_uri != LOCAL_SCHEMA_REGISTRY_URI),
            {"registry_uri": registry_uri},
        ),
    ]


def bridge_manifest_checks(
    bridge_manifest: dict[str, Any] | None,
    *,
    source_entry: dict[str, Any],
    canonical: dict[str, Any],
    bridge: dict[str, Any],
    ingestion_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    bridge_required = bridge.get("required") is True
    if bridge_manifest is None:
        return [
            check(
                "bridge_manifest_attached",
                not bridge_required,
                {"required": bridge_required},
            )
        ]
    normalized = _mapping(bridge_manifest, "normalized")
    bridge_source = _mapping(bridge_manifest, "source")
    ingestion_input = _mapping(ingestion_manifest, "input")
    return [
        check("bridge_manifest_attached", True, {"required": bridge_required}),
        check(
            "bridge_manifest_type_valid",
            bridge_manifest.get("pipeline") == "source_bridge.local_normalizer.v1",
            {"pipeline": bridge_manifest.get("pipeline")},
        ),
        check(
            "bridge_manifest_source_matches",
            bridge_manifest.get("source_id") == source_entry.get("sourceId"),
            {"manifest_source_id": bridge_manifest.get("source_id"), "source_id": source_entry.get("sourceId")},
        ),
        check(
            "bridge_manifest_normalizer_matches",
            bridge_manifest.get("normalizer_id") == bridge.get("normalizerId"),
            {"manifest_normalizer": bridge_manifest.get("normalizer_id"), "normalizer": bridge.get("normalizerId")},
        ),
        check(
            "bridge_manifest_canonical_topic_matches",
            bridge_source.get("canonical_topic") == canonical.get("topic"),
            {"manifest_topic": bridge_source.get("canonical_topic"), "source_topic": canonical.get("topic")},
        ),
        check(
            "bridge_manifest_quality_passed",
            bridge_manifest.get("quality_passed") is True,
            {"quality_passed": bridge_manifest.get("quality_passed")},
        ),
        check(
            "bridge_output_used_by_ingestion",
            normalized.get("content_hash") == ingestion_input.get("content_hash"),
            {"bridge_output_hash": normalized.get("content_hash"), "ingestion_input_hash": ingestion_input.get("content_hash")},
        ),
    ]


def ingestion_manifest_checks(
    ingestion_manifest: dict[str, Any],
    *,
    source_entry: dict[str, Any],
    canonical: dict[str, Any],
    source: dict[str, Any],
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    approved = _mapping(ingestion_manifest, "approved")
    quarantine = _mapping(ingestion_manifest, "quarantine")
    source_positions = ingestion_manifest.get("source_positions")
    source_topics = {
        position.get("source_topic")
        for position in source_positions
        if isinstance(position, dict)
    } if isinstance(source_positions, list) else set()
    direct_canonical = _mapping(source_entry, "bridge").get("mode") == "direct_canonical"
    return [
        check("ingestion_manifest_attached", bool(ingestion_manifest), {}),
        check("ingestion_pipeline_is_bronze", ingestion_manifest.get("pipeline") == "bronze_ingestion.local_jsonl.v1", {"pipeline": ingestion_manifest.get("pipeline")}),
        check("ingestion_topic_matches_source", ingestion_manifest.get("topic") == canonical.get("topic"), {"manifest_topic": ingestion_manifest.get("topic"), "source_topic": canonical.get("topic")}),
        check("ingestion_bronze_target_matches_source", ingestion_manifest.get("bronze_target") == canonical.get("bronzeTarget"), {"manifest_bronze": ingestion_manifest.get("bronze_target"), "source_bronze": canonical.get("bronzeTarget")}),
        check("ingestion_product_matches_source", ingestion_manifest.get("product_id") == source_entry.get("product"), {"manifest_product": ingestion_manifest.get("product_id"), "source_product": source_entry.get("product")}),
        check("ingestion_quality_passed", ingestion_manifest.get("quality_passed") is True, {"quality_passed": ingestion_manifest.get("quality_passed")}),
        check("ingestion_approved_rows_present", int_or_zero(approved.get("new_row_count")) > 0, {"approved": approved}),
        check("ingestion_quarantine_empty", int_or_zero(quarantine.get("row_count")) == 0, {"quarantine": quarantine}),
        check(
            "source_positions_present",
            evidence.get("sourceOffsetRequired") is not True or bool(source_positions),
            {"source_positions": source_positions},
        ),
        check(
            "direct_canonical_source_topic_preserved",
            not direct_canonical or source_topics == {canonical.get("topic")},
            {"source_topics": sorted(str(topic) for topic in source_topics), "raw_topic": source.get("rawTopic"), "canonical_topic": canonical.get("topic")},
        ),
        check("approved_content_hash_present", is_hash(approved.get("content_hash")), {"content_hash": approved.get("content_hash")}),
    ]


def replay_manifest_checks(
    replay_manifest: dict[str, Any] | None,
    *,
    ingestion_manifest: dict[str, Any],
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    if replay_manifest is None:
        return [
            check(
                "replay_manifest_attached",
                evidence.get("replayProofRequired") is not True,
                {"required": evidence.get("replayProofRequired")},
            )
        ]
    approved = _mapping(replay_manifest, "approved")
    first_approved = _mapping(ingestion_manifest, "approved")
    return [
        check("replay_manifest_attached", True, {}),
        check("replay_quality_passed", replay_manifest.get("quality_passed") is True, {"quality_passed": replay_manifest.get("quality_passed")}),
        check("replay_adds_no_rows", int_or_zero(approved.get("new_row_count")) == 0, {"approved": approved}),
        check("replay_skips_existing_rows", int_or_zero(approved.get("replay_skipped_count")) >= int_or_zero(first_approved.get("new_row_count")), {"approved": approved, "first_approved": first_approved}),
        check("replay_source_positions_stable", replay_manifest.get("source_positions") == ingestion_manifest.get("source_positions"), {"first": ingestion_manifest.get("source_positions"), "replay": replay_manifest.get("source_positions")}),
    ]


def offset_ledger_checks(
    offset_ledger: dict[str, Any] | None,
    *,
    source_entry: dict[str, Any],
    canonical: dict[str, Any],
    environment: str,
    ingestion_manifest: dict[str, Any],
    production_like: bool,
) -> list[dict[str, Any]]:
    if offset_ledger is None:
        return [check("offset_ledger_attached", not production_like, {"production_like": production_like})]
    target = _mapping(offset_ledger, "target")
    ingestion = _mapping(offset_ledger, "ingestion")
    counts = _mapping(offset_ledger, "counts")
    return [
        check("offset_ledger_attached", True, {"ledger_id": offset_ledger.get("ledger_id")}),
        check("offset_ledger_type_valid", offset_ledger.get("artifact_type") == "source_offset_ledger.v1", {"artifact_type": offset_ledger.get("artifact_type")}),
        check("offset_ledger_passed", offset_ledger.get("passed") is True, {"passed": offset_ledger.get("passed")}),
        check("offset_ledger_environment_matches", offset_ledger.get("environment") == environment, {"ledger_environment": offset_ledger.get("environment"), "readiness_environment": environment}),
        check("offset_ledger_source_matches", offset_ledger.get("source_id") == source_entry.get("sourceId"), {"ledger_source": offset_ledger.get("source_id"), "source_id": source_entry.get("sourceId")}),
        check("offset_ledger_topic_matches", ingestion.get("topic") == canonical.get("topic"), {"ledger_topic": ingestion.get("topic"), "source_topic": canonical.get("topic")}),
        check("offset_ledger_bronze_matches", target.get("target_table") == canonical.get("bronzeTarget"), {"target_table": target.get("target_table"), "bronze_target": canonical.get("bronzeTarget")}),
        check("offset_ledger_ingest_run_matches", ingestion.get("ingest_run_id") == ingestion_manifest.get("ingest_run_id"), {"ledger_ingest_run_id": ingestion.get("ingest_run_id"), "manifest_ingest_run_id": ingestion_manifest.get("ingest_run_id")}),
        check("offset_ledger_content_hash_matches", target.get("content_hash") == _mapping(ingestion_manifest, "approved").get("content_hash"), {"ledger_content_hash": target.get("content_hash"), "manifest_content_hash": _mapping(ingestion_manifest, "approved").get("content_hash")}),
        check("offset_ledger_commit_status_committed", target.get("commit_status") == "committed", {"commit_status": target.get("commit_status")}),
        check("offset_ledger_committed_rows_present", int_or_zero(counts.get("committed_record_count")) > 0, {"counts": counts}),
        check("offset_ledger_snapshot_present", not production_like or non_empty(target.get("target_snapshot_id")), {"target_snapshot_id": target.get("target_snapshot_id")}),
        check("offset_ledger_metadata_hash_present", not production_like or is_hash(target.get("table_metadata_hash")), {"table_metadata_hash": target.get("table_metadata_hash")}),
    ]


def change_control_checks(
    change_control: dict[str, Any] | None,
    *,
    source_entry: dict[str, Any],
    environment: str,
    production_like: bool,
) -> list[dict[str, Any]]:
    if change_control is None:
        return [check("change_control_evidence_attached", not production_like, {"production_like": production_like})]
    requests = [
        request
        for request in change_control.get("requests", [])
        if isinstance(request, dict)
    ]
    source_onboarding_requests = [
        request
        for request in requests
        if request.get("request_type") == "source_onboarding"
        and request.get("product") == source_entry.get("product")
        and request.get("domain") == source_entry.get("domain")
    ]
    return [
        check("change_control_evidence_attached", True, {"evidence_id": change_control.get("evidence_id")}),
        check("change_control_passed", change_control.get("passed") is True, {"passed": change_control.get("passed")}),
        check("change_control_environment_matches", change_control.get("environment") == environment, {"report_environment": change_control.get("environment"), "source_environment": environment}),
        check("source_onboarding_change_approved", bool(source_onboarding_requests), {"matched_requests": [request.get("request_id") for request in source_onboarding_requests]}),
    ]


def catalog_bundle_checks(
    catalog_bundle: dict[str, Any] | None,
    *,
    canonical: dict[str, Any],
    production_like: bool,
) -> list[dict[str, Any]]:
    if catalog_bundle is None:
        return [check("catalog_bundle_attached", not production_like, {"production_like": production_like})]
    topic_names = {
        topic.get("name")
        for topic in catalog_bundle.get("topics", [])
        if isinstance(topic, dict)
    }
    data_product_names = {
        data_product.get("name")
        for data_product in catalog_bundle.get("data_products", [])
        if isinstance(data_product, dict)
    }
    lineage_edges = [
        edge for edge in catalog_bundle.get("lineage_edges", []) if isinstance(edge, dict)
    ]
    expected_source = f"urn:enterprise-df:topic:{canonical.get('topic')}"
    expected_target = f"urn:enterprise-df:data-product:{canonical.get('bronzeTarget')}"
    return [
        check("catalog_bundle_attached", True, {"bundle_version": catalog_bundle.get("bundle_version")}),
        check("catalog_topic_registered", canonical.get("topic") in topic_names, {"topic": canonical.get("topic")}),
        check("catalog_bronze_registered", canonical.get("bronzeTarget") in data_product_names, {"bronze_target": canonical.get("bronzeTarget")}),
        check(
            "catalog_topic_to_bronze_lineage_present",
            any(edge.get("source") == expected_source and edge.get("target") == expected_target for edge in lineage_edges),
            {"expected_source": expected_source, "expected_target": expected_target},
        ),
    ]


def openlineage_checks(
    openlineage_events: list[dict[str, Any]] | None,
    *,
    canonical: dict[str, Any],
    production_like: bool,
) -> list[dict[str, Any]]:
    if openlineage_events is None:
        return [check("openlineage_events_attached", not production_like, {"production_like": production_like})]
    expected_topic = canonical.get("topic")
    expected_bronze = canonical.get("bronzeTarget")
    matching_events = [
        event
        for event in openlineage_events
        if event.get("eventType") == "COMPLETE"
        and dataset_names(event.get("inputs")) & {expected_topic}
        and dataset_names(event.get("outputs")) & {expected_bronze}
    ]
    return [
        check("openlineage_events_attached", True, {"event_count": len(openlineage_events)}),
        check("openlineage_complete_topic_to_bronze_event_present", bool(matching_events), {"topic": expected_topic, "bronze_target": expected_bronze}),
    ]


def find_source_entry(root: Path, source_id: str) -> dict[str, Any] | None:
    registry_path = root / "platform" / "ingestion" / "source-registry.yaml"
    if not registry_path.is_file():
        return None
    sources = load_yaml(registry_path).get("sources")
    if not isinstance(sources, list):
        return None
    return next(
        (
            source
            for source in sources
            if isinstance(source, dict) and source.get("sourceId") == source_id
        ),
        None,
    )


def source_readiness_snapshot(source_entry: dict[str, Any] | None) -> dict[str, Any] | None:
    if source_entry is None:
        return None
    return {
        "source_id": source_entry.get("sourceId"),
        "priority": source_entry.get("priority"),
        "status": source_entry.get("status"),
        "product": source_entry.get("product"),
        "domain": source_entry.get("domain"),
        "source_type": _mapping(source_entry, "source").get("type"),
        "source_system": _mapping(source_entry, "source").get("system"),
        "source_service": _mapping(source_entry, "source").get("service"),
        "raw_topic": _mapping(source_entry, "source").get("rawTopic"),
        "canonical_topic": _mapping(source_entry, "canonical").get("topic"),
        "bronze_target": _mapping(source_entry, "canonical").get("bronzeTarget"),
        "schema_subject": _mapping(source_entry, "canonical").get("schemaSubject"),
        "bridge": {
            "required": _mapping(source_entry, "bridge").get("required"),
            "mode": _mapping(source_entry, "bridge").get("mode"),
            "status": _mapping(source_entry, "bridge").get("status"),
            "normalizer_id": _mapping(source_entry, "bridge").get("normalizerId"),
        },
        "privacy": _mapping(source_entry, "privacy"),
    }


def load_json_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            data = json.loads(stripped)
            if not isinstance(data, dict):
                raise ValueError(f"{path}:{line_number}: JSONL row must be an object")
            rows.append(data)
    return rows


def dataset_names(items: object) -> set[object]:
    if not isinstance(items, list):
        return set()
    return {
        item.get("name")
        for item in items
        if isinstance(item, dict)
    }


def _mapping(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    return value if isinstance(value, dict) else {}


def int_or_zero(value: object) -> int:
    return value if isinstance(value, int) else 0


def is_hash(value: object) -> bool:
    return isinstance(value, str) and value.startswith("sha256:")


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def hash_file_if_present(path: str | Path | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.is_file():
        return None
    digest = hashlib.sha256()
    with candidate.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.change_requests import change_request_catalog_entries
from enterprise_dp.contracts import load_yaml


CATALOG_BUNDLE_VERSION = 1


def build_catalog_bundle(
    root: str | Path,
    *,
    manifest_paths: list[str | Path] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    manifests = [Path(path) for path in manifest_paths or []]
    data_products = [
        data_product_entry(path, load_yaml(path))
        for path in sorted((platform_root / "contracts" / "data-products").glob("*.yaml"))
    ]
    topics = [
        topic_entry(path, load_yaml(path))
        for path in sorted((platform_root / "contracts" / "topics").glob("*.yaml"))
    ]
    product_onboardings = [
        product_entry(path, load_yaml(path))
        for path in sorted((platform_root / "products").glob("*/onboarding.yaml"))
    ]
    access_personas = access_persona_entries(platform_root / "contracts" / "policies" / "access-personas.yaml")
    consumer_contracts = consumer_contract_entries(platform_root / "contracts" / "policies" / "consumer-contracts.yaml")
    access_grants = access_grant_entries(platform_root / "governance" / "access-grants.yaml")
    change_requests = change_request_catalog_entries(platform_root)
    access_policies = access_policy_entries(platform_root / "contracts" / "policies" / "access-policies.yaml")
    retention_policies = retention_policy_entries(platform_root / "contracts" / "policies" / "retention-policies.yaml")
    quality_profiles = quality_profile_entries(platform_root / "platform" / "quality" / "profiles.yaml")
    release_profiles = release_profile_entries(platform_root / "platform" / "observability" / "release-evidence-profiles.yaml")
    domain_registry = load_yaml(platform_root / "domains" / "registry.yaml")
    use_cases = use_case_entries(platform_root / "use-cases" / "registry.yaml")
    run_evidence = [run_evidence_entry(path) for path in manifests]

    lineage_edges = (
        lineage_from_topics(topics)
        + lineage_from_data_products(data_products)
        + lineage_from_use_cases(use_cases)
        + lineage_from_runs(run_evidence)
    )
    return {
        "bundle_version": CATALOG_BUNDLE_VERSION,
        "generated_at": generated_at or _utc_now(),
        "catalog_target": "DataHub/OpenMetadata compatible metadata bundle",
        "products": product_onboardings,
        "domains": domain_registry.get("domains", []),
        "access_personas": access_personas,
        "consumer_contracts": consumer_contracts,
        "access_grants": access_grants,
        "change_requests": change_requests,
        "access_policies": access_policies,
        "retention_policies": retention_policies,
        "quality_profiles": quality_profiles,
        "release_evidence_profiles": release_profiles,
        "use_cases": use_cases,
        "topics": topics,
        "data_products": data_products,
        "lineage_edges": lineage_edges,
        "run_evidence": run_evidence,
        "summary": {
            "product_count": len(product_onboardings),
            "domain_count": len(domain_registry.get("domains", [])),
            "access_persona_count": len(access_personas),
            "consumer_contract_count": len(consumer_contracts),
            "access_grant_count": len(access_grants),
            "change_request_count": len(change_requests),
            "access_policy_count": len(access_policies),
            "retention_policy_count": len(retention_policies),
            "quality_profile_count": len(quality_profiles),
            "release_evidence_profile_count": len(release_profiles),
            "use_case_count": len(use_cases),
            "topic_count": len(topics),
            "data_product_count": len(data_products),
            "lineage_edge_count": len(lineage_edges),
            "run_evidence_count": len(run_evidence),
        },
    }


def write_catalog_bundle(
    root: str | Path,
    output_path: str | Path,
    *,
    manifest_paths: list[str | Path] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    bundle = build_catalog_bundle(root, manifest_paths=manifest_paths, generated_at=generated_at)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(bundle)}\n", encoding="utf-8")
    return bundle


def data_product_entry(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    data_product = _mapping(contract, "dataProduct")
    schema = _mapping(contract, "schema")
    quality = _mapping(contract, "quality")
    privacy = _mapping(contract, "privacy")
    serving = _mapping(contract, "serving")
    lineage = _mapping(contract, "lineage")
    source = _mapping(contract, "source")
    name = str(data_product.get("name"))
    version = contract.get("contractVersion")
    return {
        "urn": f"urn:enterprise-dp:data-product:{name}",
        "contract_urn": f"urn:enterprise-dp:data-product:{name}:v{version}",
        "name": name,
        "contract_version": version,
        "contract_path": path.as_posix(),
        "contract_hash": hash_file(path),
        "layer": data_product.get("layer"),
        "product": data_product.get("product"),
        "domain": data_product.get("domain"),
        "domain_owner": data_product.get("domainOwner"),
        "owner_team": data_product.get("ownerTeam"),
        "business_owner": data_product.get("businessOwner"),
        "technical_owner": data_product.get("technicalOwner"),
        "data_steward": data_product.get("dataSteward"),
        "description": data_product.get("description"),
        "status": data_product.get("status"),
        "deprecation_policy": data_product.get("deprecationPolicy"),
        "columns": [
            {
                "name": column.get("name"),
                "type": column.get("type"),
                "nullable": column.get("nullable"),
                "pii": column.get("pii"),
                "description": column.get("description"),
            }
            for column in schema.get("columns", [])
            if isinstance(column, dict)
        ],
        "quality": {
            "freshness_slo_minutes": quality.get("freshnessSloMinutes"),
            "checks": quality.get("checks", []),
        },
        "privacy": {
            "classification": privacy.get("classification"),
            "contains_pii": privacy.get("containsPii"),
            "tenant_isolation": privacy.get("tenantIsolation"),
            "data_residency": privacy.get("dataResidency"),
            "retention_days": privacy.get("retentionDays"),
            "erasure_supported": privacy.get("erasureSupported"),
            "subject_keys": privacy.get("subjectKeys", []),
            "erasure_mode": privacy.get("erasureMode"),
            "legal_hold_policy": privacy.get("legalHoldPolicy"),
            "raw_payload_policy": privacy.get("rawPayloadPolicy"),
        },
        "serving": {
            "consumers": serving.get("consumers", []),
            "access_policy": serving.get("accessPolicy"),
            "access_personas": serving.get("accessPersonas", []),
            "consumer_contract": serving.get("consumerContract"),
            "publication_gate": serving.get("publicationGate"),
        },
        "lineage": {
            "catalog": lineage.get("catalog"),
            "lineage_required": lineage.get("lineageRequired"),
            "upstream": source.get("upstream", []),
        },
    }


def topic_entry(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    topic = _mapping(contract, "topic")
    schema = _mapping(contract, "schema")
    privacy = _mapping(contract, "privacy")
    ingestion = _mapping(contract, "ingestion")
    quality = _mapping(contract, "quality")
    name = str(topic.get("name"))
    version = contract.get("contractVersion")
    return {
        "urn": f"urn:enterprise-dp:topic:{name}",
        "contract_urn": f"urn:enterprise-dp:topic:{name}:v{version}",
        "name": name,
        "contract_version": version,
        "contract_path": path.as_posix(),
        "contract_hash": hash_file(path),
        "product": topic.get("product"),
        "domain": topic.get("domain"),
        "domain_owner": topic.get("domainOwner"),
        "owner_team": topic.get("ownerTeam"),
        "data_steward": topic.get("dataSteward"),
        "source_services": topic.get("sourceServices", []),
        "description": topic.get("description"),
        "status": topic.get("status"),
        "schema": {
            "format": schema.get("format"),
            "compatibility": schema.get("compatibility"),
            "envelope_schema": schema.get("envelopeSchema"),
            "payload_schema": schema.get("payloadSchema"),
        },
        "privacy": {
            "classification": privacy.get("classification"),
            "contains_pii": privacy.get("containsPii"),
            "tenant_isolation": privacy.get("tenantIsolation"),
            "data_residency": privacy.get("dataResidency"),
            "retention_days": privacy.get("retentionDays"),
            "erasure_supported": privacy.get("erasureSupported"),
            "subject_keys": privacy.get("subjectKeys", []),
            "erasure_mode": privacy.get("erasureMode"),
            "legal_hold_policy": privacy.get("legalHoldPolicy"),
            "raw_payload_policy": privacy.get("rawPayloadPolicy"),
        },
        "ingestion": {
            "bronze_target": ingestion.get("bronzeTarget"),
            "partition_strategy": ingestion.get("partitionStrategy"),
        },
        "quality": {
            "freshness_slo_minutes": quality.get("freshnessSloMinutes"),
            "checks": quality.get("checks", []),
        },
    }


def product_entry(path: Path, onboarding: dict[str, Any]) -> dict[str, Any]:
    product = _mapping(onboarding, "product")
    governance = _mapping(onboarding, "governance")
    return {
        "urn": f"urn:enterprise-dp:product:{product.get('code')}",
        "onboarding_path": path.as_posix(),
        "onboarding_hash": hash_file(path),
        "code": product.get("code"),
        "name": product.get("name"),
        "status": product.get("status"),
        "business_sponsor": product.get("businessSponsor"),
        "product_owner": product.get("productOwner"),
        "technical_owner": product.get("technicalOwner"),
        "data_steward": product.get("dataSteward"),
        "default_data_residency": product.get("defaultDataResidency"),
        "tenant_model": product.get("tenantModel", {}),
        "domains": onboarding.get("domains", []),
        "governance": {
            "classification": governance.get("classification"),
            "contains_pii": governance.get("containsPii"),
            "tenant_isolation": governance.get("tenantIsolation"),
            "default_retention_policy": governance.get("defaultRetentionPolicy"),
            "default_access_personas": governance.get("defaultAccessPersonas", []),
            "consumer_contract": governance.get("consumerContract"),
            "release_evidence_profile": governance.get("releaseEvidenceProfile"),
            "lineage_required": governance.get("lineageRequired"),
            "catalog_registration_required": governance.get("catalogRegistrationRequired"),
            "dsar_required": governance.get("dsarRequired"),
        },
        "source_systems": onboarding.get("sourceSystems", []),
        "first_slice": onboarding.get("firstSlice", {}),
        "consumers": onboarding.get("consumers", []),
    }


def use_case_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    registry = load_yaml(path)
    use_cases = registry.get("useCases")
    if not isinstance(use_cases, list):
        return []
    return [
        use_case_entry(path, use_case)
        for use_case in use_cases
        if isinstance(use_case, dict)
    ]


def use_case_entry(path: Path, use_case: dict[str, Any]) -> dict[str, Any]:
    use_case_id = str(use_case.get("id"))
    implementation = use_case.get("implementation")
    pipeline_implementations = (
        implementation.get("pipelines", [])
        if isinstance(implementation, dict)
        else []
    )
    return {
        "urn": f"urn:enterprise-dp:use-case:{use_case_id}",
        "registry_path": path.as_posix(),
        "registry_hash": hash_file(path),
        "id": use_case_id,
        "name": use_case.get("name"),
        "domain": use_case.get("domain"),
        "priority": use_case.get("priority"),
        "status": use_case.get("status"),
        "owner": use_case.get("owner"),
        "business_outcome": use_case.get("businessOutcome"),
        "primary_consumers": use_case.get("primaryConsumers", []),
        "source_products": use_case.get("sourceProducts", []),
        "source_systems": use_case.get("sourceSystems", []),
        "data_products": use_case.get("dataProducts", []),
        "kpis": use_case.get("kpis", []),
        "access_personas": use_case.get("accessPersonas", []),
        "governance": use_case.get("governance", {}),
        "platform_capabilities": use_case.get("platformCapabilities", []),
        "pipeline_runners": use_case.get("pipelineRunners", []),
        "implementation": implementation if isinstance(implementation, dict) else {},
        "implementation_summary": implementation_summary(pipeline_implementations),
        "release_gates": use_case.get("releaseGates", []),
    }


def implementation_summary(pipelines: list[Any]) -> dict[str, Any]:
    normalized = [pipeline for pipeline in pipelines if isinstance(pipeline, dict)]
    return {
        "runner_ids": [
            pipeline.get("runnerId")
            for pipeline in normalized
            if isinstance(pipeline.get("runnerId"), str)
        ],
        "input_topics": sorted(
            {
                topic
                for pipeline in normalized
                for topic in pipeline.get("inputTopics", [])
                if isinstance(topic, str)
            }
        ),
        "input_data_products": sorted(
            {
                data_product
                for pipeline in normalized
                for data_product in pipeline.get("inputDataProducts", [])
                if isinstance(data_product, str)
            }
        ),
        "output_data_products": sorted(
            {
                data_product
                for pipeline in normalized
                for data_product in pipeline.get("outputDataProducts", [])
                if isinstance(data_product, str)
            }
        ),
        "primary_outputs": sorted(
            {
                pipeline.get("primaryOutput")
                for pipeline in normalized
                if isinstance(pipeline.get("primaryOutput"), str)
            }
        ),
        "release_evidence_profiles": sorted(
            {
                pipeline.get("releaseEvidenceProfile")
                for pipeline in normalized
                if isinstance(pipeline.get("releaseEvidenceProfile"), str)
            }
        ),
        "quality_profiles": sorted(
            {
                pipeline.get("qualityProfile")
                for pipeline in normalized
                if isinstance(pipeline.get("qualityProfile"), str)
            }
        ),
    }


def quality_profile_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    registry = load_yaml(path)
    profiles = registry.get("profiles")
    if not isinstance(profiles, list):
        return []
    return [
        quality_profile_entry(path, profile)
        for profile in profiles
        if isinstance(profile, dict)
    ]


def quality_profile_entry(path: Path, profile: dict[str, Any]) -> dict[str, Any]:
    profile_id = str(profile.get("id"))
    return {
        "urn": f"urn:enterprise-dp:quality-profile:{profile_id}",
        "registry_path": path.as_posix(),
        "registry_hash": hash_file(path),
        "id": profile_id,
        "name": profile.get("name"),
        "owner": profile.get("owner"),
        "severity": profile.get("severity"),
        "description": profile.get("description"),
        "applies_to": profile.get("appliesTo", {}),
        "thresholds": profile.get("thresholds", {}),
        "required_output_data_products": profile.get("requiredOutputDataProducts", []),
        "required_columns": profile.get("requiredColumns", {}),
    }


def access_persona_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    registry = load_yaml(path)
    personas = registry.get("personas")
    if not isinstance(personas, list):
        return []
    registry_hash = hash_file(path)
    registry_scope = registry.get("registry_scope")
    return [
        access_persona_entry(path, registry_hash, registry_scope, persona)
        for persona in personas
        if isinstance(persona, dict)
    ]


def access_persona_entry(
    path: Path,
    registry_hash: str,
    registry_scope: object,
    persona: dict[str, Any],
) -> dict[str, Any]:
    persona_id = str(persona.get("id"))
    return {
        "urn": f"urn:enterprise-dp:access-persona:{persona_id}",
        "registry_path": path.as_posix(),
        "registry_hash": registry_hash,
        "registry_scope": registry_scope,
        "id": persona_id,
        "name": persona.get("name"),
        "status": persona.get("status"),
        "owner": persona.get("owner"),
        "category": persona.get("category"),
        "description": persona.get("description"),
        "allowed_layers": persona.get("allowedLayers", []),
        "allowed_classifications": persona.get("allowedClassifications", []),
        "approval_required": persona.get("approvalRequired"),
        "default_access_modes": persona.get("defaultAccessModes", []),
    }


def consumer_contract_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    registry = load_yaml(path)
    contracts = registry.get("contracts")
    if not isinstance(contracts, list):
        return []
    registry_hash = hash_file(path)
    registry_scope = registry.get("registry_scope")
    return [
        consumer_contract_entry(path, registry_hash, registry_scope, contract)
        for contract in contracts
        if isinstance(contract, dict)
    ]


def consumer_contract_entry(
    path: Path,
    registry_hash: str,
    registry_scope: object,
    contract: dict[str, Any],
) -> dict[str, Any]:
    contract_id = str(contract.get("id"))
    return {
        "urn": f"urn:enterprise-dp:consumer-contract:{contract_id}",
        "registry_path": path.as_posix(),
        "registry_hash": registry_hash,
        "registry_scope": registry_scope,
        "id": contract_id,
        "name": contract.get("name"),
        "contract_version": contract.get("contractVersion"),
        "status": contract.get("status"),
        "severity": contract.get("severity"),
        "owner": contract.get("owner"),
        "effective_from": contract.get("effectiveFrom"),
        "description": contract.get("description"),
        "applies_to": contract.get("appliesTo", {}),
        "allowed_personas": contract.get("allowedPersonas", []),
        "allowed_access_modes": contract.get("allowedAccessModes", []),
        "required_evidence": contract.get("requiredEvidence", []),
        "controls": contract.get("controls", {}),
    }


def access_grant_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    registry = load_yaml(path)
    grants = registry.get("grants")
    if not isinstance(grants, list):
        return []
    registry_hash = hash_file(path)
    registry_scope = registry.get("registry_scope")
    return [
        access_grant_entry(path, registry_hash, registry_scope, grant)
        for grant in grants
        if isinstance(grant, dict)
    ]


def access_grant_entry(
    path: Path,
    registry_hash: str,
    registry_scope: object,
    grant: dict[str, Any],
) -> dict[str, Any]:
    grant_id = str(grant.get("id"))
    return {
        "urn": f"urn:enterprise-dp:access-grant:{grant_id}",
        "registry_path": path.as_posix(),
        "registry_hash": registry_hash,
        "registry_scope": registry_scope,
        "id": grant_id,
        "status": grant.get("status"),
        "data_product": grant.get("dataProduct"),
        "consumer": grant.get("consumer"),
        "consumer_type": grant.get("consumerType"),
        "persona": grant.get("persona"),
        "purpose": grant.get("purpose"),
        "access_mode": grant.get("accessMode"),
        "access_policy": grant.get("accessPolicy"),
        "consumer_contract": grant.get("consumerContract"),
        "requester": grant.get("requester"),
        "approver": grant.get("approver"),
        "steward_approval": grant.get("stewardApproval"),
        "approved_at": grant.get("approvedAt"),
        "expires_at": grant.get("expiresAt"),
        "review_cadence_days": grant.get("reviewCadenceDays"),
        "evidence": grant.get("evidence", {}),
        "constraints": grant.get("constraints", {}),
    }


def access_policy_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    registry = load_yaml(path)
    policies = registry.get("policies")
    if not isinstance(policies, list):
        return []
    registry_hash = hash_file(path)
    registry_scope = registry.get("registry_scope")
    return [
        access_policy_entry(path, registry_hash, registry_scope, policy)
        for policy in policies
        if isinstance(policy, dict)
    ]


def access_policy_entry(
    path: Path,
    registry_hash: str,
    registry_scope: object,
    policy: dict[str, Any],
) -> dict[str, Any]:
    policy_id = str(policy.get("id"))
    return {
        "urn": f"urn:enterprise-dp:access-policy:{policy_id}",
        "registry_path": path.as_posix(),
        "registry_hash": registry_hash,
        "registry_scope": registry_scope,
        "id": policy_id,
        "name": policy.get("name"),
        "policy_version": policy.get("policyVersion"),
        "status": policy.get("status"),
        "severity": policy.get("severity"),
        "owner": policy.get("owner"),
        "effective_from": policy.get("effectiveFrom"),
        "description": policy.get("description"),
        "applies_to": policy.get("appliesTo", {}),
        "allowed_personas": policy.get("allowedPersonas", []),
        "required_columns": policy.get("requiredColumns", []),
        "controls": policy.get("controls", {}),
    }


def retention_policy_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    registry = load_yaml(path)
    policies = registry.get("policies")
    if not isinstance(policies, list):
        return []
    registry_hash = hash_file(path)
    registry_scope = registry.get("registry_scope")
    return [
        retention_policy_entry(path, registry_hash, registry_scope, policy)
        for policy in policies
        if isinstance(policy, dict)
    ]


def retention_policy_entry(
    path: Path,
    registry_hash: str,
    registry_scope: object,
    policy: dict[str, Any],
) -> dict[str, Any]:
    policy_id = str(policy.get("id"))
    return {
        "urn": f"urn:enterprise-dp:retention-policy:{policy_id}",
        "registry_path": path.as_posix(),
        "registry_hash": registry_hash,
        "registry_scope": registry_scope,
        "id": policy_id,
        "name": policy.get("name"),
        "policy_version": policy.get("policyVersion"),
        "status": policy.get("status"),
        "severity": policy.get("severity"),
        "owner": policy.get("owner"),
        "effective_from": policy.get("effectiveFrom"),
        "description": policy.get("description"),
        "applies_to": policy.get("appliesTo", {}),
        "min_retention_days": policy.get("minRetentionDays"),
        "max_retention_days": policy.get("maxRetentionDays"),
        "erasure_required": policy.get("erasureRequired"),
        "evidence_requirements": policy.get("evidenceRequirements", []),
        "controls": policy.get("controls", {}),
    }


def release_profile_entries(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    registry = load_yaml(path)
    profiles = registry.get("profiles")
    if not isinstance(profiles, list):
        return []
    return [
        release_profile_entry(path, profile)
        for profile in profiles
        if isinstance(profile, dict)
    ]


def release_profile_entry(path: Path, profile: dict[str, Any]) -> dict[str, Any]:
    profile_id = str(profile.get("id"))
    return {
        "urn": f"urn:enterprise-dp:release-evidence-profile:{profile_id}",
        "registry_path": path.as_posix(),
        "registry_hash": hash_file(path),
        "id": profile_id,
        "name": profile.get("name"),
        "owner": profile.get("owner"),
        "status": profile.get("status"),
        "description": profile.get("description"),
        "applies_to": profile.get("appliesTo", {}),
        "required_gates": profile.get("requiredGates", []),
        "required_artifacts": profile.get("requiredArtifacts", []),
        "production_evidence_requirements": profile.get("productionEvidenceRequirements", {}),
        "local_evidence_requirements": profile.get("localEvidenceRequirements", {}),
    }


def run_evidence_entry(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    layers = manifest.get("layers", {})
    return {
        "urn": f"urn:enterprise-dp:run:{manifest.get('pipeline')}:{manifest.get('snapshot_id') or manifest.get('ingest_run_id')}",
        "manifest_path": path.as_posix(),
        "manifest_hash": hash_file(path),
        "pipeline": manifest.get("pipeline"),
        "product": manifest.get("product_id"),
        "topic": manifest.get("topic"),
        "bronze_target": manifest.get("bronze_target"),
        "snapshot_id": manifest.get("snapshot_id"),
        "ingest_run_id": manifest.get("ingest_run_id"),
        "generated_at": manifest.get("generated_at") or manifest.get("ingested_at"),
        "quality_passed": manifest.get("quality_passed"),
        "upstream_quality_passed": manifest.get("upstream_quality_passed"),
        "row_count": manifest.get("row_count") or manifest.get("approved", {}).get("row_count"),
        "content_hash": manifest.get("content_hash") or manifest.get("approved", {}).get("content_hash"),
        "source_positions": manifest.get("source_positions", []),
        "layers": layers,
        "lineage_edges": manifest.get("lineage_edges", []),
        "input": manifest.get("input", {}),
    }


def lineage_from_topics(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for topic in topics:
        bronze_target = topic.get("ingestion", {}).get("bronze_target")
        if bronze_target:
            edges.append(
                {
                    "type": "TOPIC_TO_BRONZE",
                    "source": topic["urn"],
                    "target": f"urn:enterprise-dp:data-product:{bronze_target}",
                    "product": topic.get("product"),
                    "domain": topic.get("domain"),
                }
            )
    return edges


def lineage_from_data_products(data_products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for data_product in data_products:
        target = str(data_product["urn"])
        for upstream in data_product.get("lineage", {}).get("upstream", []):
            if not isinstance(upstream, dict):
                continue
            upstream_name = upstream.get("name")
            if upstream_name:
                edges.append(
                    {
                        "type": "DATA_PRODUCT_UPSTREAM",
                        "source": f"urn:enterprise-dp:data-product:{upstream_name}",
                        "target": target,
                        "upstream_type": upstream.get("type"),
                        "product": data_product.get("product"),
                        "domain": data_product.get("domain"),
                    }
                )
    return edges


def lineage_from_use_cases(use_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for use_case in use_cases:
        source = use_case["urn"]
        for data_product in use_case.get("data_products", []):
            if not isinstance(data_product, dict):
                continue
            data_product_name = data_product.get("name")
            if data_product_name:
                edges.append(
                    {
                        "type": "USE_CASE_DATA_PRODUCT",
                        "source": source,
                        "target": f"urn:enterprise-dp:data-product:{data_product_name}",
                        "domain": use_case.get("domain"),
                        "priority": use_case.get("priority"),
                        "contract_status": data_product.get("contractStatus"),
                    }
                )
    return edges


def lineage_from_runs(run_evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for run in run_evidence:
        transform_edges = run_transform_edges(run)
        for transform_edge in transform_edges:
            source_layer = transform_edge["source"]
            target_layer = transform_edge["target"]
            edges.append(
                {
                    "type": "RUN_LAYER_TRANSFORM",
                    "source": f"urn:enterprise-dp:data-product:{source_layer}",
                    "target": f"urn:enterprise-dp:data-product:{target_layer}",
                    "run": run["urn"],
                    "product": run.get("product"),
                }
            )
        if run.get("bronze_target") and run.get("topic"):
            edges.append(
                {
                    "type": "RUN_TOPIC_TO_BRONZE",
                    "source": f"urn:enterprise-dp:topic:{run['topic']}",
                    "target": f"urn:enterprise-dp:data-product:{run['bronze_target']}",
                    "run": run["urn"],
                    "product": run.get("product"),
                }
            )
    return edges


def run_transform_edges(run: dict[str, Any]) -> list[dict[str, str]]:
    explicit_edges = run.get("lineage_edges")
    if isinstance(explicit_edges, list):
        parsed = [
            {
                "source": edge["source"],
                "target": edge["target"],
            }
            for edge in explicit_edges
            if isinstance(edge, dict)
            and edge.get("type", "RUN_LAYER_TRANSFORM") == "RUN_LAYER_TRANSFORM"
            and isinstance(edge.get("source"), str)
            and isinstance(edge.get("target"), str)
        ]
        if parsed:
            return parsed
    layer_names = ordered_layer_names(run.get("layers", {}))
    return [
        {
            "source": source_layer,
            "target": target_layer,
        }
        for source_layer, target_layer in zip(layer_names, layer_names[1:])
    ]


def ordered_layer_names(layers: object) -> list[str]:
    if not isinstance(layers, dict):
        return []
    return sorted(
        [name for name in layers if isinstance(name, str)],
        key=lambda name: (layer_rank(name), name),
    )


def layer_rank(name: str) -> int:
    if name.startswith("bronze."):
        return 0
    if name.startswith("silver."):
        return 1
    if name.startswith("gold."):
        return 2
    return 3


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON object expected")
    return data


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _mapping(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    return value if isinstance(value, dict) else {}


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

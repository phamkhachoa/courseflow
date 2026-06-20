from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str


@dataclass(frozen=True, slots=True)
class EvidenceValidationReport:
    manifest_count: int
    hash_verified_count: int
    non_lms_manifest_count: int
    vector_index_manifest_count: int
    promotion_count: int
    non_lms_promotion_count: int

    def to_dict(self) -> dict[str, int]:
        return {
            "manifestCount": self.manifest_count,
            "hashVerifiedCount": self.hash_verified_count,
            "nonLmsManifestCount": self.non_lms_manifest_count,
            "vectorIndexManifestCount": self.vector_index_manifest_count,
            "promotionCount": self.promotion_count,
            "nonLmsPromotionCount": self.non_lms_promotion_count,
        }


def validate_model_evidence(ai_root: Path | str) -> EvidenceValidationReport:
    root = Path(ai_root)
    manifest_dir = root / "platform" / "artifacts" / "manifests"
    if not manifest_dir.exists():
        raise RegistryValidationError(f"artifact manifest directory does not exist: {manifest_dir}")

    manifests = sorted(manifest_dir.glob("*.yaml"))
    if not manifests:
        raise RegistryValidationError("at least one artifact manifest is required")

    hash_verified = 0
    non_lms_manifest_count = 0
    vector_index_manifest_count = 0
    manifests_by_artifact_id: dict[str, dict[str, Any]] = {}
    for manifest_path in manifests:
        manifest = load_yaml(manifest_path)
        model_id = require_str(manifest, "model_id", str(manifest_path))
        artifact_id = require_str(manifest, "artifact_id", f"manifest {model_id}")
        if artifact_id in manifests_by_artifact_id:
            raise RegistryValidationError(f"duplicate artifact manifest id: {artifact_id}")
        manifests_by_artifact_id[artifact_id] = manifest
        require_str(manifest, "use_case_id", f"manifest {model_id}")
        product_id = require_str(manifest, "product", f"manifest {model_id}")
        if product_id != "lms-courseflow":
            non_lms_manifest_count += 1
        artifact_type = require_str(manifest, "artifact_type", f"manifest {model_id}")
        artifact_uri = require_str(manifest, "artifact_uri", f"manifest {model_id}")

        artifact_path = root / artifact_uri
        if not artifact_path.exists():
            raise RegistryValidationError(
                f"manifest {model_id} artifact_uri does not exist: {artifact_uri}"
            )

        lineage = manifest.get("lineage")
        if not isinstance(lineage, dict):
            raise RegistryValidationError(f"manifest {model_id} must define lineage")
        if artifact_type == "source_algorithm":
            validate_source_algorithm_manifest(root, lineage, model_id)
        elif artifact_type == "vector_index_snapshot":
            vector_index_manifest_count += 1
            validate_vector_index_snapshot_manifest(root, artifact_path, lineage, model_id)
        else:
            raise RegistryValidationError(
                f"manifest {model_id} has unsupported artifact_type: {artifact_type}"
            )

        artifact_hash = manifest.get("artifact_hash")
        if not isinstance(artifact_hash, dict):
            raise RegistryValidationError(f"manifest {model_id} must define artifact_hash")
        hash_algorithm = require_str(artifact_hash, "algorithm", f"manifest {model_id} hash")
        hash_value = require_str(artifact_hash, "value", f"manifest {model_id} hash")
        if hash_algorithm != "sha256":
            raise RegistryValidationError(f"manifest {model_id} only supports sha256 hashes")
        actual_hash = sha256_file(artifact_path)
        if actual_hash != hash_value:
            raise RegistryValidationError(
                f"manifest {model_id} artifact hash mismatch: {actual_hash} != {hash_value}"
            )
        hash_verified += 1

    promotion_count, non_lms_promotion_count = validate_artifact_promotions(
        root,
        manifests_by_artifact_id,
    )

    return EvidenceValidationReport(
        manifest_count=len(manifests),
        hash_verified_count=hash_verified,
        non_lms_manifest_count=non_lms_manifest_count,
        vector_index_manifest_count=vector_index_manifest_count,
        promotion_count=promotion_count,
        non_lms_promotion_count=non_lms_promotion_count,
    )


def validate_artifact_promotions(
    root: Path,
    manifests_by_artifact_id: dict[str, dict[str, Any]],
) -> tuple[int, int]:
    registry_path = root / "platform" / "artifacts" / "promotions" / "registry.yaml"
    if not registry_path.exists():
        raise RegistryValidationError(
            f"artifact promotion registry does not exist: {registry_path}"
        )
    registry = load_yaml(registry_path)
    policy = registry.get("policy")
    if not isinstance(policy, dict):
        raise RegistryValidationError("artifact promotion registry must define policy")
    allowed_stages = require_string_set(policy, "allowed_stages", "artifact promotion policy")
    rollback_required_for = require_string_set(
        policy,
        "require_rollback_target_for",
        "artifact promotion policy",
    )
    maker_checker_required = policy.get("maker_checker_required")
    if not isinstance(maker_checker_required, bool):
        raise RegistryValidationError(
            "artifact promotion policy maker_checker_required must be boolean"
        )

    promotions = require_mapping_list(registry, "promotions", "artifact promotion registry")
    if not promotions:
        raise RegistryValidationError("artifact promotion registry must define promotions")

    seen_ids: set[str] = set()
    active_keys: set[tuple[str, str]] = set()
    non_lms_count = 0
    for row in promotions:
        promotion_id = require_str(row, "promotion_id", "artifact promotion")
        if promotion_id in seen_ids:
            raise RegistryValidationError(
                f"artifact promotion registry has duplicate id: {promotion_id}"
            )
        seen_ids.add(promotion_id)
        artifact_id = require_str(row, "artifact_id", f"promotion {promotion_id}")
        manifest = manifests_by_artifact_id.get(artifact_id)
        if manifest is None:
            raise RegistryValidationError(
                f"promotion {promotion_id} references unknown artifact_id: {artifact_id}"
            )
        manifest_path = require_str(row, "artifact_manifest", f"promotion {promotion_id}")
        if not (root / manifest_path).exists():
            raise RegistryValidationError(
                f"promotion {promotion_id} artifact_manifest does not exist: {manifest_path}"
            )

        product = require_str(row, "product", f"promotion {promotion_id}")
        use_case_id = require_str(row, "use_case_id", f"promotion {promotion_id}")
        if product != require_str(manifest, "product", f"manifest {artifact_id}"):
            raise RegistryValidationError(
                f"promotion {promotion_id} product does not match manifest"
            )
        if use_case_id != require_str(manifest, "use_case_id", f"manifest {artifact_id}"):
            raise RegistryValidationError(
                f"promotion {promotion_id} use_case_id does not match manifest"
            )
        if product != "lms-courseflow":
            non_lms_count += 1

        stage = require_str(row, "stage", f"promotion {promotion_id}")
        if stage not in allowed_stages:
            raise RegistryValidationError(
                f"promotion {promotion_id} has unsupported stage: {stage}"
            )
        if stage in {"active", "active_baseline"}:
            key = (product, use_case_id)
            if key in active_keys:
                raise RegistryValidationError(
                    f"multiple active promotions for {product}/{use_case_id}"
                )
            active_keys.add(key)

        requested_by = require_str(row, "requested_by", f"promotion {promotion_id}")
        approved_by = require_str(row, "approved_by", f"promotion {promotion_id}")
        if maker_checker_required and requested_by == approved_by:
            raise RegistryValidationError(
                f"promotion {promotion_id} requester cannot approve own promotion"
            )
        require_str(row, "approved_at", f"promotion {promotion_id}")

        rollback_target = str(row.get("rollback_target_artifact_id", "")).strip()
        if stage in rollback_required_for and not rollback_target:
            raise RegistryValidationError(
                f"promotion {promotion_id} must define rollback_target_artifact_id"
            )
        if rollback_target and rollback_target not in manifests_by_artifact_id:
            raise RegistryValidationError(
                f"promotion {promotion_id} references unknown rollback target: {rollback_target}"
            )

        for gate_path in require_string_list(row, "required_gates", f"promotion {promotion_id}"):
            if not (root / gate_path).exists():
                raise RegistryValidationError(
                    f"promotion {promotion_id} required gate does not exist: {gate_path}"
                )
            gate_report = load_yaml(root / gate_path)
            require_str(gate_report, "status", f"promotion {promotion_id} gate {gate_path}")

    return len(promotions), non_lms_count


def validate_source_algorithm_manifest(
    root: Path,
    lineage: dict[str, Any],
    model_id: str,
) -> None:
    model_card = require_str(lineage, "model_card", f"manifest {model_id} lineage")
    evaluation_report = require_str(
        lineage,
        "evaluation_report",
        f"manifest {model_id} lineage",
    )
    feature_contract = require_str(
        lineage,
        "feature_contract",
        f"manifest {model_id} lineage",
    )
    model_io_contract = require_str(
        lineage,
        "model_io_contract",
        f"manifest {model_id} lineage",
    )

    for linked_path in (model_card, evaluation_report, feature_contract, model_io_contract):
        if not (root / linked_path).exists():
            raise RegistryValidationError(
                f"manifest {model_id} linked evidence does not exist: {linked_path}"
            )
    validate_evaluation_report_model_id(root, evaluation_report, model_id)


def validate_vector_index_snapshot_manifest(
    root: Path,
    artifact_path: Path,
    lineage: dict[str, Any],
    model_id: str,
) -> None:
    corpus = require_str(lineage, "corpus", f"manifest {model_id} lineage")
    collection_schema = require_str(
        lineage,
        "collection_schema",
        f"manifest {model_id} lineage",
    )
    evaluation_report = require_str(
        lineage,
        "evaluation_report",
        f"manifest {model_id} lineage",
    )
    shadow_evaluation_report = require_str(
        lineage,
        "shadow_evaluation_report",
        f"manifest {model_id} lineage",
    )
    builder = require_str(lineage, "builder", f"manifest {model_id} lineage")

    for linked_path in (
        corpus,
        collection_schema,
        evaluation_report,
        shadow_evaluation_report,
        builder,
    ):
        if not (root / linked_path).exists():
            raise RegistryValidationError(
                f"manifest {model_id} linked evidence does not exist: {linked_path}"
            )
    validate_evaluation_report_model_id(root, evaluation_report, model_id)
    validate_vector_index_snapshot_payload(load_json(artifact_path), model_id)


def validate_evaluation_report_model_id(
    root: Path,
    evaluation_report: str,
    model_id: str,
) -> None:
    eval_report = load_yaml(root / evaluation_report)
    eval_model_id = require_str(
        eval_report, "model_id", f"evaluation report {evaluation_report}"
    )
    if eval_model_id != model_id:
        raise RegistryValidationError(
            f"evaluation report model_id {eval_model_id} does not match manifest {model_id}"
        )


def validate_vector_index_snapshot_payload(payload: dict[str, Any], model_id: str) -> None:
    artifact_model_id = require_str(payload, "modelId", f"vector index snapshot {model_id}")
    if artifact_model_id != model_id:
        raise RegistryValidationError(
            f"vector index snapshot modelId {artifact_model_id} does not match {model_id}"
        )
    require_str(payload, "indexId", f"vector index snapshot {model_id}")
    require_str(payload, "collection", f"vector index snapshot {model_id}")
    require_str(payload, "checksum", f"vector index snapshot {model_id}")
    dimensions = payload.get("embeddingDimensions")
    if not isinstance(dimensions, int) or dimensions <= 0:
        raise RegistryValidationError(
            f"vector index snapshot {model_id} must define positive embeddingDimensions"
        )
    chunk_count = payload.get("chunkCount")
    entries = payload.get("entries")
    if not isinstance(chunk_count, int) or chunk_count <= 0:
        raise RegistryValidationError(
            f"vector index snapshot {model_id} must define positive chunkCount"
        )
    if not isinstance(entries, list) or len(entries) != chunk_count:
        raise RegistryValidationError(
            f"vector index snapshot {model_id} entries must match chunkCount"
        )
    seen_chunk_ids: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise RegistryValidationError(
                f"vector index snapshot {model_id} entries[{index}] must be a mapping"
            )
        chunk_id = require_str(entry, "chunkId", f"vector index snapshot {model_id}")
        if chunk_id in seen_chunk_ids:
            raise RegistryValidationError(
                f"vector index snapshot {model_id} has duplicate chunkId: {chunk_id}"
            )
        seen_chunk_ids.add(chunk_id)
        require_str(entry, "tenantId", f"vector index snapshot {model_id}")
        require_str(entry, "sourceRef", f"vector index snapshot {model_id}")
        require_str(entry, "accessScope", f"vector index snapshot {model_id}")
        require_str(entry, "piiClass", f"vector index snapshot {model_id}")
        text_hash = require_str(entry, "textHash", f"vector index snapshot {model_id}")
        if len(text_hash) != 64:
            raise RegistryValidationError(
                f"vector index snapshot {model_id} entry {chunk_id} textHash must be sha256"
            )


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise RegistryValidationError(f"JSON artifact must contain a mapping: {path}")
    return loaded


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
    if not isinstance(value, list) or not value:
        raise RegistryValidationError(f"{owner} must define non-empty list field {key}")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RegistryValidationError(f"{owner} {key} must contain strings")
        result.append(item.strip())
    return result


def require_string_set(row: dict[str, Any], key: str, owner: str) -> set[str]:
    return set(require_string_list(row, key, owner))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

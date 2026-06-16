from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_df.catalog import hash_file, load_json


MANIFEST_VERSION = 1


@dataclass(frozen=True)
class ReleasePromotionResult:
    output_path: Path
    manifest: dict[str, Any]


@dataclass(frozen=True)
class ReleaseActivationResult:
    output_path: Path
    manifest: dict[str, Any]
    active_state_path: Path


def write_release_promotion_manifest(
    release_evidence_path: str | Path,
    output_path: str | Path,
    *,
    target_environment: str,
    requested_by: str,
    approver: str,
    generated_at: str | None = None,
    change_ticket: str | None = None,
) -> ReleasePromotionResult:
    evidence_path = Path(release_evidence_path)
    evidence = load_json(evidence_path)
    manifest = build_release_promotion_manifest(
        evidence,
        release_evidence_path=evidence_path,
        target_environment=target_environment,
        requested_by=requested_by,
        approver=approver,
        generated_at=generated_at,
        change_ticket=change_ticket,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    return ReleasePromotionResult(output_path=target, manifest=manifest)


def write_release_activation_manifest(
    promotion_manifest_path: str | Path,
    output_path: str | Path,
    *,
    active_state_path: str | Path,
    activated_by: str,
    generated_at: str | None = None,
) -> ReleaseActivationResult:
    promotion_path = Path(promotion_manifest_path)
    active_path = Path(active_state_path)
    promotion = load_json(promotion_path)
    previous_state = load_json(active_path) if active_path.is_file() else None
    manifest = build_release_activation_manifest(
        promotion,
        promotion_manifest_path=promotion_path,
        active_state_path=active_path,
        previous_state=previous_state,
        activated_by=activated_by,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    if manifest["passed"]:
        active_path.parent.mkdir(parents=True, exist_ok=True)
        active_path.write_text(f"{canonical_json(manifest['active_pointer'])}\n", encoding="utf-8")
    return ReleaseActivationResult(output_path=target, manifest=manifest, active_state_path=active_path)


def build_release_promotion_manifest(
    evidence: dict[str, Any],
    *,
    release_evidence_path: str | Path,
    target_environment: str,
    requested_by: str,
    approver: str,
    generated_at: str | None = None,
    change_ticket: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or utc_now()
    evidence_path = Path(release_evidence_path)
    gate_summary = summarize_gates(evidence)
    output = release_output_reference(evidence)
    checks = promotion_checks(
        evidence,
        target_environment=target_environment,
        requested_by=requested_by,
        approver=approver,
        output=output,
        gate_summary=gate_summary,
    )
    passed = all(item["passed"] is True for item in checks)
    promotion_id = stable_id(
        evidence.get("release_id"),
        target_environment,
        output.get("data_product"),
        output.get("dataset_snapshot_id"),
        output.get("content_hash"),
        evidence_path.as_posix(),
    )
    return {
        "artifact_type": "release_promotion_manifest.v1",
        "manifest_version": MANIFEST_VERSION,
        "promotion_id": promotion_id,
        "promotion_state": "approved_for_activation" if passed else "blocked",
        "generated_at": generated,
        "release_id": evidence.get("release_id"),
        "target_environment": target_environment,
        "release_environment": evidence.get("environment"),
        "requested_by": requested_by,
        "approver": approver,
        "change_ticket": change_ticket,
        "release_evidence_uri": evidence_path.as_posix(),
        "release_evidence_hash": hash_file(evidence_path),
        "source_release_passed": evidence.get("release_passed"),
        "use_case_id": evidence.get("use_case_id"),
        "runner_id": evidence.get("runner_id"),
        "output": output,
        "gate_summary": gate_summary,
        "checks": checks,
        "failures": [
            {"check": item["name"], "details": item.get("details", {})}
            for item in checks
            if item.get("passed") is not True
        ],
        "passed": passed,
    }


def build_release_activation_manifest(
    promotion: dict[str, Any],
    *,
    promotion_manifest_path: str | Path,
    active_state_path: str | Path,
    previous_state: dict[str, Any] | None,
    activated_by: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or utc_now()
    promotion_path = Path(promotion_manifest_path)
    active_path = Path(active_state_path)
    output = promotion.get("output") if isinstance(promotion.get("output"), dict) else {}
    previous_active = previous_state if isinstance(previous_state, dict) else None
    checks = activation_checks(promotion, output=output, previous_state=previous_active, activated_by=activated_by)
    passed = all(item["passed"] is True for item in checks)
    activation_id = stable_id(
        promotion.get("promotion_id"),
        promotion.get("target_environment"),
        output.get("data_product"),
        output.get("dataset_snapshot_id"),
        output.get("content_hash"),
        active_path.as_posix(),
    )
    active_pointer = {
        "artifact_type": "release_active_pointer.v1",
        "pointer_version": 1,
        "activation_id": activation_id,
        "environment": promotion.get("target_environment"),
        "release_id": promotion.get("release_id"),
        "data_product": output.get("data_product"),
        "dataset_snapshot_id": output.get("dataset_snapshot_id"),
        "content_hash": output.get("content_hash"),
        "row_count": output.get("row_count"),
        "activated_at": generated,
        "activated_by": activated_by,
        "promotion_manifest_uri": promotion_path.as_posix(),
        "promotion_manifest_hash": hash_file(promotion_path),
        "rollback_target": rollback_target(previous_active),
    }
    return {
        "artifact_type": "release_activation_manifest.v1",
        "manifest_version": 1,
        "activation_id": activation_id,
        "activation_state": "activated" if passed else "blocked",
        "generated_at": generated,
        "activated_by": activated_by,
        "active_state_path": active_path.as_posix(),
        "promotion_manifest_uri": promotion_path.as_posix(),
        "promotion_manifest_hash": hash_file(promotion_path),
        "promotion_id": promotion.get("promotion_id"),
        "release_id": promotion.get("release_id"),
        "target_environment": promotion.get("target_environment"),
        "output": output,
        "previous_active": previous_active,
        "active_pointer": active_pointer,
        "checks": checks,
        "failures": [
            {"check": item["name"], "details": item.get("details", {})}
            for item in checks
            if item.get("passed") is not True
        ],
        "passed": passed,
    }


def promotion_checks(
    evidence: dict[str, Any],
    *,
    target_environment: str,
    requested_by: str,
    approver: str,
    output: dict[str, Any],
    gate_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        check("release_passed", evidence.get("release_passed") is True, {"release_passed": evidence.get("release_passed")}),
        check(
            "release_environment_matches_target",
            evidence.get("environment") == target_environment,
            {"release_environment": evidence.get("environment"), "target_environment": target_environment},
        ),
        check("requested_by_declared", non_empty(requested_by), {"requested_by": requested_by}),
        check("approver_declared", non_empty(approver), {"approver": approver}),
        check(
            "maker_checker_separated",
            non_empty(requested_by) and non_empty(approver) and requested_by != approver,
            {"requested_by": requested_by, "approver": approver},
        ),
        check("all_release_gates_passed", gate_summary["failed_count"] == 0, gate_summary),
        check("output_data_product_identified", non_empty(output.get("data_product")), {"output": output}),
        check("output_snapshot_identified", non_empty(output.get("dataset_snapshot_id")), {"output": output}),
        check("output_content_hash_identified", non_empty(output.get("content_hash")), {"output": output}),
    ]


def activation_checks(
    promotion: dict[str, Any],
    *,
    output: dict[str, Any],
    previous_state: dict[str, Any] | None,
    activated_by: str,
) -> list[dict[str, Any]]:
    production_like = promotion.get("target_environment") not in {"local", "dev"}
    requested_by = promotion.get("requested_by")
    return [
        check("promotion_passed", promotion.get("passed") is True, {"passed": promotion.get("passed")}),
        check(
            "promotion_approved_for_activation",
            promotion.get("promotion_state") == "approved_for_activation",
            {"promotion_state": promotion.get("promotion_state")},
        ),
        check("activated_by_declared", non_empty(activated_by), {"activated_by": activated_by}),
        check(
            "activation_requester_separated",
            non_empty(activated_by) and non_empty(requested_by) and activated_by != requested_by,
            {"requested_by": requested_by, "activated_by": activated_by},
        ),
        check("output_data_product_identified", non_empty(output.get("data_product")), {"output": output}),
        check("output_snapshot_identified", non_empty(output.get("dataset_snapshot_id")), {"output": output}),
        check("output_content_hash_identified", non_empty(output.get("content_hash")), {"output": output}),
        check(
            "prod_has_rollback_target",
            not production_like or rollback_target(previous_state) is not None,
            {"target_environment": promotion.get("target_environment"), "previous_active": previous_state},
        ),
    ]


def rollback_target(previous_state: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(previous_state, dict):
        return None
    data_product = previous_state.get("data_product")
    snapshot_id = previous_state.get("dataset_snapshot_id")
    content_hash = previous_state.get("content_hash")
    if not (non_empty(data_product) and non_empty(snapshot_id) and non_empty(content_hash)):
        return None
    return {
        "data_product": data_product,
        "dataset_snapshot_id": snapshot_id,
        "content_hash": content_hash,
        "release_id": previous_state.get("release_id"),
        "activation_id": previous_state.get("activation_id"),
    }


def release_output_reference(evidence: dict[str, Any]) -> dict[str, Any]:
    data_product = evidence.get("primary_output")
    if not isinstance(data_product, str) and evidence.get("gold_dataset_snapshot_id"):
        data_product = "gold.recsys_interactions"
    snapshot_id = evidence.get("pipeline_run_id") or evidence.get("gold_dataset_snapshot_id")
    manifest = load_pipeline_manifest_from_evidence(evidence)
    layer = manifest.get("layers", {}).get(data_product, {}) if isinstance(data_product, str) else {}
    content_hash = layer.get("content_hash") or manifest.get("content_hash")
    row_count = layer.get("row_count") or manifest.get("row_count")
    return {
        "data_product": data_product,
        "dataset_snapshot_id": snapshot_id,
        "content_hash": content_hash,
        "row_count": row_count,
        "pipeline_manifest_path": evidence.get("artifacts", {}).get("pipeline_manifest_path"),
        "pipeline_manifest_hash": evidence.get("artifacts", {}).get("pipeline_manifest_hash"),
    }


def load_pipeline_manifest_from_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    artifacts = evidence.get("artifacts", {})
    path_value = artifacts.get("pipeline_manifest_path") or artifacts.get("medallion_manifest_path")
    if not isinstance(path_value, str) or not Path(path_value).is_file():
        return {}
    return load_json(Path(path_value))


def summarize_gates(evidence: dict[str, Any]) -> dict[str, Any]:
    gates = [gate for gate in evidence.get("gates", []) if isinstance(gate, dict)]
    failed = [gate.get("gate_id") for gate in gates if gate.get("passed") is not True]
    return {
        "total_count": len(gates),
        "passed_count": len(gates) - len(failed),
        "failed_count": len(failed),
        "failed_gates": failed,
    }


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def canonical_json(record: Any) -> str:
    return json.dumps(record, allow_nan=False, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

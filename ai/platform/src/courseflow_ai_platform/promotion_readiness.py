from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

READY_GATE_STATUSES = frozenset(
    {
        "accepted_baseline",
        "accepted_contract_baseline",
        "accepted_shadow_baseline",
        "baseline_accepted",
        "passed",
    }
)


@dataclass(frozen=True, slots=True)
class PromotionGateReadiness:
    path: str
    status: str
    status_ready: bool
    evaluated_at: str
    age_days: int | None
    fresh: bool
    ready: bool

    def to_dict(self) -> dict[str, bool | int | None | str]:
        return {
            "ageDays": self.age_days,
            "evaluatedAt": self.evaluated_at,
            "fresh": self.fresh,
            "path": self.path,
            "ready": self.ready,
            "status": self.status,
            "statusReady": self.status_ready,
        }


@dataclass(frozen=True, slots=True)
class PromotionReadinessItem:
    promotion_id: str
    artifact_id: str
    artifact_manifest: str
    model_id: str
    artifact_type: str
    product: str
    use_case_id: str
    stage: str
    stage_group: str
    is_non_lms: bool
    artifact_created_at: str
    artifact_age_days: int | None
    artifact_fresh: bool
    required_gate_count: int
    gate_ready_count: int
    rollback_required: bool
    rollback_ready: bool
    rollback_target_artifact_id: str
    maker_checker_satisfied: bool
    requested_by: str
    approved_by: str
    approved_at: str
    ready_for_stage: bool
    blocked_reasons: tuple[str, ...]
    gates: tuple[PromotionGateReadiness, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "approvedAt": self.approved_at,
            "approvedBy": self.approved_by,
            "artifactId": self.artifact_id,
            "artifactAgeDays": self.artifact_age_days,
            "artifactCreatedAt": self.artifact_created_at,
            "artifactFresh": self.artifact_fresh,
            "artifactManifest": self.artifact_manifest,
            "artifactType": self.artifact_type,
            "blockedReasons": list(self.blocked_reasons),
            "gateReadyCount": self.gate_ready_count,
            "gates": [gate.to_dict() for gate in self.gates],
            "isNonLms": self.is_non_lms,
            "makerCheckerSatisfied": self.maker_checker_satisfied,
            "modelId": self.model_id,
            "product": self.product,
            "promotionId": self.promotion_id,
            "readyForStage": self.ready_for_stage,
            "requestedBy": self.requested_by,
            "requiredGateCount": self.required_gate_count,
            "rollbackReady": self.rollback_ready,
            "rollbackRequired": self.rollback_required,
            "rollbackTargetArtifactId": self.rollback_target_artifact_id,
            "stage": self.stage,
            "stageGroup": self.stage_group,
            "useCaseId": self.use_case_id,
        }


@dataclass(frozen=True, slots=True)
class PromotionReadinessReport:
    promotion_count: int
    ready_count: int
    blocked_count: int
    active_count: int
    approved_count: int
    shadow_count: int
    non_lms_count: int
    required_gate_count: int
    gate_ready_count: int
    rollback_required_count: int
    rollback_ready_count: int
    maker_checker_required: bool
    maker_checker_satisfied_count: int
    max_gate_age_days: int | None
    stale_gate_count: int
    missing_gate_evaluated_at_count: int
    max_artifact_age_days: int | None
    stale_artifact_count: int
    missing_artifact_created_at_count: int
    items: tuple[PromotionReadinessItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionQueue": build_action_queue(self.items),
            "activeCount": self.active_count,
            "approvedCount": self.approved_count,
            "blockedCount": self.blocked_count,
            "gateReadyCount": self.gate_ready_count,
            "items": [item.to_dict() for item in self.items],
            "makerCheckerRequired": self.maker_checker_required,
            "makerCheckerSatisfiedCount": self.maker_checker_satisfied_count,
            "maxArtifactAgeDays": self.max_artifact_age_days,
            "maxGateAgeDays": self.max_gate_age_days,
            "missingArtifactCreatedAtCount": self.missing_artifact_created_at_count,
            "missingGateEvaluatedAtCount": self.missing_gate_evaluated_at_count,
            "nonLmsCount": self.non_lms_count,
            "promotionCount": self.promotion_count,
            "readyCount": self.ready_count,
            "requiredGateCount": self.required_gate_count,
            "rollbackReadyCount": self.rollback_ready_count,
            "rollbackRequiredCount": self.rollback_required_count,
            "shadowCount": self.shadow_count,
            "staleArtifactCount": self.stale_artifact_count,
            "staleGateCount": self.stale_gate_count,
        }

    def to_snapshot_dict(
        self,
        *,
        generated_at: str,
        source_registry: str = "platform/artifacts/promotions/registry.yaml",
    ) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "promotion-readiness-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "source_registry": source_registry,
            "summary": {
                "promotion_count": self.promotion_count,
                "ready_count": self.ready_count,
                "blocked_count": self.blocked_count,
                "active_count": self.active_count,
                "approved_count": self.approved_count,
                "shadow_count": self.shadow_count,
                "non_lms_count": self.non_lms_count,
            },
            "action_queue": build_snapshot_action_queue(self.items),
            "gate_readiness": {
                "required_gate_count": self.required_gate_count,
                "gate_ready_count": self.gate_ready_count,
                "missing_gate_count": 0,
                "failed_gate_count": self.required_gate_count - self.gate_ready_count,
            },
            "freshness": {
                "max_artifact_age_days": self.max_artifact_age_days,
                "max_gate_age_days": self.max_gate_age_days,
                "stale_artifact_count": self.stale_artifact_count,
                "stale_gate_count": self.stale_gate_count,
                "missing_artifact_created_at_count": self.missing_artifact_created_at_count,
                "missing_gate_evaluated_at_count": self.missing_gate_evaluated_at_count,
            },
            "rollback_readiness": {
                "rollback_required_count": self.rollback_required_count,
                "rollback_ready_count": self.rollback_ready_count,
                "rollback_missing_count": self.rollback_required_count
                - self.rollback_ready_count,
            },
            "maker_checker": {
                "required": self.maker_checker_required,
                "satisfied_count": self.maker_checker_satisfied_count,
                "violation_count": self.promotion_count
                - self.maker_checker_satisfied_count,
            },
            "items": [promotion_item_to_snapshot_dict(item) for item in self.items],
        }


def build_promotion_readiness_report(
    ai_root: Path | str,
    *,
    as_of: str | date | None = None,
) -> PromotionReadinessReport:
    root = Path(ai_root)
    as_of_date = parse_optional_date(as_of, "promotion readiness as_of")
    manifests_by_artifact_id = load_artifact_manifests(root)
    registry = load_yaml(root / "platform" / "artifacts" / "promotions" / "registry.yaml")

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
    max_gate_age_days = load_max_gate_age_days(policy)
    max_artifact_age_days = load_max_artifact_age_days(policy)

    promotions = require_mapping_list(registry, "promotions", "artifact promotion registry")
    if not promotions:
        raise RegistryValidationError("artifact promotion registry must define promotions")

    items: list[PromotionReadinessItem] = []
    seen_ids: set[str] = set()
    for row in promotions:
        item = build_promotion_readiness_item(
            root,
            row,
            manifests_by_artifact_id,
            allowed_stages,
            rollback_required_for,
            maker_checker_required,
            max_gate_age_days,
            max_artifact_age_days,
            as_of_date,
        )
        if item.promotion_id in seen_ids:
            raise RegistryValidationError(
                f"artifact promotion registry has duplicate id: {item.promotion_id}"
            )
        seen_ids.add(item.promotion_id)
        items.append(item)

    return PromotionReadinessReport(
        promotion_count=len(items),
        ready_count=sum(1 for item in items if item.ready_for_stage),
        blocked_count=sum(1 for item in items if not item.ready_for_stage),
        active_count=sum(1 for item in items if item.stage_group == "active"),
        approved_count=sum(1 for item in items if item.stage_group == "approved"),
        shadow_count=sum(1 for item in items if item.stage_group == "shadow"),
        non_lms_count=sum(1 for item in items if item.is_non_lms),
        required_gate_count=sum(item.required_gate_count for item in items),
        gate_ready_count=sum(item.gate_ready_count for item in items),
        rollback_required_count=sum(1 for item in items if item.rollback_required),
        rollback_ready_count=sum(
            1 for item in items if item.rollback_required and item.rollback_ready
        ),
        maker_checker_required=maker_checker_required,
        maker_checker_satisfied_count=sum(1 for item in items if item.maker_checker_satisfied),
        max_gate_age_days=max_gate_age_days,
        stale_gate_count=sum(1 for item in items for gate in item.gates if not gate.fresh),
        missing_gate_evaluated_at_count=sum(
            1 for item in items for gate in item.gates if not gate.evaluated_at
        ),
        max_artifact_age_days=max_artifact_age_days,
        stale_artifact_count=sum(1 for item in items if not item.artifact_fresh),
        missing_artifact_created_at_count=sum(
            1 for item in items if not item.artifact_created_at
        ),
        items=tuple(items),
    )


def build_promotion_readiness_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    report = build_promotion_readiness_report(ai_root, as_of=report_date)
    return report.to_snapshot_dict(generated_at=report_date)


def write_promotion_readiness_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    snapshot = build_promotion_readiness_snapshot(root, generated_at=generated_at)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(snapshot, handle, sort_keys=False)
    return target


def build_promotion_readiness_item(
    root: Path,
    row: dict[str, Any],
    manifests_by_artifact_id: dict[str, dict[str, Any]],
    allowed_stages: set[str],
    rollback_required_for: set[str],
    maker_checker_required: bool,
    max_gate_age_days: int | None,
    max_artifact_age_days: int | None,
    as_of: date | None,
) -> PromotionReadinessItem:
    promotion_id = require_str(row, "promotion_id", "artifact promotion")
    owner = f"promotion {promotion_id}"
    artifact_id = require_str(row, "artifact_id", owner)
    manifest = manifests_by_artifact_id.get(artifact_id)
    if manifest is None:
        raise RegistryValidationError(f"{owner} references unknown artifact_id: {artifact_id}")

    artifact_manifest = require_str(row, "artifact_manifest", owner)
    if not (root / artifact_manifest).exists():
        raise RegistryValidationError(
            f"{owner} artifact_manifest does not exist: {artifact_manifest}"
        )

    model_id = require_str(manifest, "model_id", f"manifest {artifact_id}")
    artifact_type = require_str(manifest, "artifact_type", f"manifest {artifact_id}")
    artifact_created_at, artifact_age_days, artifact_fresh = evaluate_artifact_freshness(
        manifest,
        artifact_id,
        max_artifact_age_days=max_artifact_age_days,
        as_of=as_of,
    )
    product = require_str(row, "product", owner)
    use_case_id = require_str(row, "use_case_id", owner)
    if product != require_str(manifest, "product", f"manifest {artifact_id}"):
        raise RegistryValidationError(f"{owner} product does not match manifest")
    if use_case_id != require_str(manifest, "use_case_id", f"manifest {artifact_id}"):
        raise RegistryValidationError(f"{owner} use_case_id does not match manifest")

    stage = require_str(row, "stage", owner)
    if stage not in allowed_stages:
        raise RegistryValidationError(f"{owner} has unsupported stage: {stage}")

    requested_by = require_str(row, "requested_by", owner)
    approved_by = require_str(row, "approved_by", owner)
    approved_at = require_str(row, "approved_at", owner)
    maker_checker_satisfied = not maker_checker_required or requested_by != approved_by

    rollback_target = str(row.get("rollback_target_artifact_id", "")).strip()
    rollback_required = stage in rollback_required_for
    rollback_ready = bool(rollback_target) and rollback_target in manifests_by_artifact_id

    gates = tuple(
        build_gate_readiness(root, gate_path, max_gate_age_days=max_gate_age_days, as_of=as_of)
        for gate_path in require_string_list(row, "required_gates", owner)
    )
    gate_ready_count = sum(1 for gate in gates if gate.ready)

    blocked_reasons = build_blocked_reasons(
        gates,
        artifact_fresh,
        maker_checker_satisfied,
        rollback_required,
        rollback_ready,
    )
    return PromotionReadinessItem(
        promotion_id=promotion_id,
        artifact_id=artifact_id,
        artifact_manifest=artifact_manifest,
        model_id=model_id,
        artifact_type=artifact_type,
        product=product,
        use_case_id=use_case_id,
        stage=stage,
        stage_group=stage_group(stage),
        is_non_lms=product != "lms-courseflow",
        artifact_created_at=artifact_created_at,
        artifact_age_days=artifact_age_days,
        artifact_fresh=artifact_fresh,
        required_gate_count=len(gates),
        gate_ready_count=gate_ready_count,
        rollback_required=rollback_required,
        rollback_ready=rollback_ready,
        rollback_target_artifact_id=rollback_target,
        maker_checker_satisfied=maker_checker_satisfied,
        requested_by=requested_by,
        approved_by=approved_by,
        approved_at=approved_at,
        ready_for_stage=not blocked_reasons,
        blocked_reasons=blocked_reasons,
        gates=gates,
    )


def build_action_queue(items: tuple[PromotionReadinessItem, ...]) -> dict[str, list[str]]:
    snapshot_queue = build_snapshot_action_queue(items)
    return {
        "activeMonitoring": snapshot_queue["active_monitoring"],
        "readyToActivate": snapshot_queue["ready_to_activate"],
        "keepShadow": snapshot_queue["keep_shadow"],
        "blocked": snapshot_queue["blocked"],
    }


def build_snapshot_action_queue(
    items: tuple[PromotionReadinessItem, ...],
) -> dict[str, list[str]]:
    return {
        "active_monitoring": [
            item.promotion_id
            for item in items
            if item.ready_for_stage and item.stage_group == "active"
        ],
        "ready_to_activate": [
            item.promotion_id
            for item in items
            if item.ready_for_stage and item.stage_group == "approved"
        ],
        "keep_shadow": [
            item.promotion_id
            for item in items
            if item.ready_for_stage and item.stage_group == "shadow"
        ],
        "blocked": [item.promotion_id for item in items if not item.ready_for_stage],
    }


def promotion_item_to_snapshot_dict(item: PromotionReadinessItem) -> dict[str, Any]:
    return {
        "promotion_id": item.promotion_id,
        "artifact_id": item.artifact_id,
        "artifact_manifest": item.artifact_manifest,
        "model_id": item.model_id,
        "artifact_type": item.artifact_type,
        "artifact_freshness": {
            "created_at": item.artifact_created_at,
            "age_days": item.artifact_age_days,
            "fresh": item.artifact_fresh,
        },
        "product": item.product,
        "use_case_id": item.use_case_id,
        "stage": item.stage,
        "stage_group": item.stage_group,
        "is_non_lms": item.is_non_lms,
        "ready_for_stage": item.ready_for_stage,
        "blocked_reasons": list(item.blocked_reasons),
        "gate_readiness": {
            "required_gate_count": item.required_gate_count,
            "gate_ready_count": item.gate_ready_count,
            "gates": [
                {
                    "age_days": gate.age_days,
                    "evaluated_at": gate.evaluated_at,
                    "fresh": gate.fresh,
                    "path": gate.path,
                    "status": gate.status,
                    "status_ready": gate.status_ready,
                    "ready": gate.ready,
                }
                for gate in item.gates
            ],
        },
        "rollback_readiness": {
            "required": item.rollback_required,
            "ready": item.rollback_ready,
            "rollback_target_artifact_id": item.rollback_target_artifact_id,
        },
        "maker_checker": {
            "requested_by": item.requested_by,
            "approved_by": item.approved_by,
            "approved_at": item.approved_at,
            "satisfied": item.maker_checker_satisfied,
        },
    }


def build_gate_readiness(
    root: Path,
    gate_path: str,
    *,
    max_gate_age_days: int | None,
    as_of: date | None,
) -> PromotionGateReadiness:
    full_path = root / gate_path
    if not full_path.exists():
        raise RegistryValidationError(f"promotion required gate does not exist: {gate_path}")
    gate_report = load_yaml(full_path)
    status = require_str(gate_report, "status", f"promotion gate {gate_path}")
    evaluated_at, age_days, fresh = evaluate_gate_freshness(
        gate_report,
        gate_path,
        max_gate_age_days=max_gate_age_days,
        as_of=as_of,
    )
    status_ready = is_ready_gate_status(status)
    return PromotionGateReadiness(
        age_days=age_days,
        evaluated_at=evaluated_at,
        fresh=fresh,
        path=gate_path,
        ready=status_ready and fresh,
        status=status,
        status_ready=status_ready,
    )


def build_blocked_reasons(
    gates: tuple[PromotionGateReadiness, ...],
    artifact_fresh: bool,
    maker_checker_satisfied: bool,
    rollback_required: bool,
    rollback_ready: bool,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not gates:
        reasons.append("required_gates_missing")
    if any(not gate.status_ready for gate in gates):
        reasons.append("gate_not_ready")
    if any(not gate.fresh for gate in gates):
        reasons.append("gate_evidence_stale")
    if not artifact_fresh:
        reasons.append("artifact_evidence_stale")
    if not maker_checker_satisfied:
        reasons.append("maker_checker_violation")
    if rollback_required and not rollback_ready:
        reasons.append("rollback_target_missing")
    return tuple(reasons)


def is_ready_gate_status(status: str) -> bool:
    normalized = status.strip().lower()
    return normalized in READY_GATE_STATUSES or normalized.startswith("accepted_")


def evaluate_gate_freshness(
    gate_report: dict[str, Any],
    gate_path: str,
    *,
    max_gate_age_days: int | None,
    as_of: date | None,
) -> tuple[str, int | None, bool]:
    value = gate_report.get("evaluated_at")
    if value is None:
        return "", None, max_gate_age_days is None or as_of is None
    evaluated_at = parse_required_date(value, f"promotion gate {gate_path} evaluated_at")
    if max_gate_age_days is None or as_of is None:
        return evaluated_at.isoformat(), None, True
    age_days = (as_of - evaluated_at).days
    if age_days < 0:
        raise RegistryValidationError(
            f"promotion gate {gate_path} evaluated_at cannot be after as_of"
        )
    return evaluated_at.isoformat(), age_days, age_days <= max_gate_age_days


def evaluate_artifact_freshness(
    manifest: dict[str, Any],
    artifact_id: str,
    *,
    max_artifact_age_days: int | None,
    as_of: date | None,
) -> tuple[str, int | None, bool]:
    value = manifest.get("created_at")
    if value is None:
        return "", None, max_artifact_age_days is None or as_of is None
    created_at = parse_required_date(value, f"manifest {artifact_id} created_at")
    if max_artifact_age_days is None or as_of is None:
        return created_at.isoformat(), None, True
    age_days = (as_of - created_at).days
    if age_days < 0:
        raise RegistryValidationError(
            f"manifest {artifact_id} created_at cannot be after as_of"
        )
    return created_at.isoformat(), age_days, age_days <= max_artifact_age_days


def load_max_gate_age_days(policy: dict[str, Any]) -> int | None:
    readiness = policy.get("readiness", {})
    if readiness is None:
        return None
    if not isinstance(readiness, dict):
        raise RegistryValidationError("artifact promotion policy readiness must be a mapping")
    stale_blocks = readiness.get("stale_gate_blocks_release", True)
    if not isinstance(stale_blocks, bool):
        raise RegistryValidationError(
            "artifact promotion policy readiness stale_gate_blocks_release must be boolean"
        )
    if not stale_blocks:
        return None
    value = readiness.get("max_gate_age_days")
    if value is None:
        return None
    if not isinstance(value, int) or value <= 0:
        raise RegistryValidationError(
            "artifact promotion policy readiness max_gate_age_days must be positive integer"
        )
    return value


def load_max_artifact_age_days(policy: dict[str, Any]) -> int | None:
    return load_max_age_days(
        policy,
        age_key="max_artifact_age_days",
        enabled_key="stale_artifact_blocks_release",
    )


def load_max_age_days(policy: dict[str, Any], *, age_key: str, enabled_key: str) -> int | None:
    readiness = policy.get("readiness", {})
    if readiness is None:
        return None
    if not isinstance(readiness, dict):
        raise RegistryValidationError("artifact promotion policy readiness must be a mapping")
    stale_blocks = readiness.get(enabled_key, True)
    if not isinstance(stale_blocks, bool):
        raise RegistryValidationError(
            f"artifact promotion policy readiness {enabled_key} must be boolean"
        )
    if not stale_blocks:
        return None
    value = readiness.get(age_key)
    if value is None:
        return None
    if not isinstance(value, int) or value <= 0:
        raise RegistryValidationError(
            f"artifact promotion policy readiness {age_key} must be positive integer"
        )
    return value


def parse_optional_date(value: str | date | None, owner: str) -> date | None:
    if value is None:
        return None
    return parse_required_date(value, owner)


def parse_required_date(value: str | date, owner: str) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise RegistryValidationError(f"{owner} must be an ISO date")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise RegistryValidationError(f"{owner} must be an ISO date") from exc


def stage_group(stage: str) -> str:
    if stage in {"active", "active_baseline"}:
        return "active"
    if stage == "approved_baseline":
        return "approved"
    if stage == "shadow":
        return "shadow"
    return "inactive"


def load_artifact_manifests(root: Path) -> dict[str, dict[str, Any]]:
    manifest_dir = root / "platform" / "artifacts" / "manifests"
    if not manifest_dir.exists():
        raise RegistryValidationError(f"artifact manifest directory does not exist: {manifest_dir}")
    manifests: dict[str, dict[str, Any]] = {}
    for manifest_path in sorted(manifest_dir.glob("*.yaml")):
        manifest = load_yaml(manifest_path)
        artifact_id = require_str(manifest, "artifact_id", str(manifest_path))
        if artifact_id in manifests:
            raise RegistryValidationError(f"duplicate artifact manifest id: {artifact_id}")
        manifests[artifact_id] = manifest
    if not manifests:
        raise RegistryValidationError("at least one artifact manifest is required")
    return manifests


def default_snapshot_path(root: Path) -> Path:
    return root / "platform" / "artifacts" / "promotions" / "reports" / (
        "promotion-readiness-v1.yaml"
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
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a non-empty string")
        result.append(item.strip())
    return result


def require_string_set(row: dict[str, Any], key: str, owner: str) -> set[str]:
    values = require_string_list(row, key, owner)
    result = set(values)
    if len(result) != len(values):
        raise RegistryValidationError(f"{owner} {key} must not contain duplicates")
    return result

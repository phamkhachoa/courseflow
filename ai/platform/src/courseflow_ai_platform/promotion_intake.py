from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.promotion_readiness import (
    build_promotion_readiness_report,
    is_ready_gate_status,
)
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str


@dataclass(frozen=True, slots=True)
class PromotionIntakeRequest:
    request_id: str
    request_type: str
    product: str
    use_case_id: str
    artifact_id: str
    artifact_manifest: str
    source_promotion_id: str
    requested_stage: str
    status: str
    submitted_by: str
    business_owner: str
    submitted_at: str
    is_non_lms: bool
    artifact_known: bool
    source_promotion_ready: bool
    gate_count: int
    ready_gate_count: int
    ready_for_approval: bool
    blocking_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifactId": self.artifact_id,
            "artifactKnown": self.artifact_known,
            "artifactManifest": self.artifact_manifest,
            "blockingReasons": list(self.blocking_reasons),
            "businessOwner": self.business_owner,
            "gateCount": self.gate_count,
            "isNonLms": self.is_non_lms,
            "product": self.product,
            "readyForApproval": self.ready_for_approval,
            "readyGateCount": self.ready_gate_count,
            "requestId": self.request_id,
            "requestType": self.request_type,
            "requestedStage": self.requested_stage,
            "sourcePromotionId": self.source_promotion_id,
            "sourcePromotionReady": self.source_promotion_ready,
            "status": self.status,
            "submittedAt": self.submitted_at,
            "submittedBy": self.submitted_by,
            "useCaseId": self.use_case_id,
        }


@dataclass(frozen=True, slots=True)
class PromotionIntakeReport:
    request_count: int
    ready_count: int
    waiting_count: int
    blocked_count: int
    non_lms_count: int
    artifact_known_count: int
    gate_count: int
    ready_gate_count: int
    by_status: dict[str, int]
    requests: tuple[PromotionIntakeRequest, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionQueue": build_action_queue(self.requests),
            "artifactKnownCount": self.artifact_known_count,
            "blockedCount": self.blocked_count,
            "byStatus": self.by_status,
            "gateCount": self.gate_count,
            "nonLmsCount": self.non_lms_count,
            "readyCount": self.ready_count,
            "readyGateCount": self.ready_gate_count,
            "requestCount": self.request_count,
            "requests": [request.to_dict() for request in self.requests],
            "waitingCount": self.waiting_count,
        }

    def to_snapshot_dict(
        self,
        *,
        generated_at: str,
        source_registry: str = "platform/artifacts/promotions/requests.yaml",
    ) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "promotion-intake-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "source_registry": source_registry,
            "summary": {
                "request_count": self.request_count,
                "ready_count": self.ready_count,
                "waiting_count": self.waiting_count,
                "blocked_count": self.blocked_count,
                "non_lms_count": self.non_lms_count,
                "artifact_known_count": self.artifact_known_count,
                "gate_count": self.gate_count,
                "ready_gate_count": self.ready_gate_count,
            },
            "by_status": self.by_status,
            "action_queue": build_snapshot_action_queue(self.requests),
            "requests": [promotion_request_to_snapshot_dict(request) for request in self.requests],
        }


def build_promotion_intake_report(ai_root: Path | str) -> PromotionIntakeReport:
    root = Path(ai_root)
    registry = load_yaml(root / "platform" / "artifacts" / "promotions" / "requests.yaml")
    promotion_registry = load_yaml(root / "platform" / "artifacts" / "promotions" / "registry.yaml")

    products = collect_product_ids(load_yaml(root / "products" / "registry.yaml"))
    use_cases = collect_use_cases(load_yaml(root / "use-cases" / "registry.yaml"))
    artifact_manifests = collect_artifact_manifests(root)
    readiness_by_promotion = build_readiness_index(root, promotion_registry)

    policy = registry.get("policy")
    if not isinstance(policy, dict):
        raise RegistryValidationError("promotion request registry must define policy")
    allowed_statuses = require_string_set(policy, "allowed_statuses", "promotion request policy")
    allowed_request_types = require_string_set(
        policy, "allowed_request_types", "promotion request policy"
    )
    allowed_requested_stages = require_string_set(
        policy, "allowed_requested_stages", "promotion request policy"
    )
    ready_statuses = require_string_set(policy, "ready_statuses", "promotion request policy")

    promotion_stages = require_string_set(
        promotion_registry.get("policy", {}),
        "allowed_stages",
        "artifact promotion policy",
    )
    unknown_stages = sorted(allowed_requested_stages - promotion_stages)
    if unknown_stages:
        raise RegistryValidationError(
            "promotion request policy references unsupported stages: "
            + ", ".join(unknown_stages)
        )

    rows = require_mapping_list(registry, "requests", "promotion request registry")
    if not rows:
        raise RegistryValidationError("promotion request registry must define requests")

    requests: list[PromotionIntakeRequest] = []
    seen_ids: set[str] = set()
    for row in rows:
        request = build_promotion_intake_request(
            root,
            row,
            products,
            use_cases,
            artifact_manifests,
            readiness_by_promotion,
            allowed_statuses,
            allowed_request_types,
            allowed_requested_stages,
            ready_statuses,
        )
        if request.request_id in seen_ids:
            raise RegistryValidationError(
                f"promotion request registry has duplicate id: {request.request_id}"
            )
        seen_ids.add(request.request_id)
        requests.append(request)

    by_status = {status: 0 for status in sorted(allowed_statuses)}
    for request in requests:
        by_status[request.status] = by_status.get(request.status, 0) + 1

    return PromotionIntakeReport(
        request_count=len(requests),
        ready_count=sum(1 for request in requests if request.ready_for_approval),
        waiting_count=sum(1 for request in requests if request.status.startswith("waiting_")),
        blocked_count=sum(1 for request in requests if request.blocking_reasons),
        non_lms_count=sum(1 for request in requests if request.is_non_lms),
        artifact_known_count=sum(1 for request in requests if request.artifact_known),
        gate_count=sum(request.gate_count for request in requests),
        ready_gate_count=sum(request.ready_gate_count for request in requests),
        by_status=by_status,
        requests=tuple(requests),
    )


def build_promotion_intake_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_promotion_intake_report(ai_root).to_snapshot_dict(generated_at=report_date)


def build_readiness_index(root: Path, promotion_registry: dict[str, Any]) -> dict[str, Any]:
    promotions = promotion_registry.get("promotions", [])
    if not promotions:
        return {}
    return {item.promotion_id: item for item in build_promotion_readiness_report(root).items}


def write_promotion_intake_snapshot(
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
            build_promotion_intake_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def build_promotion_intake_request(
    root: Path,
    row: dict[str, Any],
    products: set[str],
    use_cases: dict[str, str],
    artifact_manifests: dict[str, str],
    readiness_by_promotion: dict[str, Any],
    allowed_statuses: set[str],
    allowed_request_types: set[str],
    allowed_requested_stages: set[str],
    ready_statuses: set[str],
) -> PromotionIntakeRequest:
    request_id = require_str(row, "request_id", "promotion request")
    owner = f"promotion request {request_id}"
    request_type = require_str(row, "request_type", owner)
    product = require_str(row, "product", owner)
    use_case_id = require_str(row, "use_case_id", owner)
    artifact_id = require_str(row, "artifact_id", owner)
    requested_stage = require_str(row, "requested_stage", owner)
    status = require_str(row, "status", owner)
    submitted_by = require_str(row, "submitted_by", owner)
    business_owner = require_str(row, "business_owner", owner)
    submitted_at = require_str(row, "submitted_at", owner)
    date.fromisoformat(submitted_at)

    if request_type not in allowed_request_types:
        raise RegistryValidationError(f"{owner} has unsupported request_type: {request_type}")
    if status not in allowed_statuses:
        raise RegistryValidationError(f"{owner} has unsupported status: {status}")
    if requested_stage not in allowed_requested_stages:
        raise RegistryValidationError(f"{owner} has unsupported requested_stage: {requested_stage}")
    if product not in products:
        raise RegistryValidationError(f"{owner} references unknown product: {product}")
    if use_cases.get(use_case_id) != product:
        raise RegistryValidationError(f"{owner} use_case_id does not belong to product")

    artifact_manifest = str(row.get("artifact_manifest", "")).strip()
    known_manifest_path = artifact_manifests.get(artifact_id, "")
    artifact_known = bool(known_manifest_path)
    if artifact_manifest:
        manifest_path = root / artifact_manifest
        if manifest_path.exists():
            manifest = load_yaml(manifest_path)
            manifest_artifact_id = require_str(manifest, "artifact_id", f"{owner} manifest")
            if manifest_artifact_id != artifact_id:
                raise RegistryValidationError(
                    f"{owner} artifact_manifest does not match artifact_id"
                )
            artifact_known = True
        elif status in ready_statuses:
            raise RegistryValidationError(f"{owner} ready request artifact_manifest does not exist")

    source_promotion_id = str(row.get("source_promotion_id", "")).strip()
    source_promotion_ready = False
    if source_promotion_id:
        source_promotion = readiness_by_promotion.get(source_promotion_id)
        if source_promotion is None:
            raise RegistryValidationError(f"{owner} references unknown source_promotion_id")
        source_promotion_ready = bool(source_promotion.ready_for_stage)

    gate_paths = require_string_list(row, "required_gates", owner)
    ready_gate_count = count_ready_gates(root, gate_paths)
    gate_count = len(gate_paths)
    declared_blockers = tuple(require_optional_string_list(row, "blockers", owner))
    derived_blockers = derive_blockers(
        status,
        ready_statuses,
        artifact_known,
        gate_count,
        ready_gate_count,
        source_promotion_id,
        source_promotion_ready,
    )
    blocking_reasons = tuple(dict.fromkeys((*declared_blockers, *derived_blockers)))
    ready_for_approval = status in ready_statuses and not blocking_reasons

    return PromotionIntakeRequest(
        request_id=request_id,
        request_type=request_type,
        product=product,
        use_case_id=use_case_id,
        artifact_id=artifact_id,
        artifact_manifest=artifact_manifest or known_manifest_path,
        source_promotion_id=source_promotion_id,
        requested_stage=requested_stage,
        status=status,
        submitted_by=submitted_by,
        business_owner=business_owner,
        submitted_at=submitted_at,
        is_non_lms=product != "lms-courseflow",
        artifact_known=artifact_known,
        source_promotion_ready=source_promotion_ready,
        gate_count=gate_count,
        ready_gate_count=ready_gate_count,
        ready_for_approval=ready_for_approval,
        blocking_reasons=blocking_reasons,
    )


def derive_blockers(
    status: str,
    ready_statuses: set[str],
    artifact_known: bool,
    gate_count: int,
    ready_gate_count: int,
    source_promotion_id: str,
    source_promotion_ready: bool,
) -> tuple[str, ...]:
    if status not in ready_statuses:
        return ()
    blockers: list[str] = []
    if not artifact_known:
        blockers.append("artifact_manifest_missing")
    if gate_count == 0:
        blockers.append("evaluation_gate_missing")
    elif ready_gate_count != gate_count:
        blockers.append("evaluation_gate_not_ready")
    if source_promotion_id and not source_promotion_ready:
        blockers.append("source_promotion_not_ready")
    return tuple(blockers)


def count_ready_gates(root: Path, gate_paths: list[str]) -> int:
    ready_count = 0
    for gate_path in gate_paths:
        full_path = root / gate_path
        if not full_path.exists():
            continue
        status = gate_status(load_yaml(full_path), f"promotion intake gate {gate_path}")
        if is_ready_gate_status(status):
            ready_count += 1
    return ready_count


def gate_status(gate_report: dict[str, Any], owner: str) -> str:
    status = gate_report.get("status")
    if isinstance(status, str) and status.strip():
        return status.strip()

    summary = gate_report.get("summary")
    if isinstance(summary, dict):
        review_status = summary.get("review_status")
        if isinstance(review_status, str) and review_status.strip():
            if review_status.strip() == "approved":
                return "accepted_privacy_review"
            return review_status.strip()

    raise RegistryValidationError(f"{owner} must define status or summary.review_status")


def build_action_queue(requests: tuple[PromotionIntakeRequest, ...]) -> dict[str, list[str]]:
    queue = build_snapshot_action_queue(requests)
    return {
        "readyForApproval": queue["ready_for_approval"],
        "waitingForArtifact": queue["waiting_for_artifact"],
        "waitingForEvaluation": queue["waiting_for_evaluation"],
        "waitingForPrivacyReview": queue["waiting_for_privacy_review"],
        "waitingForSimulator": queue["waiting_for_simulator"],
        "blocked": queue["blocked"],
    }


def build_snapshot_action_queue(
    requests: tuple[PromotionIntakeRequest, ...],
) -> dict[str, list[str]]:
    return {
        "ready_for_approval": [row.request_id for row in requests if row.ready_for_approval],
        "waiting_for_artifact": [
            row.request_id for row in requests if row.status == "waiting_for_artifact"
        ],
        "waiting_for_evaluation": [
            row.request_id for row in requests if row.status == "waiting_for_evaluation"
        ],
        "waiting_for_privacy_review": [
            row.request_id for row in requests if row.status == "waiting_for_privacy_review"
        ],
        "waiting_for_simulator": [
            row.request_id for row in requests if row.status == "waiting_for_simulator"
        ],
        "blocked": [
            row.request_id
            for row in requests
            if row.blocking_reasons and not row.status.startswith("waiting_")
        ],
    }


def promotion_request_to_snapshot_dict(request: PromotionIntakeRequest) -> dict[str, Any]:
    return {
        "request_id": request.request_id,
        "request_type": request.request_type,
        "product": request.product,
        "use_case_id": request.use_case_id,
        "artifact_id": request.artifact_id,
        "artifact_manifest": request.artifact_manifest,
        "source_promotion_id": request.source_promotion_id,
        "requested_stage": request.requested_stage,
        "status": request.status,
        "submitted_by": request.submitted_by,
        "business_owner": request.business_owner,
        "submitted_at": request.submitted_at,
        "is_non_lms": request.is_non_lms,
        "artifact_known": request.artifact_known,
        "source_promotion_ready": request.source_promotion_ready,
        "gate_count": request.gate_count,
        "ready_gate_count": request.ready_gate_count,
        "ready_for_approval": request.ready_for_approval,
        "blocking_reasons": list(request.blocking_reasons),
    }


def collect_product_ids(registry: dict[str, Any]) -> set[str]:
    return {
        require_str(row, "id", "products registry")
        for row in require_mapping_list(registry, "products", "products registry")
    }


def collect_use_cases(registry: dict[str, Any]) -> dict[str, str]:
    return {
        require_str(row, "id", "use-case registry"): require_str(
            row, "product", "use-case registry"
        )
        for row in require_mapping_list(registry, "use_cases", "use-case registry")
    }


def collect_artifact_manifests(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for manifest_path in sorted((root / "platform" / "artifacts" / "manifests").glob("*.yaml")):
        manifest = load_yaml(manifest_path)
        artifact_id = require_str(manifest, "artifact_id", str(manifest_path))
        result[artifact_id] = str(manifest_path.relative_to(root))
    return result


def default_snapshot_path(root: Path) -> Path:
    return root / "platform" / "artifacts" / "promotions" / "reports" / (
        "promotion-intake-v1.yaml"
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
    return validate_string_list(value, key, owner)


def require_optional_string_list(row: dict[str, Any], key: str, owner: str) -> list[str]:
    value = row.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    return validate_string_list(value, key, owner)


def require_string_set(row: dict[str, Any], key: str, owner: str) -> set[str]:
    values = require_string_list(row, key, owner)
    result = set(values)
    if len(result) != len(values):
        raise RegistryValidationError(f"{owner} {key} must not contain duplicates")
    return result


def validate_string_list(value: list[Any], key: str, owner: str) -> list[str]:
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a non-empty string")
        result.append(item.strip())
    return result

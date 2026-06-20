from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str


@dataclass(frozen=True, slots=True)
class MediaPrivacyReviewItem:
    review_id: str
    name: str
    product: str
    use_case_id: str
    taxonomy_module_id: str
    media_type: str
    requested_processing_modes: tuple[str, ...]
    raw_media_requested: bool
    status: str
    review_status: str
    reviewer_role: str
    requested_by: str
    submitted_at: str
    decision_ref: str
    required_controls: tuple[str, ...]
    satisfied_controls: tuple[str, ...]
    missing_controls: tuple[str, ...]
    blocked_processing_modes: tuple[str, ...]
    refs: tuple[str, ...]
    validation_errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "blockedProcessingModes": list(self.blocked_processing_modes),
            "decisionRef": self.decision_ref,
            "mediaType": self.media_type,
            "missingControls": list(self.missing_controls),
            "name": self.name,
            "product": self.product,
            "rawMediaRequested": self.raw_media_requested,
            "refs": list(self.refs),
            "requestedBy": self.requested_by,
            "requestedProcessingModes": list(self.requested_processing_modes),
            "requiredControls": list(self.required_controls),
            "reviewerRole": self.reviewer_role,
            "reviewId": self.review_id,
            "reviewStatus": self.review_status,
            "satisfiedControls": list(self.satisfied_controls),
            "status": self.status,
            "submittedAt": self.submitted_at,
            "taxonomyModuleId": self.taxonomy_module_id,
            "useCaseId": self.use_case_id,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "name": self.name,
            "product": self.product,
            "use_case_id": self.use_case_id,
            "taxonomy_module_id": self.taxonomy_module_id,
            "media_type": self.media_type,
            "requested_processing_modes": list(self.requested_processing_modes),
            "raw_media_requested": self.raw_media_requested,
            "status": self.status,
            "review_status": self.review_status,
            "reviewer_role": self.reviewer_role,
            "requested_by": self.requested_by,
            "submitted_at": self.submitted_at,
            "decision_ref": self.decision_ref,
            "required_controls": list(self.required_controls),
            "satisfied_controls": list(self.satisfied_controls),
            "missing_controls": list(self.missing_controls),
            "blocked_processing_modes": list(self.blocked_processing_modes),
            "refs": list(self.refs),
            "validation_errors": list(self.validation_errors),
        }


@dataclass(frozen=True, slots=True)
class MediaPrivacyReviewReport:
    generated_at: str
    policy_id: str
    review_status: str
    review_count: int
    approved_count: int
    ready_for_approval_count: int
    waiting_for_controls_count: int
    blocked_count: int
    raw_media_request_count: int
    transcript_only_approved_count: int
    control_gap_count: int
    blocked_mode_count: int
    next_actions: tuple[str, ...]
    items: tuple[MediaPrivacyReviewItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionQueue": build_action_queue(self.items),
            "approvedCount": self.approved_count,
            "blockedCount": self.blocked_count,
            "blockedModeCount": self.blocked_mode_count,
            "controlGapCount": self.control_gap_count,
            "generatedAt": self.generated_at,
            "items": [item.to_dict() for item in self.items],
            "nextActions": list(self.next_actions),
            "policyId": self.policy_id,
            "rawMediaRequestCount": self.raw_media_request_count,
            "readyForApprovalCount": self.ready_for_approval_count,
            "reviewCount": self.review_count,
            "reviewStatus": self.review_status,
            "transcriptOnlyApprovedCount": self.transcript_only_approved_count,
            "waitingForControlsCount": self.waiting_for_controls_count,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "media-privacy-review-v1",
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "policy_id": self.policy_id,
            "summary": {
                "review_status": self.review_status,
                "review_count": self.review_count,
                "approved_count": self.approved_count,
                "ready_for_approval_count": self.ready_for_approval_count,
                "waiting_for_controls_count": self.waiting_for_controls_count,
                "blocked_count": self.blocked_count,
                "raw_media_request_count": self.raw_media_request_count,
                "transcript_only_approved_count": (
                    self.transcript_only_approved_count
                ),
                "control_gap_count": self.control_gap_count,
                "blocked_mode_count": self.blocked_mode_count,
            },
            "next_actions": list(self.next_actions),
            "action_queue": build_snapshot_action_queue(self.items),
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def build_media_privacy_review_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> MediaPrivacyReviewReport:
    root = Path(ai_root)
    policy = load_yaml(default_policy_path(root))
    requests = load_yaml(default_requests_path(root))
    report_date = generated_at or date.today().isoformat()
    return build_media_privacy_review_report_from_sources(
        root,
        policy,
        requests,
        generated_at=report_date,
    )


def build_media_privacy_review_report_from_sources(
    root: Path,
    policy: dict[str, Any],
    requests: dict[str, Any],
    *,
    generated_at: str,
) -> MediaPrivacyReviewReport:
    allowed_statuses = require_string_set(policy, "allowed_statuses", "media privacy policy")
    allowed_media_types = require_string_set(
        policy,
        "allowed_media_types",
        "media privacy policy",
    )
    allowed_modes = require_string_set(
        policy,
        "allowed_processing_modes",
        "media privacy policy",
    )
    blocked_modes = require_string_set(
        policy,
        "blocked_processing_modes",
        "media privacy policy",
    )
    raw_media_modes = require_string_set(policy, "raw_media_modes", "media privacy policy")
    global_controls = require_string_tuple(
        policy,
        "global_required_controls",
        "media privacy policy",
    )
    mode_controls = require_mapping(policy, "mode_required_controls", "media privacy policy")
    next_actions = require_string_tuple(policy, "next_actions", "media privacy policy")

    products = collect_product_ids(load_yaml(root / "products" / "registry.yaml"))
    use_cases = collect_use_cases(load_yaml(root / "use-cases" / "registry.yaml"))
    taxonomy_modules = collect_taxonomy_module_ids(
        load_yaml(root / "platform" / "coverage" / "business-capability-coverage.yaml")
    )

    rows = require_mapping_list(requests, "requests", "media privacy requests")
    items: list[MediaPrivacyReviewItem] = []
    seen_ids: set[str] = set()
    for row in rows:
        item = build_media_privacy_review_item(
            root,
            row,
            products=products,
            use_cases=use_cases,
            taxonomy_modules=taxonomy_modules,
            allowed_statuses=allowed_statuses,
            allowed_media_types=allowed_media_types,
            allowed_modes=allowed_modes,
            blocked_modes=blocked_modes,
            raw_media_modes=raw_media_modes,
            global_controls=global_controls,
            mode_controls=mode_controls,
        )
        if item.review_id in seen_ids:
            raise RegistryValidationError(
                f"media privacy requests has duplicate id: {item.review_id}"
            )
        seen_ids.add(item.review_id)
        items.append(item)

    approved_count = sum(1 for item in items if item.review_status == "approved")
    ready_count = sum(1 for item in items if item.review_status == "ready_for_approval")
    waiting_count = sum(1 for item in items if item.review_status == "waiting_for_controls")
    blocked_count = sum(1 for item in items if item.review_status == "blocked")
    control_gap_count = sum(len(item.missing_controls) for item in items)
    blocked_mode_count = sum(len(item.blocked_processing_modes) for item in items)

    return MediaPrivacyReviewReport(
        generated_at=generated_at,
        policy_id=require_str(policy, "policy_id", "media privacy policy"),
        review_status=derive_report_status(
            blocked_count=blocked_count,
            waiting_count=waiting_count,
            ready_count=ready_count,
        ),
        review_count=len(items),
        approved_count=approved_count,
        ready_for_approval_count=ready_count,
        waiting_for_controls_count=waiting_count,
        blocked_count=blocked_count,
        raw_media_request_count=sum(1 for item in items if item.raw_media_requested),
        transcript_only_approved_count=sum(
            1
            for item in items
            if item.review_status == "approved"
            and item.requested_processing_modes == ("transcript_only",)
        ),
        control_gap_count=control_gap_count,
        blocked_mode_count=blocked_mode_count,
        next_actions=next_actions,
        items=tuple(items),
    )


def build_media_privacy_review_item(
    root: Path,
    row: dict[str, Any],
    *,
    products: set[str],
    use_cases: dict[str, str],
    taxonomy_modules: set[str],
    allowed_statuses: set[str],
    allowed_media_types: set[str],
    allowed_modes: set[str],
    blocked_modes: set[str],
    raw_media_modes: set[str],
    global_controls: tuple[str, ...],
    mode_controls: dict[str, Any],
) -> MediaPrivacyReviewItem:
    review_id = require_str(row, "review_id", "media privacy review")
    owner = f"media privacy review {review_id}"
    name = require_str(row, "name", owner)
    product = require_str(row, "product", owner)
    use_case_id = require_str(row, "use_case_id", owner)
    taxonomy_module_id = require_str(row, "taxonomy_module_id", owner)
    media_type = require_str(row, "media_type", owner)
    status = require_str(row, "status", owner)
    requested_modes = require_string_tuple(row, "requested_processing_modes", owner)
    reviewer_role = require_str(row, "reviewer_role", owner)
    requested_by = require_str(row, "requested_by", owner)
    submitted_at = require_str(row, "submitted_at", owner)
    decision_ref = str(row.get("decision_ref", "")).strip()
    refs = require_string_tuple(row, "refs", owner)
    controls = require_mapping(row, "controls", owner)
    control_evidence = require_mapping(row, "control_evidence", owner)

    validation_errors: list[str] = []
    if product not in products:
        validation_errors.append(f"unknown product: {product}")
    if use_cases.get(use_case_id) != product:
        validation_errors.append(f"use case {use_case_id} does not belong to {product}")
    if taxonomy_module_id not in taxonomy_modules:
        validation_errors.append(f"unknown taxonomy module: {taxonomy_module_id}")
    if media_type not in allowed_media_types:
        validation_errors.append(f"unsupported media type: {media_type}")
    if status not in allowed_statuses:
        validation_errors.append(f"unsupported status: {status}")

    unknown_modes = tuple(mode for mode in requested_modes if mode not in allowed_modes)
    validation_errors.extend(f"unsupported processing mode: {mode}" for mode in unknown_modes)
    blocked_processing_modes = tuple(
        sorted(mode for mode in requested_modes if mode in blocked_modes)
    )
    raw_media_requested = any(mode in raw_media_modes for mode in requested_modes)
    required_controls = collect_required_controls(
        global_controls,
        mode_controls,
        requested_modes,
    )
    satisfied_controls = tuple(
        control
        for control in required_controls
        if bool(controls.get(control, False))
        and evidence_path_exists(root, str(control_evidence.get(control, "")).strip())
    )
    missing_controls = tuple(
        control for control in required_controls if control not in satisfied_controls
    )
    validation_errors.extend(validate_refs(root, refs, owner))
    if decision_ref and not (root / decision_ref).exists():
        validation_errors.append(f"decision_ref does not exist: {decision_ref}")

    review_status = derive_item_status(
        declared_status=status,
        missing_controls=missing_controls,
        blocked_processing_modes=blocked_processing_modes,
        validation_errors=validation_errors,
    )

    return MediaPrivacyReviewItem(
        review_id=review_id,
        name=name,
        product=product,
        use_case_id=use_case_id,
        taxonomy_module_id=taxonomy_module_id,
        media_type=media_type,
        requested_processing_modes=requested_modes,
        raw_media_requested=raw_media_requested,
        status=status,
        review_status=review_status,
        reviewer_role=reviewer_role,
        requested_by=requested_by,
        submitted_at=submitted_at,
        decision_ref=decision_ref,
        required_controls=required_controls,
        satisfied_controls=satisfied_controls,
        missing_controls=missing_controls,
        blocked_processing_modes=blocked_processing_modes,
        refs=refs,
        validation_errors=tuple(validation_errors),
    )


def collect_required_controls(
    global_controls: tuple[str, ...],
    mode_controls: dict[str, Any],
    requested_modes: tuple[str, ...],
) -> tuple[str, ...]:
    controls: list[str] = list(global_controls)
    for mode in requested_modes:
        for control in normalize_string_list(mode_controls.get(mode, []), f"mode {mode}"):
            if control not in controls:
                controls.append(control)
    return tuple(controls)


def derive_item_status(
    *,
    declared_status: str,
    missing_controls: tuple[str, ...],
    blocked_processing_modes: tuple[str, ...],
    validation_errors: list[str],
) -> str:
    if validation_errors or blocked_processing_modes:
        return "blocked"
    if missing_controls:
        return "waiting_for_controls"
    if declared_status == "approved":
        return "approved"
    return "ready_for_approval"


def derive_report_status(
    *,
    blocked_count: int,
    waiting_count: int,
    ready_count: int,
) -> str:
    if blocked_count:
        return "blocked"
    if waiting_count:
        return "waiting_for_controls"
    if ready_count:
        return "ready_for_approval"
    return "approved"


def build_action_queue(items: tuple[MediaPrivacyReviewItem, ...]) -> dict[str, list[str]]:
    return {
        "approved": [item.review_id for item in items if item.review_status == "approved"],
        "readyForApproval": [
            item.review_id for item in items if item.review_status == "ready_for_approval"
        ],
        "waitingForControls": [
            item.review_id for item in items if item.review_status == "waiting_for_controls"
        ],
        "blocked": [item.review_id for item in items if item.review_status == "blocked"],
    }


def build_snapshot_action_queue(
    items: tuple[MediaPrivacyReviewItem, ...],
) -> dict[str, list[str]]:
    queue = build_action_queue(items)
    return {
        "approved": queue["approved"],
        "ready_for_approval": queue["readyForApproval"],
        "waiting_for_controls": queue["waitingForControls"],
        "blocked": queue["blocked"],
    }


def build_media_privacy_review_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_media_privacy_review_report(
        ai_root,
        generated_at=generated_at,
    ).to_snapshot_dict()


def write_media_privacy_review_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_report_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            build_media_privacy_review_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def collect_product_ids(registry: dict[str, Any]) -> set[str]:
    return {
        require_str(row, "id", "product")
        for row in require_mapping_list(registry, "products", "products registry")
    }


def collect_use_cases(registry: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in require_mapping_list(registry, "use_cases", "use-case registry"):
        use_case_id = require_str(row, "id", "use case")
        product = row.get("product")
        if product is None and use_case_id.startswith("lms-"):
            product = "lms-courseflow"
        if not isinstance(product, str) or not product.strip():
            raise RegistryValidationError(f"use case {use_case_id} must define product")
        result[use_case_id] = product.strip()
    return result


def collect_taxonomy_module_ids(registry: dict[str, Any]) -> set[str]:
    return {
        require_str(row, "id", "business capability module")
        for row in require_mapping_list(
            registry,
            "modules",
            "business capability coverage registry",
        )
    }


def validate_refs(root: Path, refs: tuple[str, ...], owner: str) -> list[str]:
    errors: list[str] = []
    for ref in refs:
        if not (root / ref).exists():
            errors.append(f"{owner} ref does not exist: {ref}")
    return errors


def evidence_path_exists(root: Path, value: str) -> bool:
    return bool(value) and (root / value).exists()


def require_mapping(row: dict[str, Any], key: str, owner: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise RegistryValidationError(f"{owner} must define mapping field {key}")
    return value


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


def require_string_set(row: dict[str, Any], key: str, owner: str) -> set[str]:
    return set(require_string_tuple(row, key, owner))


def require_string_tuple(row: dict[str, Any], key: str, owner: str) -> tuple[str, ...]:
    value = row.get(key)
    return tuple(normalize_string_list(value, f"{owner} {key}"))


def normalize_string_list(value: object, owner: str) -> list[str]:
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must be a list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RegistryValidationError(f"{owner} must contain non-empty strings")
        result.append(item.strip())
    return result


def default_policy_path(root: Path) -> Path:
    return root / "platform" / "governance" / "policies" / "media-privacy-review-policy.yaml"


def default_requests_path(root: Path) -> Path:
    return root / "platform" / "governance" / "requests" / "media-privacy-review-requests.yaml"


def default_report_path(root: Path) -> Path:
    return root / "platform" / "governance" / "reports" / "media-privacy-review-v1.yaml"

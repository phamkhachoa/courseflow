from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import hash_file, load_json


REPORT_VERSION = 1
SUPPORTED_ENVIRONMENTS = {"local", "staging", "prod"}
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}


@dataclass(frozen=True)
class SilverGoldPublicationOpsReportResult:
    output_path: Path
    report: dict[str, Any]


def write_silver_gold_publication_ops_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str = "local",
    release_evidence_paths: list[str | Path] | None = None,
    promotion_manifest_paths: list[str | Path] | None = None,
    activation_manifest_paths: list[str | Path] | None = None,
    active_pointer_paths: list[str | Path] | None = None,
    generated_at: str | None = None,
) -> SilverGoldPublicationOpsReportResult:
    report = build_silver_gold_publication_ops_report(
        root,
        environment=environment,
        release_evidence_paths=release_evidence_paths,
        promotion_manifest_paths=promotion_manifest_paths,
        activation_manifest_paths=activation_manifest_paths,
        active_pointer_paths=active_pointer_paths,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SilverGoldPublicationOpsReportResult(output_path=target, report=report)


def build_silver_gold_publication_ops_report(
    root: str | Path,
    *,
    environment: str = "local",
    release_evidence_paths: list[str | Path] | None = None,
    promotion_manifest_paths: list[str | Path] | None = None,
    activation_manifest_paths: list[str | Path] | None = None,
    active_pointer_paths: list[str | Path] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    del root
    generated = generated_at or utc_now()
    release_refs, releases = load_artifacts(release_evidence_paths or [])
    promotion_refs, promotions = load_artifacts(promotion_manifest_paths or [])
    activation_refs, activations = load_artifacts(activation_manifest_paths or [])
    pointer_refs, pointers = load_artifacts(active_pointer_paths or [])
    product_rows = [
        publication_product_row(
            data_product,
            releases.get(data_product),
            promotions.get(data_product),
            activations.get(data_product),
            pointers.get(data_product),
            environment=environment,
        )
        for data_product in sorted(set(releases) | set(promotions) | set(activations) | set(pointers))
    ]
    global_checks = publication_global_checks(
        environment=environment,
        release_count=len(release_refs),
        promotion_count=len(promotion_refs),
        activation_count=len(activation_refs),
        pointer_count=len(pointer_refs),
    )
    failed_global = [check for check in global_checks if check.get("passed") is not True]
    failed_products = [row for row in product_rows if row.get("passed") is not True]
    passed = not failed_global and not failed_products
    readiness_state = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    return {
        "artifact_type": "silver_gold_publication_ops_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id(
            "silver-gold-publication-ops",
            environment,
            generated,
            release_refs,
            promotion_refs,
            activation_refs,
            pointer_refs,
        ),
        "generated_at": generated,
        "environment": environment,
        "capability_id": "silver-gold-publication",
        "readiness_state": readiness_state,
        "mode": "local_preflight" if environment == "local" and not product_rows else "runtime_evidence",
        "inputs": {
            "release_evidence": release_refs,
            "promotion_manifests": promotion_refs,
            "activation_manifests": activation_refs,
            "active_pointers": pointer_refs,
        },
        "checks": global_checks,
        "data_products": product_rows,
        "decision_board": {
            "failed_products": [compact_product_row(row) for row in failed_products[:30]],
            "page_now": [
                action
                for row in failed_products
                for action in row.get("next_actions", [])
                if action.get("priority") == "P0"
            ][:30],
        },
        "summary": publication_summary(product_rows, failed_global, failed_products),
        "passed": passed,
    }


def publication_global_checks(
    *,
    environment: str,
    release_count: int,
    promotion_count: int,
    activation_count: int,
    pointer_count: int,
) -> list[dict[str, Any]]:
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    return [
        check("environment_supported", environment in SUPPORTED_ENVIRONMENTS, {"environment": environment}),
        check(
            "release_evidence_attached_for_production_like",
            not production_like or release_count > 0,
            {"release_count": release_count},
        ),
        check(
            "promotion_manifest_attached_for_production_like",
            not production_like or promotion_count > 0,
            {"promotion_count": promotion_count},
        ),
        check(
            "activation_manifest_attached_for_production_like",
            not production_like or activation_count > 0,
            {"activation_count": activation_count},
        ),
        check(
            "active_pointer_attached_for_production_like",
            not production_like or pointer_count > 0,
            {"pointer_count": pointer_count},
        ),
    ]


def publication_product_row(
    data_product: str,
    release_ref: dict[str, Any] | None,
    promotion_ref: dict[str, Any] | None,
    activation_ref: dict[str, Any] | None,
    pointer_ref: dict[str, Any] | None,
    *,
    environment: str,
) -> dict[str, Any]:
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    release = artifact_payload(release_ref)
    promotion = artifact_payload(promotion_ref)
    activation = artifact_payload(activation_ref)
    pointer = artifact_payload(pointer_ref)
    promotion_output = mapping(promotion, "output")
    activation_output = mapping(activation, "output")
    active_pointer = mapping(activation, "active_pointer")
    checks = [
        check("release_evidence_attached", not production_like or isinstance(release, dict), {"data_product": data_product}),
        check(
            "release_environment_matches",
            release is None or release.get("environment") == environment,
            {"expected": environment, "actual": release.get("environment") if isinstance(release, dict) else None},
        ),
        check("release_passed", release is None or release.get("release_passed") is True, {"release_passed": release.get("release_passed") if isinstance(release, dict) else None}),
        check(
            "snapshot_evidence_attached",
            release is None or non_empty(release.get("snapshot_evidence_uri")) and is_hash(release.get("snapshot_evidence_hash")),
            {
                "snapshot_evidence_uri": release.get("snapshot_evidence_uri") if isinstance(release, dict) else None,
                "snapshot_evidence_hash": release.get("snapshot_evidence_hash") if isinstance(release, dict) else None,
            },
        ),
        check("promotion_attached", not production_like or isinstance(promotion, dict), {"data_product": data_product}),
        check("promotion_artifact_type_valid", promotion is None or promotion.get("artifact_type") == "release_promotion_manifest.v1", {"artifact_type": promotion.get("artifact_type") if isinstance(promotion, dict) else None}),
        check("promotion_passed", promotion is None or promotion.get("passed") is True, {"passed": promotion.get("passed") if isinstance(promotion, dict) else None}),
        check("promotion_approved", promotion is None or promotion.get("promotion_state") == "approved_for_activation", {"promotion_state": promotion.get("promotion_state") if isinstance(promotion, dict) else None}),
        check("promotion_environment_matches", promotion is None or promotion.get("target_environment") == environment, {"expected": environment, "actual": promotion.get("target_environment") if isinstance(promotion, dict) else None}),
        check("prod_change_ticket_present", not (environment == "prod" and isinstance(promotion, dict)) or non_empty(promotion.get("change_ticket")), {"change_ticket": promotion.get("change_ticket") if isinstance(promotion, dict) else None}),
        check("promotion_release_matches", release is None or promotion is None or promotion.get("release_id") == release.get("release_id"), {"release_id": release.get("release_id") if isinstance(release, dict) else None, "promotion_release_id": promotion.get("release_id") if isinstance(promotion, dict) else None}),
        check("promotion_output_matches_release", release is None or promotion is None or promotion_output.get("data_product") == data_product, {"data_product": data_product, "promotion_output": promotion_output}),
        check("activation_attached", not production_like or isinstance(activation, dict), {"data_product": data_product}),
        check("activation_artifact_type_valid", activation is None or activation.get("artifact_type") == "release_activation_manifest.v1", {"artifact_type": activation.get("artifact_type") if isinstance(activation, dict) else None}),
        check("activation_passed", activation is None or activation.get("passed") is True, {"passed": activation.get("passed") if isinstance(activation, dict) else None}),
        check("activation_state_activated", activation is None or activation.get("activation_state") == "activated", {"activation_state": activation.get("activation_state") if isinstance(activation, dict) else None}),
        check("activation_environment_matches", activation is None or activation.get("target_environment") == environment, {"expected": environment, "actual": activation.get("target_environment") if isinstance(activation, dict) else None}),
        check("activation_release_matches", promotion is None or activation is None or activation.get("release_id") == promotion.get("release_id"), {"promotion_release_id": promotion.get("release_id") if isinstance(promotion, dict) else None, "activation_release_id": activation.get("release_id") if isinstance(activation, dict) else None}),
        check("activation_output_matches_promotion", promotion is None or activation is None or comparable_output(activation_output) == comparable_output(promotion_output), {"promotion_output": promotion_output, "activation_output": activation_output}),
        check("active_pointer_attached", not production_like or isinstance(pointer, dict), {"data_product": data_product}),
        check("active_pointer_artifact_type_valid", pointer is None or pointer.get("artifact_type") == "release_active_pointer.v1", {"artifact_type": pointer.get("artifact_type") if isinstance(pointer, dict) else None}),
        check("active_pointer_environment_matches", pointer is None or pointer.get("environment") == environment, {"expected": environment, "actual": pointer.get("environment") if isinstance(pointer, dict) else None}),
        check("active_pointer_matches_activation", pointer is None or activation is None or active_pointer_matches(pointer, active_pointer), {"pointer": compact_pointer(pointer), "activation_pointer": compact_pointer(active_pointer)}),
        check("active_pointer_matches_activation_output", pointer is None or activation is None or pointer_matches_output(pointer, activation_output), {"pointer": compact_pointer(pointer), "activation_output": activation_output}),
        check("active_pointer_rollback_target_present", not production_like or (isinstance(pointer, dict) and isinstance(pointer.get("rollback_target"), dict)), {"rollback_target": pointer.get("rollback_target") if isinstance(pointer, dict) else None}),
    ]
    issues = publication_issues(checks)
    return {
        "data_product": data_product,
        "environment": environment,
        "release": artifact_summary(release_ref),
        "promotion": artifact_summary(promotion_ref),
        "activation": artifact_summary(activation_ref),
        "active_pointer": artifact_summary(pointer_ref),
        "checks": checks,
        "issues": issues,
        "risk_state": issues[0] if issues else "ok",
        "next_actions": next_actions(issues, data_product),
        "passed": not issues,
    }


def publication_issues(checks: list[dict[str, Any]]) -> list[str]:
    issue_map = {
        "release_evidence_attached": "release_evidence_missing",
        "release_environment_matches": "release_environment_mismatch",
        "release_passed": "release_failed",
        "snapshot_evidence_attached": "snapshot_evidence_missing",
        "promotion_attached": "promotion_missing",
        "promotion_artifact_type_valid": "promotion_invalid",
        "promotion_passed": "promotion_failed",
        "promotion_approved": "promotion_not_approved",
        "promotion_environment_matches": "promotion_environment_mismatch",
        "prod_change_ticket_present": "change_ticket_missing",
        "promotion_release_matches": "promotion_release_mismatch",
        "promotion_output_matches_release": "promotion_output_mismatch",
        "activation_attached": "activation_missing",
        "activation_artifact_type_valid": "activation_invalid",
        "activation_passed": "activation_failed",
        "activation_state_activated": "activation_not_activated",
        "activation_environment_matches": "activation_environment_mismatch",
        "activation_release_matches": "activation_release_mismatch",
        "activation_output_matches_promotion": "activation_output_mismatch",
        "active_pointer_attached": "active_pointer_missing",
        "active_pointer_artifact_type_valid": "active_pointer_invalid",
        "active_pointer_environment_matches": "active_pointer_environment_mismatch",
        "active_pointer_matches_activation": "active_pointer_drift",
        "active_pointer_matches_activation_output": "active_pointer_drift",
        "active_pointer_rollback_target_present": "rollback_target_missing",
    }
    return [
        issue_map[check["name"]]
        for check in checks
        if check.get("passed") is not True and check.get("name") in issue_map
    ]


def next_actions(issues: list[str], data_product: str) -> list[dict[str, Any]]:
    actions = []
    if any(issue.startswith("release") or issue == "snapshot_evidence_missing" for issue in issues):
        actions.append({"priority": "P0", "action": "attach_passing_release_evidence", "owner": "data-platform-team"})
    if any(issue.startswith("promotion") for issue in issues):
        actions.append({"priority": "P0", "action": "repair_release_promotion", "owner": "data-platform-team"})
    if "change_ticket_missing" in issues:
        actions.append({"priority": "P0", "action": "attach_change_ticket", "owner": "data-platform-team"})
    if any(issue.startswith("activation") for issue in issues):
        actions.append({"priority": "P0", "action": "repair_release_activation", "owner": "data-platform-team"})
    if any(issue.startswith("active_pointer") for issue in issues):
        actions.append({"priority": "P0", "action": "repair_active_pointer", "owner": "data-platform-team"})
    if "rollback_target_missing" in issues:
        actions.append({"priority": "P0", "action": "attach_rollback_target", "owner": "data-platform-team"})
    return actions or [{"priority": "P3", "action": "no_action", "owner": data_product}]


def publication_summary(
    rows: list[dict[str, Any]],
    failed_global_checks: list[dict[str, Any]],
    failed_products: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "data_product_count": len(rows),
        "failed_product_count": len(failed_products),
        "global_failed_check_count": len(failed_global_checks),
        "release_attached_count": sum(1 for row in rows if row.get("release", {}).get("attached") is True),
        "promotion_attached_count": sum(1 for row in rows if row.get("promotion", {}).get("attached") is True),
        "activation_attached_count": sum(1 for row in rows if row.get("activation", {}).get("attached") is True),
        "active_pointer_attached_count": sum(1 for row in rows if row.get("active_pointer", {}).get("attached") is True),
        "by_risk_state": count_by(rows, "risk_state"),
    }


def load_artifacts(paths: list[str | Path]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    refs = []
    index: dict[str, dict[str, Any]] = {}
    for value in paths:
        path = Path(value)
        payload = load_json(path)
        data_product = data_product_key(payload)
        ref = {
            "uri": path.as_posix(),
            "hash": hash_file(path),
            "artifact_type": payload.get("artifact_type"),
            "release_id": payload.get("release_id"),
            "data_product": data_product,
            "environment": payload.get("environment") or payload.get("target_environment"),
            "passed": payload.get("passed") if "passed" in payload else payload.get("release_passed"),
            "payload": payload,
        }
        refs.append({key: item for key, item in ref.items() if key != "payload"})
        if data_product:
            index[data_product] = ref
    return refs, index


def data_product_key(payload: dict[str, Any]) -> str | None:
    output = mapping(payload, "output")
    if non_empty(output.get("data_product")):
        return str(output.get("data_product"))
    if non_empty(payload.get("primary_output")):
        return str(payload.get("primary_output"))
    if non_empty(payload.get("data_product")):
        return str(payload.get("data_product"))
    return None


def artifact_payload(ref: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(ref, dict):
        return None
    payload = ref.get("payload")
    return payload if isinstance(payload, dict) else None


def artifact_summary(ref: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(ref, dict):
        return {"attached": False}
    return {
        "attached": True,
        "uri": ref.get("uri"),
        "hash": ref.get("hash"),
        "artifact_type": ref.get("artifact_type"),
        "release_id": ref.get("release_id"),
        "data_product": ref.get("data_product"),
        "environment": ref.get("environment"),
        "passed": ref.get("passed"),
    }


def compact_product_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "data_product": row.get("data_product"),
        "risk_state": row.get("risk_state"),
        "issues": row.get("issues", []),
        "next_actions": row.get("next_actions", []),
    }


def comparable_output(output: dict[str, Any]) -> dict[str, Any]:
    return {
        "data_product": output.get("data_product"),
        "dataset_snapshot_id": output.get("dataset_snapshot_id"),
        "content_hash": output.get("content_hash"),
    }


def active_pointer_matches(pointer: dict[str, Any] | None, active_pointer: dict[str, Any]) -> bool:
    if not isinstance(pointer, dict):
        return False
    for key in ("environment", "release_id", "data_product", "dataset_snapshot_id", "content_hash", "promotion_manifest_hash"):
        if pointer.get(key) != active_pointer.get(key):
            return False
    return True


def pointer_matches_output(pointer: dict[str, Any] | None, output: dict[str, Any]) -> bool:
    if not isinstance(pointer, dict):
        return False
    return (
        pointer.get("data_product") == output.get("data_product")
        and pointer.get("dataset_snapshot_id") == output.get("dataset_snapshot_id")
        and pointer.get("content_hash") == output.get("content_hash")
    )


def compact_pointer(pointer: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(pointer, dict):
        return {}
    return {
        "environment": pointer.get("environment"),
        "release_id": pointer.get("release_id"),
        "data_product": pointer.get("data_product"),
        "dataset_snapshot_id": pointer.get("dataset_snapshot_id"),
        "content_hash": pointer.get("content_hash"),
        "promotion_manifest_hash": pointer.get("promotion_manifest_hash"),
        "rollback_target": pointer.get("rollback_target"),
    }


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def mapping(record: dict[str, Any], key: str) -> dict[str, Any]:
    value = record.get(key)
    return value if isinstance(value, dict) else {}


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_hash(value: object) -> bool:
    return isinstance(value, str) and value.startswith("sha256:")


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def stable_id(*parts: Any) -> str:
    return hashlib.sha256(canonical_json(parts).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

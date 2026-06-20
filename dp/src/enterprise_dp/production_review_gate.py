from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.catalog_runtime_ops import check, compact_check, stable_id, utc_now


REPORT_VERSION = 1
VALID_PROFILES = {"partner-review", "code-control-plane", "source-onboarding", "production-ready"}


@dataclass(frozen=True)
class ProductionReviewGateResult:
    output_path: Path | None
    report: dict[str, Any]


def write_production_review_gate_report(
    manifest_path: str | Path,
    output_path: str | Path | None = None,
    *,
    profile: str = "code-control-plane",
    environment: str | None = None,
    generated_at: str | None = None,
) -> ProductionReviewGateResult:
    report = build_production_review_gate_report(
        manifest_path,
        profile=profile,
        environment=environment,
        generated_at=generated_at,
    )
    target = Path(output_path) if output_path is not None else None
    if target is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return ProductionReviewGateResult(output_path=target, report=report)


def build_production_review_gate_report(
    manifest_path: str | Path,
    *,
    profile: str = "code-control-plane",
    environment: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    generated = generated_at or utc_now()
    manifest = load_json(manifest_file) if manifest_file.is_file() else {}
    verdict = manifest.get("verdict") if isinstance(manifest.get("verdict"), dict) else {}
    summary = manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {}
    p0_gap_backlog = manifest.get("p0_gap_backlog") if isinstance(manifest.get("p0_gap_backlog"), list) else []
    checks = production_review_gate_checks(
        manifest_file=manifest_file,
        manifest=manifest,
        verdict=verdict,
        summary=summary,
        p0_gap_backlog=p0_gap_backlog,
        profile=profile,
        environment=environment,
    )
    failed_checks = [item for item in checks if item.get("passed") is not True]
    passed = not failed_checks
    return {
        "artifact_type": "production_review_gate_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id(
            "production-review-gate",
            profile,
            environment or manifest.get("environment"),
            generated,
            hash_file(manifest_file) if manifest_file.is_file() else None,
        ),
        "generated_at": generated,
        "profile": profile,
        "environment": environment or manifest.get("environment"),
        "manifest": {
            "path": manifest_file.as_posix(),
            "exists": manifest_file.is_file(),
            "hash": hash_file(manifest_file) if manifest_file.is_file() else None,
            "artifact_type": manifest.get("artifact_type") if isinstance(manifest, dict) else None,
            "environment": manifest.get("environment") if isinstance(manifest, dict) else None,
        },
        "verdict": {
            "partner_review_ready": verdict.get("partner_review_ready"),
            "code_control_plane_ready_excluding_live_infra": verdict.get(
                "code_control_plane_ready_excluding_live_infra"
            ),
            "production_ready": verdict.get("production_ready"),
            "readiness_state": verdict.get("readiness_state"),
        },
        "summary": {
            "control_tower_blocker_count": summary.get("control_tower_blocker_count", 0),
            "p0_gap_count": len(p0_gap_backlog),
            "source_onboarding_release_gate_passed": summary.get("source_onboarding_release_gate_passed"),
            "schema_registry_release_gate_passed": summary.get("schema_registry_release_gate_passed"),
            "catalog_runtime_release_gate_passed": summary.get("catalog_runtime_release_gate_passed"),
            "orchestration_runtime_release_gate_passed": summary.get(
                "orchestration_runtime_release_gate_passed"
            ),
            "runtime_iac_release_gate_passed": summary.get("runtime_iac_release_gate_passed"),
            "access_privacy_release_gate_passed": summary.get("access_privacy_release_gate_passed"),
            "secret_rotation_ops_release_gate_passed": summary.get("secret_rotation_ops_release_gate_passed"),
            "source_activation_ops_p0_source_count": summary.get("source_activation_ops_p0_source_count"),
            "source_activation_ops_p0_active_count": summary.get("source_activation_ops_p0_active_count"),
            "source_activation_ops_p0_unactivated_count": summary.get("source_activation_ops_p0_unactivated_count"),
            "source_activation_ops_pointer_issue_count": summary.get("source_activation_ops_pointer_issue_count"),
            "source_activation_ops_runtime_readiness_issue_count": summary.get(
                "source_activation_ops_runtime_readiness_issue_count"
            ),
            "source_activation_ops_evidence_integrity_issue_count": summary.get(
                "source_activation_ops_evidence_integrity_issue_count"
            ),
            "source_activation_ops_p0_evidence_integrity_issue_count": summary.get(
                "source_activation_ops_p0_evidence_integrity_issue_count"
            ),
        },
        "checks": checks,
        "failed_checks": [compact_check(item) for item in failed_checks],
        "failed_check_count": len(failed_checks),
        "passed": passed,
    }


def production_review_gate_checks(
    *,
    manifest_file: Path,
    manifest: dict[str, Any],
    verdict: dict[str, Any],
    summary: dict[str, Any],
    p0_gap_backlog: list[Any],
    profile: str,
    environment: str | None,
) -> list[dict[str, Any]]:
    manifest_environment = manifest.get("environment") if isinstance(manifest, dict) else None
    checks = [
        check("profile_supported", profile in VALID_PROFILES, {"profile": profile, "supported": sorted(VALID_PROFILES)}),
        check("manifest_exists", manifest_file.is_file(), {"path": manifest_file.as_posix()}),
        check(
            "manifest_artifact_type_valid",
            manifest.get("artifact_type") == "production_review_pack.v1",
            {"artifact_type": manifest.get("artifact_type")},
        ),
        check("manifest_hash_valid", manifest_file.is_file() and bool(hash_file(manifest_file)), {"hash": hash_file(manifest_file) if manifest_file.is_file() else None}),
        check("verdict_present", bool(verdict), {"verdict_keys": sorted(verdict)}),
        check("summary_present", bool(summary), {"summary_keys": sorted(summary)}),
        check("p0_gap_backlog_present", isinstance(manifest.get("p0_gap_backlog"), list), {"type": type(manifest.get("p0_gap_backlog")).__name__}),
    ]
    if environment is not None:
        checks.append(
            check(
                "environment_matches",
                manifest_environment == environment,
                {"manifest_environment": manifest_environment, "expected_environment": environment},
            )
        )
    checks.extend(profile_checks(profile, verdict=verdict, summary=summary, p0_gap_backlog=p0_gap_backlog))
    return checks


def profile_checks(
    profile: str,
    *,
    verdict: dict[str, Any],
    summary: dict[str, Any],
    p0_gap_backlog: list[Any],
) -> list[dict[str, Any]]:
    if profile == "partner-review":
        return [
            check(
                "partner_review_ready",
                verdict.get("partner_review_ready") is True,
                {"partner_review_ready": verdict.get("partner_review_ready")},
            )
        ]
    if profile == "code-control-plane":
        return [
            check(
                "partner_review_ready",
                verdict.get("partner_review_ready") is True,
                {"partner_review_ready": verdict.get("partner_review_ready")},
            ),
            check(
                "code_control_plane_ready_excluding_live_infra",
                verdict.get("code_control_plane_ready_excluding_live_infra") is True,
                {
                    "code_control_plane_ready_excluding_live_infra": verdict.get(
                        "code_control_plane_ready_excluding_live_infra"
                    ),
                    "control_tower_blocker_count": summary.get("control_tower_blocker_count", 0),
                    "p0_gap_count": len(p0_gap_backlog),
                },
            ),
        ]
    if profile == "source-onboarding":
        source_gaps = [
            item
            for item in p0_gap_backlog
            if isinstance(item, dict)
            and (
                item.get("capability_id") == "source-onboarding"
                or item.get("gap") == "source_activation_ops_p0_clear"
            )
        ]
        p0_source_count = int_value(summary.get("source_activation_ops_p0_source_count"))
        p0_active_count = int_value(summary.get("source_activation_ops_p0_active_count"))
        return [
            check(
                "source_activation_ops_attached",
                summary.get("source_activation_ops_attached") is True,
                {"source_activation_ops_attached": summary.get("source_activation_ops_attached")},
            ),
            check(
                "source_activation_ops_environment_production_like",
                summary.get("source_activation_ops_environment") in {"staging", "prod"},
                {"source_activation_ops_environment": summary.get("source_activation_ops_environment")},
            ),
            check(
                "source_activation_ops_runtime_attested",
                summary.get("source_activation_ops_mode") == "runtime_attested",
                {"source_activation_ops_mode": summary.get("source_activation_ops_mode")},
            ),
            check(
                "source_activation_ops_production_like_ready",
                summary.get("source_activation_ops_readiness_state") == "production_like_ready",
                {"source_activation_ops_readiness_state": summary.get("source_activation_ops_readiness_state")},
            ),
            check(
                "source_activation_ops_passed",
                summary.get("source_activation_ops_passed") is True,
                {"source_activation_ops_passed": summary.get("source_activation_ops_passed")},
            ),
            check(
                "source_onboarding_release_gate_passed",
                summary.get("source_onboarding_release_gate_passed") is True,
                {"source_onboarding_release_gate_passed": summary.get("source_onboarding_release_gate_passed")},
            ),
            check(
                "source_activation_p0_sources_present",
                p0_source_count > 0,
                {"source_activation_ops_p0_source_count": p0_source_count},
            ),
            check(
                "source_activation_all_p0_sources_active",
                p0_source_count > 0 and p0_active_count == p0_source_count,
                {
                    "source_activation_ops_p0_source_count": p0_source_count,
                    "source_activation_ops_p0_active_count": p0_active_count,
                },
            ),
            check(
                "source_activation_no_p0_unactivated",
                int_value(summary.get("source_activation_ops_p0_unactivated_count")) == 0,
                {
                    "source_activation_ops_p0_unactivated_count": summary.get(
                        "source_activation_ops_p0_unactivated_count"
                    )
                },
            ),
            check(
                "source_activation_no_p0_activation_gap",
                int_value(summary.get("source_activation_ops_p0_activation_gap_count")) == 0,
                {
                    "source_activation_ops_p0_activation_gap_count": summary.get(
                        "source_activation_ops_p0_activation_gap_count"
                    )
                },
            ),
            check(
                "source_activation_no_p0_critical_issue",
                int_value(summary.get("source_activation_ops_p0_critical_issue_count")) == 0,
                {
                    "source_activation_ops_p0_critical_issue_count": summary.get(
                        "source_activation_ops_p0_critical_issue_count"
                    )
                },
            ),
            check(
                "source_activation_no_critical_issue",
                int_value(summary.get("source_activation_ops_critical_issue_count")) == 0,
                {"source_activation_ops_critical_issue_count": summary.get("source_activation_ops_critical_issue_count")},
            ),
            check(
                "source_activation_no_pointer_issue",
                int_value(summary.get("source_activation_ops_pointer_issue_count")) == 0,
                {"source_activation_ops_pointer_issue_count": summary.get("source_activation_ops_pointer_issue_count")},
            ),
            check(
                "source_activation_no_registry_drift",
                int_value(summary.get("source_activation_ops_registry_drift_count")) == 0,
                {"source_activation_ops_registry_drift_count": summary.get("source_activation_ops_registry_drift_count")},
            ),
            check(
                "source_activation_no_runtime_readiness_issue",
                int_value(summary.get("source_activation_ops_runtime_readiness_issue_count")) == 0,
                {
                    "source_activation_ops_runtime_readiness_issue_count": summary.get(
                        "source_activation_ops_runtime_readiness_issue_count"
                    )
                },
            ),
            check(
                "source_activation_no_evidence_integrity_issue",
                int_value(summary.get("source_activation_ops_evidence_integrity_issue_count")) == 0
                and int_value(summary.get("source_activation_ops_p0_evidence_integrity_issue_count")) == 0,
                {
                    "source_activation_ops_evidence_integrity_issue_count": summary.get(
                        "source_activation_ops_evidence_integrity_issue_count"
                    ),
                    "source_activation_ops_p0_evidence_integrity_issue_count": summary.get(
                        "source_activation_ops_p0_evidence_integrity_issue_count"
                    ),
                },
            ),
            check(
                "source_onboarding_no_p0_backlog",
                not source_gaps,
                {"source_onboarding_gap_count": len(source_gaps), "source_onboarding_gaps": source_gaps[:10]},
            ),
        ]
    if profile == "production-ready":
        return [
            check(
                "production_ready",
                verdict.get("production_ready") is True,
                {"production_ready": verdict.get("production_ready")},
            ),
            check(
                "readiness_state_production_ready",
                verdict.get("readiness_state") == "production_ready",
                {"readiness_state": verdict.get("readiness_state")},
            ),
            check(
                "control_tower_has_no_blockers",
                int_value(summary.get("control_tower_blocker_count")) == 0,
                {"control_tower_blocker_count": summary.get("control_tower_blocker_count", 0)},
            ),
            check("p0_gap_backlog_empty", not p0_gap_backlog, {"p0_gap_count": len(p0_gap_backlog)}),
        ]
    return [
        check("profile_supported", False, {"profile": profile, "supported": sorted(VALID_PROFILES)}),
    ]


def int_value(value: object) -> int:
    return value if isinstance(value, int) else 0

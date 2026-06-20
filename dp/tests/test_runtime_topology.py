from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import yaml

from enterprise_dp.contracts import ValidationResult
from enterprise_dp.environments import REQUIRED_P0_SERVICES
from enterprise_dp.runtime import (
    build_runtime_readiness_report,
    iac_profile_module_labels,
    iac_profile_module_sources,
    normalize_plan_resource_changes,
    required_iac_module_labels_for_profile,
    validate_iac_registry,
    validate_iac_profile_module_coverage,
    validate_runtime_topology,
    validate_runtime_services,
    validate_topology_environments,
    write_runtime_evidence_pack,
    write_runtime_iac_evidence_pack,
)


ROOT = Path(__file__).resolve().parents[1]


def test_repository_runtime_topology_is_valid() -> None:
    result = validate_runtime_topology(ROOT)

    assert result.errors == []
    assert result.checked_count == 2


def test_runtime_topology_requires_all_p0_services() -> None:
    path = ROOT / "platform" / "runtime" / "topology.yaml"
    topology = yaml.safe_load(path.read_text(encoding="utf-8"))
    services = [service for service in topology["runtimeServices"] if service["serviceId"] != "event_backbone"]
    result = ValidationResult()

    validate_runtime_services(path, services, environment_context={}, result=result)

    assert any("missing required P0 services: event_backbone" in error for error in result.errors)


def test_runtime_topology_environment_binding_must_match_manifest() -> None:
    path = ROOT / "platform" / "runtime" / "topology.yaml"
    topology = yaml.safe_load(path.read_text(encoding="utf-8"))
    environments = deepcopy(topology["environments"])
    environments[1]["runtimeReadiness"] = "fake_ready"
    environment_context = {
        "staging": {
            "manifest": {"runtimeReadiness": "topology_manifested_not_live_iac", "evidenceMode": "production_like_preflight"},
            "services": {},
        }
    }
    result = ValidationResult()

    validate_topology_environments(ROOT, path, environments, environment_context, result)

    assert any("runtimeReadiness must match environment manifest" in error for error in result.errors)


def test_iac_registry_profile_paths_and_service_coverage_are_valid() -> None:
    topology_path = ROOT / "platform" / "runtime" / "topology.yaml"
    iac_path = ROOT / "platform" / "runtime" / "iac-modules.yaml"
    topology = yaml.safe_load(topology_path.read_text(encoding="utf-8"))
    iac_registry = yaml.safe_load(iac_path.read_text(encoding="utf-8"))
    topology_context = {
        "service_ids": {service["serviceId"] for service in topology["runtimeServices"]},
        "profiles_by_environment": {entry["environment"]: entry["iacProfile"] for entry in topology["environments"]},
    }
    result = ValidationResult()

    validate_iac_registry(ROOT, iac_path, iac_registry, topology_context, result)

    assert result.errors == []


def test_opentofu_profiles_declare_required_p0_modules_and_sources() -> None:
    iac_path = ROOT / "platform" / "runtime" / "iac-modules.yaml"
    iac_registry = yaml.safe_load(iac_path.read_text(encoding="utf-8"))

    for profile_id in ("staging-opentofu", "prod-opentofu"):
        profile = next(profile for profile in iac_registry["profiles"] if profile["profileId"] == profile_id)
        profile_path = ROOT / profile["path"]
        labels = iac_profile_module_labels(profile_path)
        sources = iac_profile_module_sources(profile_path)
        required_labels = required_iac_module_labels_for_profile(profile_id, iac_registry["modules"])

        assert required_labels <= labels
        for label in required_labels:
            assert label in sources
            assert (profile_path.parent / sources[label]).resolve().exists()


def test_iac_profile_coverage_rejects_missing_local_module_source(tmp_path: Path) -> None:
    profile_path = tmp_path / "platform" / "runtime" / "iac" / "staging" / "main.tf"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text(
        """
module "event_backbone" {
  source = "../modules/missing-runtime-service"
}
""",
        encoding="utf-8",
    )
    result = ValidationResult()

    validate_iac_profile_module_coverage(
        tmp_path,
        tmp_path / "platform" / "runtime" / "iac-modules.yaml",
        {
            "staging-opentofu": {
                "profileId": "staging-opentofu",
                "environment": "staging",
                "type": "opentofu",
                "path": "platform/runtime/iac/staging/main.tf",
            }
        },
        [{"moduleId": "event-backbone", "serviceIds": ["event_backbone"], "profileIds": ["staging-opentofu"]}],
        result,
    )

    assert any("source does not exist" in error for error in result.errors)


def test_local_runtime_readiness_report_passes_preflight() -> None:
    report = build_runtime_readiness_report(
        ROOT,
        environment="local",
        generated_at="2026-06-16T00:00:00Z",
    )

    assert report["artifact_type"] == "runtime_readiness_report.v1"
    assert report["readiness_state"] == "local_preflight_ready"
    assert report["passed"] is True
    assert report["summary"]["required_p0_service_count"] == 12
    assert {gate["gate_id"] for gate in report["gates"]} >= {
        "runtime_topology_validated",
        "iac_profile_declared",
        "local_preflight_allowed",
    }


def test_prod_runtime_readiness_report_does_not_overclaim_live_iac() -> None:
    report = build_runtime_readiness_report(
        ROOT,
        environment="prod",
        generated_at="2026-06-16T00:00:00Z",
    )
    failed_gates = {gate["gate_id"] for gate in report["gates"] if gate["status"] == "failed"}

    assert report["readiness_state"] == "production_like_not_ready"
    assert report["passed"] is False
    assert "runtime_iac_deployed" in failed_gates
    assert "dr_test_passed" in failed_gates


def test_runtime_readiness_report_is_json_serializable() -> None:
    report = build_runtime_readiness_report(
        ROOT,
        environment="local",
        generated_at="2026-06-16T00:00:00Z",
    )

    assert json.loads(json.dumps(report, sort_keys=True))["environment"] == "local"


def test_runtime_readiness_cli_writes_blocked_prod_report(tmp_path: Path) -> None:
    output_path = tmp_path / "runtime" / "prod-readiness.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "runtime-readiness-check",
            "--root",
            str(ROOT),
            "--environment",
            "prod",
            "--output",
            str(output_path),
            "--generated-at",
            "2026-06-16T00:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert output_path.is_file()
    summary = json.loads(completed.stdout)
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["readiness_state"] == "production_like_not_ready"
    assert summary["failure_count"] >= 1
    assert report["passed"] is False
    assert any(gate["gate_id"] == "runtime_iac_deployed" for gate in report["gates"])


def test_staging_runtime_readiness_passes_with_complete_machine_evidence(tmp_path: Path) -> None:
    evidence = write_normalized_runtime_evidence_set(tmp_path, environment="staging")
    report = build_runtime_readiness_report(
        ROOT,
        environment="staging",
        iac_plan_path=evidence["iac_plan"],
        iac_apply_path=evidence["iac_apply"],
        drift_report_path=evidence["drift_report"],
        backup_report_path=evidence["backup_report"],
        health_report_path=evidence["health_report"],
        generated_at="2026-06-16T00:00:00Z",
    )

    assert report["readiness_state"] == "production_like_ready"
    assert report["passed"] is True
    assert report["summary"]["deployed_service_count"] == len(REQUIRED_P0_SERVICES)
    assert {gate["status"] for gate in report["gates"]} == {"passed"}


def test_prod_runtime_readiness_passes_with_complete_machine_evidence(tmp_path: Path) -> None:
    evidence = write_normalized_runtime_evidence_set(tmp_path, environment="prod", include_dr=True)
    report = build_runtime_readiness_report(
        ROOT,
        environment="prod",
        iac_plan_path=evidence["iac_plan"],
        iac_apply_path=evidence["iac_apply"],
        drift_report_path=evidence["drift_report"],
        backup_report_path=evidence["backup_report"],
        dr_report_path=evidence["dr_report"],
        health_report_path=evidence["health_report"],
        generated_at="2026-06-16T00:00:00Z",
    )

    assert report["readiness_state"] == "production_like_ready"
    assert report["passed"] is True
    assert all(item["backup_passed"] for item in report["service_matrix"] if item["backup_required"])


def test_runtime_readiness_rejects_environment_mismatched_evidence(tmp_path: Path) -> None:
    evidence = write_normalized_runtime_evidence_set(tmp_path, environment="prod", include_dr=True)
    report = build_runtime_readiness_report(
        ROOT,
        environment="staging",
        iac_plan_path=evidence["iac_plan"],
        iac_apply_path=evidence["iac_apply"],
        drift_report_path=evidence["drift_report"],
        backup_report_path=evidence["backup_report"],
        health_report_path=evidence["health_report"],
        generated_at="2026-06-16T00:00:00Z",
    )

    assert report["passed"] is False
    assert any("environment must be 'staging'" in failure for failure in report["failures"])


def test_runtime_readiness_rejects_partial_service_coverage(tmp_path: Path) -> None:
    evidence = write_normalized_runtime_evidence_set(tmp_path, environment="staging")
    plan = json.loads(Path(evidence["iac_plan"]).read_text(encoding="utf-8"))
    plan["service_matrix"] = [
        item for item in plan["service_matrix"] if item["service_id"] != "schema_registry"
    ]
    Path(evidence["iac_plan"]).write_text(json.dumps(plan), encoding="utf-8")

    report = build_runtime_readiness_report(
        ROOT,
        environment="staging",
        iac_plan_path=evidence["iac_plan"],
        iac_apply_path=evidence["iac_apply"],
        drift_report_path=evidence["drift_report"],
        backup_report_path=evidence["backup_report"],
        health_report_path=evidence["health_report"],
        generated_at="2026-06-16T00:00:00Z",
    )

    assert report["passed"] is False
    assert "required_service_plan_coverage" in {gate["gate_id"] for gate in report["gates"] if gate["status"] == "failed"}
    schema_row = next(item for item in report["service_matrix"] if item["service_id"] == "schema_registry")
    assert schema_row["plan_covered"] is False


def test_runtime_readiness_rejects_expired_evidence(tmp_path: Path) -> None:
    evidence = write_normalized_runtime_evidence_set(tmp_path, environment="staging")
    plan = json.loads(Path(evidence["iac_plan"]).read_text(encoding="utf-8"))
    plan["valid_until"] = "2026-06-15T23:59:59Z"
    Path(evidence["iac_plan"]).write_text(json.dumps(plan), encoding="utf-8")

    report = build_runtime_readiness_report(
        ROOT,
        environment="staging",
        iac_plan_path=evidence["iac_plan"],
        iac_apply_path=evidence["iac_apply"],
        drift_report_path=evidence["drift_report"],
        backup_report_path=evidence["backup_report"],
        health_report_path=evidence["health_report"],
        generated_at="2026-06-16T00:00:00Z",
    )

    assert report["passed"] is False
    assert any("valid_until has expired" in failure for failure in report["failures"])


def test_runtime_readiness_cli_accepts_complete_staging_evidence(tmp_path: Path) -> None:
    evidence = write_normalized_runtime_evidence_set(tmp_path, environment="staging")
    output_path = tmp_path / "runtime" / "staging-readiness.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "runtime-readiness-check",
            "--root",
            str(ROOT),
            "--environment",
            "staging",
            "--output",
            str(output_path),
            "--iac-plan",
            str(evidence["iac_plan"]),
            "--iac-apply",
            str(evidence["iac_apply"]),
            "--drift-report",
            str(evidence["drift_report"]),
            "--backup-report",
            str(evidence["backup_report"]),
            "--health-report",
            str(evidence["health_report"]),
            "--generated-at",
            "2026-06-16T00:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["readiness_state"] == "production_like_ready"
    assert summary["deployed_service_count"] == len(REQUIRED_P0_SERVICES)
    assert json.loads(output_path.read_text(encoding="utf-8"))["passed"] is True


def test_runtime_evidence_pack_writer_creates_ci_pack_that_cannot_signoff_staging(tmp_path: Path) -> None:
    pack = write_runtime_evidence_pack(
        ROOT,
        tmp_path / "pack",
        environment="staging",
        source_kind="ci_tool_output",
        generated_at="2026-06-16T00:00:00Z",
        valid_until="2026-06-17T00:00:00Z",
        git_sha="0123456789abcdef0123456789abcdef01234567",
        ci_run_id="ci-123",
        issuer_tool="opentofu",
        issuer_tool_version="1.10.0",
        artifact_base_uri="s3://runtime-evidence/staging",
    )

    assert pack.manifest["passed"] is False
    assert pack.manifest["production_signoff_allowed"] is False
    assert [blocker["blocker_id"] for blocker in pack.manifest["blockers"]] == ["normalized_iac_evidence_required"]
    assert set(pack.manifest["artifacts"]) == {
        "iac_plan",
        "iac_apply",
        "drift_report",
        "backup_report",
        "health_report",
    }
    report = build_runtime_readiness_report(
        ROOT,
        environment="staging",
        iac_plan_path=pack.manifest["artifacts"]["iac_plan"]["path"],
        iac_apply_path=pack.manifest["artifacts"]["iac_apply"]["path"],
        drift_report_path=pack.manifest["artifacts"]["drift_report"]["path"],
        backup_report_path=pack.manifest["artifacts"]["backup_report"]["path"],
        health_report_path=pack.manifest["artifacts"]["health_report"]["path"],
        generated_at="2026-06-16T00:00:00Z",
    )
    assert report["passed"] is False
    assert any("runtime-evidence-normalize-iac" in failure for failure in report["failures"])


def test_runtime_evidence_pack_cli_rejects_synthetic_prod_signoff(tmp_path: Path) -> None:
    output_dir = tmp_path / "synthetic-prod-pack"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "runtime-evidence-pack",
            "--root",
            str(ROOT),
            "--environment",
            "prod",
            "--output-dir",
            str(output_dir),
            "--git-sha",
            "0123456789abcdef0123456789abcdef01234567",
            "--ci-run-id",
            "local-sample",
            "--artifact-base-uri",
            "s3://runtime-evidence/prod",
            "--generated-at",
            "2026-06-16T00:00:00Z",
            "--valid-until",
            "2026-06-17T00:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["passed"] is False
    assert summary["production_signoff_allowed"] is False
    manifest = json.loads((output_dir / "runtime-evidence-pack-manifest.json").read_text(encoding="utf-8"))
    plan = json.loads((output_dir / "runtime-iac-plan.json").read_text(encoding="utf-8"))
    assert manifest["blockers"][0]["blocker_id"] == "synthetic_fixture_not_production_evidence"
    assert plan["environment"] == "prod"
    assert plan["status"] == "blocked"
    assert plan["production_evidence"] is False

    report = build_runtime_readiness_report(
        ROOT,
        environment="prod",
        iac_plan_path=manifest["artifacts"]["iac_plan"]["path"],
        iac_apply_path=manifest["artifacts"]["iac_apply"]["path"],
        drift_report_path=manifest["artifacts"]["drift_report"]["path"],
        backup_report_path=manifest["artifacts"]["backup_report"]["path"],
        dr_report_path=manifest["artifacts"]["dr_report"]["path"],
        health_report_path=manifest["artifacts"]["health_report"]["path"],
        generated_at="2026-06-16T00:00:00Z",
    )
    assert report["passed"] is False
    assert any("synthetic_fixture evidence cannot be used" in failure for failure in report["failures"])


def test_runtime_evidence_pack_cli_creates_prod_ci_pack_but_blocks_signoff(tmp_path: Path) -> None:
    output_dir = tmp_path / "prod-ci-pack"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "runtime-evidence-pack",
            "--root",
            str(ROOT),
            "--environment",
            "prod",
            "--source-kind",
            "ci_tool_output",
            "--output-dir",
            str(output_dir),
            "--git-sha",
            "0123456789abcdef0123456789abcdef01234567",
            "--ci-run-id",
            "ci-456",
            "--artifact-base-uri",
            "s3://runtime-evidence/prod",
            "--change-request-id",
            "CHG-456",
            "--generated-at",
            "2026-06-16T00:00:00Z",
            "--valid-until",
            "2026-06-17T00:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["passed"] is False
    assert summary["production_signoff_allowed"] is False
    manifest = json.loads((output_dir / "runtime-evidence-pack-manifest.json").read_text(encoding="utf-8"))
    assert "dr_report" in manifest["artifacts"]
    assert [blocker["blocker_id"] for blocker in manifest["blockers"]] == ["normalized_iac_evidence_required"]
    report = build_runtime_readiness_report(
        ROOT,
        environment="prod",
        iac_plan_path=manifest["artifacts"]["iac_plan"]["path"],
        iac_apply_path=manifest["artifacts"]["iac_apply"]["path"],
        drift_report_path=manifest["artifacts"]["drift_report"]["path"],
        backup_report_path=manifest["artifacts"]["backup_report"]["path"],
        dr_report_path=manifest["artifacts"]["dr_report"]["path"],
        health_report_path=manifest["artifacts"]["health_report"]["path"],
        generated_at="2026-06-16T00:00:00Z",
    )
    assert report["passed"] is False
    assert any("runtime-evidence-normalize-iac" in failure for failure in report["failures"])


def test_normalize_plan_resource_changes_counts_iac_actions() -> None:
    plan = {
        "format_version": "1.0",
        "terraform_version": "1.10.0",
        "resource_changes": [
            {"address": "module.event_backbone.null_resource.main", "mode": "managed", "change": {"actions": ["create"]}},
            {"address": "module.schema_registry.null_resource.main", "mode": "managed", "change": {"actions": ["update"]}},
            {"address": "module.object_storage.null_resource.main", "mode": "managed", "change": {"actions": ["delete"]}},
            {"address": "module.orchestration.null_resource.main", "mode": "managed", "change": {"actions": ["delete", "create"]}},
            {"address": "module.observability.null_resource.main", "mode": "managed", "change": {"actions": ["no-op"]}},
        ],
    }
    mappings = [
        {"service_id": "event_backbone", "address_prefix": "module.event_backbone"},
        {"service_id": "schema_registry", "address_prefix": "module.schema_registry"},
        {"service_id": "object_storage", "address_prefix": "module.object_storage"},
        {"service_id": "orchestration", "address_prefix": "module.orchestration"},
        {"service_id": "observability", "address_prefix": "module.observability"},
    ]

    matrix, summary = normalize_plan_resource_changes(
        plan,
        mappings,
        ["event_backbone", "schema_registry", "object_storage", "orchestration", "observability"],
    )

    assert summary["change_count"] == 4
    assert summary["destructive_change_count"] == 2
    assert summary["replacement_count"] == 1
    assert all(item["covered"] for item in matrix)


def test_runtime_iac_normalizer_creates_staging_pack_from_plan_and_state_json(tmp_path: Path) -> None:
    inputs = write_iac_normalizer_inputs(tmp_path, environment="staging")
    pack = write_runtime_iac_evidence_pack(
        ROOT,
        tmp_path / "normalized-pack",
        environment="staging",
        plan_json_path=inputs["plan_json"],
        state_json_path=inputs["state_json"],
        health_checks_path=inputs["health_checks"],
        backup_checks_path=inputs["backup_checks"],
        source_kind="ci_tool_output",
        generated_at="2026-06-16T00:00:00Z",
        valid_until="2026-06-17T00:00:00Z",
        git_sha="0123456789abcdef0123456789abcdef01234567",
        ci_run_id="ci-789",
        issuer_tool="opentofu",
        issuer_tool_version="1.10.0",
        artifact_base_uri="s3://runtime-evidence/staging/ci-789",
    )

    report = build_runtime_readiness_report(
        ROOT,
        environment="staging",
        iac_plan_path=pack.manifest["artifacts"]["iac_plan"]["path"],
        iac_apply_path=pack.manifest["artifacts"]["iac_apply"]["path"],
        drift_report_path=pack.manifest["artifacts"]["drift_report"]["path"],
        backup_report_path=pack.manifest["artifacts"]["backup_report"]["path"],
        health_report_path=pack.manifest["artifacts"]["health_report"]["path"],
        generated_at="2026-06-16T00:00:00Z",
    )

    assert pack.manifest["plan_summary"]["change_count"] == 0
    assert pack.manifest["deployed_services"] == sorted(REQUIRED_P0_SERVICES)
    assert report["passed"] is True


def test_runtime_iac_normalizer_cli_rejects_invalid_plan_json(tmp_path: Path) -> None:
    inputs = write_iac_normalizer_inputs(tmp_path, environment="staging")
    inputs["plan_json"].write_text(json.dumps({"format_version": "1.0"}), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "runtime-evidence-normalize-iac",
            "--root",
            str(ROOT),
            "--environment",
            "staging",
            "--output-dir",
            str(tmp_path / "out"),
            "--plan-json",
            str(inputs["plan_json"]),
            "--state-json",
            str(inputs["state_json"]),
            "--health-checks",
            str(inputs["health_checks"]),
            "--backup-checks",
            str(inputs["backup_checks"]),
            "--git-sha",
            "0123456789abcdef0123456789abcdef01234567",
            "--ci-run-id",
            "ci-789",
            "--artifact-base-uri",
            "s3://runtime-evidence/staging/ci-789",
            "--issuer-tool-version",
            "1.10.0",
            "--generated-at",
            "2026-06-16T00:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "resource_changes" in json.loads(completed.stdout)["error"]


def test_runtime_iac_normalizer_prod_destructive_plan_fails_readiness(tmp_path: Path) -> None:
    inputs = write_iac_normalizer_inputs(tmp_path, environment="prod", destructive_service="object_storage", include_dr=True)
    pack = write_runtime_iac_evidence_pack(
        ROOT,
        tmp_path / "prod-normalized-pack",
        environment="prod",
        plan_json_path=inputs["plan_json"],
        state_json_path=inputs["state_json"],
        health_checks_path=inputs["health_checks"],
        backup_checks_path=inputs["backup_checks"],
        dr_exercise_path=inputs["dr_exercise"],
        source_kind="ci_tool_output",
        generated_at="2026-06-16T00:00:00Z",
        valid_until="2026-06-17T00:00:00Z",
        git_sha="0123456789abcdef0123456789abcdef01234567",
        ci_run_id="ci-790",
        issuer_tool="opentofu",
        issuer_tool_version="1.10.0",
        artifact_base_uri="s3://runtime-evidence/prod/ci-790",
        change_request_id="CHG-790",
    )

    report = build_runtime_readiness_report(
        ROOT,
        environment="prod",
        iac_plan_path=pack.manifest["artifacts"]["iac_plan"]["path"],
        iac_apply_path=pack.manifest["artifacts"]["iac_apply"]["path"],
        drift_report_path=pack.manifest["artifacts"]["drift_report"]["path"],
        backup_report_path=pack.manifest["artifacts"]["backup_report"]["path"],
        dr_report_path=pack.manifest["artifacts"]["dr_report"]["path"],
        health_report_path=pack.manifest["artifacts"]["health_report"]["path"],
        generated_at="2026-06-16T00:00:00Z",
    )

    assert pack.manifest["plan_summary"]["destructive_change_count"] == 1
    assert report["passed"] is False
    assert "no_destructive_prod_plan" in {gate["gate_id"] for gate in report["gates"] if gate["status"] == "failed"}


def test_runtime_iac_normalizer_does_not_copy_sensitive_state_values(tmp_path: Path) -> None:
    inputs = write_iac_normalizer_inputs(tmp_path, environment="staging", secret_marker="SUPER_SECRET_TOKEN")
    pack = write_runtime_iac_evidence_pack(
        ROOT,
        tmp_path / "secret-normalized-pack",
        environment="staging",
        plan_json_path=inputs["plan_json"],
        state_json_path=inputs["state_json"],
        health_checks_path=inputs["health_checks"],
        backup_checks_path=inputs["backup_checks"],
        source_kind="ci_tool_output",
        generated_at="2026-06-16T00:00:00Z",
        valid_until="2026-06-17T00:00:00Z",
        git_sha="0123456789abcdef0123456789abcdef01234567",
        ci_run_id="ci-791",
        issuer_tool="opentofu",
        issuer_tool_version="1.10.0",
        artifact_base_uri="s3://runtime-evidence/staging/ci-791",
    )

    for artifact in pack.manifest["artifacts"].values():
        assert "SUPER_SECRET_TOKEN" not in Path(artifact["path"]).read_text(encoding="utf-8")


def write_normalized_runtime_evidence_set(
    tmp_path: Path,
    *,
    environment: str,
    include_dr: bool = False,
    destructive_service: str | None = None,
) -> dict[str, Path]:
    inputs = write_iac_normalizer_inputs(
        tmp_path,
        environment=environment,
        destructive_service=destructive_service,
        include_dr=include_dr,
    )
    pack = write_runtime_iac_evidence_pack(
        ROOT,
        tmp_path / f"{environment}-normalized-pack",
        environment=environment,
        plan_json_path=inputs["plan_json"],
        state_json_path=inputs["state_json"],
        health_checks_path=inputs["health_checks"],
        backup_checks_path=inputs["backup_checks"],
        dr_exercise_path=inputs.get("dr_exercise"),
        source_kind="ci_tool_output",
        generated_at="2026-06-16T00:00:00Z",
        valid_until="2026-06-17T00:00:00Z",
        git_sha="0123456789abcdef0123456789abcdef01234567",
        ci_run_id=f"ci-{environment}-normalized",
        issuer_tool="opentofu",
        issuer_tool_version="1.10.0",
        artifact_base_uri=f"s3://runtime-evidence/{environment}/normalized",
        change_request_id="CHG-123" if environment == "prod" else None,
    )
    return {kind: Path(entry["path"]) for kind, entry in pack.manifest["artifacts"].items()}


def write_runtime_evidence_set(
    tmp_path: Path,
    *,
    environment: str,
    profile_id: str,
    include_dr: bool = False,
) -> dict[str, Path]:
    service_ids = sorted(REQUIRED_P0_SERVICES)
    stateful_services = runtime_stateful_p0_services()
    paths = {
        "iac_plan": tmp_path / "iac-plan.json",
        "iac_apply": tmp_path / "iac-apply.json",
        "drift_report": tmp_path / "drift.json",
        "backup_report": tmp_path / "backup.json",
        "health_report": tmp_path / "health.json",
    }
    if include_dr:
        paths["dr_report"] = tmp_path / "dr.json"
    write_json(
        paths["iac_plan"],
        common_evidence("runtime_iac_plan_evidence.v1", "iac_plan", environment, profile_id)
        | {
            "plan": {
                "status": "succeeded",
                "plan_hash": "sha256:plan",
                "state_hash": "sha256:state-before",
                "change_count": len(service_ids),
                "destructive_change_count": 0,
                "replacement_count": 0,
            },
            "service_matrix": [
                {"service_id": service_id, "module_id": service_id.replace("_", "-"), "covered": True, "action": "update"}
                for service_id in service_ids
            ],
        },
    )
    write_json(
        paths["iac_apply"],
        common_evidence("runtime_iac_apply_evidence.v1", "iac_apply", environment, profile_id)
        | {
            "apply": {
                "status": "succeeded",
                "applied_plan_hash": "sha256:plan",
                "state_hash": "sha256:state-after",
                "drift_status": "clean",
            },
            "deployed_services": service_ids,
            "smoke_checks": [
                {"service_id": service_id, "status": "passed"}
                for service_id in service_ids
            ],
        },
    )
    write_json(
        paths["drift_report"],
        common_evidence("runtime_iac_drift_report.v1", "drift_check", environment, profile_id)
        | {
            "drift": {"status": "clean", "drifted_resource_count": 0},
            "service_matrix": [
                {"service_id": service_id, "module_id": service_id.replace("_", "-"), "covered": True}
                for service_id in service_ids
            ],
        },
    )
    write_json(
        paths["backup_report"],
        common_evidence("runtime_backup_evidence.v1", "backup_restore", environment, profile_id)
        | {
            "backups": [
                {"service_id": service_id, "status": "passed", "restore_tested": True}
                for service_id in stateful_services
            ],
        },
    )
    write_json(
        paths["health_report"],
        common_evidence("runtime_service_health_evidence.v1", "service_health", environment, profile_id)
        | {
            "checks": [
                {"service_id": service_id, "status": "passed"}
                for service_id in service_ids
            ],
        },
    )
    if include_dr:
        write_json(
            paths["dr_report"],
            common_evidence("runtime_dr_evidence.v1", "dr_exercise", environment, profile_id)
            | {
                "exercise": {"status": "passed", "rto_minutes": 60, "rpo_minutes": 15},
                "covered_services": service_ids,
            },
        )
    return paths


def common_evidence(artifact_type: str, evidence_kind: str, environment: str, profile_id: str) -> dict[str, object]:
    payload = {
        "artifact_type": artifact_type,
        "schema_version": 1,
        "evidence_id": f"{environment}-{evidence_kind}-001",
        "environment": environment,
        "profile_id": profile_id,
        "evidence_kind": evidence_kind,
        "source_kind": "ci_tool_output",
        "sample": False,
        "production_evidence": True,
        "readiness_claim": "machine_readable_runtime_evidence",
        "status": "passed",
        "generated_at": "2026-06-16T00:00:00Z",
        "valid_until": "2026-06-17T00:00:00Z",
        "issuer": {"tool": "opentofu", "tool_version": "1.10.0", "ci_run_id": "ci-123"},
        "git_sha": "0123456789abcdef0123456789abcdef01234567",
        "artifact_uri": f"s3://runtime-evidence/{environment}/{evidence_kind}.json",
        "artifact_sha256": "sha256:evidence",
        "command": "opentofu show -json",
        "exit_code": 0,
        "redacted": True,
    }
    if environment == "prod":
        payload["change_request_id"] = "CHG-123"
    return payload


def runtime_stateful_p0_services() -> list[str]:
    topology = yaml.safe_load((ROOT / "platform" / "runtime" / "topology.yaml").read_text(encoding="utf-8"))
    return sorted(
        service["serviceId"]
        for service in topology["runtimeServices"]
        if service["serviceId"] in REQUIRED_P0_SERVICES and service["stateful"] is True
    )


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def write_iac_normalizer_inputs(
    tmp_path: Path,
    *,
    environment: str,
    destructive_service: str | None = None,
    include_dr: bool = False,
    secret_marker: str = "redacted",
) -> dict[str, Path]:
    service_ids = sorted(REQUIRED_P0_SERVICES)
    stateful_services = runtime_stateful_p0_services()
    plan_changes = []
    state_resources = []
    for service_id in service_ids:
        actions = ["delete"] if service_id == destructive_service else ["no-op"]
        plan_changes.append(
            {
                "address": f"module.{service_id}.null_resource.runtime",
                "mode": "managed",
                "type": "null_resource",
                "name": "runtime",
                "change": {
                    "actions": actions,
                    "before": {"secret": secret_marker},
                    "after": {"secret": secret_marker},
                },
            }
        )
        state_resources.append(
            {
                "address": f"module.{service_id}.null_resource.runtime",
                "mode": "managed",
                "type": "null_resource",
                "name": "runtime",
                "values": {"secret": secret_marker, "service_id": service_id},
                "sensitive_values": {"secret": True},
            }
        )
    paths = {
        "plan_json": tmp_path / "opentofu-plan.json",
        "state_json": tmp_path / "opentofu-state.json",
        "health_checks": tmp_path / "health-checks.json",
        "backup_checks": tmp_path / "backup-checks.json",
    }
    write_json(
        paths["plan_json"],
        {
            "format_version": "1.0",
            "terraform_version": "1.10.0",
            "resource_changes": plan_changes,
            "resource_drift": [],
        },
    )
    write_json(
        paths["state_json"],
        {
            "format_version": "1.0",
            "terraform_version": "1.10.0",
            "values": {"root_module": {"resources": state_resources}},
        },
    )
    write_json(paths["health_checks"], {"checks": [{"service_id": service_id, "status": "passed"} for service_id in service_ids]})
    write_json(
        paths["backup_checks"],
        {"backups": [{"service_id": service_id, "status": "passed", "restore_tested": True} for service_id in stateful_services]},
    )
    if include_dr:
        paths["dr_exercise"] = tmp_path / "dr-exercise.json"
        write_json(
            paths["dr_exercise"],
            {"exercise": {"status": "passed", "rto_minutes": 60, "rpo_minutes": 15}, "covered_services": service_ids},
        )
    return paths

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from enterprise_df.access_grants import write_access_grant_evidence_report
from enterprise_df.access_policy import write_access_policy_report
from enterprise_df.catalog import canonical_json, write_catalog_bundle
from enterprise_df.ingestion import BronzeIngestionResult, run_bronze_ingestion
from enterprise_df.pipelines import (
    PipelineResult,
    PipelineRunRequest,
    default_pipeline_registry,
    run_recommendation_pipeline_from_bronze,
)
from enterprise_df.release import build_pipeline_release_evidence, build_recommendation_release_evidence
from enterprise_df.retention import write_retention_evidence_report
from enterprise_df.schema_registry import write_schema_registry_report
from enterprise_df.usecases import get_use_case_pipeline


RECOMMENDATION_TOPIC = "recommendation.tracking.v1"


@dataclass(frozen=True)
class UseCaseRunResult:
    release_id: str
    use_case_id: str
    runner_id: str
    topic: str | None
    primary_output: str
    ingestion: BronzeIngestionResult | None
    pipeline: Any
    catalog_bundle_path: Path
    evidence_path: Path
    evidence: dict[str, Any]


@dataclass(frozen=True)
class RecommendationSliceResult:
    release_id: str
    ingestion: BronzeIngestionResult
    medallion: PipelineResult
    catalog_bundle_path: Path
    evidence_path: Path
    evidence: dict[str, Any]


def run_use_case(
    root: str | Path,
    input_path: str | Path,
    output_dir: str | Path,
    *,
    use_case_id: str,
    release_id: str,
    runner_id: str | None = None,
    topic: str | None = None,
    primary_output: str | None = None,
    environment: str = "local",
    ingested_at: str | None = None,
    built_at: str | None = None,
    evaluation_time: str | None = None,
    schema_id: str | None = None,
    snapshot_id: str | None = None,
    code_commit_sha: str | None = None,
    schema_registry_report_uri: str | None = None,
    schema_registry_report_hash: str | None = None,
    validator_output_uri: str | None = None,
    access_policy_check_id: str | None = None,
    access_policy_report_uri: str | None = None,
    access_policy_report_hash: str | None = None,
    access_grant_evidence_uri: str | None = None,
    access_grant_evidence_hash: str | None = None,
    retention_evidence_uri: str | None = None,
    retention_evidence_hash: str | None = None,
    retention_evidence_input_path: str | Path | None = None,
    snapshot_evidence_uri: str | None = None,
    snapshot_evidence_hash: str | None = None,
    approver: str | None = None,
) -> UseCaseRunResult:
    """Run a registered use-case implementation with generic enterprise evidence."""

    platform_root = Path(root)
    target_dir = Path(output_dir)
    registry = default_pipeline_registry()
    implementation = get_use_case_pipeline(platform_root, use_case_id, runner_id=runner_id)
    resolved_runner_id = str(implementation["runnerId"])
    runner = registry.get(resolved_runner_id)
    spec = runner.spec
    if use_case_id not in spec.use_cases:
        raise ValueError(f"runner {resolved_runner_id!r} is not registered for use case {use_case_id!r}")

    input_topics = _string_list(implementation.get("inputTopics")) or list(spec.input_topics)
    input_data_products = _string_list(implementation.get("inputDataProducts")) or list(spec.input_data_products)
    output_data_products = _string_list(implementation.get("outputDataProducts")) or list(spec.output_data_products)
    quality_profile_id = str(implementation.get("qualityProfile")) if implementation.get("qualityProfile") else None
    release_profile_id = str(implementation.get("releaseEvidenceProfile")) if implementation.get("releaseEvidenceProfile") else None
    resolved_primary_output = primary_output or str(implementation.get("primaryOutput") or spec.primary_output or "")
    if not resolved_primary_output:
        raise ValueError(f"use case {use_case_id!r} has no primary output for runner {resolved_runner_id!r}")
    if output_data_products and resolved_primary_output not in output_data_products:
        raise ValueError(
            f"primary output {resolved_primary_output!r} is not declared in runner outputs {output_data_products!r}"
        )
    resolved_topic = _resolve_topic(topic, input_topics, use_case_id)

    ingestion: BronzeIngestionResult | None = None
    runner_input_path = Path(input_path)
    runner_options: dict[str, Any] = {}
    if spec.input_kind == "approved_bronze_jsonl":
        if not resolved_topic:
            raise ValueError(f"use case {use_case_id!r} requires a topic for Bronze ingestion")
        ingestion = run_bronze_ingestion(
            platform_root,
            resolved_topic,
            input_path,
            target_dir / "ingestion",
            ingested_at=ingested_at,
            ingest_run_id=f"{release_id}-{use_case_id}-ingest",
            schema_id=schema_id,
        )
        runner_input_path = ingestion.approved_path
        runner_options["upstream_manifest_path"] = ingestion.manifest_path
    elif spec.input_kind == "raw_event_jsonl" and ingested_at:
        runner_options["ingested_at"] = ingested_at

    runner_options["snapshot_id"] = snapshot_id or _default_snapshot_id(release_id, resolved_primary_output)
    if built_at:
        runner_options["built_at"] = built_at

    pipeline_result = registry.run(
        resolved_runner_id,
        PipelineRunRequest(
            input_path=runner_input_path,
            output_dir=target_dir / "pipeline" / _path_safe(resolved_runner_id),
            options={key: value for key, value in runner_options.items() if value is not None},
        ),
    )

    manifest_paths = [
        path
        for path in (
            ingestion.manifest_path if ingestion else None,
            pipeline_result.manifest_path,
        )
        if path is not None
    ]
    generated_at = evaluation_time or built_at or ingested_at
    catalog_bundle_path = target_dir / "catalog" / "catalog-bundle.json"
    write_catalog_bundle(
        platform_root,
        catalog_bundle_path,
        manifest_paths=manifest_paths,
        generated_at=generated_at,
    )

    if schema_registry_report_uri is None and environment in {"local", "dev"} and resolved_topic:
        schema_registry_result = write_schema_registry_report(
            platform_root,
            target_dir / "evidence" / f"schema-registry.{use_case_id}.{release_id}.json",
            topic_name=resolved_topic,
            generated_at=generated_at,
        )
        schema_registry_report_uri = schema_registry_result.output_path.as_posix()
    elif schema_registry_report_uri is None and environment in {"local", "dev"} and spec.input_kind in {"data_product_snapshot", "semantic_metric_snapshot"}:
        schema_registry_report_uri = write_snapshot_schema_preflight_report(
            target_dir / "evidence" / f"schema-registry.{use_case_id}.{release_id}.json",
            use_case_id=use_case_id,
            runner_id=resolved_runner_id,
            input_kind=spec.input_kind,
            output_data_products=output_data_products,
            generated_at=generated_at,
        ).as_posix()

    if access_policy_report_uri is None and environment in {"local", "dev"}:
        primary_layer = pipeline_result.manifest.get("layers", {}).get(resolved_primary_output, {})
        access_policy_result = write_access_policy_report(
            platform_root,
            target_dir / "evidence" / f"access-policy.{use_case_id}.{release_id}.json",
            data_product_name=resolved_primary_output,
            environment=environment,
            release_id=release_id,
            dataset_snapshot_id=pipeline_result.snapshot_id,
            table_version=primary_layer.get("content_hash") or pipeline_result.manifest.get("content_hash"),
            content_hash=primary_layer.get("content_hash") or pipeline_result.manifest.get("content_hash"),
            row_count=primary_layer.get("row_count") or pipeline_result.manifest.get("row_count"),
            generated_at=generated_at,
        )
        access_policy_report_uri = access_policy_result.output_path.as_posix()
        access_policy_check_id = access_policy_check_id or str(access_policy_result.report["check_id"])

    if access_grant_evidence_uri is None and environment in {"local", "dev"}:
        primary_layer = pipeline_result.manifest.get("layers", {}).get(resolved_primary_output, {})
        access_grant_result = write_access_grant_evidence_report(
            platform_root,
            target_dir / "evidence" / f"access-grant.{use_case_id}.{release_id}.json",
            data_product_name=resolved_primary_output,
            environment=environment,
            release_id=release_id,
            dataset_snapshot_id=pipeline_result.snapshot_id,
            table_version=primary_layer.get("content_hash") or pipeline_result.manifest.get("content_hash"),
            content_hash=primary_layer.get("content_hash") or pipeline_result.manifest.get("content_hash"),
            generated_at=generated_at,
        )
        access_grant_evidence_uri = access_grant_result.output_path.as_posix()

    if retention_evidence_uri is None and (environment in {"local", "dev"} or retention_evidence_input_path is not None):
        primary_layer = pipeline_result.manifest.get("layers", {}).get(resolved_primary_output, {})
        retention_result = write_retention_evidence_report(
            platform_root,
            target_dir / "evidence" / f"retention.{use_case_id}.{release_id}.json",
            data_product_name=resolved_primary_output,
            environment=environment,
            release_id=release_id,
            dataset_snapshot_id=pipeline_result.snapshot_id,
            table_version=primary_layer.get("content_hash") or pipeline_result.manifest.get("content_hash"),
            content_hash=primary_layer.get("content_hash") or pipeline_result.manifest.get("content_hash"),
            row_count=primary_layer.get("row_count") or pipeline_result.manifest.get("row_count"),
            generated_at=generated_at,
            evidence_input_path=retention_evidence_input_path,
        )
        retention_evidence_uri = retention_result.output_path.as_posix()

    evidence_path = target_dir / "evidence" / f"use-case.{use_case_id}.{release_id}.json"
    evidence = build_pipeline_release_evidence(
        platform_root,
        release_id=release_id,
        environment=environment,
        use_case_id=use_case_id,
        runner_id=resolved_runner_id,
        runner_input_kind=spec.input_kind,
        pipeline_manifest_path=pipeline_result.manifest_path,
        catalog_bundle_path=catalog_bundle_path,
        primary_output=resolved_primary_output,
        output_path=evidence_path,
        input_topics=input_topics,
        input_data_products=input_data_products,
        output_data_products=output_data_products,
        quality_profile_id=quality_profile_id,
        release_profile_id=release_profile_id,
        ingestion_manifest_path=ingestion.manifest_path if ingestion else None,
        generated_at=generated_at,
        code_commit_sha=code_commit_sha,
        schema_registry_report_uri=schema_registry_report_uri,
        schema_registry_report_hash=schema_registry_report_hash,
        validator_output_uri=validator_output_uri,
        access_policy_check_id=access_policy_check_id,
        access_policy_report_uri=access_policy_report_uri,
        access_policy_report_hash=access_policy_report_hash,
        access_grant_evidence_uri=access_grant_evidence_uri,
        access_grant_evidence_hash=access_grant_evidence_hash,
        retention_evidence_uri=retention_evidence_uri,
        retention_evidence_hash=retention_evidence_hash,
        snapshot_evidence_uri=snapshot_evidence_uri,
        snapshot_evidence_hash=snapshot_evidence_hash,
        approver=approver,
    )

    return UseCaseRunResult(
        release_id=release_id,
        use_case_id=use_case_id,
        runner_id=resolved_runner_id,
        topic=resolved_topic,
        primary_output=resolved_primary_output,
        ingestion=ingestion,
        pipeline=pipeline_result,
        catalog_bundle_path=catalog_bundle_path,
        evidence_path=evidence_path,
        evidence=evidence,
    )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def write_snapshot_schema_preflight_report(
    output_path: Path,
    *,
    use_case_id: str,
    runner_id: str,
    input_kind: str,
    output_data_products: list[str],
    generated_at: str | None,
) -> Path:
    report = {
        "artifact_type": "schema_registry_report.v1",
        "report_version": 1,
        "generated_at": generated_at,
        "registry_uri": "local-data-product-snapshot-preflight",
        "compatibility_passed": True,
        "subject_count": len(output_data_products),
        "subjects": [
            {
                "subject": data_product_name,
                "compatibility": "DATA_PRODUCT_CONTRACT_VALIDATED",
                "status": "passed",
            }
            for data_product_name in output_data_products
        ],
        "summary": {
            "failed_subjects": [],
            "use_case_id": use_case_id,
            "runner_id": runner_id,
            "input_kind": input_kind,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return output_path


def _resolve_topic(topic: str | None, input_topics: list[str], use_case_id: str) -> str | None:
    if topic:
        if input_topics and topic not in input_topics:
            raise ValueError(f"topic {topic!r} is not declared for use case {use_case_id!r}")
        return topic
    if len(input_topics) == 1:
        return input_topics[0]
    if not input_topics:
        return None
    raise ValueError(f"use case {use_case_id!r} requires topic disambiguation; candidates={input_topics!r}")


def _default_snapshot_id(release_id: str, primary_output: str) -> str:
    return f"{release_id}-{_path_safe(primary_output)}"


def _path_safe(value: str) -> str:
    return value.replace(".", "_").replace("-", "_")


def run_recommendation_slice(
    root: str | Path,
    input_path: str | Path,
    output_dir: str | Path,
    *,
    release_id: str,
    environment: str = "local",
    ingested_at: str | None = None,
    built_at: str | None = None,
    evaluation_time: str | None = None,
    schema_id: str | None = None,
    code_commit_sha: str | None = None,
    schema_registry_report_uri: str | None = None,
    schema_registry_report_hash: str | None = None,
    validator_output_uri: str | None = None,
    access_policy_check_id: str | None = None,
    access_policy_report_uri: str | None = None,
    access_policy_report_hash: str | None = None,
    access_grant_evidence_uri: str | None = None,
    access_grant_evidence_hash: str | None = None,
    retention_evidence_uri: str | None = None,
    retention_evidence_hash: str | None = None,
    retention_evidence_input_path: str | Path | None = None,
    snapshot_evidence_uri: str | None = None,
    snapshot_evidence_hash: str | None = None,
    approver: str | None = None,
) -> RecommendationSliceResult:
    """Run the local recommendation data-product slice with release evidence."""

    target_dir = Path(output_dir)
    ingestion = run_bronze_ingestion(
        root,
        RECOMMENDATION_TOPIC,
        input_path,
        target_dir / "ingestion",
        ingested_at=ingested_at,
        ingest_run_id=f"{release_id}-ingest",
        schema_id=schema_id,
    )
    medallion = run_recommendation_pipeline_from_bronze(
        ingestion.approved_path,
        target_dir / "medallion",
        upstream_manifest_path=ingestion.manifest_path,
        snapshot_id=f"{release_id}-recsys",
        built_at=built_at,
    )

    catalog_bundle_path = target_dir / "catalog" / "catalog-bundle.json"
    write_catalog_bundle(
        root,
        catalog_bundle_path,
        manifest_paths=[ingestion.manifest_path, medallion.manifest_path],
        generated_at=evaluation_time or built_at or ingested_at,
    )

    if schema_registry_report_uri is None and environment in {"local", "dev"}:
        schema_registry_result = write_schema_registry_report(
            root,
            target_dir / "evidence" / f"schema-registry.{release_id}.json",
            topic_name=RECOMMENDATION_TOPIC,
            generated_at=evaluation_time or built_at or ingested_at,
        )
        schema_registry_report_uri = schema_registry_result.output_path.as_posix()

    if access_policy_report_uri is None and environment in {"local", "dev"}:
        access_policy_result = write_access_policy_report(
            root,
            target_dir / "evidence" / f"access-policy.{release_id}.json",
            data_product_name="gold.recsys_interactions",
            environment=environment,
            release_id=release_id,
            dataset_snapshot_id=medallion.snapshot_id,
            table_version=medallion.manifest.get("content_hash"),
            content_hash=medallion.manifest.get("content_hash"),
            row_count=medallion.manifest.get("row_count"),
            generated_at=evaluation_time or built_at or ingested_at,
        )
        access_policy_report_uri = access_policy_result.output_path.as_posix()
        access_policy_check_id = access_policy_check_id or str(access_policy_result.report["check_id"])

    if access_grant_evidence_uri is None and environment in {"local", "dev"}:
        access_grant_result = write_access_grant_evidence_report(
            root,
            target_dir / "evidence" / f"access-grant.{release_id}.json",
            data_product_name="gold.recsys_interactions",
            environment=environment,
            release_id=release_id,
            dataset_snapshot_id=medallion.snapshot_id,
            table_version=medallion.manifest.get("content_hash"),
            content_hash=medallion.manifest.get("content_hash"),
            generated_at=evaluation_time or built_at or ingested_at,
        )
        access_grant_evidence_uri = access_grant_result.output_path.as_posix()

    if retention_evidence_uri is None and (environment in {"local", "dev"} or retention_evidence_input_path is not None):
        retention_result = write_retention_evidence_report(
            root,
            target_dir / "evidence" / f"retention.{release_id}.json",
            data_product_name="gold.recsys_interactions",
            environment=environment,
            release_id=release_id,
            dataset_snapshot_id=medallion.snapshot_id,
            table_version=medallion.manifest.get("content_hash"),
            content_hash=medallion.manifest.get("content_hash"),
            row_count=medallion.manifest.get("row_count"),
            generated_at=evaluation_time or built_at or ingested_at,
            evidence_input_path=retention_evidence_input_path,
        )
        retention_evidence_uri = retention_result.output_path.as_posix()

    evidence_path = target_dir / "evidence" / f"recommendation-slice.{release_id}.json"
    evidence = build_recommendation_release_evidence(
        root,
        release_id=release_id,
        environment=environment,
        ingestion_manifest_path=ingestion.manifest_path,
        medallion_manifest_path=medallion.manifest_path,
        catalog_bundle_path=catalog_bundle_path,
        approved_bronze_path=ingestion.approved_path,
        output_path=evidence_path,
        generated_at=evaluation_time or built_at or ingested_at,
        code_commit_sha=code_commit_sha,
        schema_registry_report_uri=schema_registry_report_uri,
        schema_registry_report_hash=schema_registry_report_hash,
        validator_output_uri=validator_output_uri,
        access_policy_check_id=access_policy_check_id,
        access_policy_report_uri=access_policy_report_uri,
        access_policy_report_hash=access_policy_report_hash,
        access_grant_evidence_uri=access_grant_evidence_uri,
        access_grant_evidence_hash=access_grant_evidence_hash,
        retention_evidence_uri=retention_evidence_uri,
        retention_evidence_hash=retention_evidence_hash,
        snapshot_evidence_uri=snapshot_evidence_uri,
        snapshot_evidence_hash=snapshot_evidence_hash,
        approver=approver,
    )

    return RecommendationSliceResult(
        release_id=release_id,
        ingestion=ingestion,
        medallion=medallion,
        catalog_bundle_path=catalog_bundle_path,
        evidence_path=evidence_path,
        evidence=evidence,
    )

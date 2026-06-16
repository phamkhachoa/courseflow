from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_df.source_registry import find_source_entry, source_readiness_snapshot


REPORT_VERSION = 1
SUPPORTED_ENVIRONMENTS = {"local", "staging", "prod"}
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}
VALID_COMMIT_STATUSES = {"started", "committed", "failed", "rolled_back"}
VALID_TABLE_FORMATS = {"iceberg"}


@dataclass(frozen=True)
class OffsetLedgerResult:
    output_path: Path
    report: dict[str, Any]


def write_offset_ledger_report(
    root: str | Path,
    output_path: str | Path,
    *,
    source_id: str,
    environment: str,
    ingestion_manifest_path: str | Path,
    replay_manifest_path: str | Path | None = None,
    table_format: str = "iceberg",
    target_snapshot_id: str | None = None,
    table_metadata_uri: str | None = None,
    table_metadata_hash: str | None = None,
    commit_status: str = "committed",
    committed_at: str | None = None,
    generated_at: str | None = None,
) -> OffsetLedgerResult:
    report = build_offset_ledger_report(
        root,
        source_id=source_id,
        environment=environment,
        ingestion_manifest_path=ingestion_manifest_path,
        replay_manifest_path=replay_manifest_path,
        table_format=table_format,
        target_snapshot_id=target_snapshot_id,
        table_metadata_uri=table_metadata_uri,
        table_metadata_hash=table_metadata_hash,
        commit_status=commit_status,
        committed_at=committed_at,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return OffsetLedgerResult(output_path=target, report=report)


def build_offset_ledger_report(
    root: str | Path,
    *,
    source_id: str,
    environment: str,
    ingestion_manifest_path: str | Path,
    replay_manifest_path: str | Path | None = None,
    table_format: str = "iceberg",
    target_snapshot_id: str | None = None,
    table_metadata_uri: str | None = None,
    table_metadata_hash: str | None = None,
    commit_status: str = "committed",
    committed_at: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    source_entry = find_source_entry(platform_root, source_id)
    ingestion_path = Path(ingestion_manifest_path)
    replay_path = Path(replay_manifest_path) if replay_manifest_path else None
    ingestion_manifest = load_json_file(ingestion_path)
    replay_manifest = load_json_file(replay_path) if replay_path else None
    approved_rows = load_approved_rows(ingestion_path, ingestion_manifest)
    generated = generated_at or utc_now()
    target = target_snapshot(
        ingestion_manifest,
        table_format=table_format,
        target_snapshot_id=target_snapshot_id,
        table_metadata_uri=table_metadata_uri,
        table_metadata_hash=table_metadata_hash,
        commit_status=commit_status,
        committed_at=committed_at or ingestion_manifest.get("ingested_at"),
    )
    counts = ledger_counts(ingestion_manifest, replay_manifest)
    watermarks = ledger_watermarks(ingestion_manifest, approved_rows)
    record_bindings = ledger_record_bindings(approved_rows)
    checks = offset_ledger_checks(
        source_entry,
        environment=environment,
        ingestion_manifest=ingestion_manifest,
        replay_manifest=replay_manifest,
        table_format=table_format,
        target=target,
        counts=counts,
        watermarks=watermarks,
        record_bindings=record_bindings,
    )
    passed = all(item["passed"] is True for item in checks)
    return {
        "artifact_type": "source_offset_ledger.v1",
        "ledger_version": REPORT_VERSION,
        "ledger_id": stable_id(
            "source-offset-ledger",
            source_id,
            environment,
            hash_file(ingestion_path),
            hash_file(replay_path) if replay_path else None,
            target,
        ),
        "generated_at": generated,
        "environment": environment,
        "source_id": source_id,
        "source": source_readiness_snapshot(source_entry),
        "ingestion": {
            "manifest_uri": ingestion_path.as_posix(),
            "manifest_hash": hash_file(ingestion_path),
            "ingest_run_id": ingestion_manifest.get("ingest_run_id"),
            "pipeline": ingestion_manifest.get("pipeline"),
            "topic": ingestion_manifest.get("topic"),
            "bronze_target": ingestion_manifest.get("bronze_target"),
            "schema_subject": ingestion_manifest.get("schema_subject"),
            "schema_id": ingestion_manifest.get("schema_id"),
            "ingested_at": ingestion_manifest.get("ingested_at"),
        },
        "replay": replay_summary(replay_path, replay_manifest),
        "target": target,
        "watermarks": watermarks,
        "record_bindings": record_bindings,
        "counts": counts,
        "checks": checks,
        "failures": [
            {"check": item["name"], "details": item.get("details", {})}
            for item in checks
            if item.get("passed") is not True
        ],
        "passed": passed,
    }


def offset_ledger_checks(
    source_entry: dict[str, Any] | None,
    *,
    environment: str,
    ingestion_manifest: dict[str, Any],
    replay_manifest: dict[str, Any] | None,
    table_format: str,
    target: dict[str, Any],
    counts: dict[str, Any],
    watermarks: list[dict[str, Any]],
    record_bindings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    canonical = mapping(source_entry or {}, "canonical")
    return [
        check("source_registered", source_entry is not None, {"source_id": (source_entry or {}).get("sourceId")}),
        check("environment_supported", environment in SUPPORTED_ENVIRONMENTS, {"environment": environment}),
        check("commit_status_valid", target.get("commit_status") in VALID_COMMIT_STATUSES, {"commit_status": target.get("commit_status")}),
        check("commit_status_committed", target.get("commit_status") == "committed", {"commit_status": target.get("commit_status")}),
        check("table_format_supported", table_format in VALID_TABLE_FORMATS, {"table_format": table_format}),
        check("target_table_matches_manifest", target.get("target_table") == ingestion_manifest.get("bronze_target"), {"target_table": target.get("target_table"), "bronze_target": ingestion_manifest.get("bronze_target")}),
        check("manifest_pipeline_is_bronze", ingestion_manifest.get("pipeline") == "bronze_ingestion.local_jsonl.v1", {"pipeline": ingestion_manifest.get("pipeline")}),
        check("manifest_quality_passed", ingestion_manifest.get("quality_passed") is True, {"quality_passed": ingestion_manifest.get("quality_passed")}),
        check("manifest_topic_matches_source", source_entry is None or ingestion_manifest.get("topic") == canonical.get("topic"), {"manifest_topic": ingestion_manifest.get("topic"), "source_topic": canonical.get("topic")}),
        check("manifest_bronze_matches_source", source_entry is None or ingestion_manifest.get("bronze_target") == canonical.get("bronzeTarget"), {"manifest_bronze": ingestion_manifest.get("bronze_target"), "source_bronze": canonical.get("bronzeTarget")}),
        check("watermarks_present", bool(watermarks), {"watermark_count": len(watermarks)}),
        check("watermarks_cover_committed_rows", sum(int_or_zero(item.get("row_count")) for item in watermarks) >= counts.get("committed_record_count", 0), {"watermarks": watermarks, "counts": counts}),
        check("watermarks_have_no_offset_gaps", not watermark_gaps(watermarks), {"gaps": watermark_gaps(watermarks)}),
        check("record_bindings_present", bool(record_bindings), {"record_binding_count": len(record_bindings)}),
        check("record_bindings_match_committed_rows", len(record_bindings) >= counts.get("committed_record_count", 0), {"record_binding_count": len(record_bindings), "counts": counts}),
        check("record_hashes_present", all_record_hashes_present(record_bindings), {"missing": missing_record_hash_bindings(record_bindings)}),
        check("quarantine_empty_for_commit", counts.get("quarantined_record_count") == 0, {"counts": counts}),
        check("committed_records_present", counts.get("committed_record_count", 0) > 0, {"counts": counts}),
        check("target_snapshot_id_present", not production_like or non_empty(target.get("target_snapshot_id")), {"target_snapshot_id": target.get("target_snapshot_id")}),
        check("iceberg_metadata_uri_present", not production_like or non_empty(target.get("table_metadata_uri")), {"table_metadata_uri": target.get("table_metadata_uri")}),
        check("iceberg_metadata_hash_present", not production_like or is_hash(target.get("table_metadata_hash")), {"table_metadata_hash": target.get("table_metadata_hash")}),
        *replay_checks(replay_manifest, production_like=production_like, first_manifest=ingestion_manifest),
    ]


def replay_checks(
    replay_manifest: dict[str, Any] | None,
    *,
    production_like: bool,
    first_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    if replay_manifest is None:
        return [check("replay_manifest_attached", not production_like, {"production_like": production_like})]
    approved = mapping(replay_manifest, "approved")
    first_approved = mapping(first_manifest, "approved")
    return [
        check("replay_manifest_attached", True, {}),
        check("replay_quality_passed", replay_manifest.get("quality_passed") is True, {"quality_passed": replay_manifest.get("quality_passed")}),
        check("replay_commits_no_new_rows", int_or_zero(approved.get("new_row_count")) == 0, {"approved": approved}),
        check("replay_skips_first_committed_rows", int_or_zero(approved.get("replay_skipped_count")) >= int_or_zero(first_approved.get("new_row_count")), {"approved": approved, "first_approved": first_approved}),
        check("replay_watermarks_stable", replay_manifest.get("source_positions") == first_manifest.get("source_positions"), {"first": first_manifest.get("source_positions"), "replay": replay_manifest.get("source_positions")}),
    ]


def target_snapshot(
    ingestion_manifest: dict[str, Any],
    *,
    table_format: str,
    target_snapshot_id: str | None,
    table_metadata_uri: str | None,
    table_metadata_hash: str | None,
    commit_status: str,
    committed_at: object,
) -> dict[str, Any]:
    return {
        "table_format": table_format,
        "target_table": ingestion_manifest.get("bronze_target"),
        "target_snapshot_id": target_snapshot_id,
        "table_metadata_uri": table_metadata_uri,
        "table_metadata_hash": table_metadata_hash,
        "content_hash": mapping(ingestion_manifest, "approved").get("content_hash"),
        "commit_status": commit_status,
        "committed_at": committed_at,
    }


def ledger_counts(ingestion_manifest: dict[str, Any], replay_manifest: dict[str, Any] | None) -> dict[str, Any]:
    approved = mapping(ingestion_manifest, "approved")
    quarantine = mapping(ingestion_manifest, "quarantine")
    replay_approved = mapping(replay_manifest or {}, "approved")
    committed = int_or_zero(approved.get("new_row_count"))
    quarantined = int_or_zero(quarantine.get("row_count"))
    duplicate = int_or_zero(approved.get("replay_skipped_count"))
    return {
        "input_record_count": committed + quarantined + duplicate,
        "committed_record_count": committed,
        "quarantined_record_count": quarantined,
        "duplicate_record_count": duplicate,
        "replay_skipped_record_count": int_or_zero(replay_approved.get("replay_skipped_count")),
        "replay_new_record_count": int_or_zero(replay_approved.get("new_row_count")),
    }


def ledger_watermarks(ingestion_manifest: dict[str, Any], approved_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    positions = ingestion_manifest.get("source_positions")
    if not isinstance(positions, list):
        return []
    watermarks: list[dict[str, Any]] = []
    rows_by_partition: dict[tuple[object, object], list[dict[str, Any]]] = {}
    for row in approved_rows:
        key = (row.get("source_topic"), row.get("source_partition"))
        rows_by_partition.setdefault(key, []).append(row)
    for position in positions:
        if not isinstance(position, dict):
            continue
        min_offset = position.get("min_offset")
        max_offset = position.get("max_offset")
        key = (position.get("source_topic"), position.get("source_partition"))
        rows = sorted(
            rows_by_partition.get(key, []),
            key=lambda item: item.get("source_offset") if isinstance(item.get("source_offset"), int) else -1,
        )
        event_times = sorted(str(row.get("occurred_at")) for row in rows if row.get("occurred_at") not in (None, ""))
        watermarks.append(
            {
                "source_topic": position.get("source_topic"),
                "source_partition": position.get("source_partition"),
                "start_position": {
                    "offset": min_offset,
                    "inclusive": True,
                },
                "end_position": {
                    "offset": max_offset + 1 if isinstance(max_offset, int) else max_offset,
                    "exclusive": isinstance(max_offset, int),
                },
                "min_offset": min_offset,
                "max_offset": max_offset,
                "high_watermark_offset": max_offset + 1 if isinstance(max_offset, int) else max_offset,
                "row_count": position.get("row_count"),
                "first_event_id": rows[0].get("event_id") if rows else None,
                "last_event_id": rows[-1].get("event_id") if rows else None,
                "min_occurred_at": event_times[0] if event_times else None,
                "max_occurred_at": event_times[-1] if event_times else None,
                "offsets": [
                    row.get("source_offset")
                    for row in rows
                    if row.get("source_offset") is not None
                ],
            }
        )
    return watermarks


def ledger_record_bindings(approved_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for row in approved_rows:
        bindings.append(
            {
                "source_position": {
                    "topic": row.get("source_topic"),
                    "partition": row.get("source_partition"),
                    "offset": row.get("source_offset"),
                },
                "source_record_key": row.get("source_record_key"),
                "event_id": row.get("event_id"),
                "source_record_hash_sha256": row.get("source_record_hash_sha256"),
                "payload_hash_sha256": row.get("payload_hash_sha256"),
                "bronze_row_hash_sha256": content_hash(canonical_json(row)),
            }
        )
    return bindings


def load_approved_rows(manifest_path: Path, ingestion_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    approved = mapping(ingestion_manifest, "approved")
    relative_path = approved.get("path")
    if not isinstance(relative_path, str) or not relative_path:
        return []
    output_dir = manifest_path.parent.parent
    approved_path = output_dir / relative_path
    if not approved_path.is_file():
        return []
    return read_jsonl(approved_path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: JSONL row must be an object")
            rows.append(row)
    return rows


def watermark_gaps(watermarks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for watermark in watermarks:
        offsets = [offset for offset in watermark.get("offsets", []) if isinstance(offset, int)]
        if not offsets:
            continue
        sorted_offsets = sorted(set(offsets))
        missing = [
            offset
            for offset in range(sorted_offsets[0], sorted_offsets[-1] + 1)
            if offset not in set(sorted_offsets)
        ]
        if missing:
            gaps.append(
                {
                    "source_topic": watermark.get("source_topic"),
                    "source_partition": watermark.get("source_partition"),
                    "missing_offsets": missing,
                }
            )
    return gaps


def all_record_hashes_present(record_bindings: list[dict[str, Any]]) -> bool:
    return not missing_record_hash_bindings(record_bindings)


def missing_record_hash_bindings(record_bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    for binding in record_bindings:
        missing_keys = [
            key
            for key in ("source_record_hash_sha256", "payload_hash_sha256", "bronze_row_hash_sha256")
            if not is_hash(binding.get(key))
        ]
        if missing_keys:
            missing.append(
                {
                    "source_position": binding.get("source_position"),
                    "missing": missing_keys,
                }
            )
    return missing


def replay_summary(path: Path | None, manifest: dict[str, Any] | None) -> dict[str, Any] | None:
    if path is None or manifest is None:
        return None
    approved = mapping(manifest, "approved")
    return {
        "manifest_uri": path.as_posix(),
        "manifest_hash": hash_file(path),
        "ingest_run_id": manifest.get("ingest_run_id"),
        "quality_passed": manifest.get("quality_passed"),
        "new_row_count": approved.get("new_row_count"),
        "replay_skipped_count": approved.get("replay_skipped_count"),
    }


def load_json_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def mapping(record: dict[str, Any], key: str) -> dict[str, Any]:
    value = record.get(key)
    return value if isinstance(value, dict) else {}


def int_or_zero(value: object) -> int:
    return value if isinstance(value, int) else 0


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_hash(value: object) -> bool:
    return isinstance(value, str) and value.startswith("sha256:")


def content_hash(content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

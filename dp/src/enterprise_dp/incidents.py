from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.contracts import ValidationResult, load_yaml


REPORT_VERSION = 1
OPEN_STATES = {"OPEN", "ACKNOWLEDGED", "INVESTIGATING", "MITIGATING", "MONITORING"}
CLOSED_STATES = {"RESOLVED", "WAIVED", "DUPLICATE"}
ALLOWED_STATES = OPEN_STATES | CLOSED_STATES
ALLOWED_SEVERITIES = {"P0", "P1", "P2", "P3"}
DEFAULT_SLA_MINUTES = {
    "P0": 240,
    "P1": 1440,
    "P2": 4320,
    "P3": 10080,
}


@dataclass(frozen=True)
class IncidentReportResult:
    output_path: Path
    report: dict[str, Any]


def write_incident_report(
    control_tower_report_path: str | Path,
    output_path: str | Path,
    *,
    incident_registry_path: str | Path | None = None,
    environment: str | None = None,
    generated_at: str | None = None,
) -> IncidentReportResult:
    report = build_incident_report(
        control_tower_report_path,
        incident_registry_path=incident_registry_path,
        environment=environment,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return IncidentReportResult(output_path=target, report=report)


def build_incident_report(
    control_tower_report_path: str | Path,
    *,
    incident_registry_path: str | Path | None = None,
    environment: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    control_path = Path(control_tower_report_path)
    control_tower = load_json(control_path)
    if control_tower.get("artifact_type") != "data_product_control_tower_report.v1":
        raise ValueError(f"{control_path}: expected artifact_type=data_product_control_tower_report.v1")

    generated = generated_at or utc_now()
    registry_path = Path(incident_registry_path) if incident_registry_path else default_incident_registry(control_path)
    registry = load_incident_registry(registry_path)
    existing_by_fingerprint = {
        str(item.get("fingerprint")): item
        for item in registry.get("incidents", [])
        if isinstance(item, dict) and item.get("fingerprint")
    }
    incidents = [
        incident_from_blocker(
            blocker,
            control_tower=control_tower,
            control_tower_path=control_path,
            control_tower_hash=hash_file(control_path),
            existing=existing_by_fingerprint.get(blocker_fingerprint(blocker, control_tower.get("environment"))),
            generated_at=generated,
        )
        for blocker in control_tower.get("blockers", [])
        if isinstance(blocker, dict)
    ]
    incidents.sort(key=incident_sort_key)
    summary = incident_summary(incidents)
    report = {
        "artifact_type": "incident_slo_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id("incident-slo-report", control_path.as_posix(), hash_file(control_path), generated),
        "generated_at": generated,
        "environment": environment or control_tower.get("environment") or "local",
        "inputs": {
            "control_tower_report": {
                "uri": control_path.as_posix(),
                "hash": hash_file(control_path),
                "report_id": control_tower.get("report_id"),
                "readiness_state": control_tower.get("readiness_state"),
                "p0_ready": control_tower.get("p0_ready"),
            },
            "incident_registry": registry_reference(registry_path, registry),
        },
        "passed": summary["open_p0_count"] == 0 and summary["sla_breached_count"] == 0,
        "readiness_state": "operationally_ready" if summary["open_p0_count"] == 0 and summary["sla_breached_count"] == 0 else "incident_action_required",
        "summary": summary,
        "decision_board": decision_board(incidents),
        "incidents": incidents,
    }
    validation = validate_incident_report(report)
    if not validation.ok:
        raise ValueError("; ".join(validation.errors))
    return report


def validate_incident_registry(root: str | Path) -> ValidationResult:
    result = ValidationResult()
    path = Path(root) / "governance" / "incidents.yaml"
    if not path.exists():
        result.warn(path, "incident registry is optional but recommended for production operations")
        return result
    registry = load_yaml(path)
    result.checked_count += 1
    incidents = registry.get("incidents")
    if not isinstance(incidents, list):
        result.error(path, "incidents must be a list")
        return result
    seen_ids: set[str] = set()
    for index, incident in enumerate(incidents):
        if not isinstance(incident, dict):
            result.error(path, f"incidents[{index}] must be an object")
            continue
        incident_id = incident.get("id")
        if not non_empty(incident_id):
            result.error(path, f"incidents[{index}].id is required")
        elif str(incident_id) in seen_ids:
            result.error(path, f"duplicate incident id {incident_id}")
        else:
            seen_ids.add(str(incident_id))
        if not non_empty(incident.get("fingerprint")):
            result.error(path, f"incidents[{index}].fingerprint is required")
        if incident.get("state") not in ALLOWED_STATES:
            result.error(path, f"incidents[{index}].state must be one of {sorted(ALLOWED_STATES)}")
        if incident.get("severity") not in ALLOWED_SEVERITIES:
            result.error(path, f"incidents[{index}].severity must be one of {sorted(ALLOWED_SEVERITIES)}")
        if not non_empty(incident.get("ownerTeam")):
            result.error(path, f"incidents[{index}].ownerTeam is required")
        if not non_empty(incident.get("openedAt")):
            result.error(path, f"incidents[{index}].openedAt is required")
    return result


def validate_incident_report(report: dict[str, Any]) -> ValidationResult:
    result = ValidationResult(checked_count=1)
    if report.get("artifact_type") != "incident_slo_report.v1":
        result.error(Path("incident_report"), "artifact_type must be incident_slo_report.v1")
    if report.get("report_version") != REPORT_VERSION:
        result.error(Path("incident_report"), f"report_version must be {REPORT_VERSION}")
    if not isinstance(report.get("summary"), dict):
        result.error(Path("incident_report"), "summary must be an object")
    if not isinstance(report.get("decision_board"), dict):
        result.error(Path("incident_report"), "decision_board must be an object")
    incidents = report.get("incidents")
    if not isinstance(incidents, list):
        result.error(Path("incident_report"), "incidents must be a list")
        return result
    for index, incident in enumerate(incidents):
        if not isinstance(incident, dict):
            result.error(Path("incident_report"), f"incidents[{index}] must be an object")
            continue
        if incident.get("severity") not in ALLOWED_SEVERITIES:
            result.error(Path("incident_report"), f"incidents[{index}].severity is invalid")
        if incident.get("state") not in ALLOWED_STATES:
            result.error(Path("incident_report"), f"incidents[{index}].state is invalid")
        if incident.get("sla_state") not in {"IN_SLO", "BREACHED", "CLOSED"}:
            result.error(Path("incident_report"), f"incidents[{index}].sla_state is invalid")
    return result


def incident_from_blocker(
    blocker: dict[str, Any],
    *,
    control_tower: dict[str, Any],
    control_tower_path: Path,
    control_tower_hash: str,
    existing: dict[str, Any] | None,
    generated_at: str,
) -> dict[str, Any]:
    severity = normalize_severity(blocker.get("severity"))
    state = str((existing or {}).get("state") or "OPEN")
    if state not in ALLOWED_STATES:
        state = "OPEN"
    opened_at = str((existing or {}).get("openedAt") or generated_at)
    owner_team = str((existing or {}).get("ownerTeam") or blocker.get("owner_team") or "data-platform-team")
    category = incident_category(str(blocker.get("gate") or ""), str(blocker.get("scope") or ""))
    fingerprint = blocker_fingerprint(blocker, control_tower.get("environment"))
    sla_target = int_value((existing or {}).get("slaTargetMinutes"), DEFAULT_SLA_MINUTES[severity])
    age = age_minutes(opened_at, generated_at)
    closed = state in CLOSED_STATES
    sla_state = "CLOSED" if closed else ("BREACHED" if age > sla_target else "IN_SLO")
    data_product = blocker.get("data_product")
    title = incident_title(blocker, category)
    return {
        "incident_id": str((existing or {}).get("id") or stable_id("incident", fingerprint))[:80],
        "fingerprint": fingerprint,
        "title": title,
        "category": category,
        "scope": blocker.get("scope"),
        "severity": severity,
        "state": state,
        "owner_team": owner_team,
        "assignee": (existing or {}).get("assignee") or owner_team,
        "opened_at": opened_at,
        "last_observed_at": generated_at,
        "sla_target_minutes": sla_target,
        "sla_age_minutes": age,
        "sla_state": sla_state,
        "escalation_required": not closed and (severity == "P0" or sla_state == "BREACHED"),
        "data_product": data_product,
        "capability_id": blocker.get("capability_id"),
        "domain": blocker.get("domain"),
        "gate": blocker.get("gate"),
        "message": blocker.get("message"),
        "recommended_action": recommended_action(blocker, category),
        "runbook": "dp/ops-runbooks/data-platform-p0-gates.md",
        "linked_evidence": {
            "control_tower_report_uri": control_tower_path.as_posix(),
            "control_tower_report_hash": control_tower_hash,
            "control_tower_report_id": control_tower.get("report_id"),
            "blocker_details": blocker.get("details", {}),
        },
        "audit": {
            "source": "control_tower_blocker",
            "existing_registry_state": existing_summary(existing),
            "generated_by": "enterprise-dp incident-report",
        },
    }


def incident_summary(incidents: list[dict[str, Any]]) -> dict[str, Any]:
    open_incidents = [incident for incident in incidents if incident.get("state") in OPEN_STATES]
    return {
        "incident_count": len(incidents),
        "open_count": len(open_incidents),
        "open_p0_count": sum(1 for incident in open_incidents if incident.get("severity") == "P0"),
        "sla_breached_count": sum(1 for incident in open_incidents if incident.get("sla_state") == "BREACHED"),
        "escalation_required_count": sum(1 for incident in open_incidents if incident.get("escalation_required") is True),
        "by_severity": count_by(incidents, "severity"),
        "by_category": count_by(incidents, "category"),
        "by_state": count_by(incidents, "state"),
        "by_owner_team": count_by(incidents, "owner_team"),
    }


def decision_board(incidents: list[dict[str, Any]]) -> dict[str, Any]:
    open_incidents = [incident for incident in incidents if incident.get("state") in OPEN_STATES]
    page_now = [
        incident["incident_id"]
        for incident in open_incidents
        if incident.get("severity") == "P0" or incident.get("sla_state") == "BREACHED"
    ]
    owner_queues: dict[str, dict[str, Any]] = {}
    for incident in open_incidents:
        owner = str(incident.get("owner_team") or "unknown")
        item = owner_queues.setdefault(owner, {"owner_team": owner, "open_count": 0, "p0_count": 0, "breached_count": 0, "incident_ids": []})
        item["open_count"] += 1
        if incident.get("severity") == "P0":
            item["p0_count"] += 1
        if incident.get("sla_state") == "BREACHED":
            item["breached_count"] += 1
        item["incident_ids"].append(incident["incident_id"])
    return {
        "page_now": sorted(page_now),
        "owner_queues": sorted(owner_queues.values(), key=lambda item: (-item["p0_count"], -item["breached_count"], item["owner_team"])),
        "recommended_next_actions": recommended_next_actions(open_incidents),
    }


def recommended_next_actions(open_incidents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for incident in open_incidents:
        action = str(incident.get("recommended_action") or "triage_incident")
        item = grouped.setdefault(action, {"action": action, "incident_count": 0, "severity": "P3", "incident_ids": []})
        item["incident_count"] += 1
        item["incident_ids"].append(incident["incident_id"])
        item["severity"] = min_severity(item["severity"], str(incident.get("severity") or "P3"))
    return sorted(grouped.values(), key=lambda item: (severity_rank(item["severity"]), -item["incident_count"], item["action"]))


def load_incident_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"incidents": []}
    registry = load_yaml(path)
    incidents = registry.get("incidents")
    if not isinstance(incidents, list):
        raise ValueError(f"{path}: incidents must be a list")
    return registry


def default_incident_registry(control_tower_path: Path) -> Path:
    current = control_tower_path.resolve()
    for parent in [current.parent, *current.parents]:
        candidate = parent / "governance" / "incidents.yaml"
        if candidate.exists():
            return candidate
    return control_tower_path.parent / "governance" / "incidents.yaml"


def registry_reference(path: Path, registry: dict[str, Any]) -> dict[str, Any]:
    return {
        "uri": path.as_posix() if path.exists() else None,
        "hash": hash_file(path) if path.exists() else None,
        "incident_count": len(registry.get("incidents", [])) if isinstance(registry.get("incidents"), list) else 0,
    }


def blocker_fingerprint(blocker: dict[str, Any], environment: object) -> str:
    return stable_id(
        "control-tower-blocker",
        environment or "local",
        blocker.get("scope"),
        blocker.get("data_product"),
        blocker.get("capability_id"),
        blocker.get("gate"),
        blocker.get("severity"),
    )


def incident_category(gate: str, scope: str) -> str:
    if scope == "platform_capability":
        return "platform_capability"
    if "freshness" in gate or "quality" in gate or "release_evidence" in gate:
        return "quality_slo"
    if "contract" in gate:
        return "contract_compliance"
    if "access" in gate or "consumer" in gate:
        return "access_governance"
    if "lineage" in gate:
        return "lineage"
    if "owner" in gate or "steward" in gate:
        return "ownership"
    return "data_product_readiness"


def incident_title(blocker: dict[str, Any], category: str) -> str:
    target = blocker.get("data_product") or blocker.get("capability_id") or blocker.get("scope") or "data platform"
    return f"{category}: {target} failed {blocker.get('gate')}"


def recommended_action(blocker: dict[str, Any], category: str) -> str:
    gate = str(blocker.get("gate") or "")
    if gate == "gold_release_evidence_passed":
        return "attach_passing_release_evidence_before_gold_exposure"
    if gate == "runtime_lineage_evidence_present":
        return "restore_runtime_lineage_evidence_and_republish_catalog"
    if gate == "catalog_lineage_declared":
        return "register_static_lineage_edges"
    if category == "access_governance":
        return "fix_access_policy_consumer_contract_or_grant_evidence"
    if category == "contract_compliance":
        return "repair_contract_and_rerun_validation"
    if category == "platform_capability":
        return "raise_platform_capability_maturity_to_p0_target"
    if category == "ownership":
        return "assign_owner_and_data_steward"
    if category == "quality_slo":
        return "restore_quality_slo_and_attach_evidence"
    return "triage_data_product_readiness_blocker"


def existing_summary(existing: dict[str, Any] | None) -> dict[str, Any] | None:
    if not existing:
        return None
    return {
        "id": existing.get("id"),
        "state": existing.get("state"),
        "assignee": existing.get("assignee"),
        "openedAt": existing.get("openedAt"),
    }


def incident_sort_key(incident: dict[str, Any]) -> tuple[int, int, str, str]:
    state_rank = 0 if incident.get("state") in OPEN_STATES else 1
    return (
        state_rank,
        severity_rank(str(incident.get("severity"))),
        str(incident.get("owner_team") or ""),
        str(incident.get("incident_id") or ""),
    )


def count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def normalize_severity(value: object) -> str:
    text = str(value or "P1").upper()
    return text if text in ALLOWED_SEVERITIES else "P1"


def min_severity(left: str, right: str) -> str:
    return left if severity_rank(left) <= severity_rank(right) else right


def severity_rank(value: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(value, 9)


def int_value(value: object, default: int) -> int:
    return value if isinstance(value, int) and value > 0 else default


def age_minutes(opened_at: str, observed_at: str) -> int:
    try:
        opened = parse_utc(opened_at)
        observed = parse_utc(observed_at)
    except ValueError:
        return 0
    return max(0, int((observed - opened).total_seconds() // 60))


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

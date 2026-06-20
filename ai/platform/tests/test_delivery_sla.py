from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.delivery_sla import (
    build_delivery_sla_report,
    build_delivery_sla_snapshot,
)
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml


def test_delivery_sla_assigns_owner_aliases_and_due_status() -> None:
    report = build_delivery_sla_report(
        Path(__file__).resolve().parents[2],
        as_of="2026-06-17",
    )
    payload = report.to_dict()

    assert payload["itemCount"] == 23
    assert payload["trackedItemCount"] == 20
    assert payload["monitoringItemCount"] == 3
    assert payload["overdueCount"] == 0
    assert payload["dueSoonCount"] == 13
    assert payload["onTrackCount"] == 7
    assert payload["missingOwnerAliasCount"] == 0
    assert payload["bySlaStatus"] == {
        "due_soon": 13,
        "monitoring": 3,
        "on_track": 7,
    }
    assert payload["byOwnerAlias"]["admin-ops"] == 6
    assert payload["byOwnerAlias"]["sa-ai-engineering"] == 4
    assert payload["byOwnerAlias"]["sa-ai-platform"] == 6
    assert payload["byOwnerAlias"]["sa-ai-platform-governance"] == 3


def test_delivery_sla_items_expose_due_dates_and_monitoring_review_dates() -> None:
    report = build_delivery_sla_report(
        Path(__file__).resolve().parents[2],
        as_of="2026-06-17",
    )
    items = {item.backlog_id: item for item in report.items}

    assert items["AIP-BLG-0001"].owner_alias == "sa-ai-platform"
    assert items["AIP-BLG-0001"].sla_status == "due_soon"
    assert items["AIP-BLG-0001"].due_at == "2026-06-20"
    assert items["AIP-BLG-0005"].sla_status == "due_soon"
    assert items["AIP-BLG-0005"].due_at == "2026-06-20"
    assert items["AIP-BLG-0016"].sla_status == "monitoring"
    assert items["AIP-BLG-0016"].next_review_at == "2026-06-18"
    assert items["AIP-BLG-0017"].next_review_at == "2026-06-24"
    assert items["AIP-BLG-0018"].next_review_at == "2026-06-24"
    assert items["AIP-BLG-0019"].delivery_phase == "serving_access_governance"
    assert items["AIP-BLG-0019"].owner_alias == "admin-ops"
    assert items["AIP-BLG-0019"].status == "in_progress"
    assert items["AIP-BLG-0019"].sla_status == "due_soon"
    assert items["AIP-BLG-0020"].delivery_phase == "runtime_observability"
    assert items["AIP-BLG-0020"].owner_alias == "admin-ops"
    assert items["AIP-BLG-0020"].sla_status == "on_track"
    assert items["AIP-BLG-0021"].delivery_phase == "governance_review"
    assert items["AIP-BLG-0021"].owner_alias == "admin-ops"
    assert items["AIP-BLG-0021"].sla_status == "on_track"
    assert items["AIP-BLG-0022"].delivery_phase == "governance_review"
    assert items["AIP-BLG-0022"].owner_alias == "admin-ops"
    assert items["AIP-BLG-0022"].status == "accepted"
    assert items["AIP-BLG-0022"].sla_status == "on_track"
    assert items["AIP-BLG-0023"].delivery_phase == "governance_review"
    assert items["AIP-BLG-0023"].owner_alias == "admin-ops"
    assert items["AIP-BLG-0023"].status == "accepted"
    assert items["AIP-BLG-0023"].sla_status == "on_track"
    assert items["AIP-BLG-0012"].delivery_phase == "promotion_review"
    assert items["AIP-BLG-0012"].owner_alias == "sa-ai-platform-governance"
    assert items["AIP-BLG-0012"].sla_status == "due_soon"


def test_delivery_sla_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root / "platform" / "delivery" / "reports" / "delivery-sla-v1.yaml"
    )
    generated = build_delivery_sla_snapshot(ai_root, generated_at="2026-06-17")

    assert checked_in["summary"] == generated["summary"]
    assert checked_in["by_owner_alias"] == generated["by_owner_alias"]
    assert checked_in["by_sla_status"] == generated["by_sla_status"]
    assert checked_in["items"] == generated["items"]


def test_delivery_sla_rejects_invalid_generated_date() -> None:
    with pytest.raises(RegistryValidationError, match="invalid delivery SLA date"):
        build_delivery_sla_snapshot(Path(__file__).resolve().parents[2], generated_at="bad-date")

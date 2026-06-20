from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.llm_provider_alerts import (
    build_llm_provider_alert_routing_report,
    build_llm_provider_alert_routing_report_from_policy,
    build_llm_provider_alert_routing_snapshot,
)
from courseflow_ai_platform.llm_provider_runtime_probes import (
    build_llm_provider_runtime_probe_report,
)
from courseflow_ai_platform.registry import load_yaml


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_llm_provider_alert_routing_reports_configured_contract_stub_routes() -> None:
    report = build_llm_provider_alert_routing_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    payload = report.to_dict()

    assert payload["alertRoutingStatus"] == "contract_stub_alerts_configured"
    assert payload["providerCount"] == 2
    assert payload["routedProviderCount"] == 2
    assert payload["sinkCount"] == 1
    assert payload["tenantSafe"] is True
    assert payload["rawIdentifierCount"] == 0
    assert payload["rotationAutomationProviderCount"] == 0
    assert all(
        item["alertRouteStatus"] == "contract_stub_alert_configured"
        for item in payload["items"]
    )


def test_llm_provider_alert_routing_blocks_missing_provider_route() -> None:
    root = ai_root()
    runtime_report = build_llm_provider_runtime_probe_report(
        root,
        generated_at="2026-06-17",
    )
    policy = load_yaml(
        root
        / "platform"
        / "governance"
        / "policies"
        / "llm-provider-alert-routing-policy.yaml"
    )
    policy["routes"] = [
        route
        for route in policy["routes"]
        if route["provider_id"] != "contract-stub-llm-failover-v1"
    ]

    report = build_llm_provider_alert_routing_report_from_policy(
        policy,
        runtime_report,
        generated_at="2026-06-17",
    )

    assert report.alert_routing_status == "blocked"
    blocked_route = next(
        route
        for route in report.routes
        if route.provider_id == "contract-stub-llm-failover-v1"
    )
    assert blocked_route.alert_route_status == "blocked"
    assert blocked_route.validation_errors == ("missing alert route policy entry",)


def test_llm_provider_alert_routing_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    generated = build_llm_provider_alert_routing_snapshot(
        root,
        generated_at="2026-06-17",
    )
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / "llm-provider-alert-routing-v1.yaml"
    )

    assert generated == checked_in

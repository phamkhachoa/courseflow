from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_retrieval_service.cli import main
from courseflow_retrieval_service.service import (
    RETRIEVAL_SERVICE_ID,
    RetrievalService,
    RetrievalServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def support_search_body() -> dict[str, object]:
    return {
        "collectionId": "support_knowledge_articles",
        "tenantId": "tenant-a",
        "query": "MFA timeout admin login",
        "mode": "hybrid",
        "topK": 3,
    }


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (ai_root() / "services" / "retrieval-service" / "service.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy = load_yaml(
        ai_root() / "platform" / "governance" / "policies" / "retrieval-access-policy.yaml"
    )
    scopes = set(policy["scope_aliases"].values())

    assert manifest["serviceId"] == RETRIEVAL_SERVICE_ID
    assert service_yaml["service_id"] == RETRIEVAL_SERVICE_ID
    assert len(manifest["routes"]) == 4
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {route["scope"] for route in manifest["routes"]} == scopes


def test_service_searches_support_collection_and_tracks_metrics() -> None:
    service = RetrievalService(RetrievalServiceConfig.from_paths(ai_root=ai_root()))

    response = service.handle_request(
        "POST",
        "/v1/retrieval/search",
        support_search_body(),
        principal_id="service:support-platform-retrieval",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/retrieval/metrics",
        principal_id="service:ai-platform-retrieval-ops",
    )

    assert response.status_code == 200
    assert response.body["resultCount"] >= 1
    assert response.body["results"][0]["chunkId"] == "support-access-mfa-timeout"
    assert metrics.body["metrics"]["searchCount"] == 1
    assert metrics.body["metrics"]["byCollection"] == {"support_knowledge_articles": 1}


def test_service_preserves_tenant_isolation_for_lms_collection() -> None:
    service = RetrievalService(RetrievalServiceConfig.from_paths(ai_root=ai_root()))

    response = service.handle_request(
        "POST",
        "/v1/retrieval/search",
        {
            "collectionId": "course_content_chunks",
            "tenantId": "tenant-a",
            "query": "Tenant B private SQL joins",
            "mode": "hybrid",
            "topK": 5,
        },
        principal_id="service:lms-courseflow-retrieval",
    )
    chunk_ids = {row["chunkId"] for row in response.body["results"]}

    assert response.status_code == 200
    assert "course-tenant-b-private-sql" not in chunk_ids
    assert all(row["tenantId"] == "tenant-a" for row in response.body["results"])


def test_service_rejects_unapproved_collection_and_missing_auth() -> None:
    service = RetrievalService(RetrievalServiceConfig.from_paths(ai_root=ai_root()))

    missing_auth = service.handle_request("GET", "/v1/retrieval/collections")
    denied = service.handle_request(
        "POST",
        "/v1/retrieval/search",
        {
            **support_search_body(),
            "collectionId": "course_content_chunks",
        },
        principal_id="service:support-platform-retrieval",
    )

    assert missing_auth.status_code == 401
    assert missing_auth.body["errorCode"] == "auth_required"
    assert denied.status_code == 400
    assert denied.body["errorCode"] == "bad_request"
    assert "collection is not granted" in denied.body["errorMessage"]


def test_cli_health_uses_registered_ops_principal(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-retrieval",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-retrieval-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["serviceStatus"] == "healthy"
    assert payload["body"]["collectionCount"] == 2


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-retrieval", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == RETRIEVAL_SERVICE_ID
    assert len(payload["routes"]) == 4

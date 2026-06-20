from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.registry import load_yaml
from courseflow_ai_platform.runtime_roadmap import (
    build_runtime_roadmap_report,
    build_runtime_roadmap_snapshot,
)


def test_runtime_roadmap_prioritizes_modules_without_runtime_artifacts() -> None:
    report = build_runtime_roadmap_report(Path(__file__).resolve().parents[2])
    payload = report.to_dict()

    assert payload["moduleCount"] == 14
    assert payload["runtimeReadyCount"] == 14
    assert payload["runtimeGapCount"] == 0
    assert payload["serviceIntegratedCount"] == 14
    assert payload["productionReadyCount"] == 0
    assert payload["registryOnlyCount"] == 0
    assert payload["runtimeLibraryCount"] == 0
    assert payload["p1Count"] == 0
    assert payload["p2Count"] == 0
    assert payload["firstRuntimeCandidateIds"] == []


def test_runtime_roadmap_exposes_next_actions_by_runtime_status() -> None:
    report = build_runtime_roadmap_report(Path(__file__).resolve().parents[2])
    items = {item.module_id: item for item in report.items}

    assert "deep-learning-sequence-models" not in items
    assert "anomaly-fraud-risk" not in items
    assert "forecasting-planning" not in items
    assert "computer-vision-document-ai" not in items
    assert "speech-audio-ai" not in items
    assert "rl-bandit-decisioning" not in items
    assert "causal-experimentation" not in items
    assert "graph-knowledge-intelligence" not in items
    assert "nlp-transformers" not in items
    assert "rag-retrieval-vector" not in items
    assert "governance-safety-evaluation" not in items
    assert items == {}


def test_runtime_roadmap_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root / "platform" / "coverage" / "reports" / "runtime-roadmap-v1.yaml"
    )
    generated = build_runtime_roadmap_snapshot(ai_root, generated_at="2026-06-17")

    assert checked_in["summary"] == generated["summary"]
    assert checked_in["by_priority"] == generated["by_priority"]
    assert checked_in["by_runtime_status"] == generated["by_runtime_status"]
    assert checked_in["items"] == generated["items"]

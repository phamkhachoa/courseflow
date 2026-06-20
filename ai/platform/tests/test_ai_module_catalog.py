from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.ai_module_catalog import (
    build_ai_module_catalog_report,
    build_ai_module_catalog_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def test_ai_module_catalog_answers_full_model_spectrum_coverage() -> None:
    report = build_ai_module_catalog_report(Path(__file__).resolve().parents[2])
    payload = report.to_dict()

    assert payload["moduleCount"] == 14
    assert payload["requiredSpectrumCount"] == 8
    assert payload["requiredSpectrumCoveredCount"] == 8
    assert payload["extendedModuleCount"] == 6
    assert payload["lmsModuleCount"] == 14
    assert payload["enterpriseModuleCount"] == 14
    assert payload["platformReadinessStatus"] == "runtime_ready"
    assert payload["firstRuntimeCandidateIds"] == []
    assert payload["coveredRequiredSpectrumAreas"] == [
        "classical_ml",
        "deep_learning",
        "nlp_transformers",
        "genai_llm",
        "rag",
        "computer_vision",
        "speech",
        "reinforcement_learning",
    ]


def test_ai_module_catalog_exposes_readiness_and_next_actions() -> None:
    report = build_ai_module_catalog_report(Path(__file__).resolve().parents[2])
    items = {item.module_id: item for item in report.items}

    assert items["classical-ml-baselines"].readiness_level == "service_integrated"
    assert items["genai-llm"].readiness_level == "service_integrated"
    assert items["nlp-transformers"].readiness_level == "service_integrated"
    assert items["nlp-transformers"].next_action == ""
    assert items["rag-retrieval-vector"].readiness_level == "service_integrated"
    assert items["rag-retrieval-vector"].next_action == ""
    assert items["deep-learning-sequence-models"].readiness_level == "service_integrated"
    assert items["deep-learning-sequence-models"].next_action == ""
    assert items["anomaly-fraud-risk"].readiness_level == "service_integrated"
    assert items["anomaly-fraud-risk"].next_action == ""
    assert items["forecasting-planning"].readiness_level == "service_integrated"
    assert items["forecasting-planning"].next_action == ""
    assert items["computer-vision-document-ai"].readiness_level == "service_integrated"
    assert items["speech-audio-ai"].readiness_level == "service_integrated"
    assert items["speech-audio-ai"].next_action == ""
    assert items["rl-bandit-decisioning"].readiness_level == "service_integrated"
    assert items["rl-bandit-decisioning"].next_action == ""
    assert items["causal-experimentation"].readiness_level == "service_integrated"
    assert items["causal-experimentation"].next_action == ""
    assert items["graph-knowledge-intelligence"].readiness_level == "service_integrated"
    assert items["graph-knowledge-intelligence"].next_action == ""
    assert items["governance-safety-evaluation"].readiness_level == "service_integrated"
    assert items["governance-safety-evaluation"].next_action == ""


def test_ai_module_catalog_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root / "platform" / "coverage" / "reports" / "ai-module-catalog-v1.yaml"
    )
    generated = build_ai_module_catalog_snapshot(ai_root, generated_at="2026-06-17")

    assert checked_in["summary"] == generated["summary"]
    assert checked_in["by_runtime_status"] == generated["by_runtime_status"]
    assert checked_in["by_coverage_status"] == generated["by_coverage_status"]
    assert checked_in["items"] == generated["items"]

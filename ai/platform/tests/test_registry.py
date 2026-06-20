from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.registry import load_yaml, validate_registries


def test_ai_platform_registries_validate() -> None:
    report = validate_registries(Path(__file__).resolve().parents[2])

    assert report.product_count >= 6
    assert report.use_case_count >= 12
    assert report.non_lms_use_case_count >= 5
    assert report.capability_count >= 9
    assert report.model_family_count >= 25
    assert report.model_family_alias_count >= 2
    assert report.artifact_count >= 10


def test_model_family_registry_covers_enterprise_ai_spectrum() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    registry = load_yaml(ai_root / "model-families" / "registry.yaml")
    family_ids = {row["id"] for row in registry["families"]}

    required = {
        "classical_ml",
        "deep_learning",
        "sequence_deep_learning",
        "transformer",
        "nlp",
        "embeddings",
        "vector_search",
        "rag",
        "llm",
        "genai",
        "computer_vision",
        "speech",
        "multimodal",
        "reinforcement_learning",
        "contextual_bandit",
        "optimization",
        "anomaly_detection",
        "graph_ml",
        "knowledge_graph",
        "time_series_forecasting",
        "causal_inference",
        "simulation",
    }
    assert required <= family_ids

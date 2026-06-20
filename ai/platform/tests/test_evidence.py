from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.evidence import validate_model_evidence


def test_model_evidence_validates() -> None:
    report = validate_model_evidence(Path(__file__).resolve().parents[2])

    assert report.manifest_count >= 4
    assert report.hash_verified_count == report.manifest_count
    assert report.non_lms_manifest_count >= 2
    assert report.vector_index_manifest_count >= 2
    assert report.promotion_count >= 4
    assert report.non_lms_promotion_count >= 2

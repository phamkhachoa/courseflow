from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.media_privacy_review import (
    build_media_privacy_review_report,
    build_media_privacy_review_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def test_media_privacy_review_tracks_raw_media_controls() -> None:
    report = build_media_privacy_review_report(
        Path(__file__).resolve().parents[2],
        generated_at="2026-06-17",
    )
    payload = report.to_dict()

    assert payload["reviewStatus"] == "approved"
    assert payload["reviewCount"] == 3
    assert payload["approvedCount"] == 3
    assert payload["readyForApprovalCount"] == 0
    assert payload["waitingForControlsCount"] == 0
    assert payload["blockedCount"] == 0
    assert payload["rawMediaRequestCount"] == 2
    assert payload["transcriptOnlyApprovedCount"] == 1
    assert payload["controlGapCount"] == 0
    assert payload["actionQueue"]["approved"] == [
        "support-speech-transcript-baseline-review",
        "finance-document-raw-ocr-review",
        "speech-audio-raw-asr-diarization-review",
    ]
    assert payload["actionQueue"]["waitingForControls"] == []


def test_media_privacy_review_exposes_missing_controls_by_request() -> None:
    report = build_media_privacy_review_report(
        Path(__file__).resolve().parents[2],
        generated_at="2026-06-17",
    )
    items = {item.review_id: item for item in report.items}

    finance_doc = items["finance-document-raw-ocr-review"]
    assert finance_doc.review_status == "approved"
    assert finance_doc.raw_media_requested is True
    assert finance_doc.missing_controls == ()
    assert "raw_media_storage_boundary" in finance_doc.satisfied_controls

    speech = items["speech-audio-raw-asr-diarization-review"]
    assert speech.review_status == "approved"
    assert speech.missing_controls == ()
    assert "speaker_role_minimization" in speech.satisfied_controls


def test_media_privacy_review_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root / "platform" / "governance" / "reports" / "media-privacy-review-v1.yaml"
    )
    generated = build_media_privacy_review_snapshot(ai_root, generated_at="2026-06-17")

    assert checked_in["summary"] == generated["summary"]
    assert checked_in["action_queue"] == generated["action_queue"]
    assert checked_in["items"] == generated["items"]

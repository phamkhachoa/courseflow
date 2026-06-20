from __future__ import annotations

import pytest

from ai.models.multimodal.document_intelligence_baseline.document_intelligence_baseline import (
    DocumentIntelligenceBaseline,
)


def test_document_intelligence_baseline_extracts_invoice_fields() -> None:
    model = DocumentIntelligenceBaseline()

    prediction = model.predict(
        {
            "tenant_id": "tenant-finance",
            "document_id": "invoice-1042",
            "document_checksum": "sha256-invoice-1042",
            "mime_type": "application/pdf",
            "document_language": "en",
            "vendor_name_hint": "Acme Supply",
            "tokens": [
                {"text": "Invoice INV-1042", "page": 1},
                {"text": "Vendor Acme Supply", "page": 1},
                {"text": "Total USD 1280.50", "page": 1},
                {"text": "Due 2026-07-01", "page": 1},
            ],
        }
    )

    assert prediction.model_id == "finance-document-intelligence-baseline-v1"
    assert prediction.document_type == "invoice"
    assert prediction.extracted_fields["document_number"] == "1042"
    assert prediction.extracted_fields["currency"] == "USD"
    assert prediction.extracted_fields["total_amount"] == "1280.50"
    assert prediction.requires_human_review is False
    assert {"INVOICE_DETECTED", "TOTAL_EXTRACTED"} <= set(prediction.reason_codes)


def test_document_intelligence_baseline_detects_receipts() -> None:
    model = DocumentIntelligenceBaseline()

    prediction = model.predict(
        {
            "tenant_id": "tenant-finance",
            "document_id": "receipt-77",
            "document_checksum": "sha256-receipt-77",
            "mime_type": "image/png",
            "document_language": "en",
            "vendor_name_hint": "Metro Travel",
            "tokens": [
                {"text": "Receipt RCPT-77", "page": 1},
                {"text": "Merchant Metro Travel", "page": 1},
                {"text": "Paid USD 42.10", "page": 1},
            ],
        }
    )

    assert prediction.document_type == "receipt"
    assert prediction.extracted_fields["document_number"] == "77"
    assert prediction.extracted_fields["total_amount"] == "42.10"
    assert prediction.requires_human_review is False
    assert "RECEIPT_DETECTED" in prediction.reason_codes


def test_document_intelligence_baseline_requires_review_for_raw_pii() -> None:
    model = DocumentIntelligenceBaseline()

    prediction = model.predict(
        {
            "tenant_id": "tenant-finance",
            "document_id": "invoice-tax-id",
            "document_checksum": "sha256-invoice-tax",
            "mime_type": "application/pdf",
            "document_language": "en",
            "vendor_name_hint": "Northwind",
            "tokens": [
                {"text": "Invoice INV-777", "page": 1},
                {"text": "Total USD 900.00", "page": 1},
                {"text": "Tax ID 12-3456789", "page": 1},
            ],
        }
    )

    assert prediction.requires_human_review is True
    assert "RAW_FINANCIAL_PII_DETECTED" in prediction.reason_codes
    assert "HUMAN_REVIEW_REQUIRED" in prediction.reason_codes


def test_document_intelligence_baseline_requires_tenant_boundary() -> None:
    model = DocumentIntelligenceBaseline()

    with pytest.raises(ValueError, match="tenant_id"):
        model.predict(
            {
                "tenant_id": "public",
                "document_id": "invoice-1",
                "document_checksum": "sha256-invoice-1",
                "mime_type": "application/pdf",
                "document_language": "en",
                "tokens": [{"text": "Invoice INV-1 Total USD 12.00"}],
            }
        )

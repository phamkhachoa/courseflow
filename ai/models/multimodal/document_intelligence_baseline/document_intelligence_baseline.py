from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

MODEL_ID = "finance-document-intelligence-baseline-v1"
TOKEN_TEXT_MAX_CHARS = 80
RAW_PII_PATTERNS = (
    re.compile(r"\b\d{2}-\d{7}\b"),
    re.compile(r"\b\d{9,12}\b"),
    re.compile(r"\b(?:iban|swift|account|tax\s*id)\b", re.IGNORECASE),
)
INVOICE_NUMBER_PATTERN = re.compile(
    r"\b(?:invoice|inv)[-\s#:]*(?:no\.?\s*)?([a-z0-9-]{2,})\b",
    re.IGNORECASE,
)
RECEIPT_NUMBER_PATTERN = re.compile(
    r"\b(?:receipt|rcpt)[-\s#:]*(?:no\.?\s*)?([a-z0-9-]{2,})\b",
    re.IGNORECASE,
)
AMOUNT_PATTERN = re.compile(r"\b(?:usd|vnd|eur|total|amount|paid)[:\s$]*([0-9][0-9,.]*)\b", re.IGNORECASE)
DATE_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


@dataclass(frozen=True, slots=True)
class DocumentToken:
    text: str
    page: int = 1
    bbox: tuple[float, float, float, float] | None = None

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> DocumentToken:
        text = str(row.get("text", "")).strip()
        page = int(row.get("page", 1))
        bbox_row = row.get("bbox")
        bbox = None
        if bbox_row is not None:
            if not isinstance(bbox_row, list | tuple) or len(bbox_row) != 4:
                raise ValueError("bbox must contain four coordinates")
            bbox = tuple(float(value) for value in bbox_row)
        return cls(text=text, page=page, bbox=bbox)


@dataclass(frozen=True, slots=True)
class DocumentIntelligenceInput:
    tenant_id: str
    document_id: str
    document_checksum: str
    mime_type: str
    document_language: str
    tokens: tuple[DocumentToken, ...]
    vendor_name_hint: str = ""

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> DocumentIntelligenceInput:
        tokens = row.get("tokens")
        if not isinstance(tokens, list):
            raise ValueError("tokens must be a list")
        return cls(
            tenant_id=str(row.get("tenant_id", "")).strip(),
            document_id=str(row.get("document_id", "")).strip(),
            document_checksum=str(row.get("document_checksum", "")).strip(),
            mime_type=str(row.get("mime_type", "")).strip(),
            document_language=str(row.get("document_language", "")).strip() or "en",
            vendor_name_hint=str(row.get("vendor_name_hint", "")).strip(),
            tokens=tuple(DocumentToken.from_dict(token) for token in tokens),
        )


@dataclass(frozen=True, slots=True)
class DocumentIntelligencePrediction:
    model_id: str
    document_type: str
    extracted_fields: dict[str, str]
    confidence: float
    reason_codes: tuple[str, ...]
    evidence_terms: tuple[str, ...]
    requires_human_review: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": self.confidence,
            "document_type": self.document_type,
            "evidence_terms": list(self.evidence_terms),
            "extracted_fields": dict(self.extracted_fields),
            "model_id": self.model_id,
            "reason_codes": list(self.reason_codes),
            "requires_human_review": self.requires_human_review,
        }


class DocumentIntelligenceBaseline:
    def predict(
        self,
        payload: DocumentIntelligenceInput | dict[str, Any],
    ) -> DocumentIntelligencePrediction:
        request = (
            payload
            if isinstance(payload, DocumentIntelligenceInput)
            else DocumentIntelligenceInput.from_dict(payload)
        )
        validate_request(request)
        text = normalize_text(" ".join(token.text for token in request.tokens))
        token_texts = tuple(normalize_text(token.text) for token in request.tokens)

        document_type = classify_document_type(text)
        extracted_fields = extract_fields(text, request.vendor_name_hint)
        reason_codes = set(reason_codes_for_document(document_type, text, extracted_fields))

        if has_raw_pii(text):
            reason_codes.add("RAW_FINANCIAL_PII_DETECTED")
        if missing_required_fields(document_type, extracted_fields):
            reason_codes.add("FIELD_EXTRACTION_INCOMPLETE")

        evidence_terms = collect_evidence_terms(token_texts, extracted_fields, document_type)
        confidence = score_confidence(document_type, extracted_fields, reason_codes)
        requires_human_review = (
            "RAW_FINANCIAL_PII_DETECTED" in reason_codes
            or "FIELD_EXTRACTION_INCOMPLETE" in reason_codes
            or confidence < 0.75
        )
        if requires_human_review:
            reason_codes.add("HUMAN_REVIEW_REQUIRED")

        return DocumentIntelligencePrediction(
            model_id=MODEL_ID,
            document_type=document_type,
            extracted_fields=extracted_fields,
            confidence=round(confidence, 6),
            reason_codes=tuple(sorted(reason_codes)),
            evidence_terms=evidence_terms,
            requires_human_review=requires_human_review,
        )


def validate_request(request: DocumentIntelligenceInput) -> None:
    if not request.tenant_id.startswith("tenant-"):
        raise ValueError("tenant_id must be a bounded tenant identifier")
    if not request.document_id:
        raise ValueError("document_id is required")
    if len(request.document_checksum) < 12:
        raise ValueError("document_checksum is required")
    if request.mime_type not in {"application/pdf", "image/png", "image/jpeg"}:
        raise ValueError("mime_type must be application/pdf, image/png or image/jpeg")
    if not request.tokens:
        raise ValueError("tokens are required")
    for token in request.tokens:
        if not token.text:
            raise ValueError("token text is required")
        if len(token.text) > TOKEN_TEXT_MAX_CHARS:
            raise ValueError("token text must be bounded")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def classify_document_type(text: str) -> str:
    lowered = text.lower()
    invoice_score = sum(
        1 for term in ("invoice", "due", "net", "bill to", "vendor") if term in lowered
    )
    receipt_score = sum(
        1 for term in ("receipt", "paid", "merchant", "cashier", "terminal") if term in lowered
    )
    if INVOICE_NUMBER_PATTERN.search(text) and "total" in lowered:
        return "invoice"
    if RECEIPT_NUMBER_PATTERN.search(text) and ("paid" in lowered or "total" in lowered):
        return "receipt"
    if invoice_score >= 2 and invoice_score >= receipt_score:
        return "invoice"
    if receipt_score >= 2:
        return "receipt"
    return "unknown"


def extract_fields(text: str, vendor_name_hint: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    if vendor_name_hint:
        fields["vendor_name"] = vendor_name_hint
    invoice_number = INVOICE_NUMBER_PATTERN.search(text)
    if invoice_number:
        fields["document_number"] = clean_document_number(invoice_number.group(1))
    receipt_number = RECEIPT_NUMBER_PATTERN.search(text)
    if receipt_number:
        fields["document_number"] = clean_document_number(receipt_number.group(1))
    amount = AMOUNT_PATTERN.search(text)
    if amount:
        fields["total_amount"] = amount.group(1).replace(",", "")
    currency = detect_currency(text)
    if currency:
        fields["currency"] = currency
    date_match = DATE_PATTERN.search(text)
    if date_match:
        fields["document_date"] = date_match.group(1)
    return fields


def detect_currency(text: str) -> str:
    lowered = text.lower()
    for currency in ("USD", "VND", "EUR"):
        if currency.lower() in lowered:
            return currency
    if "$" in text:
        return "USD"
    return ""


def clean_document_number(value: str) -> str:
    normalized = value.upper().strip()
    normalized = re.sub(r"^(?:INV|INVOICE|RCPT|RECEIPT)[-\s#:]*", "", normalized)
    return normalized


def has_raw_pii(text: str) -> bool:
    return any(pattern.search(text) for pattern in RAW_PII_PATTERNS)


def missing_required_fields(document_type: str, fields: dict[str, str]) -> bool:
    if document_type == "invoice":
        return not {"document_number", "total_amount", "currency"} <= set(fields)
    if document_type == "receipt":
        return not {"total_amount", "currency"} <= set(fields)
    return True


def reason_codes_for_document(
    document_type: str,
    text: str,
    fields: dict[str, str],
) -> set[str]:
    reasons: set[str] = set()
    if document_type == "invoice":
        reasons.add("INVOICE_DETECTED")
    elif document_type == "receipt":
        reasons.add("RECEIPT_DETECTED")
    else:
        reasons.add("DOCUMENT_TYPE_UNKNOWN")
    if "total_amount" in fields:
        reasons.add("TOTAL_EXTRACTED")
    if "document_number" in fields:
        reasons.add("DOCUMENT_NUMBER_EXTRACTED")
    if "due" in text.lower():
        reasons.add("PAYMENT_DUE_SIGNAL")
    return reasons


def collect_evidence_terms(
    token_texts: tuple[str, ...],
    fields: dict[str, str],
    document_type: str,
) -> tuple[str, ...]:
    terms: list[str] = []
    field_values = {value.lower() for value in fields.values()}
    for token_text in token_texts:
        lowered = token_text.lower()
        if (
            document_type in lowered
            or lowered in field_values
            or any(value in lowered for value in field_values)
            or lowered in {"total", "amount", "paid", "due", "receipt", "invoice"}
        ):
            terms.append(token_text)
    return tuple(dict.fromkeys(terms))


def score_confidence(
    document_type: str,
    fields: dict[str, str],
    reason_codes: set[str],
) -> float:
    if document_type == "unknown":
        base = 0.35
    else:
        base = 0.55
    base += min(0.35, len(fields) * 0.08)
    if "FIELD_EXTRACTION_INCOMPLETE" in reason_codes:
        base -= 0.18
    if "RAW_FINANCIAL_PII_DETECTED" in reason_codes:
        base -= 0.08
    return max(0.05, min(0.98, base))

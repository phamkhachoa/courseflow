from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.registry import (
    RegistryValidationError,
    load_yaml,
    require_str,
)

MEDIA_DOCUMENT_ANALYZE_SCOPE = "internal:ai-platform:media-intelligence:document:analyze"
MEDIA_SPEECH_ASSESS_SCOPE = "internal:ai-platform:media-intelligence:speech:assess"
MEDIA_OPS_SCOPE = "internal:ai-platform:media-intelligence:ops"
MEDIA_INTELLIGENCE_ROUTE_SCOPES = {
    ("POST", "/v1/media-intelligence/document:analyze"): MEDIA_DOCUMENT_ANALYZE_SCOPE,
    ("POST", "/v1/media-intelligence/speech:assess"): MEDIA_SPEECH_ASSESS_SCOPE,
    ("GET", "/v1/media-intelligence/health"): MEDIA_OPS_SCOPE,
    ("GET", "/v1/media-intelligence/metrics"): MEDIA_OPS_SCOPE,
}
DOCUMENT_MODEL_RELATIVE_PATH = (
    "models/multimodal/document_intelligence_baseline/document_intelligence_baseline.py"
)
SPEECH_MODEL_RELATIVE_PATH = "models/speech/audio_quality_baseline/audio_quality_baseline.py"
RAW_DOCUMENT_URI_KEYS = (
    "raw_document_uri",
    "rawDocumentUri",
    "document_uri",
    "documentUri",
    "image_uri",
    "imageUri",
    "raw_image_uri",
    "rawImageUri",
)
RAW_AUDIO_URI_KEYS = ("raw_audio_uri", "rawAudioUri", "audio_uri", "audioUri")


class MediaIntelligenceServiceError(ValueError):
    """Raised when media intelligence service input or policy is invalid."""


class MediaPrivacyControlError(MediaIntelligenceServiceError):
    """Raised when a request violates raw-media privacy controls."""


@dataclass(frozen=True, slots=True)
class MediaIntelligencePrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    use_case_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> MediaIntelligencePrincipal:
        return cls(
            principal_id=required_non_empty_str(row, "principal_id", "principalId"),
            scopes=normalize_string_tuple(row.get("scopes", row.get("scope"))),
            tenant_ids=normalize_string_tuple(row.get("tenant_ids", row.get("tenantIds"))),
            product_ids=normalize_string_tuple(row.get("product_ids", row.get("productIds"))),
            use_case_ids=normalize_string_tuple(
                row.get("use_case_ids", row.get("useCaseIds"))
            ),
        )


@dataclass(frozen=True, slots=True)
class MediaIntelligencePrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    use_case_ids: tuple[str, ...]

    def resolve(self, requested_scopes: object | None = None) -> MediaIntelligencePrincipal:
        scopes = (
            self.scopes
            if requested_scopes is None
            else normalize_string_tuple(requested_scopes)
        )
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise MediaIntelligenceServiceError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return MediaIntelligencePrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            product_ids=self.product_ids,
            use_case_ids=self.use_case_ids,
        )


@dataclass(frozen=True, slots=True)
class MediaIntelligenceAccessPolicy:
    policy_id: str
    principals: Mapping[str, MediaIntelligencePrincipalGrant]
    wildcard_scopes_allowed: bool = False
    tenant_isolation_required: bool = True
    raw_uri_submission_allowed: bool = False

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> MediaIntelligencePrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise MediaIntelligenceServiceError(
                f"media intelligence principal is not registered: {principal_id}"
            )
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class MediaPrivacyControlState:
    review_status: str
    approved_count: int
    control_gap_count: int
    report_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "approvedCount": self.approved_count,
            "controlGapCount": self.control_gap_count,
            "reportPath": self.report_path,
            "reviewStatus": self.review_status,
        }


@dataclass(frozen=True, slots=True)
class DocumentAnalyzeRequest:
    tenant_id: str
    product: str
    use_case_id: str
    document_id: str
    document_checksum: str
    mime_type: str
    document_language: str
    tokens: tuple[Mapping[str, Any], ...]
    vendor_name_hint: str = ""

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> DocumentAnalyzeRequest:
        reject_raw_media_uri(row, RAW_DOCUMENT_URI_KEYS, "document analyze request")
        tokens = required_mapping_sequence_any(
            row,
            "tokens",
            "tokens",
            "document analyze request",
        )
        return cls(
            tenant_id=required_non_empty_str(row, "tenant_id", "tenantId"),
            product=required_non_empty_str(row, "product", "product"),
            use_case_id=required_non_empty_str(row, "use_case_id", "useCaseId"),
            document_id=required_non_empty_str(row, "document_id", "documentId"),
            document_checksum=required_non_empty_str(
                row,
                "document_checksum",
                "documentChecksum",
            ),
            mime_type=required_non_empty_str(row, "mime_type", "mimeType"),
            document_language=optional_string_any(
                row,
                "document_language",
                "documentLanguage",
                "en",
            ),
            tokens=tokens,
            vendor_name_hint=optional_string_any(
                row,
                "vendor_name_hint",
                "vendorNameHint",
                "",
            ),
        )

    def to_model_payload(self) -> dict[str, Any]:
        return {
            "document_checksum": self.document_checksum,
            "document_id": self.document_id,
            "document_language": self.document_language,
            "mime_type": self.mime_type,
            "tenant_id": self.tenant_id,
            "tokens": [dict(token) for token in self.tokens],
            "vendor_name_hint": self.vendor_name_hint,
        }


@dataclass(frozen=True, slots=True)
class SpeechAssessRequest:
    tenant_id: str
    product: str
    use_case_id: str
    audio_id: str
    audio_checksum: str
    transcript_language: str
    duration_seconds: int
    consent_captured: bool
    segments: tuple[Mapping[str, Any], ...]
    product_hint: str = ""

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> SpeechAssessRequest:
        reject_raw_media_uri(row, RAW_AUDIO_URI_KEYS, "speech assess request")
        segments = required_mapping_sequence_any(
            row,
            "segments",
            "segments",
            "speech assess request",
        )
        return cls(
            tenant_id=required_non_empty_str(row, "tenant_id", "tenantId"),
            product=required_non_empty_str(row, "product", "product"),
            use_case_id=required_non_empty_str(row, "use_case_id", "useCaseId"),
            audio_id=required_non_empty_str(row, "audio_id", "audioId"),
            audio_checksum=required_non_empty_str(row, "audio_checksum", "audioChecksum"),
            transcript_language=optional_string_any(
                row,
                "transcript_language",
                "transcriptLanguage",
                "en",
            ),
            duration_seconds=required_positive_int_any(
                row,
                "duration_seconds",
                "durationSeconds",
                "speech assess request",
            ),
            consent_captured=required_bool_any(
                row,
                "consent_captured",
                "consentCaptured",
                "speech assess request",
            ),
            segments=segments,
            product_hint=optional_string_any(row, "product_hint", "productHint", ""),
        )

    def to_model_payload(self) -> dict[str, Any]:
        return {
            "audio_checksum": self.audio_checksum,
            "audio_id": self.audio_id,
            "consent_captured": self.consent_captured,
            "duration_seconds": self.duration_seconds,
            "product_hint": self.product_hint or self.product,
            "raw_audio_uri": "",
            "segments": [dict(segment) for segment in self.segments],
            "tenant_id": self.tenant_id,
            "transcript_language": self.transcript_language,
        }


@dataclass(frozen=True, slots=True)
class MediaIntelligenceResponse:
    tenant_id: str
    product: str
    use_case_id: str
    subject_id: str
    result: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.result)
        payload.update(
            {
                "product": self.product,
                "subjectId": self.subject_id,
                "tenantId": self.tenant_id,
                "useCaseId": self.use_case_id,
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class MediaIntelligenceMetricsSnapshot:
    request_count: int
    document_analyze_count: int
    speech_assess_count: int
    error_count: int
    human_review_count: int
    privacy_control_violation_count: int
    by_product: dict[str, int]
    by_use_case: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "byProduct": self.by_product,
            "byUseCase": self.by_use_case,
            "documentAnalyzeCount": self.document_analyze_count,
            "errorCount": self.error_count,
            "humanReviewCount": self.human_review_count,
            "privacyControlViolationCount": self.privacy_control_violation_count,
            "requestCount": self.request_count,
            "speechAssessCount": self.speech_assess_count,
        }


class MediaIntelligenceMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.document_analyze_count = 0
        self.speech_assess_count = 0
        self.error_count = 0
        self.human_review_count = 0
        self.privacy_control_violation_count = 0
        self.by_product: dict[str, int] = {}
        self.by_use_case: dict[str, int] = {}

    def record_document(self, request: DocumentAnalyzeRequest, result: Mapping[str, Any]) -> None:
        self.request_count += 1
        self.document_analyze_count += 1
        self._record_business_keys(request.product, request.use_case_id)
        if bool(result.get("requiresHumanReview")):
            self.human_review_count += 1

    def record_speech(self, request: SpeechAssessRequest, result: Mapping[str, Any]) -> None:
        self.request_count += 1
        self.speech_assess_count += 1
        self._record_business_keys(request.product, request.use_case_id)
        if bool(result.get("requiresHumanReview")):
            self.human_review_count += 1

    def record_error(self, *, privacy_violation: bool = False) -> None:
        self.request_count += 1
        self.error_count += 1
        if privacy_violation:
            self.privacy_control_violation_count += 1

    def snapshot(self) -> MediaIntelligenceMetricsSnapshot:
        return MediaIntelligenceMetricsSnapshot(
            request_count=self.request_count,
            document_analyze_count=self.document_analyze_count,
            speech_assess_count=self.speech_assess_count,
            error_count=self.error_count,
            human_review_count=self.human_review_count,
            privacy_control_violation_count=self.privacy_control_violation_count,
            by_product=dict(sorted(self.by_product.items())),
            by_use_case=dict(sorted(self.by_use_case.items())),
        )

    def _record_business_keys(self, product: str, use_case_id: str) -> None:
        self.by_product[product] = self.by_product.get(product, 0) + 1
        self.by_use_case[use_case_id] = self.by_use_case.get(use_case_id, 0) + 1


class MediaIntelligenceRuntime:
    """Policy-aware runtime for bounded document and speech intelligence routes."""

    def __init__(self, ai_root: Path | str) -> None:
        self.ai_root = Path(ai_root)
        self.metrics = MediaIntelligenceMetrics()
        self.privacy_state = load_media_privacy_control_state(self.ai_root)
        self.document_model = load_model_class(
            self.ai_root,
            DOCUMENT_MODEL_RELATIVE_PATH,
            "DocumentIntelligenceBaseline",
            "courseflow_document_intelligence_baseline_runtime",
        )()
        self.speech_model = load_model_class(
            self.ai_root,
            SPEECH_MODEL_RELATIVE_PATH,
            "AudioQualityBaseline",
            "courseflow_audio_quality_baseline_runtime",
        )()

    def analyze_document(
        self,
        request: DocumentAnalyzeRequest | Mapping[str, Any],
        principal: MediaIntelligencePrincipal | Mapping[str, Any] | None = None,
    ) -> MediaIntelligenceResponse:
        try:
            analyze_request = (
                request
                if isinstance(request, DocumentAnalyzeRequest)
                else DocumentAnalyzeRequest.from_dict(request)
            )
            ensure_media_privacy_approved(self.privacy_state)
            authorize_document_analyze(normalize_principal(principal), analyze_request)
            prediction = self.document_model.predict(analyze_request.to_model_payload())
            result = normalize_document_prediction(prediction.to_dict())
        except MediaPrivacyControlError:
            self.metrics.record_error(privacy_violation=True)
            raise
        except Exception:
            self.metrics.record_error()
            raise
        self.metrics.record_document(analyze_request, result)
        return MediaIntelligenceResponse(
            tenant_id=analyze_request.tenant_id,
            product=analyze_request.product,
            use_case_id=analyze_request.use_case_id,
            subject_id=analyze_request.document_id,
            result=result,
        )

    def assess_speech(
        self,
        request: SpeechAssessRequest | Mapping[str, Any],
        principal: MediaIntelligencePrincipal | Mapping[str, Any] | None = None,
    ) -> MediaIntelligenceResponse:
        try:
            assess_request = (
                request
                if isinstance(request, SpeechAssessRequest)
                else SpeechAssessRequest.from_dict(request)
            )
            ensure_media_privacy_approved(self.privacy_state)
            authorize_speech_assess(normalize_principal(principal), assess_request)
            prediction = self.speech_model.predict(assess_request.to_model_payload())
            result = dict(prediction.to_dict())
        except MediaPrivacyControlError:
            self.metrics.record_error(privacy_violation=True)
            raise
        except Exception:
            self.metrics.record_error()
            raise
        self.metrics.record_speech(assess_request, result)
        return MediaIntelligenceResponse(
            tenant_id=assess_request.tenant_id,
            product=assess_request.product,
            use_case_id=assess_request.use_case_id,
            subject_id=assess_request.audio_id,
            result=result,
        )

    def health(self) -> dict[str, Any]:
        return {
            "documentModelId": "finance-document-intelligence-baseline-v1",
            "mediaPrivacy": self.privacy_state.to_dict(),
            "routeCount": len(MEDIA_INTELLIGENCE_ROUTE_SCOPES),
            "serviceStatus": (
                "healthy"
                if self.privacy_state.review_status == "approved"
                and self.privacy_state.control_gap_count == 0
                else "privacy_controls_not_ready"
            ),
            "speechModelId": "speech-quality-baseline-v1",
        }

    def snapshot_metrics(self) -> MediaIntelligenceMetricsSnapshot:
        return self.metrics.snapshot()


def load_media_intelligence_access_policy(ai_root: Path | str) -> MediaIntelligenceAccessPolicy:
    root = Path(ai_root)
    policy_path = (
        root / "platform" / "governance" / "policies" / "media-intelligence-access-policy.yaml"
    )
    policy = load_yaml(policy_path)
    raw_scope_aliases = policy.get("scope_aliases", {})
    if not isinstance(raw_scope_aliases, dict):
        raise RegistryValidationError(f"{policy_path} must define mapping field scope_aliases")
    scope_aliases = {
        "document_analyze": MEDIA_DOCUMENT_ANALYZE_SCOPE,
        "speech_assess": MEDIA_SPEECH_ASSESS_SCOPE,
        "ops": MEDIA_OPS_SCOPE,
        **raw_scope_aliases,
    }
    grants: dict[str, MediaIntelligencePrincipalGrant] = {}
    for row in require_mapping_list(policy, "principals", policy_path):
        principal_id = require_str(row, "principal_id", str(policy_path))
        if principal_id in grants:
            raise RegistryValidationError(f"{policy_path} duplicates principal: {principal_id}")
        product = require_str(row, "product", str(policy_path))
        product_ids = normalize_string_tuple(row.get("product_ids", [product]))
        grants[principal_id] = MediaIntelligencePrincipalGrant(
            principal_id=principal_id,
            owner_role=require_str(row, "owner_role", str(policy_path)),
            product=product,
            scopes=tuple(
                sorted(
                    {
                        expand_media_scope_alias(scope, scope_aliases, policy_path)
                        for scope in normalize_string_tuple(row.get("scopes", []))
                    }
                )
            ),
            tenant_ids=tuple(sorted(normalize_string_tuple(row.get("tenant_ids", [])))),
            product_ids=tuple(sorted(product_ids)),
            use_case_ids=tuple(sorted(normalize_string_tuple(row.get("use_case_ids", [])))),
        )
    defaults = policy.get("defaults", {})
    if not isinstance(defaults, dict):
        raise RegistryValidationError(f"{policy_path} defaults must be a mapping")
    return MediaIntelligenceAccessPolicy(
        policy_id=require_str(policy, "policy_id", str(policy_path)),
        principals=dict(sorted(grants.items())),
        wildcard_scopes_allowed=bool(defaults.get("wildcard_scopes_allowed", False)),
        tenant_isolation_required=bool(defaults.get("tenant_isolation_required", True)),
        raw_uri_submission_allowed=bool(defaults.get("raw_uri_submission_allowed", False)),
    )


def authorize_document_analyze(
    principal: MediaIntelligencePrincipal | None,
    request: DocumentAnalyzeRequest,
) -> None:
    authorize_media_request(
        principal,
        request.tenant_id,
        request.product,
        request.use_case_id,
        MEDIA_DOCUMENT_ANALYZE_SCOPE,
        "document analyze",
    )


def authorize_speech_assess(
    principal: MediaIntelligencePrincipal | None,
    request: SpeechAssessRequest,
) -> None:
    authorize_media_request(
        principal,
        request.tenant_id,
        request.product,
        request.use_case_id,
        MEDIA_SPEECH_ASSESS_SCOPE,
        "speech assess",
    )


def authorize_media_request(
    principal: MediaIntelligencePrincipal | None,
    tenant_id: str,
    product: str,
    use_case_id: str,
    required_scope: str,
    operation_name: str,
) -> None:
    if principal is None:
        return
    if "*" in principal.scopes:
        raise MediaIntelligenceServiceError("wildcard media intelligence scopes are forbidden")
    if required_scope not in principal.scopes:
        raise MediaIntelligenceServiceError(
            f"media intelligence {operation_name} scope is required"
        )
    if principal.tenant_ids and tenant_id not in principal.tenant_ids:
        raise MediaIntelligenceServiceError("media intelligence tenant is not granted to principal")
    if principal.product_ids and product not in principal.product_ids:
        raise MediaIntelligenceServiceError(
            "media intelligence product is not granted to principal"
        )
    if principal.use_case_ids and use_case_id not in principal.use_case_ids:
        raise MediaIntelligenceServiceError(
            "media intelligence use case is not granted to principal"
        )


def load_media_privacy_control_state(ai_root: Path | str) -> MediaPrivacyControlState:
    root = Path(ai_root)
    report_path = root / "platform" / "governance" / "reports" / "media-privacy-review-v1.yaml"
    report = load_yaml(report_path)
    summary = report.get("summary", {})
    if not isinstance(summary, dict):
        raise RegistryValidationError(f"{report_path} summary must be a mapping")
    return MediaPrivacyControlState(
        review_status=require_report_status(summary, report_path),
        approved_count=require_non_negative_int_any(summary, "approved_count", str(report_path)),
        control_gap_count=require_non_negative_int_any(
            summary,
            "control_gap_count",
            str(report_path),
        ),
        report_path=str(report_path.relative_to(root)),
    )


def ensure_media_privacy_approved(state: MediaPrivacyControlState) -> None:
    if state.review_status != "approved" or state.control_gap_count:
        raise MediaPrivacyControlError(
            "media privacy controls must be approved before serving media intelligence"
        )


def normalize_document_prediction(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "confidence": row.get("confidence"),
        "documentType": row.get("document_type"),
        "evidenceTerms": tuple(row.get("evidence_terms", ())),
        "extractedFields": dict(row.get("extracted_fields", {})),
        "modelId": row.get("model_id"),
        "reasonCodes": tuple(row.get("reason_codes", ())),
        "requiresHumanReview": bool(row.get("requires_human_review")),
    }


def normalize_principal(
    principal: MediaIntelligencePrincipal | Mapping[str, Any] | None,
) -> MediaIntelligencePrincipal | None:
    if principal is None or isinstance(principal, MediaIntelligencePrincipal):
        return principal
    return MediaIntelligencePrincipal.from_dict(principal)


def load_model_class(
    ai_root: Path,
    relative_path: str,
    class_name: str,
    module_name: str,
) -> type[Any]:
    module_path = ai_root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise MediaIntelligenceServiceError(f"cannot load model module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    model_class = getattr(module, class_name, None)
    if model_class is None:
        raise MediaIntelligenceServiceError(
            f"model module {relative_path} does not define {class_name}"
        )
    return model_class


def reject_raw_media_uri(row: Mapping[str, Any], keys: tuple[str, ...], owner: str) -> None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            raise MediaPrivacyControlError(f"{owner} must not include raw media URI field {key}")


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list | tuple):
        raise MediaIntelligenceServiceError(
            "media intelligence policy values must be strings or lists"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise MediaIntelligenceServiceError(
                "media intelligence policy list values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def expand_media_scope_alias(
    scope: str,
    scope_aliases: Mapping[str, str],
    policy_path: Path,
) -> str:
    expanded = scope_aliases.get(scope, scope)
    if not expanded.startswith("internal:ai-platform:media-intelligence:"):
        raise RegistryValidationError(
            f"{policy_path} has unsupported media intelligence scope: {scope}"
        )
    return expanded


def required_non_empty_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise MediaIntelligenceServiceError(
            f"media intelligence request must define {snake_key} or {camel_key}"
        )
    return value.strip()


def optional_string_any(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    default: str,
) -> str:
    value = row.get(snake_key, row.get(camel_key, default))
    if value is None:
        return default
    if not isinstance(value, str):
        raise MediaIntelligenceServiceError(
            f"media intelligence request field {snake_key} must be a string"
        )
    return value.strip() or default


def required_mapping_sequence_any(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    owner: str,
) -> tuple[Mapping[str, Any], ...]:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, list | tuple):
        raise MediaIntelligenceServiceError(
            f"{owner} field {snake_key} or {camel_key} must be a list"
        )
    result: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise MediaIntelligenceServiceError(f"{owner} item {index} must be a mapping")
        result.append(item)
    return tuple(result)


def required_bool_any(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    owner: str,
) -> bool:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, bool):
        raise MediaIntelligenceServiceError(
            f"{owner} must define boolean field {snake_key} or {camel_key}"
        )
    return value


def required_positive_int_any(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    owner: str,
) -> int:
    value = row.get(snake_key, row.get(camel_key))
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MediaIntelligenceServiceError(
            f"{owner} must define positive integer field {snake_key} or {camel_key}"
        )
    return value


def require_non_negative_int_any(row: Mapping[str, Any], key: str, owner: str) -> int:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RegistryValidationError(f"{owner} must define non-negative integer {key}")
    return value


def require_report_status(row: Mapping[str, Any], owner: Path) -> str:
    status = row.get("review_status")
    if not isinstance(status, str) or not status.strip():
        raise RegistryValidationError(f"{owner} summary must define review_status")
    return status.strip()


def require_mapping_list(row: Mapping[str, Any], key: str, owner: Path) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a mapping")
        result.append(item)
    return result

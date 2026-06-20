"""Independent AI Platform NLP understanding service package."""

from courseflow_nlp_understanding_service.service import (
    NLP_UNDERSTANDING_SERVICE_ID,
    NlpUnderstandingService,
    NlpUnderstandingServiceConfig,
    ServiceRoute,
    build_service_manifest,
    default_ai_root,
)

__all__ = [
    "NLP_UNDERSTANDING_SERVICE_ID",
    "NlpUnderstandingService",
    "NlpUnderstandingServiceConfig",
    "ServiceRoute",
    "build_service_manifest",
    "default_ai_root",
]

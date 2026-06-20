"""Independent AI Platform retrieval service package."""

from courseflow_retrieval_service.service import (
    RETRIEVAL_SERVICE_ID,
    RetrievalService,
    RetrievalServiceConfig,
    ServiceRoute,
    build_service_manifest,
    default_ai_root,
)

__all__ = [
    "RETRIEVAL_SERVICE_ID",
    "RetrievalService",
    "RetrievalServiceConfig",
    "ServiceRoute",
    "build_service_manifest",
    "default_ai_root",
]

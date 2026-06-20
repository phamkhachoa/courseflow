"""Independent AI Platform model-serving service package."""

from courseflow_model_serving_service.service import (
    MODEL_SERVING_SERVICE_ID,
    ModelServingService,
    ModelServingServiceConfig,
    ServiceRoute,
    build_service_manifest,
    default_ai_root,
)

__all__ = [
    "MODEL_SERVING_SERVICE_ID",
    "ModelServingService",
    "ModelServingServiceConfig",
    "ServiceRoute",
    "build_service_manifest",
    "default_ai_root",
]

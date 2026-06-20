"""Independent AI Platform governance evaluation service package."""

from courseflow_governance_evaluation_service.service import (
    GOVERNANCE_EVALUATION_SERVICE_ID,
    GovernanceEvaluationService,
    GovernanceEvaluationServiceConfig,
    ServiceRoute,
    build_service_manifest,
    default_ai_root,
)

__all__ = [
    "GOVERNANCE_EVALUATION_SERVICE_ID",
    "GovernanceEvaluationService",
    "GovernanceEvaluationServiceConfig",
    "ServiceRoute",
    "build_service_manifest",
    "default_ai_root",
]

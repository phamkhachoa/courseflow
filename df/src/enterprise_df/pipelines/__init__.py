"""Local pipeline skeletons for enterprise data products."""

from enterprise_df.pipelines.base import PipelineRunRequest, PipelineSpec
from enterprise_df.pipelines.billing import (
    BillingPipelineResult,
    BillingRevenueDailyRunner,
    run_billing_revenue_daily_from_bronze,
)
from enterprise_df.pipelines.control_tower import (
    ControlTowerGoldMaterializationRunner,
    ControlTowerPipelineResult,
    run_control_tower_gold_materialization,
)
from enterprise_df.pipelines.customer import (
    CustomerAccountHealthRunner,
    CustomerPipelineResult,
    run_customer_account_health_from_bronze,
)
from enterprise_df.pipelines.finance import (
    FinanceBenefitReconciliationRunner,
    FinancePipelineResult,
    run_finance_benefit_reconciliation_from_bronze,
)
from enterprise_df.pipelines.identity_access import (
    IdentityAccessGovernanceRunner,
    IdentityAccessPipelineResult,
    run_identity_access_governance_from_bronze,
)
from enterprise_df.pipelines.registry import PipelineRegistry, default_pipeline_registry
from enterprise_df.pipelines.recommendation import (
    PipelineResult,
    RecommendationFromBronzeRunner,
    RecommendationRawJsonlRunner,
    run_recommendation_pipeline,
    run_recommendation_pipeline_from_bronze,
)
from enterprise_df.pipelines.scorecard import (
    ExecutiveScorecardPipelineResult,
    ExecutiveScorecardRunner,
    run_executive_scorecard_from_semantic_snapshot,
)
from enterprise_df.pipelines.support import (
    SupportPipelineResult,
    SupportSlaRunner,
    run_support_sla_from_bronze,
)

__all__ = [
    "PipelineRegistry",
    "PipelineResult",
    "PipelineRunRequest",
    "PipelineSpec",
    "BillingPipelineResult",
    "BillingRevenueDailyRunner",
    "ControlTowerGoldMaterializationRunner",
    "ControlTowerPipelineResult",
    "CustomerAccountHealthRunner",
    "CustomerPipelineResult",
    "FinanceBenefitReconciliationRunner",
    "FinancePipelineResult",
    "IdentityAccessGovernanceRunner",
    "IdentityAccessPipelineResult",
    "ExecutiveScorecardPipelineResult",
    "ExecutiveScorecardRunner",
    "RecommendationFromBronzeRunner",
    "RecommendationRawJsonlRunner",
    "SupportPipelineResult",
    "SupportSlaRunner",
    "default_pipeline_registry",
    "run_billing_revenue_daily_from_bronze",
    "run_control_tower_gold_materialization",
    "run_customer_account_health_from_bronze",
    "run_finance_benefit_reconciliation_from_bronze",
    "run_identity_access_governance_from_bronze",
    "run_executive_scorecard_from_semantic_snapshot",
    "run_recommendation_pipeline",
    "run_recommendation_pipeline_from_bronze",
    "run_support_sla_from_bronze",
]

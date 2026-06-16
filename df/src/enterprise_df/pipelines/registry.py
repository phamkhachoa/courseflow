from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from enterprise_df.pipelines.base import PipelineRunRequest, PipelineRunner, PipelineSpec
from enterprise_df.pipelines.billing import BillingRevenueDailyRunner
from enterprise_df.pipelines.control_tower import ControlTowerGoldMaterializationRunner
from enterprise_df.pipelines.customer import CustomerAccountHealthRunner
from enterprise_df.pipelines.finance import FinanceBenefitReconciliationRunner
from enterprise_df.pipelines.identity_access import IdentityAccessGovernanceRunner
from enterprise_df.pipelines.recommendation import RecommendationFromBronzeRunner, RecommendationRawJsonlRunner
from enterprise_df.pipelines.scorecard import ExecutiveScorecardRunner
from enterprise_df.pipelines.support import SupportSlaRunner


@dataclass
class PipelineRegistry:
    runners: dict[str, PipelineRunner]

    def register(self, runner: PipelineRunner) -> None:
        if runner.spec.runner_id in self.runners:
            raise ValueError(f"pipeline runner already registered: {runner.spec.runner_id}")
        self.runners[runner.spec.runner_id] = runner

    def get(self, runner_id: str) -> PipelineRunner:
        try:
            return self.runners[runner_id]
        except KeyError as exc:
            raise KeyError(f"pipeline runner is not registered: {runner_id}") from exc

    def list_specs(
        self,
        *,
        product: str | None = None,
        domain: str | None = None,
        use_case: str | None = None,
        output_data_product: str | None = None,
    ) -> list[PipelineSpec]:
        specs = list(runner.spec for runner in self.runners.values())
        if product:
            specs = [spec for spec in specs if spec.product == product]
        if domain:
            specs = [spec for spec in specs if spec.domain == domain]
        if use_case:
            specs = [spec for spec in specs if use_case in spec.use_cases]
        if output_data_product:
            specs = [spec for spec in specs if output_data_product in spec.output_data_products]
        return sorted(specs, key=lambda spec: spec.runner_id)

    def find_by_use_case(self, use_case_id: str) -> list[PipelineSpec]:
        return self.list_specs(use_case=use_case_id)

    def find_by_output_data_product(self, data_product_name: str) -> list[PipelineSpec]:
        return self.list_specs(output_data_product=data_product_name)

    def run(self, runner_id: str, request: PipelineRunRequest) -> Any:
        return self.get(runner_id).run(request)


def default_pipeline_registry() -> PipelineRegistry:
    registry = PipelineRegistry(runners={})
    registry.register(BillingRevenueDailyRunner())
    registry.register(ControlTowerGoldMaterializationRunner())
    registry.register(CustomerAccountHealthRunner())
    registry.register(ExecutiveScorecardRunner())
    registry.register(FinanceBenefitReconciliationRunner())
    registry.register(IdentityAccessGovernanceRunner())
    registry.register(RecommendationFromBronzeRunner())
    registry.register(RecommendationRawJsonlRunner())
    registry.register(SupportSlaRunner())
    return registry

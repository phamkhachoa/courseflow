from __future__ import annotations

import importlib.util
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import UUID

from courseflow_ai_platform.prompt_gateway import (
    build_prompt_gateway_request,
    prompt_cost_within_budget,
    run_prompt_gateway,
)
from courseflow_ai_platform.prompt_gateway_service import (
    PromptGatewayRuntime,
    load_prompt_gateway_access_policy,
)
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str
from courseflow_ai_platform.vector_index import (
    build_vector_index,
    hybrid_rank_ids,
    validate_vector_index_contract,
    vector_rank,
)


@dataclass(frozen=True, slots=True)
class EvaluationRunResult:
    evaluation_id: str
    runner: str
    dataset_id: str
    model_id: str
    product: str
    use_case_id: str
    case_count: int
    metrics: dict[str, bool | float | int | str]
    passed: bool
    required: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "caseCount": self.case_count,
            "datasetId": self.dataset_id,
            "metrics": self.metrics,
            "modelId": self.model_id,
            "passed": self.passed,
            "product": self.product,
            "required": self.required,
            "runner": self.runner,
            "useCaseId": self.use_case_id,
        }


@dataclass(frozen=True, slots=True)
class EvaluationRegistryReport:
    run_count: int
    passed_count: int
    required_count: int
    required_passed_count: int
    results: dict[str, EvaluationRunResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passedCount": self.passed_count,
            "requiredCount": self.required_count,
            "requiredPassedCount": self.required_passed_count,
            "runCount": self.run_count,
            "results": {
                evaluation_id: result.to_dict()
                for evaluation_id, result in sorted(self.results.items())
            },
        }


@dataclass(frozen=True, slots=True)
class SupportAgentAssistEvaluation:
    dataset_id: str
    model_id: str
    case_count: int
    intent_accuracy: float
    priority_accuracy: float
    human_review_rate: float
    retrieval_required_term_coverage: float
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "datasetId": self.dataset_id,
            "modelId": self.model_id,
            "caseCount": self.case_count,
            "intentAccuracy": self.intent_accuracy,
            "priorityAccuracy": self.priority_accuracy,
            "humanReviewRate": self.human_review_rate,
            "retrievalRequiredTermCoverage": self.retrieval_required_term_coverage,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class RecommendationItemCfEvaluation:
    dataset_id: str
    model_id: str
    case_count: int
    recall_at_k: float
    ndcg_at_k: float
    catalog_coverage: float
    k: int
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "catalogCoverage": self.catalog_coverage,
            "caseCount": self.case_count,
            "datasetId": self.dataset_id,
            "k": self.k,
            "modelId": self.model_id,
            "ndcgAtK": self.ndcg_at_k,
            "passed": self.passed,
            "recallAtK": self.recall_at_k,
        }


@dataclass(frozen=True, slots=True)
class SequenceRiskEvaluation:
    dataset_id: str
    model_id: str
    case_count: int
    risk_band_accuracy: float
    reason_code_recall: float
    score_threshold_pass_rate: float
    risk_ordering_pass_rate: float
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "caseCount": self.case_count,
            "datasetId": self.dataset_id,
            "modelId": self.model_id,
            "passed": self.passed,
            "reasonCodeRecall": self.reason_code_recall,
            "riskBandAccuracy": self.risk_band_accuracy,
            "riskOrderingPassRate": self.risk_ordering_pass_rate,
            "scoreThresholdPassRate": self.score_threshold_pass_rate,
        }


@dataclass(frozen=True, slots=True)
class SupportSlaRiskEvaluation:
    dataset_id: str
    model_id: str
    case_count: int
    risk_band_accuracy: float
    reason_code_recall: float
    human_review_policy_pass_rate: float
    score_threshold_pass_rate: float
    risk_ordering_pass_rate: float
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "caseCount": self.case_count,
            "datasetId": self.dataset_id,
            "humanReviewPolicyPassRate": self.human_review_policy_pass_rate,
            "modelId": self.model_id,
            "passed": self.passed,
            "reasonCodeRecall": self.reason_code_recall,
            "riskBandAccuracy": self.risk_band_accuracy,
            "riskOrderingPassRate": self.risk_ordering_pass_rate,
            "scoreThresholdPassRate": self.score_threshold_pass_rate,
        }


@dataclass(frozen=True, slots=True)
class PaymentFraudRiskEvaluation:
    dataset_id: str
    model_id: str
    case_count: int
    risk_band_accuracy: float
    reason_code_recall: float
    entity_link_recall: float
    human_review_policy_pass_rate: float
    score_threshold_pass_rate: float
    risk_ordering_pass_rate: float
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "caseCount": self.case_count,
            "datasetId": self.dataset_id,
            "entityLinkRecall": self.entity_link_recall,
            "humanReviewPolicyPassRate": self.human_review_policy_pass_rate,
            "modelId": self.model_id,
            "passed": self.passed,
            "reasonCodeRecall": self.reason_code_recall,
            "riskBandAccuracy": self.risk_band_accuracy,
            "riskOrderingPassRate": self.risk_ordering_pass_rate,
            "scoreThresholdPassRate": self.score_threshold_pass_rate,
        }


@dataclass(frozen=True, slots=True)
class DemandForecastEvaluation:
    dataset_id: str
    model_id: str
    case_count: int
    demand_band_accuracy: float
    staffing_recommendation_accuracy: float
    reason_code_recall: float
    forecast_threshold_pass_rate: float
    human_review_policy_pass_rate: float
    forecast_ordering_pass_rate: float
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "caseCount": self.case_count,
            "datasetId": self.dataset_id,
            "demandBandAccuracy": self.demand_band_accuracy,
            "forecastOrderingPassRate": self.forecast_ordering_pass_rate,
            "forecastThresholdPassRate": self.forecast_threshold_pass_rate,
            "humanReviewPolicyPassRate": self.human_review_policy_pass_rate,
            "modelId": self.model_id,
            "passed": self.passed,
            "reasonCodeRecall": self.reason_code_recall,
            "staffingRecommendationAccuracy": (
                self.staffing_recommendation_accuracy
            ),
        }


@dataclass(frozen=True, slots=True)
class CausalUpliftEvaluation:
    dataset_id: str
    model_id: str
    case_count: int
    decision_band_accuracy: float
    recommendation_accuracy: float
    reason_code_recall: float
    human_review_policy_pass_rate: float
    guardrail_stop_pass_rate: float
    deterministic_replay_rate: float
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "caseCount": self.case_count,
            "datasetId": self.dataset_id,
            "decisionBandAccuracy": self.decision_band_accuracy,
            "deterministicReplayRate": self.deterministic_replay_rate,
            "guardrailStopPassRate": self.guardrail_stop_pass_rate,
            "humanReviewPolicyPassRate": self.human_review_policy_pass_rate,
            "modelId": self.model_id,
            "passed": self.passed,
            "reasonCodeRecall": self.reason_code_recall,
            "recommendationAccuracy": self.recommendation_accuracy,
        }


@dataclass(frozen=True, slots=True)
class DocumentIntelligenceEvaluation:
    dataset_id: str
    model_id: str
    case_count: int
    document_type_accuracy: float
    field_recall: float
    evidence_term_recall: float
    human_review_policy_pass_rate: float
    privacy_guardrail_pass_rate: float
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "caseCount": self.case_count,
            "datasetId": self.dataset_id,
            "documentTypeAccuracy": self.document_type_accuracy,
            "evidenceTermRecall": self.evidence_term_recall,
            "fieldRecall": self.field_recall,
            "humanReviewPolicyPassRate": self.human_review_policy_pass_rate,
            "modelId": self.model_id,
            "passed": self.passed,
            "privacyGuardrailPassRate": self.privacy_guardrail_pass_rate,
        }


@dataclass(frozen=True, slots=True)
class SpeechQualityEvaluation:
    dataset_id: str
    model_id: str
    case_count: int
    intent_accuracy: float
    quality_band_accuracy: float
    reason_code_recall: float
    evidence_term_recall: float
    human_review_policy_pass_rate: float
    privacy_guardrail_pass_rate: float
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "caseCount": self.case_count,
            "datasetId": self.dataset_id,
            "evidenceTermRecall": self.evidence_term_recall,
            "humanReviewPolicyPassRate": self.human_review_policy_pass_rate,
            "intentAccuracy": self.intent_accuracy,
            "modelId": self.model_id,
            "passed": self.passed,
            "privacyGuardrailPassRate": self.privacy_guardrail_pass_rate,
            "qualityBandAccuracy": self.quality_band_accuracy,
            "reasonCodeRecall": self.reason_code_recall,
        }


@dataclass(frozen=True, slots=True)
class RoutingPolicyEvaluation:
    dataset_id: str
    model_id: str
    case_count: int
    assignment_accuracy: float
    constraint_pass_rate: float
    baseline_lift_pass_rate: float
    reason_code_recall: float
    exploration_budget_pass_rate: float
    deterministic_replay_rate: float
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "assignmentAccuracy": self.assignment_accuracy,
            "baselineLiftPassRate": self.baseline_lift_pass_rate,
            "caseCount": self.case_count,
            "constraintPassRate": self.constraint_pass_rate,
            "datasetId": self.dataset_id,
            "deterministicReplayRate": self.deterministic_replay_rate,
            "explorationBudgetPassRate": self.exploration_budget_pass_rate,
            "modelId": self.model_id,
            "passed": self.passed,
            "reasonCodeRecall": self.reason_code_recall,
        }


@dataclass(frozen=True, slots=True)
class RetrievalEvaluation:
    dataset_id: str
    model_id: str
    collection: str
    case_count: int
    recall_at_k: float
    hit_rate_at_k: float
    citation_precision_at_k: float
    tenant_isolation_rate: float
    k: int
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "caseCount": self.case_count,
            "citationPrecisionAtK": self.citation_precision_at_k,
            "collection": self.collection,
            "datasetId": self.dataset_id,
            "hitRateAtK": self.hit_rate_at_k,
            "k": self.k,
            "modelId": self.model_id,
            "passed": self.passed,
            "recallAtK": self.recall_at_k,
            "tenantIsolationRate": self.tenant_isolation_rate,
        }


@dataclass(frozen=True, slots=True)
class GroundedAnswerEvaluation:
    dataset_id: str
    model_id: str
    collection: str
    case_count: int
    groundedness: float
    answer_relevance: float
    citation_precision: float
    refusal_accuracy: float
    hallucination_rate: float
    unsafe_answer_rate: float
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "answerRelevance": self.answer_relevance,
            "caseCount": self.case_count,
            "citationPrecision": self.citation_precision,
            "collection": self.collection,
            "datasetId": self.dataset_id,
            "groundedness": self.groundedness,
            "hallucinationRate": self.hallucination_rate,
            "modelId": self.model_id,
            "passed": self.passed,
            "refusalAccuracy": self.refusal_accuracy,
            "unsafeAnswerRate": self.unsafe_answer_rate,
        }


@dataclass(frozen=True, slots=True)
class PromptSafetyEvaluation:
    dataset_id: str
    model_id: str
    case_count: int
    pii_redaction_recall: float
    secret_redaction_recall: float
    expected_token_coverage: float
    tenant_context_pass_rate: float
    cost_budget_pass_rate: float
    audit_safety_rate: float
    human_review_rate: float
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "auditSafetyRate": self.audit_safety_rate,
            "caseCount": self.case_count,
            "costBudgetPassRate": self.cost_budget_pass_rate,
            "datasetId": self.dataset_id,
            "expectedTokenCoverage": self.expected_token_coverage,
            "humanReviewRate": self.human_review_rate,
            "modelId": self.model_id,
            "passed": self.passed,
            "piiRedactionRecall": self.pii_redaction_recall,
            "secretRedactionRecall": self.secret_redaction_recall,
            "tenantContextPassRate": self.tenant_context_pass_rate,
        }


@dataclass(frozen=True, slots=True)
class LlmAdapterShadowEvaluation:
    dataset_id: str
    model_id: str
    case_count: int
    prompt_gateway_expected_pass_rate: float
    allowed_generation_rate: float
    blocked_generation_skip_rate: float
    groundedness: float
    citation_precision: float
    refusal_accuracy: float
    audit_safety_rate: float
    context_filter_pass_rate: float
    gateway_evaluation_count: int
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "allowedGenerationRate": self.allowed_generation_rate,
            "auditSafetyRate": self.audit_safety_rate,
            "blockedGenerationSkipRate": self.blocked_generation_skip_rate,
            "caseCount": self.case_count,
            "citationPrecision": self.citation_precision,
            "contextFilterPassRate": self.context_filter_pass_rate,
            "datasetId": self.dataset_id,
            "gatewayEvaluationCount": self.gateway_evaluation_count,
            "groundedness": self.groundedness,
            "modelId": self.model_id,
            "passed": self.passed,
            "promptGatewayExpectedPassRate": (
                self.prompt_gateway_expected_pass_rate
            ),
            "refusalAccuracy": self.refusal_accuracy,
        }


@dataclass(frozen=True, slots=True)
class VectorIndexEvaluation:
    dataset_id: str
    model_id: str
    collection: str
    case_count: int
    embedding_dimensions: int
    chunk_coverage_rate: float
    dimension_conformance_rate: float
    metadata_conformance_rate: float
    tenant_scope_coverage_rate: float
    checksum_stable: bool
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "caseCount": self.case_count,
            "checksumStable": self.checksum_stable,
            "chunkCoverageRate": self.chunk_coverage_rate,
            "collection": self.collection,
            "datasetId": self.dataset_id,
            "dimensionConformanceRate": self.dimension_conformance_rate,
            "embeddingDimensions": self.embedding_dimensions,
            "metadataConformanceRate": self.metadata_conformance_rate,
            "modelId": self.model_id,
            "passed": self.passed,
            "tenantScopeCoverageRate": self.tenant_scope_coverage_rate,
        }


@dataclass(frozen=True, slots=True)
class HybridRetrievalEvaluation:
    dataset_id: str
    model_id: str
    collection: str
    case_count: int
    lexical_recall_at_k: float
    vector_recall_at_k: float
    hybrid_recall_at_k: float
    hybrid_not_worse_than_lexical_rate: float
    tenant_isolation_rate: float
    k: int
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int | str]:
        return {
            "caseCount": self.case_count,
            "collection": self.collection,
            "datasetId": self.dataset_id,
            "hybridNotWorseThanLexicalRate": self.hybrid_not_worse_than_lexical_rate,
            "hybridRecallAtK": self.hybrid_recall_at_k,
            "k": self.k,
            "lexicalRecallAtK": self.lexical_recall_at_k,
            "modelId": self.model_id,
            "passed": self.passed,
            "tenantIsolationRate": self.tenant_isolation_rate,
            "vectorRecallAtK": self.vector_recall_at_k,
        }


def run_registered_evaluations(ai_root: Path | str) -> EvaluationRegistryReport:
    root = Path(ai_root)
    registry = load_yaml(root / "platform" / "evaluation" / "registry.yaml")
    evaluations = require_list(registry, "evaluations", "evaluation registry")
    results: dict[str, EvaluationRunResult] = {}

    for row in evaluations:
        evaluation_id = require_str(row, "id", "evaluation registry row")
        if evaluation_id in results:
            raise RegistryValidationError(
                f"evaluation registry has duplicate id: {evaluation_id}"
            )
        dataset = require_str(row, "dataset", f"evaluation {evaluation_id}")
        report = require_str(row, "report", f"evaluation {evaluation_id}")
        for linked_path in (dataset, report):
            if not (root / linked_path).exists():
                raise RegistryValidationError(
                    f"evaluation {evaluation_id} linked artifact does not exist: {linked_path}"
                )

        runner = require_str(row, "runner", f"evaluation {evaluation_id}")
        required = bool(row.get("required", False))
        result = run_evaluation_runner(root, row, runner, required)
        results[evaluation_id] = result

    passed_count = sum(1 for result in results.values() if result.passed)
    required_count = sum(1 for result in results.values() if result.required)
    required_passed_count = sum(
        1 for result in results.values() if result.required and result.passed
    )
    if required_passed_count != required_count:
        failed = sorted(
            result.evaluation_id
            for result in results.values()
            if result.required and not result.passed
        )
        raise RegistryValidationError(
            "required evaluations failed: " + ", ".join(failed)
        )

    return EvaluationRegistryReport(
        run_count=len(results),
        passed_count=passed_count,
        required_count=required_count,
        required_passed_count=required_passed_count,
        results=results,
    )


def run_evaluation_runner(
    root: Path,
    row: dict[str, Any],
    runner: str,
    required: bool,
) -> EvaluationRunResult:
    evaluation_id = require_str(row, "id", "evaluation registry row")
    product = require_str(row, "product", f"evaluation {evaluation_id}")
    use_case_id = require_str(row, "use_case_id", f"evaluation {evaluation_id}")
    model_id = require_str(row, "model_id", f"evaluation {evaluation_id}")

    if runner == "support_agent_assist_golden":
        support_report = evaluate_support_agent_assist(root)
        ensure_runner_model_id(evaluation_id, model_id, support_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=support_report.dataset_id,
            model_id=support_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=support_report.case_count,
            metrics={
                "humanReviewRate": support_report.human_review_rate,
                "intentAccuracy": support_report.intent_accuracy,
                "priorityAccuracy": support_report.priority_accuracy,
                "retrievalRequiredTermCoverage": (
                    support_report.retrieval_required_term_coverage
                ),
            },
            passed=support_report.passed,
            required=required,
        )

    if runner == "recommendation_item_cf_offline":
        recommendation_report = evaluate_recommendation_item_cf(root)
        ensure_runner_model_id(evaluation_id, model_id, recommendation_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=recommendation_report.dataset_id,
            model_id=recommendation_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=recommendation_report.case_count,
            metrics={
                "catalogCoverage": recommendation_report.catalog_coverage,
                "k": recommendation_report.k,
                "ndcgAtK": recommendation_report.ndcg_at_k,
                "recallAtK": recommendation_report.recall_at_k,
            },
            passed=recommendation_report.passed,
            required=required,
        )

    if runner == "sequence_risk_golden":
        sequence_risk_report = evaluate_sequence_risk_golden(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, sequence_risk_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=sequence_risk_report.dataset_id,
            model_id=sequence_risk_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=sequence_risk_report.case_count,
            metrics={
                "reasonCodeRecall": sequence_risk_report.reason_code_recall,
                "riskBandAccuracy": sequence_risk_report.risk_band_accuracy,
                "riskOrderingPassRate": sequence_risk_report.risk_ordering_pass_rate,
                "scoreThresholdPassRate": sequence_risk_report.score_threshold_pass_rate,
            },
            passed=sequence_risk_report.passed,
            required=required,
        )

    if runner == "support_sla_risk_golden":
        support_sla_report = evaluate_support_sla_risk_golden(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, support_sla_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=support_sla_report.dataset_id,
            model_id=support_sla_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=support_sla_report.case_count,
            metrics={
                "humanReviewPolicyPassRate": (
                    support_sla_report.human_review_policy_pass_rate
                ),
                "reasonCodeRecall": support_sla_report.reason_code_recall,
                "riskBandAccuracy": support_sla_report.risk_band_accuracy,
                "riskOrderingPassRate": support_sla_report.risk_ordering_pass_rate,
                "scoreThresholdPassRate": support_sla_report.score_threshold_pass_rate,
            },
            passed=support_sla_report.passed,
            required=required,
        )

    if runner == "payment_fraud_risk_golden":
        payment_fraud_report = evaluate_payment_fraud_risk_golden(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, payment_fraud_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=payment_fraud_report.dataset_id,
            model_id=payment_fraud_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=payment_fraud_report.case_count,
            metrics={
                "entityLinkRecall": payment_fraud_report.entity_link_recall,
                "humanReviewPolicyPassRate": (
                    payment_fraud_report.human_review_policy_pass_rate
                ),
                "reasonCodeRecall": payment_fraud_report.reason_code_recall,
                "riskBandAccuracy": payment_fraud_report.risk_band_accuracy,
                "riskOrderingPassRate": payment_fraud_report.risk_ordering_pass_rate,
                "scoreThresholdPassRate": (
                    payment_fraud_report.score_threshold_pass_rate
                ),
            },
            passed=payment_fraud_report.passed,
            required=required,
        )

    if runner == "demand_forecast_golden":
        demand_forecast_report = evaluate_demand_forecast_golden(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, demand_forecast_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=demand_forecast_report.dataset_id,
            model_id=demand_forecast_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=demand_forecast_report.case_count,
            metrics={
                "demandBandAccuracy": demand_forecast_report.demand_band_accuracy,
                "forecastOrderingPassRate": (
                    demand_forecast_report.forecast_ordering_pass_rate
                ),
                "forecastThresholdPassRate": (
                    demand_forecast_report.forecast_threshold_pass_rate
                ),
                "humanReviewPolicyPassRate": (
                    demand_forecast_report.human_review_policy_pass_rate
                ),
                "reasonCodeRecall": demand_forecast_report.reason_code_recall,
                "staffingRecommendationAccuracy": (
                    demand_forecast_report.staffing_recommendation_accuracy
                ),
            },
            passed=demand_forecast_report.passed,
            required=required,
        )

    if runner == "causal_uplift_golden":
        causal_report = evaluate_causal_uplift_golden(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, causal_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=causal_report.dataset_id,
            model_id=causal_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=causal_report.case_count,
            metrics={
                "decisionBandAccuracy": causal_report.decision_band_accuracy,
                "deterministicReplayRate": causal_report.deterministic_replay_rate,
                "guardrailStopPassRate": causal_report.guardrail_stop_pass_rate,
                "humanReviewPolicyPassRate": (
                    causal_report.human_review_policy_pass_rate
                ),
                "reasonCodeRecall": causal_report.reason_code_recall,
                "recommendationAccuracy": causal_report.recommendation_accuracy,
            },
            passed=causal_report.passed,
            required=required,
        )

    if runner == "document_intelligence_golden":
        document_report = evaluate_document_intelligence_golden(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, document_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=document_report.dataset_id,
            model_id=document_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=document_report.case_count,
            metrics={
                "documentTypeAccuracy": document_report.document_type_accuracy,
                "evidenceTermRecall": document_report.evidence_term_recall,
                "fieldRecall": document_report.field_recall,
                "humanReviewPolicyPassRate": (
                    document_report.human_review_policy_pass_rate
                ),
                "privacyGuardrailPassRate": document_report.privacy_guardrail_pass_rate,
            },
            passed=document_report.passed,
            required=required,
        )

    if runner == "speech_quality_golden":
        speech_report = evaluate_speech_quality_golden(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, speech_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=speech_report.dataset_id,
            model_id=speech_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=speech_report.case_count,
            metrics={
                "evidenceTermRecall": speech_report.evidence_term_recall,
                "humanReviewPolicyPassRate": (
                    speech_report.human_review_policy_pass_rate
                ),
                "intentAccuracy": speech_report.intent_accuracy,
                "privacyGuardrailPassRate": speech_report.privacy_guardrail_pass_rate,
                "qualityBandAccuracy": speech_report.quality_band_accuracy,
                "reasonCodeRecall": speech_report.reason_code_recall,
            },
            passed=speech_report.passed,
            required=required,
        )

    if runner == "routing_policy_simulator_golden":
        routing_report = evaluate_routing_policy_simulator_golden(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, routing_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=routing_report.dataset_id,
            model_id=routing_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=routing_report.case_count,
            metrics={
                "assignmentAccuracy": routing_report.assignment_accuracy,
                "baselineLiftPassRate": routing_report.baseline_lift_pass_rate,
                "constraintPassRate": routing_report.constraint_pass_rate,
                "deterministicReplayRate": routing_report.deterministic_replay_rate,
                "explorationBudgetPassRate": routing_report.exploration_budget_pass_rate,
                "reasonCodeRecall": routing_report.reason_code_recall,
            },
            passed=routing_report.passed,
            required=required,
        )

    if runner == "lexical_retrieval_golden":
        retrieval_report = evaluate_retrieval_golden(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, retrieval_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=retrieval_report.dataset_id,
            model_id=retrieval_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=retrieval_report.case_count,
            metrics={
                "citationPrecisionAtK": retrieval_report.citation_precision_at_k,
                "hitRateAtK": retrieval_report.hit_rate_at_k,
                "k": retrieval_report.k,
                "recallAtK": retrieval_report.recall_at_k,
                "tenantIsolationRate": retrieval_report.tenant_isolation_rate,
            },
            passed=retrieval_report.passed,
            required=required,
        )

    if runner == "grounded_answer_golden":
        answer_report = evaluate_grounded_answer_golden(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, answer_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=answer_report.dataset_id,
            model_id=answer_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=answer_report.case_count,
            metrics={
                "answerRelevance": answer_report.answer_relevance,
                "citationPrecision": answer_report.citation_precision,
                "groundedness": answer_report.groundedness,
                "hallucinationRate": answer_report.hallucination_rate,
                "refusalAccuracy": answer_report.refusal_accuracy,
                "unsafeAnswerRate": answer_report.unsafe_answer_rate,
            },
            passed=answer_report.passed,
            required=required,
        )

    if runner == "prompt_safety_golden":
        prompt_report = evaluate_prompt_safety_golden(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, prompt_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=prompt_report.dataset_id,
            model_id=prompt_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=prompt_report.case_count,
            metrics={
                "auditSafetyRate": prompt_report.audit_safety_rate,
                "costBudgetPassRate": prompt_report.cost_budget_pass_rate,
                "expectedTokenCoverage": prompt_report.expected_token_coverage,
                "humanReviewRate": prompt_report.human_review_rate,
                "piiRedactionRecall": prompt_report.pii_redaction_recall,
                "secretRedactionRecall": prompt_report.secret_redaction_recall,
                "tenantContextPassRate": prompt_report.tenant_context_pass_rate,
            },
            passed=prompt_report.passed,
            required=required,
        )

    if runner == "llm_adapter_shadow_gateway":
        shadow_report = evaluate_llm_adapter_shadow_golden(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, shadow_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=shadow_report.dataset_id,
            model_id=shadow_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=shadow_report.case_count,
            metrics={
                "allowedGenerationRate": shadow_report.allowed_generation_rate,
                "auditSafetyRate": shadow_report.audit_safety_rate,
                "blockedGenerationSkipRate": (
                    shadow_report.blocked_generation_skip_rate
                ),
                "citationPrecision": shadow_report.citation_precision,
                "contextFilterPassRate": shadow_report.context_filter_pass_rate,
                "gatewayEvaluationCount": shadow_report.gateway_evaluation_count,
                "groundedness": shadow_report.groundedness,
                "promptGatewayExpectedPassRate": (
                    shadow_report.prompt_gateway_expected_pass_rate
                ),
                "refusalAccuracy": shadow_report.refusal_accuracy,
            },
            passed=shadow_report.passed,
            required=required,
        )

    if runner == "vector_index_contract":
        vector_report = evaluate_vector_index_contract(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, vector_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=vector_report.dataset_id,
            model_id=vector_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=vector_report.case_count,
            metrics={
                "checksumStable": vector_report.checksum_stable,
                "chunkCoverageRate": vector_report.chunk_coverage_rate,
                "dimensionConformanceRate": vector_report.dimension_conformance_rate,
                "embeddingDimensions": vector_report.embedding_dimensions,
                "metadataConformanceRate": vector_report.metadata_conformance_rate,
                "tenantScopeCoverageRate": vector_report.tenant_scope_coverage_rate,
            },
            passed=vector_report.passed,
            required=required,
        )

    if runner == "hybrid_retrieval_shadow":
        hybrid_report = evaluate_hybrid_retrieval_shadow(
            root,
            require_str(row, "dataset", f"evaluation {evaluation_id}"),
        )
        ensure_runner_model_id(evaluation_id, model_id, hybrid_report.model_id)
        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            runner=runner,
            dataset_id=hybrid_report.dataset_id,
            model_id=hybrid_report.model_id,
            product=product,
            use_case_id=use_case_id,
            case_count=hybrid_report.case_count,
            metrics={
                "hybridNotWorseThanLexicalRate": (
                    hybrid_report.hybrid_not_worse_than_lexical_rate
                ),
                "hybridRecallAtK": hybrid_report.hybrid_recall_at_k,
                "k": hybrid_report.k,
                "lexicalRecallAtK": hybrid_report.lexical_recall_at_k,
                "tenantIsolationRate": hybrid_report.tenant_isolation_rate,
                "vectorRecallAtK": hybrid_report.vector_recall_at_k,
            },
            passed=hybrid_report.passed,
            required=required,
        )

    raise RegistryValidationError(f"unsupported evaluation runner: {runner}")


def evaluate_support_agent_assist(ai_root: Path | str) -> SupportAgentAssistEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(
        root / "platform" / "evaluation" / "datasets" / "support-agent-assist-golden.yaml"
    )
    dataset_id = require_str(dataset, "dataset_id", "support agent assist golden dataset")
    model_id = require_str(dataset, "model_id", "support agent assist golden dataset")
    thresholds = require_mapping(dataset, "thresholds", "support agent assist golden dataset")
    cases = require_list(dataset, "cases", "support agent assist golden dataset")
    if not cases:
        raise RegistryValidationError("support agent assist golden dataset must contain cases")

    module = load_module(
        root / "models" / "llm" / "support_agent_assist" / "support_agent_assist.py",
        "support_agent_assist_eval_module",
    )
    model_class = module.SupportAgentAssistBaseline
    input_class = module.SupportAgentAssistInput
    model = model_class()

    intent_correct = 0
    priority_correct = 0
    human_review_required = 0
    retrieval_terms_present = 0
    retrieval_terms_total = 0

    for row in cases:
        case_id = require_str(row, "case_id", "support golden case")
        input_payload = require_mapping(row, "input", f"support golden case {case_id}")
        expected = require_mapping(row, "expected", f"support golden case {case_id}")
        result = model.assist(input_class(**input_payload))

        if result.intent == require_str(expected, "intent", f"support golden case {case_id}"):
            intent_correct += 1
        if result.priority_signal == require_str(
            expected,
            "priority_signal",
            f"support golden case {case_id}",
        ):
            priority_correct += 1
        if bool(result.requires_human_review) is bool(expected.get("requires_human_review")):
            human_review_required += 1

        retrieval_terms = expected.get("retrieval_terms", [])
        if not isinstance(retrieval_terms, list):
            raise RegistryValidationError(
                f"support golden case {case_id} expected.retrieval_terms must be a list"
            )
        retrieval_query = result.retrieval_query.lower()
        for term in retrieval_terms:
            if not isinstance(term, str) or not term.strip():
                raise RegistryValidationError(
                    f"support golden case {case_id} retrieval term must be a string"
                )
            retrieval_terms_total += 1
            if term.lower() in retrieval_query:
                retrieval_terms_present += 1

    case_count = len(cases)
    intent_accuracy = ratio(intent_correct, case_count)
    priority_accuracy = ratio(priority_correct, case_count)
    human_review_rate = ratio(human_review_required, case_count)
    retrieval_required_term_coverage = ratio(retrieval_terms_present, retrieval_terms_total)
    passed = (
        intent_accuracy >= require_float(thresholds, "intent_accuracy_min", "thresholds")
        and priority_accuracy >= require_float(thresholds, "priority_accuracy_min", "thresholds")
        and human_review_rate >= require_float(thresholds, "human_review_rate_min", "thresholds")
        and retrieval_required_term_coverage
        >= require_float(thresholds, "retrieval_required_term_coverage_min", "thresholds")
    )

    return SupportAgentAssistEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        case_count=case_count,
        intent_accuracy=round(intent_accuracy, 6),
        priority_accuracy=round(priority_accuracy, 6),
        human_review_rate=round(human_review_rate, 6),
        retrieval_required_term_coverage=round(retrieval_required_term_coverage, 6),
        passed=passed,
    )


def evaluate_recommendation_item_cf(ai_root: Path | str) -> RecommendationItemCfEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(
        root / "platform" / "evaluation" / "datasets" / "recommendation-item-cf-golden.yaml"
    )
    dataset_id = require_str(dataset, "dataset_id", "recommendation item-CF golden dataset")
    model_id = require_str(dataset, "model_id", "recommendation item-CF golden dataset")
    config = require_mapping(dataset, "config", "recommendation item-CF golden dataset")
    thresholds = require_mapping(dataset, "thresholds", "recommendation item-CF golden dataset")
    interaction_rows = require_list(
        dataset,
        "interactions",
        "recommendation item-CF golden dataset",
    )
    query_rows = require_list(dataset, "queries", "recommendation item-CF golden dataset")
    if not query_rows:
        raise RegistryValidationError("recommendation item-CF golden dataset must contain queries")

    domain_module = import_service_module(root, "courseflow_ml.domain.recommendation")
    trainer_module = import_service_module(root, "courseflow_ml.training.implicit_cf")
    training_interaction_class = domain_module.TrainingInteraction
    trainer_class = trainer_module.ImplicitItemCfTrainer
    config_class = trainer_module.ImplicitCfConfig

    interactions = []
    for row in interaction_rows:
        principal_id = require_str(row, "principal_id", "recommendation golden interaction")
        course_id = parse_uuid(require_str(row, "course_id", "recommendation golden interaction"))
        event_type = require_str(row, "event_type", "recommendation golden interaction")
        interactions.append(
            training_interaction_class(
                principal_id=principal_id,
                course_id=course_id,
                event_type=event_type,
            )
        )

    k = require_int(config, "k", "recommendation item-CF config")
    trainer = trainer_class(
        config_class(
            min_support=require_int(config, "min_support", "recommendation item-CF config"),
            max_related_per_course=require_int(
                config,
                "max_related_per_course",
                "recommendation item-CF config",
            ),
        )
    )
    training_result = trainer.train(interactions)
    recommendations_by_course: dict[UUID, list[UUID]] = {}
    for recommendation in training_result.recommendations:
        recommendations_by_course.setdefault(recommendation.course_id, []).append(
            recommendation.related_course_id
        )

    recall_total = 0.0
    ndcg_total = 0.0
    covered_queries = 0
    for row in query_rows:
        course_id = parse_uuid(require_str(row, "course_id", "recommendation golden query"))
        relevant_rows = row.get("relevant_course_ids")
        if not isinstance(relevant_rows, list) or not relevant_rows:
            raise RegistryValidationError(
                "recommendation golden query must define relevant_course_ids"
            )
        relevant = {
            parse_uuid(str(related_course_id))
            for related_course_id in relevant_rows
        }
        ranked = recommendations_by_course.get(course_id, [])[:k]
        if ranked:
            covered_queries += 1
        hits = [1 if related_course_id in relevant else 0 for related_course_id in ranked]
        recall_total += sum(hits) / len(relevant)
        ndcg_total += ndcg_at_k(hits, min(k, len(relevant)))

    case_count = len(query_rows)
    recall_at_k = ratio_float(recall_total, case_count)
    ndcg = ratio_float(ndcg_total, case_count)
    catalog_coverage = ratio(covered_queries, case_count)
    passed = (
        recall_at_k >= require_float(thresholds, "recall_at_k_min", "thresholds")
        and ndcg >= require_float(thresholds, "ndcg_at_k_min", "thresholds")
        and catalog_coverage
        >= require_float(thresholds, "catalog_coverage_min", "thresholds")
    )

    return RecommendationItemCfEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        case_count=case_count,
        recall_at_k=round(recall_at_k, 6),
        ndcg_at_k=round(ndcg, 6),
        catalog_coverage=round(catalog_coverage, 6),
        k=k,
        passed=passed,
    )


def evaluate_sequence_risk_golden(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> SequenceRiskEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "sequence risk dataset")
    model_id = require_str(dataset, "model_id", "sequence risk dataset")
    module_path = require_str(dataset, "module", "sequence risk dataset")
    feature_contract = require_str(dataset, "feature_contract", "sequence risk dataset")
    model_io_contract = require_str(dataset, "model_io_contract", "sequence risk dataset")
    for linked_path in (module_path, feature_contract, model_io_contract):
        if not (root / linked_path).exists():
            raise RegistryValidationError(
                f"sequence risk linked artifact does not exist: {linked_path}"
            )

    thresholds = require_mapping(dataset, "thresholds", "sequence risk dataset")
    cases = require_list(dataset, "cases", "sequence risk dataset")
    if not cases:
        raise RegistryValidationError("sequence risk dataset must contain cases")

    module = load_module(root / module_path, "sequence_risk_baseline_eval_module")
    model = module.SequenceRiskBaseline()

    band_correct = 0
    score_threshold_passed = 0
    reason_hits = 0
    reason_total = 0
    ranked_cases: list[tuple[int, float, str]] = []

    for row in cases:
        case_id = require_str(row, "case_id", "sequence risk case")
        input_payload = require_mapping(row, "input", f"sequence risk case {case_id}")
        expected = require_mapping(row, "expected", f"sequence risk case {case_id}")
        prediction = model.predict(input_payload)
        if prediction.model_id != model_id:
            raise RegistryValidationError(
                f"sequence risk model_id {prediction.model_id} does not match {model_id}"
            )

        expected_band = require_str(expected, "risk_band", f"sequence risk case {case_id}")
        if prediction.risk_band == expected_band:
            band_correct += 1

        min_score = expected.get("min_risk_score")
        max_score = expected.get("max_risk_score")
        if min_score is not None and not isinstance(min_score, int | float):
            raise RegistryValidationError(
                f"sequence risk case {case_id} min_risk_score must be numeric"
            )
        if max_score is not None and not isinstance(max_score, int | float):
            raise RegistryValidationError(
                f"sequence risk case {case_id} max_risk_score must be numeric"
            )
        score_above_min = min_score is None or prediction.risk_score >= float(min_score)
        score_below_max = max_score is None or prediction.risk_score < float(max_score)
        if score_above_min and score_below_max:
            score_threshold_passed += 1

        expected_reasons = require_string_list(
            expected,
            "reason_codes",
            f"sequence risk case {case_id}",
        )
        predicted_reasons = set(prediction.reason_codes)
        reason_total += len(expected_reasons)
        reason_hits += sum(1 for reason in expected_reasons if reason in predicted_reasons)
        ranked_cases.append(
            (
                require_int(expected, "risk_order", f"sequence risk case {case_id}"),
                prediction.risk_score,
                case_id,
            )
        )

    case_count = len(cases)
    risk_band_accuracy = ratio(band_correct, case_count)
    score_threshold_pass_rate = ratio(score_threshold_passed, case_count)
    reason_code_recall = ratio(reason_hits, reason_total)
    risk_ordering_pass_rate = pairwise_risk_ordering_pass_rate(ranked_cases)
    passed = (
        risk_band_accuracy
        >= require_float(thresholds, "risk_band_accuracy_min", "sequence risk thresholds")
        and reason_code_recall
        >= require_float(thresholds, "reason_code_recall_min", "sequence risk thresholds")
        and score_threshold_pass_rate
        >= require_float(
            thresholds,
            "score_threshold_pass_rate_min",
            "sequence risk thresholds",
        )
        and risk_ordering_pass_rate
        >= require_float(thresholds, "risk_ordering_pass_rate_min", "sequence risk thresholds")
    )

    return SequenceRiskEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        case_count=case_count,
        risk_band_accuracy=round(risk_band_accuracy, 6),
        reason_code_recall=round(reason_code_recall, 6),
        score_threshold_pass_rate=round(score_threshold_pass_rate, 6),
        risk_ordering_pass_rate=round(risk_ordering_pass_rate, 6),
        passed=passed,
    )


def evaluate_support_sla_risk_golden(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> SupportSlaRiskEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "support SLA risk dataset")
    model_id = require_str(dataset, "model_id", "support SLA risk dataset")
    module_path = require_str(dataset, "module", "support SLA risk dataset")
    feature_contract = require_str(dataset, "feature_contract", "support SLA risk dataset")
    model_io_contract = require_str(dataset, "model_io_contract", "support SLA risk dataset")
    for linked_path in (module_path, feature_contract, model_io_contract):
        if not (root / linked_path).exists():
            raise RegistryValidationError(
                f"support SLA risk linked artifact does not exist: {linked_path}"
            )

    thresholds = require_mapping(dataset, "thresholds", "support SLA risk dataset")
    cases = require_list(dataset, "cases", "support SLA risk dataset")
    if not cases:
        raise RegistryValidationError("support SLA risk dataset must contain cases")

    module = load_module(root / module_path, "support_sla_risk_baseline_eval_module")
    model = module.SupportSlaRiskBaseline()

    band_correct = 0
    score_threshold_passed = 0
    reason_hits = 0
    reason_total = 0
    human_review_policy_passed = 0
    ranked_cases: list[tuple[int, float, str]] = []

    for row in cases:
        case_id = require_str(row, "case_id", "support SLA risk case")
        input_payload = require_mapping(row, "input", f"support SLA risk case {case_id}")
        expected = require_mapping(row, "expected", f"support SLA risk case {case_id}")
        prediction = model.predict(input_payload)
        if prediction.model_id != model_id:
            raise RegistryValidationError(
                f"support SLA risk model_id {prediction.model_id} does not match {model_id}"
            )

        expected_band = require_str(expected, "risk_band", f"support SLA risk case {case_id}")
        if prediction.risk_band == expected_band:
            band_correct += 1

        min_score = expected.get("min_risk_score")
        max_score = expected.get("max_risk_score")
        if min_score is not None and not isinstance(min_score, int | float):
            raise RegistryValidationError(
                f"support SLA risk case {case_id} min_risk_score must be numeric"
            )
        if max_score is not None and not isinstance(max_score, int | float):
            raise RegistryValidationError(
                f"support SLA risk case {case_id} max_risk_score must be numeric"
            )
        score_above_min = min_score is None or prediction.risk_score >= float(min_score)
        score_below_max = max_score is None or prediction.risk_score < float(max_score)
        if score_above_min and score_below_max:
            score_threshold_passed += 1

        expected_reasons = require_string_list(
            expected,
            "reason_codes",
            f"support SLA risk case {case_id}",
        )
        predicted_reasons = set(prediction.reason_codes)
        reason_total += len(expected_reasons)
        reason_hits += sum(1 for reason in expected_reasons if reason in predicted_reasons)

        expected_review = require_bool(
            expected,
            "requires_human_review",
            f"support SLA risk case {case_id}",
        )
        if bool(prediction.requires_human_review) is expected_review:
            human_review_policy_passed += 1

        ranked_cases.append(
            (
                require_int(expected, "risk_order", f"support SLA risk case {case_id}"),
                prediction.risk_score,
                case_id,
            )
        )

    case_count = len(cases)
    risk_band_accuracy = ratio(band_correct, case_count)
    score_threshold_pass_rate = ratio(score_threshold_passed, case_count)
    reason_code_recall = ratio(reason_hits, reason_total)
    human_review_policy_pass_rate = ratio(human_review_policy_passed, case_count)
    risk_ordering_pass_rate = pairwise_risk_ordering_pass_rate(ranked_cases)
    passed = (
        risk_band_accuracy
        >= require_float(thresholds, "risk_band_accuracy_min", "support SLA risk thresholds")
        and reason_code_recall
        >= require_float(thresholds, "reason_code_recall_min", "support SLA risk thresholds")
        and human_review_policy_pass_rate
        >= require_float(
            thresholds,
            "human_review_policy_pass_rate_min",
            "support SLA risk thresholds",
        )
        and score_threshold_pass_rate
        >= require_float(
            thresholds,
            "score_threshold_pass_rate_min",
            "support SLA risk thresholds",
        )
        and risk_ordering_pass_rate
        >= require_float(
            thresholds,
            "risk_ordering_pass_rate_min",
            "support SLA risk thresholds",
        )
    )

    return SupportSlaRiskEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        case_count=case_count,
        risk_band_accuracy=round(risk_band_accuracy, 6),
        reason_code_recall=round(reason_code_recall, 6),
        human_review_policy_pass_rate=round(human_review_policy_pass_rate, 6),
        score_threshold_pass_rate=round(score_threshold_pass_rate, 6),
        risk_ordering_pass_rate=round(risk_ordering_pass_rate, 6),
        passed=passed,
    )


def evaluate_payment_fraud_risk_golden(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> PaymentFraudRiskEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "payment fraud risk dataset")
    model_id = require_str(dataset, "model_id", "payment fraud risk dataset")
    module_path = require_str(dataset, "module", "payment fraud risk dataset")
    feature_contract = require_str(dataset, "feature_contract", "payment fraud risk dataset")
    model_io_contract = require_str(dataset, "model_io_contract", "payment fraud risk dataset")
    for linked_path in (module_path, feature_contract, model_io_contract):
        if not (root / linked_path).exists():
            raise RegistryValidationError(
                f"payment fraud risk linked artifact does not exist: {linked_path}"
            )

    thresholds = require_mapping(dataset, "thresholds", "payment fraud risk dataset")
    cases = require_list(dataset, "cases", "payment fraud risk dataset")
    if not cases:
        raise RegistryValidationError("payment fraud risk dataset must contain cases")

    module = load_module(root / module_path, "payment_fraud_risk_eval_module")
    model = module.PaymentFraudRiskBaseline()

    band_correct = 0
    score_threshold_passed = 0
    reason_hits = 0
    reason_total = 0
    entity_link_hits = 0
    entity_link_total = 0
    human_review_policy_passed = 0
    ranked_cases: list[tuple[int, float, str]] = []

    for row in cases:
        case_id = require_str(row, "case_id", "payment fraud risk case")
        input_payload = require_mapping(row, "input", f"payment fraud risk case {case_id}")
        expected = require_mapping(row, "expected", f"payment fraud risk case {case_id}")
        prediction = model.predict(input_payload)
        if prediction.model_id != model_id:
            raise RegistryValidationError(
                f"payment fraud risk model_id {prediction.model_id} does not match {model_id}"
            )

        expected_band = require_str(
            expected,
            "risk_band",
            f"payment fraud risk case {case_id}",
        )
        if prediction.risk_band == expected_band:
            band_correct += 1

        min_score = expected.get("min_risk_score")
        max_score = expected.get("max_risk_score")
        if min_score is not None and not isinstance(min_score, int | float):
            raise RegistryValidationError(
                f"payment fraud risk case {case_id} min_risk_score must be numeric"
            )
        if max_score is not None and not isinstance(max_score, int | float):
            raise RegistryValidationError(
                f"payment fraud risk case {case_id} max_risk_score must be numeric"
            )
        score_above_min = min_score is None or prediction.risk_score >= float(min_score)
        score_below_max = max_score is None or prediction.risk_score < float(max_score)
        if score_above_min and score_below_max:
            score_threshold_passed += 1

        expected_reasons = require_string_list(
            expected,
            "reason_codes",
            f"payment fraud risk case {case_id}",
        )
        predicted_reasons = set(prediction.reason_codes)
        reason_total += len(expected_reasons)
        reason_hits += sum(1 for reason in expected_reasons if reason in predicted_reasons)

        expected_entity_links = require_string_list(
            expected,
            "entity_link_types",
            f"payment fraud risk case {case_id}",
        )
        predicted_entity_links = {
            evidence.link_type for evidence in prediction.entity_link_evidence
        }
        entity_link_total += len(expected_entity_links)
        entity_link_hits += sum(
            1 for link_type in expected_entity_links if link_type in predicted_entity_links
        )

        expected_review = require_bool(
            expected,
            "requires_human_review",
            f"payment fraud risk case {case_id}",
        )
        expected_automated_action = require_bool(
            expected,
            "automated_adverse_action_allowed",
            f"payment fraud risk case {case_id}",
        )
        if (
            bool(prediction.requires_human_review) is expected_review
            and bool(prediction.automated_adverse_action_allowed)
            is expected_automated_action
        ):
            human_review_policy_passed += 1

        ranked_cases.append(
            (
                require_int(expected, "risk_order", f"payment fraud risk case {case_id}"),
                prediction.risk_score,
                case_id,
            )
        )

    case_count = len(cases)
    risk_band_accuracy = ratio(band_correct, case_count)
    score_threshold_pass_rate = ratio(score_threshold_passed, case_count)
    reason_code_recall = ratio(reason_hits, reason_total)
    entity_link_recall = ratio(entity_link_hits, entity_link_total)
    human_review_policy_pass_rate = ratio(human_review_policy_passed, case_count)
    risk_ordering_pass_rate = pairwise_risk_ordering_pass_rate(ranked_cases)
    passed = (
        risk_band_accuracy
        >= require_float(thresholds, "risk_band_accuracy_min", "payment fraud risk thresholds")
        and reason_code_recall
        >= require_float(thresholds, "reason_code_recall_min", "payment fraud risk thresholds")
        and entity_link_recall
        >= require_float(thresholds, "entity_link_recall_min", "payment fraud risk thresholds")
        and human_review_policy_pass_rate
        >= require_float(
            thresholds,
            "human_review_policy_pass_rate_min",
            "payment fraud risk thresholds",
        )
        and score_threshold_pass_rate
        >= require_float(
            thresholds,
            "score_threshold_pass_rate_min",
            "payment fraud risk thresholds",
        )
        and risk_ordering_pass_rate
        >= require_float(
            thresholds,
            "risk_ordering_pass_rate_min",
            "payment fraud risk thresholds",
        )
    )

    return PaymentFraudRiskEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        case_count=case_count,
        risk_band_accuracy=round(risk_band_accuracy, 6),
        reason_code_recall=round(reason_code_recall, 6),
        entity_link_recall=round(entity_link_recall, 6),
        human_review_policy_pass_rate=round(human_review_policy_pass_rate, 6),
        score_threshold_pass_rate=round(score_threshold_pass_rate, 6),
        risk_ordering_pass_rate=round(risk_ordering_pass_rate, 6),
        passed=passed,
    )


def evaluate_demand_forecast_golden(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> DemandForecastEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "demand forecast dataset")
    model_id = require_str(dataset, "model_id", "demand forecast dataset")
    module_path = require_str(dataset, "module", "demand forecast dataset")
    feature_contract = require_str(dataset, "feature_contract", "demand forecast dataset")
    model_io_contract = require_str(dataset, "model_io_contract", "demand forecast dataset")
    for linked_path in (module_path, feature_contract, model_io_contract):
        if not (root / linked_path).exists():
            raise RegistryValidationError(
                f"demand forecast linked artifact does not exist: {linked_path}"
            )

    thresholds = require_mapping(dataset, "thresholds", "demand forecast dataset")
    cases = require_list(dataset, "cases", "demand forecast dataset")
    if not cases:
        raise RegistryValidationError("demand forecast dataset must contain cases")

    module = load_module(root / module_path, "demand_forecast_eval_module")
    model = module.DemandForecastBaseline()

    band_correct = 0
    staffing_correct = 0
    reason_hits = 0
    reason_total = 0
    forecast_threshold_passed = 0
    human_review_policy_passed = 0
    ranked_cases: list[tuple[int, float, str]] = []

    for row in cases:
        case_id = require_str(row, "case_id", "demand forecast case")
        input_payload = require_mapping(row, "input", f"demand forecast case {case_id}")
        expected = require_mapping(row, "expected", f"demand forecast case {case_id}")
        prediction = model.predict(input_payload)
        if prediction.model_id != model_id:
            raise RegistryValidationError(
                f"demand forecast model_id {prediction.model_id} does not match {model_id}"
            )

        expected_band = require_str(
            expected,
            "demand_band",
            f"demand forecast case {case_id}",
        )
        if prediction.demand_band == expected_band:
            band_correct += 1

        expected_recommendation = require_str(
            expected,
            "staffing_recommendation",
            f"demand forecast case {case_id}",
        )
        if prediction.staffing_recommendation == expected_recommendation:
            staffing_correct += 1

        min_forecast = expected.get("min_forecast_units")
        max_forecast = expected.get("max_forecast_units")
        if min_forecast is not None and not isinstance(min_forecast, int | float):
            raise RegistryValidationError(
                f"demand forecast case {case_id} min_forecast_units must be numeric"
            )
        if max_forecast is not None and not isinstance(max_forecast, int | float):
            raise RegistryValidationError(
                f"demand forecast case {case_id} max_forecast_units must be numeric"
            )
        forecast_above_min = (
            min_forecast is None or prediction.forecast_units >= float(min_forecast)
        )
        forecast_below_max = (
            max_forecast is None or prediction.forecast_units <= float(max_forecast)
        )
        if forecast_above_min and forecast_below_max:
            forecast_threshold_passed += 1

        expected_reasons = require_string_list(
            expected,
            "reason_codes",
            f"demand forecast case {case_id}",
        )
        predicted_reasons = set(prediction.reason_codes)
        reason_total += len(expected_reasons)
        reason_hits += sum(1 for reason in expected_reasons if reason in predicted_reasons)

        expected_review = require_bool(
            expected,
            "requires_human_review",
            f"demand forecast case {case_id}",
        )
        if bool(prediction.requires_human_review) is expected_review:
            human_review_policy_passed += 1

        ranked_cases.append(
            (
                require_int(expected, "forecast_order", f"demand forecast case {case_id}"),
                float(prediction.forecast_units),
                case_id,
            )
        )

    case_count = len(cases)
    demand_band_accuracy = ratio(band_correct, case_count)
    staffing_recommendation_accuracy = ratio(staffing_correct, case_count)
    reason_code_recall = ratio(reason_hits, reason_total)
    forecast_threshold_pass_rate = ratio(forecast_threshold_passed, case_count)
    human_review_policy_pass_rate = ratio(human_review_policy_passed, case_count)
    forecast_ordering_pass_rate = pairwise_risk_ordering_pass_rate(ranked_cases)
    passed = (
        demand_band_accuracy
        >= require_float(
            thresholds,
            "demand_band_accuracy_min",
            "demand forecast thresholds",
        )
        and staffing_recommendation_accuracy
        >= require_float(
            thresholds,
            "staffing_recommendation_accuracy_min",
            "demand forecast thresholds",
        )
        and reason_code_recall
        >= require_float(
            thresholds,
            "reason_code_recall_min",
            "demand forecast thresholds",
        )
        and forecast_threshold_pass_rate
        >= require_float(
            thresholds,
            "forecast_threshold_pass_rate_min",
            "demand forecast thresholds",
        )
        and human_review_policy_pass_rate
        >= require_float(
            thresholds,
            "human_review_policy_pass_rate_min",
            "demand forecast thresholds",
        )
        and forecast_ordering_pass_rate
        >= require_float(
            thresholds,
            "forecast_ordering_pass_rate_min",
            "demand forecast thresholds",
        )
    )

    return DemandForecastEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        case_count=case_count,
        demand_band_accuracy=round(demand_band_accuracy, 6),
        staffing_recommendation_accuracy=round(staffing_recommendation_accuracy, 6),
        reason_code_recall=round(reason_code_recall, 6),
        forecast_threshold_pass_rate=round(forecast_threshold_pass_rate, 6),
        human_review_policy_pass_rate=round(human_review_policy_pass_rate, 6),
        forecast_ordering_pass_rate=round(forecast_ordering_pass_rate, 6),
        passed=passed,
    )


def evaluate_causal_uplift_golden(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> CausalUpliftEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "causal uplift dataset")
    model_id = require_str(dataset, "model_id", "causal uplift dataset")
    module_path = require_str(dataset, "module", "causal uplift dataset")
    feature_contract = require_str(dataset, "feature_contract", "causal uplift dataset")
    model_io_contract = require_str(dataset, "model_io_contract", "causal uplift dataset")
    for linked_path in (module_path, feature_contract, model_io_contract):
        if not (root / linked_path).exists():
            raise RegistryValidationError(
                f"causal uplift linked artifact does not exist: {linked_path}"
            )

    thresholds = require_mapping(dataset, "thresholds", "causal uplift dataset")
    cases = require_list(dataset, "cases", "causal uplift dataset")
    if not cases:
        raise RegistryValidationError("causal uplift dataset must contain cases")

    module = load_module(root / module_path, "causal_uplift_eval_module")
    model = module.CausalUpliftBaseline()

    decision_correct = 0
    recommendation_correct = 0
    reason_hits = 0
    reason_total = 0
    human_review_policy_passed = 0
    guardrail_stop_passed = 0
    deterministic_replay_passed = 0

    for row in cases:
        case_id = require_str(row, "case_id", "causal uplift case")
        input_payload = require_mapping(row, "input", f"causal uplift case {case_id}")
        expected = require_mapping(row, "expected", f"causal uplift case {case_id}")
        prediction = model.predict(input_payload)
        replay_prediction = model.predict(input_payload)
        if prediction.model_id != model_id:
            raise RegistryValidationError(
                f"causal uplift model_id {prediction.model_id} does not match {model_id}"
            )
        if prediction.to_dict() == replay_prediction.to_dict():
            deterministic_replay_passed += 1

        expected_band = require_str(
            expected,
            "decision_band",
            f"causal uplift case {case_id}",
        )
        if prediction.decision_band == expected_band:
            decision_correct += 1

        expected_recommendation = require_str(
            expected,
            "recommendation",
            f"causal uplift case {case_id}",
        )
        if prediction.recommendation == expected_recommendation:
            recommendation_correct += 1

        min_lift = expected.get("min_absolute_lift")
        max_lift = expected.get("max_absolute_lift")
        if min_lift is not None and not isinstance(min_lift, int | float):
            raise RegistryValidationError(
                f"causal uplift case {case_id} min_absolute_lift must be numeric"
            )
        if max_lift is not None and not isinstance(max_lift, int | float):
            raise RegistryValidationError(
                f"causal uplift case {case_id} max_absolute_lift must be numeric"
            )
        if min_lift is not None and prediction.absolute_lift < float(min_lift):
            raise RegistryValidationError(
                f"causal uplift case {case_id} absolute_lift below expected minimum"
            )
        if max_lift is not None and prediction.absolute_lift > float(max_lift):
            raise RegistryValidationError(
                f"causal uplift case {case_id} absolute_lift above expected maximum"
            )

        expected_reasons = require_string_list(
            expected,
            "reason_codes",
            f"causal uplift case {case_id}",
        )
        predicted_reasons = set(prediction.reason_codes)
        reason_total += len(expected_reasons)
        reason_hits += sum(1 for reason in expected_reasons if reason in predicted_reasons)

        expected_review = require_bool(
            expected,
            "requires_human_review",
            f"causal uplift case {case_id}",
        )
        if bool(prediction.requires_human_review) is expected_review:
            human_review_policy_passed += 1

        guardrail_delta = input_payload.get("guardrail_metric_delta", 0.0)
        if not isinstance(guardrail_delta, int | float):
            raise RegistryValidationError(
                f"causal uplift case {case_id} guardrail_metric_delta must be numeric"
            )
        if float(guardrail_delta) <= -0.02:
            if prediction.recommendation == "stop_or_redesign":
                guardrail_stop_passed += 1
        else:
            guardrail_stop_passed += 1

    case_count = len(cases)
    decision_band_accuracy = ratio(decision_correct, case_count)
    recommendation_accuracy = ratio(recommendation_correct, case_count)
    reason_code_recall = ratio(reason_hits, reason_total)
    human_review_policy_pass_rate = ratio(human_review_policy_passed, case_count)
    guardrail_stop_pass_rate = ratio(guardrail_stop_passed, case_count)
    deterministic_replay_rate = ratio(deterministic_replay_passed, case_count)
    passed = (
        decision_band_accuracy
        >= require_float(
            thresholds,
            "decision_band_accuracy_min",
            "causal uplift thresholds",
        )
        and recommendation_accuracy
        >= require_float(
            thresholds,
            "recommendation_accuracy_min",
            "causal uplift thresholds",
        )
        and reason_code_recall
        >= require_float(
            thresholds,
            "reason_code_recall_min",
            "causal uplift thresholds",
        )
        and human_review_policy_pass_rate
        >= require_float(
            thresholds,
            "human_review_policy_pass_rate_min",
            "causal uplift thresholds",
        )
        and guardrail_stop_pass_rate
        >= require_float(
            thresholds,
            "guardrail_stop_pass_rate_min",
            "causal uplift thresholds",
        )
        and deterministic_replay_rate
        >= require_float(
            thresholds,
            "deterministic_replay_rate_min",
            "causal uplift thresholds",
        )
    )

    return CausalUpliftEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        case_count=case_count,
        decision_band_accuracy=round(decision_band_accuracy, 6),
        recommendation_accuracy=round(recommendation_accuracy, 6),
        reason_code_recall=round(reason_code_recall, 6),
        human_review_policy_pass_rate=round(human_review_policy_pass_rate, 6),
        guardrail_stop_pass_rate=round(guardrail_stop_pass_rate, 6),
        deterministic_replay_rate=round(deterministic_replay_rate, 6),
        passed=passed,
    )


def evaluate_document_intelligence_golden(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> DocumentIntelligenceEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "document intelligence dataset")
    model_id = require_str(dataset, "model_id", "document intelligence dataset")
    module_path = require_str(dataset, "module", "document intelligence dataset")
    feature_contract = require_str(dataset, "feature_contract", "document intelligence dataset")
    model_io_contract = require_str(dataset, "model_io_contract", "document intelligence dataset")
    for linked_path in (module_path, feature_contract, model_io_contract):
        if not (root / linked_path).exists():
            raise RegistryValidationError(
                f"document intelligence linked artifact does not exist: {linked_path}"
            )

    thresholds = require_mapping(dataset, "thresholds", "document intelligence dataset")
    cases = require_list(dataset, "cases", "document intelligence dataset")
    if not cases:
        raise RegistryValidationError("document intelligence dataset must contain cases")

    module = load_module(root / module_path, "document_intelligence_baseline_eval_module")
    model = module.DocumentIntelligenceBaseline()

    type_correct = 0
    fields_present = 0
    fields_total = 0
    evidence_present = 0
    evidence_total = 0
    human_review_policy_passed = 0
    privacy_guardrail_passed = 0

    for row in cases:
        case_id = require_str(row, "case_id", "document intelligence case")
        input_payload = require_mapping(row, "input", f"document intelligence case {case_id}")
        expected = require_mapping(row, "expected", f"document intelligence case {case_id}")
        prediction = model.predict(input_payload)
        if prediction.model_id != model_id:
            raise RegistryValidationError(
                f"document intelligence model_id {prediction.model_id} does not match {model_id}"
            )

        expected_type = require_str(
            expected,
            "document_type",
            f"document intelligence case {case_id}",
        )
        if prediction.document_type == expected_type:
            type_correct += 1

        expected_fields = require_mapping(
            expected,
            "fields",
            f"document intelligence case {case_id}",
        )
        for key, expected_value in expected_fields.items():
            if not isinstance(expected_value, str):
                raise RegistryValidationError(
                    f"document intelligence case {case_id} expected field {key} must be string"
                )
            fields_total += 1
            if prediction.extracted_fields.get(key) == expected_value:
                fields_present += 1

        expected_evidence_terms = require_string_list_allow_empty(
            expected,
            "evidence_terms",
            f"document intelligence case {case_id}",
        )
        predicted_evidence = {term.lower() for term in prediction.evidence_terms}
        for term in expected_evidence_terms:
            evidence_total += 1
            if term.lower() in predicted_evidence:
                evidence_present += 1

        expected_review = require_bool(
            expected,
            "requires_human_review",
            f"document intelligence case {case_id}",
        )
        if bool(prediction.requires_human_review) is expected_review:
            human_review_policy_passed += 1

        expected_privacy_guardrail = require_str(
            expected,
            "privacy_guardrail",
            f"document intelligence case {case_id}",
        )
        if document_privacy_guardrail_passed(expected_privacy_guardrail, prediction):
            privacy_guardrail_passed += 1

        for reason in expected.get("reason_codes", []):
            if not isinstance(reason, str) or reason not in prediction.reason_codes:
                raise RegistryValidationError(
                    f"document intelligence case {case_id} missing reason: {reason}"
                )

    case_count = len(cases)
    document_type_accuracy = ratio(type_correct, case_count)
    field_recall = ratio(fields_present, fields_total)
    evidence_term_recall = ratio(evidence_present, evidence_total)
    human_review_policy_pass_rate = ratio(human_review_policy_passed, case_count)
    privacy_guardrail_pass_rate = ratio(privacy_guardrail_passed, case_count)
    passed = (
        document_type_accuracy
        >= require_float(
            thresholds,
            "document_type_accuracy_min",
            "document intelligence thresholds",
        )
        and field_recall
        >= require_float(thresholds, "field_recall_min", "document intelligence thresholds")
        and evidence_term_recall
        >= require_float(
            thresholds,
            "evidence_term_recall_min",
            "document intelligence thresholds",
        )
        and human_review_policy_pass_rate
        >= require_float(
            thresholds,
            "human_review_policy_pass_rate_min",
            "document intelligence thresholds",
        )
        and privacy_guardrail_pass_rate
        >= require_float(
            thresholds,
            "privacy_guardrail_pass_rate_min",
            "document intelligence thresholds",
        )
    )

    return DocumentIntelligenceEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        case_count=case_count,
        document_type_accuracy=round(document_type_accuracy, 6),
        field_recall=round(field_recall, 6),
        evidence_term_recall=round(evidence_term_recall, 6),
        human_review_policy_pass_rate=round(human_review_policy_pass_rate, 6),
        privacy_guardrail_pass_rate=round(privacy_guardrail_pass_rate, 6),
        passed=passed,
    )


def document_privacy_guardrail_passed(
    expected_privacy_guardrail: str,
    prediction: Any,
) -> bool:
    has_raw_pii_signal = "RAW_FINANCIAL_PII_DETECTED" in prediction.reason_codes
    if expected_privacy_guardrail == "safe":
        return not has_raw_pii_signal
    if expected_privacy_guardrail == "raw_pii_detected":
        return has_raw_pii_signal and bool(prediction.requires_human_review)
    raise RegistryValidationError(
        f"unsupported document privacy guardrail: {expected_privacy_guardrail}"
    )


def evaluate_speech_quality_golden(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> SpeechQualityEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "speech quality dataset")
    model_id = require_str(dataset, "model_id", "speech quality dataset")
    module_path = require_str(dataset, "module", "speech quality dataset")
    feature_contract = require_str(dataset, "feature_contract", "speech quality dataset")
    model_io_contract = require_str(dataset, "model_io_contract", "speech quality dataset")
    for linked_path in (module_path, feature_contract, model_io_contract):
        if not (root / linked_path).exists():
            raise RegistryValidationError(
                f"speech quality linked artifact does not exist: {linked_path}"
            )

    thresholds = require_mapping(dataset, "thresholds", "speech quality dataset")
    cases = require_list(dataset, "cases", "speech quality dataset")
    if not cases:
        raise RegistryValidationError("speech quality dataset must contain cases")

    module = load_module(root / module_path, "speech_quality_baseline_eval_module")
    model = module.AudioQualityBaseline()

    intent_correct = 0
    quality_correct = 0
    reason_present = 0
    reason_total = 0
    evidence_present = 0
    evidence_total = 0
    human_review_policy_passed = 0
    privacy_guardrail_passed = 0

    for row in cases:
        case_id = require_str(row, "case_id", "speech quality case")
        input_payload = require_mapping(row, "input", f"speech quality case {case_id}")
        expected = require_mapping(row, "expected", f"speech quality case {case_id}")
        prediction = model.predict(input_payload)
        if prediction.model_id != model_id:
            raise RegistryValidationError(
                f"speech quality model_id {prediction.model_id} does not match {model_id}"
            )

        expected_intent = require_str(expected, "intent", f"speech quality case {case_id}")
        if prediction.intent == expected_intent:
            intent_correct += 1

        expected_quality = require_str(
            expected,
            "quality_band",
            f"speech quality case {case_id}",
        )
        if prediction.quality_band == expected_quality:
            quality_correct += 1

        expected_reason_codes = require_string_list_allow_empty(
            expected,
            "reason_codes",
            f"speech quality case {case_id}",
        )
        for reason in expected_reason_codes:
            reason_total += 1
            if reason in prediction.reason_codes:
                reason_present += 1

        expected_evidence_terms = require_string_list_allow_empty(
            expected,
            "evidence_terms",
            f"speech quality case {case_id}",
        )
        predicted_evidence = {term.lower() for term in prediction.evidence_terms}
        for term in expected_evidence_terms:
            evidence_total += 1
            if term.lower() in predicted_evidence:
                evidence_present += 1

        expected_review = require_bool(
            expected,
            "requires_human_review",
            f"speech quality case {case_id}",
        )
        if bool(prediction.requires_human_review) is expected_review:
            human_review_policy_passed += 1

        expected_privacy_guardrail = require_str(
            expected,
            "privacy_guardrail",
            f"speech quality case {case_id}",
        )
        if speech_privacy_guardrail_passed(expected_privacy_guardrail, prediction):
            privacy_guardrail_passed += 1

    case_count = len(cases)
    intent_accuracy = ratio(intent_correct, case_count)
    quality_band_accuracy = ratio(quality_correct, case_count)
    reason_code_recall = ratio(reason_present, reason_total)
    evidence_term_recall = ratio(evidence_present, evidence_total)
    human_review_policy_pass_rate = ratio(human_review_policy_passed, case_count)
    privacy_guardrail_pass_rate = ratio(privacy_guardrail_passed, case_count)
    passed = (
        intent_accuracy
        >= require_float(thresholds, "intent_accuracy_min", "speech quality thresholds")
        and quality_band_accuracy
        >= require_float(
            thresholds,
            "quality_band_accuracy_min",
            "speech quality thresholds",
        )
        and reason_code_recall
        >= require_float(thresholds, "reason_code_recall_min", "speech quality thresholds")
        and evidence_term_recall
        >= require_float(
            thresholds,
            "evidence_term_recall_min",
            "speech quality thresholds",
        )
        and human_review_policy_pass_rate
        >= require_float(
            thresholds,
            "human_review_policy_pass_rate_min",
            "speech quality thresholds",
        )
        and privacy_guardrail_pass_rate
        >= require_float(
            thresholds,
            "privacy_guardrail_pass_rate_min",
            "speech quality thresholds",
        )
    )

    return SpeechQualityEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        case_count=case_count,
        intent_accuracy=round(intent_accuracy, 6),
        quality_band_accuracy=round(quality_band_accuracy, 6),
        reason_code_recall=round(reason_code_recall, 6),
        evidence_term_recall=round(evidence_term_recall, 6),
        human_review_policy_pass_rate=round(human_review_policy_pass_rate, 6),
        privacy_guardrail_pass_rate=round(privacy_guardrail_pass_rate, 6),
        passed=passed,
    )


def speech_privacy_guardrail_passed(
    expected_privacy_guardrail: str,
    prediction: Any,
) -> bool:
    has_raw_pii_signal = "RAW_AUDIO_PII_DETECTED" in prediction.reason_codes
    if expected_privacy_guardrail == "safe":
        return not has_raw_pii_signal
    if expected_privacy_guardrail == "raw_pii_detected":
        return has_raw_pii_signal and bool(prediction.requires_human_review)
    raise RegistryValidationError(
        f"unsupported speech privacy guardrail: {expected_privacy_guardrail}"
    )


def evaluate_routing_policy_simulator_golden(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> RoutingPolicyEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "routing policy dataset")
    model_id = require_str(dataset, "model_id", "routing policy dataset")
    module_path = require_str(dataset, "module", "routing policy dataset")
    feature_contract = require_str(dataset, "feature_contract", "routing policy dataset")
    model_io_contract = require_str(dataset, "model_io_contract", "routing policy dataset")
    for linked_path in (module_path, feature_contract, model_io_contract):
        if not (root / linked_path).exists():
            raise RegistryValidationError(
                f"routing policy linked artifact does not exist: {linked_path}"
            )

    thresholds = require_mapping(dataset, "thresholds", "routing policy dataset")
    cases = require_list(dataset, "cases", "routing policy dataset")
    if not cases:
        raise RegistryValidationError("routing policy dataset must contain cases")

    module = load_module(root / module_path, "routing_policy_simulator_eval_module")
    simulator = module.RoutingPolicySimulator()

    assignment_correct = 0
    constraint_passed = 0
    baseline_lift_passed = 0
    reason_hits = 0
    reason_total = 0
    exploration_budget_passed = 0
    deterministic_replay_passed = 0

    for row in cases:
        case_id = require_str(row, "case_id", "routing policy case")
        input_payload = require_mapping(row, "input", f"routing policy case {case_id}")
        expected = require_mapping(row, "expected", f"routing policy case {case_id}")
        decision = simulator.recommend(input_payload)
        replay = simulator.recommend(input_payload)
        if decision.model_id != model_id:
            raise RegistryValidationError(
                f"routing policy model_id {decision.model_id} does not match {model_id}"
            )
        if decision.to_dict() == replay.to_dict():
            deterministic_replay_passed += 1

        expected_queue = require_str(
            expected,
            "assigned_queue_id",
            f"routing policy case {case_id}",
        )
        if decision.assigned_queue_id == expected_queue:
            assignment_correct += 1

        max_violations = require_non_negative_int(
            expected,
            "max_constraint_violations",
            f"routing policy case {case_id}",
        )
        if len(decision.constraint_violations) <= max_violations:
            constraint_passed += 1

        min_lift = require_float(
            expected,
            "min_baseline_score_delta",
            f"routing policy case {case_id}",
        )
        if decision.baseline_score_delta >= min_lift:
            baseline_lift_passed += 1

        max_exploration = require_float(
            expected,
            "max_exploration_budget_used",
            f"routing policy case {case_id}",
        )
        if decision.exploration_budget_used <= max_exploration:
            exploration_budget_passed += 1

        expected_reasons = require_string_list(
            expected,
            "reason_codes",
            f"routing policy case {case_id}",
        )
        reason_total += len(expected_reasons)
        predicted_reasons = set(decision.reason_codes)
        reason_hits += sum(1 for reason in expected_reasons if reason in predicted_reasons)

    case_count = len(cases)
    assignment_accuracy = ratio(assignment_correct, case_count)
    constraint_pass_rate = ratio(constraint_passed, case_count)
    baseline_lift_pass_rate = ratio(baseline_lift_passed, case_count)
    reason_code_recall = ratio(reason_hits, reason_total)
    exploration_budget_pass_rate = ratio(exploration_budget_passed, case_count)
    deterministic_replay_rate = ratio(deterministic_replay_passed, case_count)
    passed = (
        assignment_accuracy
        >= require_float(thresholds, "assignment_accuracy_min", "routing policy thresholds")
        and constraint_pass_rate
        >= require_float(thresholds, "constraint_pass_rate_min", "routing policy thresholds")
        and baseline_lift_pass_rate
        >= require_float(
            thresholds,
            "baseline_lift_pass_rate_min",
            "routing policy thresholds",
        )
        and reason_code_recall
        >= require_float(thresholds, "reason_code_recall_min", "routing policy thresholds")
        and exploration_budget_pass_rate
        >= require_float(
            thresholds,
            "exploration_budget_pass_rate_min",
            "routing policy thresholds",
        )
        and deterministic_replay_rate
        >= require_float(
            thresholds,
            "deterministic_replay_rate_min",
            "routing policy thresholds",
        )
    )

    return RoutingPolicyEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        case_count=case_count,
        assignment_accuracy=round(assignment_accuracy, 6),
        constraint_pass_rate=round(constraint_pass_rate, 6),
        baseline_lift_pass_rate=round(baseline_lift_pass_rate, 6),
        reason_code_recall=round(reason_code_recall, 6),
        exploration_budget_pass_rate=round(exploration_budget_pass_rate, 6),
        deterministic_replay_rate=round(deterministic_replay_rate, 6),
        passed=passed,
    )


def evaluate_retrieval_golden(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> RetrievalEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "retrieval golden dataset")
    model_id = require_str(dataset, "model_id", "retrieval golden dataset")
    collection = require_str(dataset, "collection", "retrieval golden dataset")
    corpus_path = require_str(dataset, "corpus", "retrieval golden dataset")
    config = require_mapping(dataset, "config", "retrieval golden dataset")
    thresholds = require_mapping(dataset, "thresholds", "retrieval golden dataset")
    query_rows = require_list(dataset, "queries", "retrieval golden dataset")
    if not query_rows:
        raise RegistryValidationError("retrieval golden dataset must contain queries")

    corpus = load_yaml(root / corpus_path)
    corpus_collection = require_str(corpus, "collection", "retrieval corpus")
    if corpus_collection != collection:
        raise RegistryValidationError(
            f"retrieval corpus collection {corpus_collection} does not match {collection}"
        )
    chunks = require_list(corpus, "chunks", "retrieval corpus")
    if not chunks:
        raise RegistryValidationError("retrieval corpus must contain chunks")
    chunk_by_id = {
        require_str(chunk, "chunk_id", "retrieval corpus chunk"): chunk
        for chunk in chunks
    }
    if len(chunk_by_id) != len(chunks):
        raise RegistryValidationError("retrieval corpus has duplicate chunk_id")

    k = require_int(config, "k", "retrieval config")
    recall_total = 0.0
    precision_total = 0.0
    hit_count = 0
    tenant_isolated_count = 0

    for row in query_rows:
        query_id = require_str(row, "query_id", "retrieval query")
        tenant_id = require_str(row, "tenant_id", f"retrieval query {query_id}")
        query_text = require_str(row, "query", f"retrieval query {query_id}")
        expected_chunk_ids = require_string_list(
            row,
            "expected_chunk_ids",
            f"retrieval query {query_id}",
        )
        missing_expected = sorted(
            chunk_id for chunk_id in expected_chunk_ids if chunk_id not in chunk_by_id
        )
        if missing_expected:
            raise RegistryValidationError(
                f"retrieval query {query_id} references missing chunks: "
                + ", ".join(missing_expected)
            )

        ranked = lexical_retrieve(query_text, chunks, tenant_id, k)
        ranked_ids = [require_str(chunk, "chunk_id", "retrieved chunk") for chunk in ranked]
        expected = set(expected_chunk_ids)
        hits = [chunk_id for chunk_id in ranked_ids if chunk_id in expected]
        if hits:
            hit_count += 1
        recall_total += len(set(hits)) / len(expected)
        precision_total += len(hits) / len(ranked_ids) if ranked_ids else 0.0
        if all(is_chunk_allowed_for_tenant(chunk, tenant_id) for chunk in ranked):
            tenant_isolated_count += 1

    case_count = len(query_rows)
    recall_at_k = ratio_float(recall_total, case_count)
    hit_rate_at_k = ratio(hit_count, case_count)
    citation_precision_at_k = ratio_float(precision_total, case_count)
    tenant_isolation_rate = ratio(tenant_isolated_count, case_count)
    passed = (
        recall_at_k >= require_float(thresholds, "recall_at_k_min", "thresholds")
        and hit_rate_at_k >= require_float(thresholds, "hit_rate_at_k_min", "thresholds")
        and citation_precision_at_k
        >= require_float(thresholds, "citation_precision_at_k_min", "thresholds")
        and tenant_isolation_rate
        >= require_float(thresholds, "tenant_isolation_rate_min", "thresholds")
    )

    return RetrievalEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        collection=collection,
        case_count=case_count,
        recall_at_k=round(recall_at_k, 6),
        hit_rate_at_k=round(hit_rate_at_k, 6),
        citation_precision_at_k=round(citation_precision_at_k, 6),
        tenant_isolation_rate=round(tenant_isolation_rate, 6),
        k=k,
        passed=passed,
    )


def evaluate_grounded_answer_golden(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> GroundedAnswerEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "grounded answer dataset")
    model_id = require_str(dataset, "model_id", "grounded answer dataset")
    collection = require_str(dataset, "collection", "grounded answer dataset")
    corpus_path = require_str(dataset, "corpus", "grounded answer dataset")
    config = require_mapping(dataset, "config", "grounded answer dataset")
    thresholds = require_mapping(dataset, "thresholds", "grounded answer dataset")
    cases = require_list(dataset, "cases", "grounded answer dataset")
    if not cases:
        raise RegistryValidationError("grounded answer dataset must contain cases")

    corpus = load_yaml(root / corpus_path)
    corpus_collection = require_str(corpus, "collection", "grounded answer corpus")
    if corpus_collection != collection:
        raise RegistryValidationError(
            f"grounded answer corpus collection {corpus_collection} does not match {collection}"
        )
    chunks = require_list(corpus, "chunks", "grounded answer corpus")
    chunk_by_id = {
        require_str(chunk, "chunk_id", "grounded answer corpus chunk"): chunk
        for chunk in chunks
    }
    if len(chunk_by_id) != len(chunks):
        raise RegistryValidationError("grounded answer corpus has duplicate chunk_id")

    k = require_int(config, "k", "grounded answer config")
    min_score = require_float(config, "min_score_for_answer", "grounded answer config")
    grounded_count = 0
    relevant_count = 0
    citation_precision_total = 0.0
    refusal_correct_count = 0
    hallucination_count = 0
    unsafe_count = 0

    for row in cases:
        case_id = require_str(row, "case_id", "grounded answer case")
        tenant_id = require_str(row, "tenant_id", f"grounded answer case {case_id}")
        question = require_str(row, "question", f"grounded answer case {case_id}")
        expected_citations = set(
            require_string_list_allow_empty(
                row,
                "expected_citation_ids",
                f"grounded answer case {case_id}",
            )
        )
        required_terms = require_string_list_allow_empty(
            row,
            "required_answer_terms",
            f"grounded answer case {case_id}",
        )
        should_refuse = require_bool(row, "should_refuse", f"grounded answer case {case_id}")
        missing_expected = sorted(
            chunk_id for chunk_id in expected_citations if chunk_id not in chunk_by_id
        )
        if missing_expected:
            raise RegistryValidationError(
                f"grounded answer case {case_id} references missing chunks: "
                + ", ".join(missing_expected)
            )

        draft = build_grounded_answer(question, chunks, tenant_id, k, min_score)
        answer_text = str(draft["answer"])
        cited_ids = tuple(str(chunk_id) for chunk_id in draft["citations"])
        refused = bool(draft["refused"])
        cited_chunks = [chunk_by_id[chunk_id] for chunk_id in cited_ids if chunk_id in chunk_by_id]

        refusal_correct = refused is should_refuse
        if refusal_correct:
            refusal_correct_count += 1

        citation_precision = 1.0
        if cited_ids:
            citation_precision = len(set(cited_ids) & expected_citations) / len(cited_ids)
        elif not should_refuse:
            citation_precision = 0.0
        citation_precision_total += citation_precision

        grounded = answer_is_grounded(answer_text, cited_chunks) if not refused else True
        if grounded:
            grounded_count += 1

        relevant = (
            answer_contains_terms(answer_text, required_terms) if not refused else should_refuse
        )
        if relevant:
            relevant_count += 1

        cited_tenant_safe = all(
            is_chunk_allowed_for_tenant(chunk, tenant_id) for chunk in cited_chunks
        )
        unsafe = (should_refuse and not refused) or not cited_tenant_safe
        if unsafe:
            unsafe_count += 1
        if not refused and not grounded:
            hallucination_count += 1

    case_count = len(cases)
    groundedness = ratio(grounded_count, case_count)
    answer_relevance = ratio(relevant_count, case_count)
    citation_precision = ratio_float(citation_precision_total, case_count)
    refusal_accuracy = ratio(refusal_correct_count, case_count)
    hallucination_rate = ratio(hallucination_count, case_count)
    unsafe_answer_rate = ratio(unsafe_count, case_count)
    passed = (
        groundedness >= require_float(thresholds, "groundedness_min", "thresholds")
        and answer_relevance >= require_float(thresholds, "answer_relevance_min", "thresholds")
        and citation_precision
        >= require_float(thresholds, "citation_precision_min", "thresholds")
        and refusal_accuracy >= require_float(thresholds, "refusal_accuracy_min", "thresholds")
        and hallucination_rate
        <= require_float(thresholds, "hallucination_rate_max", "thresholds")
        and unsafe_answer_rate
        <= require_float(thresholds, "unsafe_answer_rate_max", "thresholds")
    )

    return GroundedAnswerEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        collection=collection,
        case_count=case_count,
        groundedness=round(groundedness, 6),
        answer_relevance=round(answer_relevance, 6),
        citation_precision=round(citation_precision, 6),
        refusal_accuracy=round(refusal_accuracy, 6),
        hallucination_rate=round(hallucination_rate, 6),
        unsafe_answer_rate=round(unsafe_answer_rate, 6),
        passed=passed,
    )


def evaluate_prompt_safety_golden(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> PromptSafetyEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "prompt safety dataset")
    model_id = require_str(dataset, "model_id", "prompt safety dataset")
    policy_path = require_str(dataset, "policy", "prompt safety dataset")
    contract_path = require_str(dataset, "contract", "prompt safety dataset")
    for linked_path in (policy_path, contract_path):
        if not (root / linked_path).exists():
            raise RegistryValidationError(
                f"prompt safety linked artifact does not exist: {linked_path}"
            )
    thresholds = require_mapping(dataset, "thresholds", "prompt safety dataset")
    cases = require_list(dataset, "cases", "prompt safety dataset")
    if not cases:
        raise RegistryValidationError("prompt safety dataset must contain cases")

    pii_total = 0
    pii_redacted = 0
    secret_total = 0
    secret_redacted = 0
    expected_token_total = 0
    expected_token_present = 0
    tenant_context_passed = 0
    cost_budget_passed = 0
    audit_safe = 0
    human_review_safe = 0

    for row in cases:
        case_id = require_str(row, "case_id", "prompt safety case")
        tenant_id = require_str(row, "tenant_id", f"prompt safety case {case_id}")
        contexts = require_list(row, "retrieved_context", f"prompt safety case {case_id}")
        output_policy = require_mapping(row, "output_policy", f"prompt safety case {case_id}")
        sensitive_values = require_string_list_allow_empty(
            row,
            "sensitive_values",
            f"prompt safety case {case_id}",
        )
        secret_values = require_string_list_allow_empty(
            row,
            "secret_values",
            f"prompt safety case {case_id}",
        )
        expected_tokens = require_string_list_allow_empty(
            row,
            "expected_redaction_tokens",
            f"prompt safety case {case_id}",
        )
        expected_included = set(
            require_string_list_allow_empty(
                row,
                "expected_included_context_ids",
                f"prompt safety case {case_id}",
            )
        )
        expected_excluded = set(
            require_string_list_allow_empty(
                row,
                "expected_excluded_context_ids",
                f"prompt safety case {case_id}",
            )
        )

        gateway_result = run_prompt_gateway(
            build_prompt_gateway_request(row, contexts, tenant_id)
        )
        sanitized_prompt = gateway_result.sanitized_prompt
        audit_payload = gateway_result.audit_payload
        included_context_ids = set(gateway_result.context_ids)

        pii_total += len(sensitive_values)
        pii_redacted += sum(
            1
            for sensitive_value in sensitive_values
            if sensitive_value not in sanitized_prompt and sensitive_value not in audit_payload
        )
        secret_total += len(secret_values)
        secret_redacted += sum(
            1
            for secret_value in secret_values
            if secret_value not in sanitized_prompt and secret_value not in audit_payload
        )
        expected_token_total += len(expected_tokens)
        expected_token_present += sum(1 for token in expected_tokens if token in sanitized_prompt)

        if expected_included <= included_context_ids and not (
            expected_excluded & included_context_ids
        ):
            tenant_context_passed += 1

        if prompt_cost_within_budget(gateway_result):
            cost_budget_passed += 1

        raw_values = sensitive_values + secret_values
        if all(raw_value not in audit_payload for raw_value in raw_values):
            audit_safe += 1

        if (
            output_policy.get("require_human_review") is True
            and output_policy.get("allow_external_auto_send") is False
        ):
            human_review_safe += 1

    case_count = len(cases)
    pii_redaction_recall = ratio(pii_redacted, pii_total) if pii_total else 1.0
    secret_redaction_recall = ratio(secret_redacted, secret_total) if secret_total else 1.0
    expected_token_coverage = (
        ratio(expected_token_present, expected_token_total) if expected_token_total else 1.0
    )
    tenant_context_pass_rate = ratio(tenant_context_passed, case_count)
    cost_budget_pass_rate = ratio(cost_budget_passed, case_count)
    audit_safety_rate = ratio(audit_safe, case_count)
    human_review_rate = ratio(human_review_safe, case_count)
    passed = (
        pii_redaction_recall >= require_float(thresholds, "pii_redaction_recall_min", "thresholds")
        and secret_redaction_recall
        >= require_float(thresholds, "secret_redaction_recall_min", "thresholds")
        and expected_token_coverage
        >= require_float(thresholds, "expected_token_coverage_min", "thresholds")
        and tenant_context_pass_rate
        >= require_float(thresholds, "tenant_context_pass_rate_min", "thresholds")
        and cost_budget_pass_rate
        >= require_float(thresholds, "cost_budget_pass_rate_min", "thresholds")
        and audit_safety_rate >= require_float(thresholds, "audit_safety_rate_min", "thresholds")
        and human_review_rate >= require_float(thresholds, "human_review_rate_min", "thresholds")
    )

    return PromptSafetyEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        case_count=case_count,
        pii_redaction_recall=round(pii_redaction_recall, 6),
        secret_redaction_recall=round(secret_redaction_recall, 6),
        expected_token_coverage=round(expected_token_coverage, 6),
        tenant_context_pass_rate=round(tenant_context_pass_rate, 6),
        cost_budget_pass_rate=round(cost_budget_pass_rate, 6),
        audit_safety_rate=round(audit_safety_rate, 6),
        human_review_rate=round(human_review_rate, 6),
        passed=passed,
    )


def evaluate_llm_adapter_shadow_golden(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> LlmAdapterShadowEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "LLM adapter shadow dataset")
    model_id = require_str(dataset, "model_id", "LLM adapter shadow dataset")
    policy_path = require_str(
        dataset,
        "prompt_gateway_policy",
        "LLM adapter shadow dataset",
    )
    contract_path = require_str(dataset, "contract", "LLM adapter shadow dataset")
    for linked_path in (policy_path, contract_path):
        if not (root / linked_path).exists():
            raise RegistryValidationError(
                f"LLM adapter shadow linked artifact does not exist: {linked_path}"
            )

    config = require_mapping(dataset, "config", "LLM adapter shadow dataset")
    thresholds = require_mapping(dataset, "thresholds", "LLM adapter shadow dataset")
    cases = require_list(dataset, "cases", "LLM adapter shadow dataset")
    if not cases:
        raise RegistryValidationError("LLM adapter shadow dataset must contain cases")

    access_policy = load_prompt_gateway_access_policy(root)
    gateway_runtime = PromptGatewayRuntime(root)
    k = require_int(config, "k", "LLM adapter shadow config")
    min_score = require_float(
        config,
        "min_score_for_answer",
        "LLM adapter shadow config",
    )

    prompt_gateway_expected = 0
    allowed_cases = 0
    allowed_generation_count = 0
    blocked_cases = 0
    blocked_generation_skipped = 0
    grounded_count = 0
    generated_count = 0
    citation_precision_total = 0.0
    refusal_correct_count = 0
    audit_safe_count = 0
    context_filter_passed = 0

    for row in cases:
        case_id = require_str(row, "case_id", "LLM adapter shadow case")
        principal_id = require_str(
            row,
            "principal_id",
            f"LLM adapter shadow case {case_id}",
        )
        tenant_id = require_str(row, "tenant_id", f"LLM adapter shadow case {case_id}")
        contexts = require_list(
            row,
            "retrieved_context",
            f"LLM adapter shadow case {case_id}",
        )
        expected = require_mapping(
            row,
            "expected",
            f"LLM adapter shadow case {case_id}",
        )
        expected_gateway_allowed = require_bool(
            expected,
            "gateway_allowed",
            f"LLM adapter shadow case {case_id}",
        )
        should_refuse = require_bool(
            expected,
            "should_refuse",
            f"LLM adapter shadow case {case_id}",
        )
        raw_values_not_in_audit = require_string_list_allow_empty(
            expected,
            "raw_values_not_in_audit",
            f"LLM adapter shadow case {case_id}",
        )
        expected_included = set(
            require_string_list_allow_empty(
                expected,
                "expected_included_context_ids",
                f"LLM adapter shadow case {case_id}",
            )
        )
        expected_excluded = set(
            require_string_list_allow_empty(
                expected,
                "expected_excluded_context_ids",
                f"LLM adapter shadow case {case_id}",
            )
        )

        principal = access_policy.resolve_principal(principal_id)
        gateway_evaluation = gateway_runtime.evaluate(row, principal)
        gateway_result = gateway_evaluation.result
        gateway_allowed = bool(gateway_result.allowed)
        if gateway_allowed is expected_gateway_allowed:
            prompt_gateway_expected += 1
        if expected_included <= set(gateway_result.context_ids) and not (
            expected_excluded & set(gateway_result.context_ids)
        ):
            context_filter_passed += 1
        if all(
            raw_value not in gateway_result.audit_payload
            for raw_value in raw_values_not_in_audit
        ):
            audit_safe_count += 1

        if gateway_allowed:
            allowed_cases += 1
            allowed_generation_count += 1
            draft = build_llm_adapter_shadow_answer(
                row,
                contexts,
                gateway_result.context_ids,
                tenant_id,
                k,
                min_score,
            )
            generated_count += 1
            answer_text = str(draft["answer"])
            cited_ids = tuple(str(chunk_id) for chunk_id in draft["citations"])
            refused = bool(draft["refused"])
            cited_chunks = [
                context_to_grounded_answer_chunk(context)
                for context in contexts
                if require_str(context, "context_id", f"LLM adapter shadow case {case_id}")
                in cited_ids
            ]
            if refused or answer_is_grounded(answer_text, cited_chunks):
                grounded_count += 1
            if refused is should_refuse:
                refusal_correct_count += 1
            expected_citations = set(
                require_string_list_allow_empty(
                    expected,
                    "expected_citation_ids",
                    f"LLM adapter shadow case {case_id}",
                )
            )
            citation_precision_total += citation_precision_for_answer(
                cited_ids,
                expected_citations,
                should_refuse,
            )
        else:
            blocked_cases += 1
            blocked_generation_skipped += 1
            if should_refuse:
                refusal_correct_count += 1

    case_count = len(cases)
    prompt_gateway_expected_pass_rate = ratio(prompt_gateway_expected, case_count)
    allowed_generation_rate = (
        ratio(allowed_generation_count, allowed_cases) if allowed_cases else 1.0
    )
    blocked_generation_skip_rate = (
        ratio(blocked_generation_skipped, blocked_cases) if blocked_cases else 1.0
    )
    groundedness = ratio(grounded_count, generated_count) if generated_count else 1.0
    citation_precision = (
        ratio_float(citation_precision_total, generated_count)
        if generated_count
        else 1.0
    )
    refusal_accuracy = ratio(refusal_correct_count, case_count)
    audit_safety_rate = ratio(audit_safe_count, case_count)
    context_filter_pass_rate = ratio(context_filter_passed, case_count)
    gateway_evaluation_count = gateway_runtime.snapshot_metrics().evaluation_count

    passed = (
        prompt_gateway_expected_pass_rate
        >= require_float(
            thresholds,
            "prompt_gateway_expected_pass_rate_min",
            "LLM adapter shadow thresholds",
        )
        and allowed_generation_rate
        >= require_float(
            thresholds,
            "allowed_generation_rate_min",
            "LLM adapter shadow thresholds",
        )
        and blocked_generation_skip_rate
        >= require_float(
            thresholds,
            "blocked_generation_skip_rate_min",
            "LLM adapter shadow thresholds",
        )
        and groundedness
        >= require_float(thresholds, "groundedness_min", "LLM adapter shadow thresholds")
        and citation_precision
        >= require_float(
            thresholds,
            "citation_precision_min",
            "LLM adapter shadow thresholds",
        )
        and refusal_accuracy
        >= require_float(
            thresholds,
            "refusal_accuracy_min",
            "LLM adapter shadow thresholds",
        )
        and audit_safety_rate
        >= require_float(
            thresholds,
            "audit_safety_rate_min",
            "LLM adapter shadow thresholds",
        )
        and context_filter_pass_rate
        >= require_float(
            thresholds,
            "context_filter_pass_rate_min",
            "LLM adapter shadow thresholds",
        )
        and gateway_evaluation_count == case_count
    )

    return LlmAdapterShadowEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        case_count=case_count,
        prompt_gateway_expected_pass_rate=round(prompt_gateway_expected_pass_rate, 6),
        allowed_generation_rate=round(allowed_generation_rate, 6),
        blocked_generation_skip_rate=round(blocked_generation_skip_rate, 6),
        groundedness=round(groundedness, 6),
        citation_precision=round(citation_precision, 6),
        refusal_accuracy=round(refusal_accuracy, 6),
        audit_safety_rate=round(audit_safety_rate, 6),
        context_filter_pass_rate=round(context_filter_pass_rate, 6),
        gateway_evaluation_count=gateway_evaluation_count,
        passed=passed,
    )


def evaluate_vector_index_contract(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> VectorIndexEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "vector index contract dataset")
    model_id = require_str(dataset, "model_id", "vector index contract dataset")
    collection = require_str(dataset, "collection", "vector index contract dataset")
    corpus_path = require_str(dataset, "corpus", "vector index contract dataset")
    collection_schema_path = require_str(
        dataset,
        "collection_schema",
        "vector index contract dataset",
    )
    config = require_mapping(dataset, "config", "vector index contract dataset")
    thresholds = require_mapping(dataset, "thresholds", "vector index contract dataset")
    corpus = load_yaml(root / corpus_path)
    collection_schema = load_yaml(root / collection_schema_path)

    artifact = build_vector_index(
        corpus,
        collection_schema,
        index_id=require_str(config, "index_id", "vector index contract config"),
        model_id=model_id,
        algorithm=require_str(config, "algorithm", "vector index contract config"),
    )
    if artifact.collection != collection:
        raise RegistryValidationError(
            f"vector index artifact collection {artifact.collection} does not match {collection}"
        )

    metrics = validate_vector_index_contract(artifact, corpus, collection_schema, thresholds)
    return VectorIndexEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        collection=collection,
        case_count=metrics.chunk_count,
        embedding_dimensions=metrics.embedding_dimensions,
        chunk_coverage_rate=metrics.chunk_coverage_rate,
        dimension_conformance_rate=metrics.dimension_conformance_rate,
        metadata_conformance_rate=metrics.metadata_conformance_rate,
        tenant_scope_coverage_rate=metrics.tenant_scope_coverage_rate,
        checksum_stable=metrics.checksum_stable,
        passed=metrics.passed,
    )


def evaluate_hybrid_retrieval_shadow(
    ai_root: Path | str,
    dataset_path: str | Path,
) -> HybridRetrievalEvaluation:
    root = Path(ai_root)
    dataset = load_yaml(root / dataset_path)
    dataset_id = require_str(dataset, "dataset_id", "hybrid retrieval dataset")
    model_id = require_str(dataset, "model_id", "hybrid retrieval dataset")
    collection = require_str(dataset, "collection", "hybrid retrieval dataset")
    corpus_path = require_str(dataset, "corpus", "hybrid retrieval dataset")
    collection_schema_path = require_str(dataset, "collection_schema", "hybrid retrieval dataset")
    config = require_mapping(dataset, "config", "hybrid retrieval dataset")
    thresholds = require_mapping(dataset, "thresholds", "hybrid retrieval dataset")
    query_rows = require_list(dataset, "queries", "hybrid retrieval dataset")
    if not query_rows:
        raise RegistryValidationError("hybrid retrieval dataset must contain queries")

    corpus = load_yaml(root / corpus_path)
    collection_schema = load_yaml(root / collection_schema_path)
    corpus_collection = require_str(corpus, "collection", "hybrid retrieval corpus")
    if corpus_collection != collection:
        raise RegistryValidationError(
            f"hybrid retrieval corpus collection {corpus_collection} does not match {collection}"
        )
    chunks = require_list(corpus, "chunks", "hybrid retrieval corpus")
    chunk_by_id = {
        require_str(chunk, "chunk_id", "hybrid retrieval corpus chunk"): chunk
        for chunk in chunks
    }
    if len(chunk_by_id) != len(chunks):
        raise RegistryValidationError("hybrid retrieval corpus has duplicate chunk_id")

    k = require_int(config, "k", "hybrid retrieval config")
    lexical_weight = require_float(config, "lexical_weight", "hybrid retrieval config")
    vector_weight = require_float(config, "vector_weight", "hybrid retrieval config")
    vector_artifact = build_vector_index(
        corpus,
        collection_schema,
        index_id=require_str(config, "index_id", "hybrid retrieval config"),
        model_id=model_id,
        algorithm=require_str(config, "algorithm", "hybrid retrieval config"),
    )

    lexical_recall_total = 0.0
    vector_recall_total = 0.0
    hybrid_recall_total = 0.0
    not_worse_count = 0
    tenant_isolated_count = 0

    for row in query_rows:
        query_id = require_str(row, "query_id", "hybrid retrieval query")
        tenant_id = require_str(row, "tenant_id", f"hybrid retrieval query {query_id}")
        query_text = require_str(row, "query", f"hybrid retrieval query {query_id}")
        expected_chunk_ids = require_string_list(
            row,
            "expected_chunk_ids",
            f"hybrid retrieval query {query_id}",
        )
        missing_expected = sorted(
            chunk_id for chunk_id in expected_chunk_ids if chunk_id not in chunk_by_id
        )
        if missing_expected:
            raise RegistryValidationError(
                f"hybrid retrieval query {query_id} references missing chunks: "
                + ", ".join(missing_expected)
            )

        lexical_ranked = lexical_rank(query_text, chunks, tenant_id, k)
        lexical_ids = [chunk_id for _, chunk_id, _ in lexical_ranked]
        lexical_scores = {chunk_id: score for score, chunk_id, _ in lexical_ranked}
        vector_ranked = vector_rank(query_text, vector_artifact, tenant_id, k)
        vector_ids = [result.chunk_id for result in vector_ranked]
        hybrid_ids = hybrid_rank_ids(
            lexical_scores,
            vector_ranked,
            k=k,
            lexical_weight=lexical_weight,
            vector_weight=vector_weight,
        )

        expected = set(expected_chunk_ids)
        lexical_recall = retrieval_recall(lexical_ids, expected)
        vector_recall = retrieval_recall(vector_ids, expected)
        hybrid_recall = retrieval_recall(hybrid_ids, expected)
        lexical_recall_total += lexical_recall
        vector_recall_total += vector_recall
        hybrid_recall_total += hybrid_recall
        if hybrid_recall >= lexical_recall:
            not_worse_count += 1

        hybrid_chunks = [
            chunk_by_id[chunk_id] for chunk_id in hybrid_ids if chunk_id in chunk_by_id
        ]
        if all(is_chunk_allowed_for_tenant(chunk, tenant_id) for chunk in hybrid_chunks):
            tenant_isolated_count += 1

    case_count = len(query_rows)
    lexical_recall_at_k = ratio_float(lexical_recall_total, case_count)
    vector_recall_at_k = ratio_float(vector_recall_total, case_count)
    hybrid_recall_at_k = ratio_float(hybrid_recall_total, case_count)
    hybrid_not_worse_than_lexical_rate = ratio(not_worse_count, case_count)
    tenant_isolation_rate = ratio(tenant_isolated_count, case_count)
    passed = (
        lexical_recall_at_k
        >= require_float(thresholds, "lexical_recall_at_k_min", "hybrid thresholds")
        and vector_recall_at_k
        >= require_float(thresholds, "vector_recall_at_k_min", "hybrid thresholds")
        and hybrid_recall_at_k
        >= require_float(thresholds, "hybrid_recall_at_k_min", "hybrid thresholds")
        and hybrid_not_worse_than_lexical_rate
        >= require_float(
            thresholds,
            "hybrid_not_worse_than_lexical_rate_min",
            "hybrid thresholds",
        )
        and tenant_isolation_rate
        >= require_float(thresholds, "tenant_isolation_rate_min", "hybrid thresholds")
    )

    return HybridRetrievalEvaluation(
        dataset_id=dataset_id,
        model_id=model_id,
        collection=collection,
        case_count=case_count,
        lexical_recall_at_k=round(lexical_recall_at_k, 6),
        vector_recall_at_k=round(vector_recall_at_k, 6),
        hybrid_recall_at_k=round(hybrid_recall_at_k, 6),
        hybrid_not_worse_than_lexical_rate=round(hybrid_not_worse_than_lexical_rate, 6),
        tenant_isolation_rate=round(tenant_isolation_rate, 6),
        k=k,
        passed=passed,
    )


def load_module(path: Path, module_name: str) -> ModuleType:
    if not path.exists():
        raise RegistryValidationError(f"evaluation module path does not exist: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RegistryValidationError(f"cannot load module spec from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def ensure_runner_model_id(evaluation_id: str, expected: str, actual: str) -> None:
    if actual != expected:
        raise RegistryValidationError(
            f"evaluation {evaluation_id} runner model_id {actual} does not match {expected}"
        )


def import_service_module(root: Path, module_name: str) -> ModuleType:
    service_src = root / "services" / "recommendation-ml-service" / "src"
    if not service_src.exists():
        raise RegistryValidationError(
            f"recommendation service source does not exist: {service_src}"
        )
    service_src_text = str(service_src)
    if service_src_text not in sys.path:
        sys.path.insert(0, service_src_text)
    return __import__(module_name, fromlist=["*"])


def require_mapping(row: dict[str, Any], key: str, owner: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise RegistryValidationError(f"{owner} must define mapping field {key}")
    return value


def require_list(row: dict[str, Any], key: str, owner: str) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a mapping")
        result.append(item)
    return result


def require_float(row: dict[str, Any], key: str, owner: str) -> float:
    value = row.get(key)
    if not isinstance(value, int | float):
        raise RegistryValidationError(f"{owner} must define numeric field {key}")
    return float(value)


def require_int(row: dict[str, Any], key: str, owner: str) -> int:
    value = row.get(key)
    if not isinstance(value, int) or value <= 0:
        raise RegistryValidationError(f"{owner} must define positive integer field {key}")
    return value


def require_non_negative_int(row: dict[str, Any], key: str, owner: str) -> int:
    value = row.get(key)
    if not isinstance(value, int) or value < 0:
        raise RegistryValidationError(f"{owner} must define non-negative integer field {key}")
    return value


def require_string_list(row: dict[str, Any], key: str, owner: str) -> list[str]:
    value = row.get(key)
    if not isinstance(value, list) or not value:
        raise RegistryValidationError(f"{owner} must define non-empty list field {key}")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RegistryValidationError(f"{owner} {key} must contain strings")
        result.append(item.strip())
    return result


def require_string_list_allow_empty(row: dict[str, Any], key: str, owner: str) -> list[str]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RegistryValidationError(f"{owner} {key} must contain strings")
        result.append(item.strip())
    return result


def require_bool(row: dict[str, Any], key: str, owner: str) -> bool:
    value = row.get(key)
    if not isinstance(value, bool):
        raise RegistryValidationError(f"{owner} must define boolean field {key}")
    return value


def parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise RegistryValidationError(f"invalid UUID in evaluation dataset: {value}") from exc


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def ratio_float(numerator: float, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def retrieval_recall(ranked_ids: list[str] | tuple[str, ...], expected_ids: set[str]) -> float:
    if not expected_ids:
        return 0.0
    return len(set(ranked_ids) & expected_ids) / len(expected_ids)


def pairwise_risk_ordering_pass_rate(ranked_cases: list[tuple[int, float, str]]) -> float:
    pair_count = 0
    passed_count = 0
    for left_index, (left_order, left_score, _) in enumerate(ranked_cases):
        for right_order, right_score, _ in ranked_cases[left_index + 1 :]:
            if left_order == right_order:
                continue
            pair_count += 1
            if left_order > right_order and left_score > right_score:
                passed_count += 1
            elif left_order < right_order and left_score < right_score:
                passed_count += 1
    return ratio(passed_count, pair_count) if pair_count else 1.0


def ndcg_at_k(hits: list[int], ideal_relevant_count: int) -> float:
    if ideal_relevant_count <= 0:
        return 0.0
    dcg = 0.0
    for index, hit in enumerate(hits, start=1):
        if hit:
            dcg += 1.0 / log2(index + 1)
    ideal_dcg = sum(1.0 / log2(index + 1) for index in range(1, ideal_relevant_count + 1))
    return dcg / ideal_dcg if ideal_dcg > 0 else 0.0


def log2(value: int) -> float:
    return math.log2(value)


def lexical_retrieve(
    query_text: str,
    chunks: list[dict[str, Any]],
    tenant_id: str,
    k: int,
) -> list[dict[str, Any]]:
    return [chunk for _, _, chunk in lexical_rank(query_text, chunks, tenant_id, k)]


def lexical_rank(
    query_text: str,
    chunks: list[dict[str, Any]],
    tenant_id: str,
    k: int,
) -> list[tuple[float, str, dict[str, Any]]]:
    query_tokens = tokenize(query_text)
    scored: list[tuple[float, str, dict[str, Any]]] = []
    for chunk in chunks:
        if not is_chunk_allowed_for_tenant(chunk, tenant_id):
            continue
        chunk_id = require_str(chunk, "chunk_id", "retrieval corpus chunk")
        text = " ".join(
            [
                require_str(chunk, "title", f"retrieval chunk {chunk_id}"),
                require_str(chunk, "text", f"retrieval chunk {chunk_id}"),
                " ".join(require_string_list(chunk, "tags", f"retrieval chunk {chunk_id}")),
            ]
        )
        score = lexical_score(query_tokens, tokenize(text))
        if score > 0:
            scored.append((score, chunk_id, chunk))

    scored.sort(key=lambda row: (-row[0], row[1]))
    return scored[:k]


def lexical_score(query_tokens: set[str], document_tokens: set[str]) -> float:
    if not query_tokens or not document_tokens:
        return 0.0
    overlap = query_tokens & document_tokens
    return len(overlap) / math.sqrt(len(query_tokens) * len(document_tokens))


def tokenize(text: str) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "before",
        "by",
        "for",
        "in",
        "is",
        "of",
        "or",
        "the",
        "to",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in stopwords and len(token) > 1
    }


def is_chunk_allowed_for_tenant(chunk: dict[str, Any], tenant_id: str) -> bool:
    chunk_tenant = require_str(chunk, "tenant_id", "retrieval corpus chunk")
    access_scope = require_str(chunk, "access_scope", "retrieval corpus chunk")
    if access_scope == "public" and chunk_tenant == "global":
        return True
    return chunk_tenant == tenant_id


def build_grounded_answer(
    question: str,
    chunks: list[dict[str, Any]],
    tenant_id: str,
    k: int,
    min_score_for_answer: float,
) -> dict[str, object]:
    if mentions_other_tenant(question, tenant_id):
        return refusal_answer()

    ranked = lexical_rank(question, chunks, tenant_id, k)
    if not ranked or ranked[0][0] < min_score_for_answer:
        return refusal_answer()

    _, _, chunk = ranked[0]
    chunk_id = require_str(chunk, "chunk_id", "grounded answer chunk")
    answer = require_str(chunk, "text", f"grounded answer chunk {chunk_id}")
    return {
        "answer": f"{answer} Citation: [{chunk_id}]",
        "citations": (chunk_id,),
        "refused": False,
    }


def build_llm_adapter_shadow_answer(
    row: dict[str, Any],
    contexts: list[dict[str, Any]],
    allowed_context_ids: tuple[str, ...],
    tenant_id: str,
    k: int,
    min_score_for_answer: float,
) -> dict[str, object]:
    question = require_str(row, "generation_question", "LLM adapter shadow case")
    allowed = set(allowed_context_ids)
    chunks = [
        context_to_grounded_answer_chunk(context)
        for context in contexts
        if require_str(context, "context_id", "LLM adapter shadow context") in allowed
    ]
    return build_grounded_answer(question, chunks, tenant_id, k, min_score_for_answer)


def context_to_grounded_answer_chunk(context: dict[str, Any]) -> dict[str, Any]:
    context_id = require_str(context, "context_id", "LLM adapter shadow context")
    return {
        "access_scope": "public"
        if context.get("tenant_id") == "global"
        else "tenant",
        "chunk_id": context_id,
        "tenant_id": require_str(
            context,
            "tenant_id",
            f"LLM adapter shadow context {context_id}",
        ),
        "text": require_str(
            context,
            "text",
            f"LLM adapter shadow context {context_id}",
        ),
        "title": require_str(
            context,
            "source_ref",
            f"LLM adapter shadow context {context_id}",
        ),
        "tags": [context_id],
    }


def citation_precision_for_answer(
    cited_ids: tuple[str, ...],
    expected_citations: set[str],
    should_refuse: bool,
) -> float:
    if cited_ids:
        return len(set(cited_ids) & expected_citations) / len(cited_ids)
    if should_refuse:
        return 1.0
    return 0.0


def refusal_answer() -> dict[str, object]:
    return {
        "answer": (
            "I do not have enough trusted source evidence to answer. "
            "Please provide more context or route this to a human reviewer."
        ),
        "citations": (),
        "refused": True,
    }


def mentions_other_tenant(text: str, tenant_id: str) -> bool:
    current = tenant_id.lower().replace("_", "-")
    for suffix in re.findall(r"\btenant[\s_-]+([a-z0-9]+)\b", text.lower()):
        mentioned = f"tenant-{suffix}"
        if mentioned != current:
            return True
    return False


def answer_contains_terms(answer: str, required_terms: list[str]) -> bool:
    lowered = answer.lower()
    return all(term.lower() in lowered for term in required_terms)


def answer_is_grounded(answer: str, cited_chunks: list[dict[str, Any]]) -> bool:
    if not cited_chunks:
        return False
    normalized_answer = normalize_for_grounding(strip_citations(answer))
    grounded_sources = " ".join(
        normalize_for_grounding(require_str(chunk, "text", "grounded answer cited chunk"))
        for chunk in cited_chunks
    )
    return normalized_answer in grounded_sources


def strip_citations(answer: str) -> str:
    return re.sub(r"\s*Citation:\s*\[[^\]]+\]\s*$", "", answer).strip()


def normalize_for_grounding(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()

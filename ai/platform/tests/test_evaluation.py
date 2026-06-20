from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.evaluation import (
    evaluate_demand_forecast_golden,
    evaluate_document_intelligence_golden,
    evaluate_grounded_answer_golden,
    evaluate_hybrid_retrieval_shadow,
    evaluate_llm_adapter_shadow_golden,
    evaluate_payment_fraud_risk_golden,
    evaluate_prompt_safety_golden,
    evaluate_recommendation_item_cf,
    evaluate_retrieval_golden,
    evaluate_routing_policy_simulator_golden,
    evaluate_sequence_risk_golden,
    evaluate_speech_quality_golden,
    evaluate_support_agent_assist,
    evaluate_support_sla_risk_golden,
    evaluate_vector_index_contract,
    run_registered_evaluations,
)


def test_support_agent_assist_golden_evaluation_passes() -> None:
    report = evaluate_support_agent_assist(Path(__file__).resolve().parents[2])

    assert report.dataset_id == "support-agent-assist-golden-v1"
    assert report.model_id == "support-agent-assist-baseline-v1"
    assert report.case_count == 5
    assert report.intent_accuracy >= 0.8
    assert report.priority_accuracy >= 0.8
    assert report.human_review_rate == 1.0
    assert report.retrieval_required_term_coverage >= 0.8
    assert report.passed is True


def test_recommendation_item_cf_offline_evaluation_passes() -> None:
    report = evaluate_recommendation_item_cf(Path(__file__).resolve().parents[2])

    assert report.dataset_id == "recommendation-item-cf-golden-v1"
    assert report.model_id == "recommendation-item-cf-v1"
    assert report.case_count == 3
    assert report.k == 10
    assert report.recall_at_k >= 0.8
    assert report.ndcg_at_k >= 0.8
    assert report.catalog_coverage == 1.0
    assert report.passed is True


def test_sequence_risk_golden_evaluation_passes() -> None:
    report = evaluate_sequence_risk_golden(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/sequence-risk-baseline-golden.yaml",
    )

    assert report.dataset_id == "sequence-risk-baseline-golden-v1"
    assert report.model_id == "sequence-risk-baseline-v1"
    assert report.case_count == 4
    assert report.risk_band_accuracy == 1.0
    assert report.reason_code_recall == 1.0
    assert report.score_threshold_pass_rate == 1.0
    assert report.risk_ordering_pass_rate == 1.0
    assert report.passed is True


def test_finance_document_intelligence_golden_evaluation_passes() -> None:
    report = evaluate_document_intelligence_golden(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/finance-document-intelligence-golden.yaml",
    )

    assert report.dataset_id == "finance-document-intelligence-golden-v1"
    assert report.model_id == "finance-document-intelligence-baseline-v1"
    assert report.case_count == 4
    assert report.document_type_accuracy == 1.0
    assert report.field_recall == 1.0
    assert report.evidence_term_recall == 1.0
    assert report.human_review_policy_pass_rate == 1.0
    assert report.privacy_guardrail_pass_rate == 1.0
    assert report.passed is True


def test_speech_quality_golden_evaluation_passes() -> None:
    report = evaluate_speech_quality_golden(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/speech-quality-golden.yaml",
    )

    assert report.dataset_id == "speech-quality-golden-v1"
    assert report.model_id == "speech-quality-baseline-v1"
    assert report.case_count == 4
    assert report.intent_accuracy == 1.0
    assert report.quality_band_accuracy == 1.0
    assert report.reason_code_recall == 1.0
    assert report.evidence_term_recall == 1.0
    assert report.human_review_policy_pass_rate == 1.0
    assert report.privacy_guardrail_pass_rate == 1.0
    assert report.passed is True


def test_operations_routing_policy_simulator_evaluation_passes() -> None:
    report = evaluate_routing_policy_simulator_golden(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/operations-routing-policy-golden.yaml",
    )

    assert report.dataset_id == "operations-routing-policy-golden-v1"
    assert report.model_id == "operations-routing-policy-simulator-v1"
    assert report.case_count == 4
    assert report.assignment_accuracy == 1.0
    assert report.constraint_pass_rate == 1.0
    assert report.baseline_lift_pass_rate == 1.0
    assert report.reason_code_recall == 1.0
    assert report.exploration_budget_pass_rate == 1.0
    assert report.deterministic_replay_rate == 1.0
    assert report.passed is True


def test_operations_demand_forecast_evaluation_passes() -> None:
    report = evaluate_demand_forecast_golden(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/operations-demand-forecast-golden.yaml",
    )

    assert report.dataset_id == "operations-demand-forecast-golden-v1"
    assert report.model_id == "operations-demand-forecast-baseline-v1"
    assert report.case_count == 4
    assert report.demand_band_accuracy == 1.0
    assert report.staffing_recommendation_accuracy == 1.0
    assert report.reason_code_recall == 1.0
    assert report.forecast_threshold_pass_rate == 1.0
    assert report.human_review_policy_pass_rate == 1.0
    assert report.forecast_ordering_pass_rate == 1.0
    assert report.passed is True


def test_support_sla_risk_golden_evaluation_passes() -> None:
    report = evaluate_support_sla_risk_golden(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/support-sla-risk-golden.yaml",
    )

    assert report.dataset_id == "support-sla-risk-golden-v1"
    assert report.model_id == "support-sla-risk-baseline-v1"
    assert report.case_count == 4
    assert report.risk_band_accuracy == 1.0
    assert report.reason_code_recall == 1.0
    assert report.human_review_policy_pass_rate == 1.0
    assert report.score_threshold_pass_rate == 1.0
    assert report.risk_ordering_pass_rate == 1.0
    assert report.passed is True


def test_finance_payment_fraud_golden_evaluation_passes() -> None:
    report = evaluate_payment_fraud_risk_golden(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/finance-payment-fraud-golden.yaml",
    )

    assert report.dataset_id == "finance-payment-fraud-golden-v1"
    assert report.model_id == "finance-payment-fraud-baseline-v1"
    assert report.case_count == 4
    assert report.risk_band_accuracy == 1.0
    assert report.reason_code_recall == 1.0
    assert report.entity_link_recall == 1.0
    assert report.human_review_policy_pass_rate == 1.0
    assert report.score_threshold_pass_rate == 1.0
    assert report.risk_ordering_pass_rate == 1.0
    assert report.passed is True


def test_support_knowledge_retrieval_evaluation_passes() -> None:
    report = evaluate_retrieval_golden(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/support-knowledge-retrieval-golden.yaml",
    )

    assert report.dataset_id == "support-knowledge-retrieval-golden-v1"
    assert report.collection == "support_knowledge_articles"
    assert report.case_count == 4
    assert report.recall_at_k == 1.0
    assert report.hit_rate_at_k == 1.0
    assert report.citation_precision_at_k >= 0.6
    assert report.tenant_isolation_rate == 1.0
    assert report.passed is True


def test_course_content_retrieval_evaluation_passes() -> None:
    report = evaluate_retrieval_golden(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/course-content-retrieval-golden.yaml",
    )

    assert report.dataset_id == "course-content-retrieval-golden-v1"
    assert report.collection == "course_content_chunks"
    assert report.case_count == 4
    assert report.recall_at_k == 1.0
    assert report.hit_rate_at_k == 1.0
    assert report.citation_precision_at_k >= 0.6
    assert report.tenant_isolation_rate == 1.0
    assert report.passed is True


def test_course_content_vector_index_contract_passes() -> None:
    report = evaluate_vector_index_contract(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/course-content-vector-index-golden.yaml",
    )

    assert report.dataset_id == "course-content-vector-index-contract-v1"
    assert report.collection == "course_content_chunks"
    assert report.case_count == 5
    assert report.embedding_dimensions == 768
    assert report.chunk_coverage_rate == 1.0
    assert report.dimension_conformance_rate == 1.0
    assert report.metadata_conformance_rate == 1.0
    assert report.tenant_scope_coverage_rate == 1.0
    assert report.checksum_stable is True
    assert report.passed is True


def test_support_knowledge_vector_index_contract_passes() -> None:
    report = evaluate_vector_index_contract(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/support-knowledge-vector-index-golden.yaml",
    )

    assert report.dataset_id == "support-knowledge-vector-index-contract-v1"
    assert report.collection == "support_knowledge_articles"
    assert report.case_count == 5
    assert report.embedding_dimensions == 768
    assert report.chunk_coverage_rate == 1.0
    assert report.dimension_conformance_rate == 1.0
    assert report.metadata_conformance_rate == 1.0
    assert report.tenant_scope_coverage_rate == 1.0
    assert report.checksum_stable is True
    assert report.passed is True


def test_course_hybrid_retrieval_shadow_passes() -> None:
    report = evaluate_hybrid_retrieval_shadow(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/course-content-hybrid-retrieval-golden.yaml",
    )

    assert report.dataset_id == "course-content-hybrid-retrieval-shadow-v1"
    assert report.collection == "course_content_chunks"
    assert report.case_count == 4
    assert report.lexical_recall_at_k == 1.0
    assert report.vector_recall_at_k == 1.0
    assert report.hybrid_recall_at_k == 1.0
    assert report.hybrid_not_worse_than_lexical_rate == 1.0
    assert report.tenant_isolation_rate == 1.0
    assert report.passed is True


def test_support_hybrid_retrieval_shadow_passes() -> None:
    report = evaluate_hybrid_retrieval_shadow(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/support-knowledge-hybrid-retrieval-golden.yaml",
    )

    assert report.dataset_id == "support-knowledge-hybrid-retrieval-shadow-v1"
    assert report.collection == "support_knowledge_articles"
    assert report.case_count == 4
    assert report.lexical_recall_at_k == 1.0
    assert report.vector_recall_at_k == 1.0
    assert report.hybrid_recall_at_k == 1.0
    assert report.hybrid_not_worse_than_lexical_rate == 1.0
    assert report.tenant_isolation_rate == 1.0
    assert report.passed is True


def test_support_rag_grounded_answer_evaluation_passes() -> None:
    report = evaluate_grounded_answer_golden(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/support-rag-answer-golden.yaml",
    )

    assert report.dataset_id == "support-rag-answer-golden-v1"
    assert report.collection == "support_knowledge_articles"
    assert report.case_count == 4
    assert report.groundedness == 1.0
    assert report.answer_relevance == 1.0
    assert report.citation_precision == 1.0
    assert report.refusal_accuracy == 1.0
    assert report.hallucination_rate == 0.0
    assert report.unsafe_answer_rate == 0.0
    assert report.passed is True


def test_course_rag_grounded_answer_evaluation_passes() -> None:
    report = evaluate_grounded_answer_golden(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/course-rag-answer-golden.yaml",
    )

    assert report.dataset_id == "course-rag-answer-golden-v1"
    assert report.collection == "course_content_chunks"
    assert report.case_count == 4
    assert report.groundedness == 1.0
    assert report.answer_relevance == 1.0
    assert report.citation_precision == 1.0
    assert report.refusal_accuracy == 1.0
    assert report.hallucination_rate == 0.0
    assert report.unsafe_answer_rate == 0.0
    assert report.passed is True


def test_prompt_safety_evaluation_passes() -> None:
    report = evaluate_prompt_safety_golden(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/prompt-safety-golden.yaml",
    )

    assert report.dataset_id == "prompt-safety-golden-v1"
    assert report.model_id == "prompt-safety-baseline-v1"
    assert report.case_count == 3
    assert report.pii_redaction_recall == 1.0
    assert report.secret_redaction_recall == 1.0
    assert report.expected_token_coverage == 1.0
    assert report.tenant_context_pass_rate == 1.0
    assert report.cost_budget_pass_rate == 1.0
    assert report.audit_safety_rate == 1.0
    assert report.human_review_rate == 1.0
    assert report.passed is True


def test_llm_adapter_shadow_gateway_evaluation_passes() -> None:
    report = evaluate_llm_adapter_shadow_golden(
        Path(__file__).resolve().parents[2],
        "platform/evaluation/datasets/llm-adapter-shadow-gateway-golden.yaml",
    )

    assert report.dataset_id == "llm-adapter-shadow-gateway-golden-v1"
    assert report.model_id == "llm-adapter-shadow-gateway-v1"
    assert report.case_count == 4
    assert report.prompt_gateway_expected_pass_rate == 1.0
    assert report.allowed_generation_rate == 1.0
    assert report.blocked_generation_skip_rate == 1.0
    assert report.groundedness == 1.0
    assert report.citation_precision == 1.0
    assert report.refusal_accuracy == 1.0
    assert report.audit_safety_rate == 1.0
    assert report.context_filter_pass_rate == 1.0
    assert report.gateway_evaluation_count == 4
    assert report.passed is True


def test_registered_evaluations_pass() -> None:
    report = run_registered_evaluations(Path(__file__).resolve().parents[2])

    assert report.run_count == 20
    assert report.required_count == 20
    assert report.required_passed_count == 20
    assert set(report.results) == {
        "causal-uplift-baseline-golden",
        "course-content-hybrid-retrieval",
        "course-content-retrieval",
        "course-content-vector-index",
        "course-rag-answer",
        "finance-document-intelligence-golden",
        "finance-payment-fraud-golden",
        "llm-adapter-shadow-gateway",
        "operations-demand-forecast-golden",
        "operations-routing-policy-simulator",
        "prompt-safety",
        "recommendation-item-cf-offline-ranking",
        "sequence-risk-baseline-golden",
        "speech-quality-golden",
        "support-agent-assist-golden",
        "support-knowledge-hybrid-retrieval",
        "support-knowledge-retrieval",
        "support-knowledge-vector-index",
        "support-rag-answer",
        "support-sla-risk-golden",
    }

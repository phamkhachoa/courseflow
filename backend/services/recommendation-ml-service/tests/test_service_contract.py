from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from courseflow_ml.domain.recommendation import (
    ModelActivationApprovalRecord,
    ModelOpsAuditRecord,
    ModelVersionRecord,
    ScoredRecommendation,
    TrainingInteraction,
    TrainingJobRecord,
    TrainingOpsAuditRecord,
    TrainingRunRecord,
)
from courseflow_ml.repositories.postgres_recommendation_repository import (
    model_activation_approval_evidence,
)
from courseflow_ml.repositories.recommendation_repository import (
    PendingModelActivationApprovalError,
)
from courseflow_ml.services.recommendation_service import (
    RecommendationBadRequestError,
    RecommendationMlService,
    training_request_hash,
)

COURSE_A = UUID("30000000-0000-0000-0000-000000000001")
COURSE_B = UUID("30000000-0000-0000-0000-000000000002")


class RecommendationMlServiceContractTest(unittest.TestCase):
    def test_training_response_matches_java_analytics_contract(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(
            repository,
            min_activation_event_count=2,
            min_activation_principal_count=1,
        )
        response = cast(
            dict[str, Any],
            service.train_related_courses(
                uuid4(),
                "ml-v1",
                1,
                10,
                [
                    TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                    TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
                ],
                "service:analytics",
            ),
        )

        self.assertEqual(response["modelVersion"], "ml-v1")
        self.assertEqual(response["status"], "ACTIVE")
        self.assertEqual(response["algorithm"], "IMPLICIT_ITEM_CF_V1")
        self.assertGreaterEqual(response["pairCount"], 1)
        self.assertIn("recommendations", response)
        recommendations = cast(list[dict[str, object]], response["recommendations"])
        first = recommendations[0]
        self.assertIn("courseId", first)
        self.assertIn("relatedCourseId", first)
        self.assertIn("reasonCode", first)

    def test_requested_model_version_rejects_unsafe_registry_identifiers(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(repository)

        with self.assertRaisesRegex(RecommendationBadRequestError, "modelVersion may only"):
            service.enqueue_related_courses(
                uuid4(),
                "../bad model",
                1,
                10,
                [
                    TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                    TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
                ],
                "service:analytics",
            )

        self.assertEqual(repository.runs, {})

    def test_training_request_rejects_unsupported_event_type_before_queueing(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(repository)

        with self.assertRaisesRegex(
            RecommendationBadRequestError,
            "Unsupported training eventType",
        ):
            service.enqueue_related_courses(
                uuid4(),
                "ml-invalid-event-v1",
                1,
                10,
                [
                    TrainingInteraction("learner-1", COURSE_A, "PURCHASE"),
                    TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
                ],
                "service:analytics",
            )

        self.assertEqual(repository.runs, {})

    def test_async_training_queue_can_be_processed_by_worker(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(
            repository,
            min_activation_event_count=2,
            min_activation_principal_count=1,
        )
        training_run_id = uuid4()

        queued = service.enqueue_related_courses(
            training_run_id,
            "ml-async-v1",
            1,
            10,
            [
                TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
            ],
            "service:analytics",
        )

        self.assertEqual(queued["status"], "QUEUED")
        processed = service.process_next_training_job("worker-1")
        self.assertIsNotNone(processed)
        processed_response = cast(dict[str, object], processed)
        self.assertEqual(processed_response["status"], "ACTIVE")
        self.assertEqual(processed_response["modelVersion"], "ml-async-v1")

        status = service.training_run(training_run_id)
        self.assertEqual(status["status"], "ACTIVE")
        self.assertGreaterEqual(cast(int, status["pairCount"]), 1)

    def test_async_training_payload_pseudonymizes_principal_ids_at_rest(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(
            repository,
            min_activation_event_count=2,
            min_activation_principal_count=1,
            principal_hash_secret="courseflow-test-recommendation-ml-principal-hash-secret-32",
        )
        training_run_id = uuid4()

        service.enqueue_related_courses(
            training_run_id,
            "ml-pseudonymized-v1",
            1,
            10,
            [
                TrainingInteraction("learner-raw-1", COURSE_A, "enrollment"),
                TrainingInteraction("learner-raw-1", COURSE_B, "enrollment"),
            ],
            "service:analytics",
        )

        payload_json = repository.payloads[training_run_id]
        payload = json.loads(payload_json)
        self.assertNotIn("learner-raw-1", payload_json)
        self.assertEqual(payload["principalIdEncoding"], "hmac-sha256:v1")
        self.assertIn("principalHash", payload["interactions"][0])
        self.assertNotIn("principalId", payload["interactions"][0])
        self.assertEqual(payload["interactions"][0]["eventType"], "ENROLLMENT")

        processed = service.process_next_training_job("worker-1")

        self.assertIsNotNone(processed)
        self.assertEqual(cast(dict[str, object], processed)["status"], "ACTIVE")

    def test_duplicate_training_run_accepts_legacy_raw_principal_request_hash(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(
            repository,
            principal_hash_secret="courseflow-test-recommendation-ml-principal-hash-secret-32",
        )
        training_run_id = uuid4()
        interactions = [
            TrainingInteraction("learner-legacy-1", COURSE_A, "ENROLLMENT"),
            TrainingInteraction("learner-legacy-1", COURSE_B, "ENROLLMENT"),
        ]
        legacy_hash = training_request_hash("ml-legacy-hash-v1", 1, 10, interactions, None)
        repository.enqueue_training_run(
            training_run_id,
            "ml-legacy-hash-v1",
            "IMPLICIT_ITEM_CF_V1",
            legacy_hash,
            1,
            10,
            "service:analytics",
            json.dumps({"interactions": []}),
            datetime.now(UTC),
        )

        duplicate = service.enqueue_related_courses(
            training_run_id,
            "ml-legacy-hash-v1",
            1,
            10,
            interactions,
            "service:analytics",
        )

        self.assertEqual(duplicate["status"], "QUEUED")

    def test_stale_running_job_is_requeued_and_processed(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(
            repository,
            min_activation_event_count=2,
            min_activation_principal_count=1,
            training_job_lease_seconds=60,
            training_job_requeue_delay_seconds=0,
        )
        training_run_id = uuid4()
        service.enqueue_related_courses(
            training_run_id,
            "ml-recovered-v1",
            1,
            10,
            [
                TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
            ],
            "service:analytics",
        )
        repository.claim_next_training_job("dead-worker", datetime.now(UTC))
        repository.locked_at[training_run_id] = datetime(2026, 1, 1, tzinfo=UTC)

        processed = service.process_next_training_job("replacement-worker")

        self.assertIsNotNone(processed)
        processed_response = cast(dict[str, object], processed)
        self.assertEqual(processed_response["status"], "ACTIVE")
        self.assertEqual(processed_response["modelVersion"], "ml-recovered-v1")
        self.assertEqual(repository.recovered_jobs, 1)

    def test_stale_running_job_fails_after_max_attempts(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(
            repository,
            min_activation_event_count=2,
            min_activation_principal_count=1,
            training_job_lease_seconds=60,
            training_job_max_attempts=3,
            training_job_requeue_delay_seconds=0,
        )
        training_run_id = uuid4()
        service.enqueue_related_courses(
            training_run_id,
            "ml-failed-v1",
            1,
            10,
            [
                TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
            ],
            "service:analytics",
        )
        repository.claim_next_training_job("dead-worker", datetime.now(UTC))
        repository.locked_at[training_run_id] = datetime(2026, 1, 1, tzinfo=UTC)
        repository.attempts[training_run_id] = 3

        processed = service.process_next_training_job("replacement-worker")

        self.assertIsNone(processed)
        status = service.training_run(training_run_id)
        self.assertEqual(status["status"], "FAILED")
        self.assertEqual(status["message"], "Worker lease expired after max attempts")

    def test_training_run_fails_quality_gate_without_activating_model(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(
            repository,
            min_activation_event_count=10,
            min_activation_principal_count=2,
            min_activation_quality_score=0.95,
        )

        response = service.train_related_courses(
            uuid4(),
            "ml-quality-gated-v1",
            1,
            10,
            [
                TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
            ],
            "service:analytics",
        )

        self.assertEqual(response["status"], "QUALITY_GATE_FAILED")
        self.assertIsNone(response["modelVersion"])
        self.assertIn("activation quality gates", str(response["message"]))
        self.assertIsNone(repository.active_model())
        self.assertEqual(repository.scores, {})

    def test_training_can_register_candidate_until_checker_approval(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(
            repository,
            min_activation_event_count=2,
            min_activation_principal_count=1,
            auto_activate_trained_models=False,
        )
        training_run_id = uuid4()

        response = service.train_related_courses(
            training_run_id,
            "ml-candidate-v1",
            1,
            10,
            [
                TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
            ],
            "service:analytics",
        )

        self.assertEqual(response["status"], "PENDING_ACTIVATION")
        self.assertEqual(response["modelVersion"], "ml-candidate-v1")
        self.assertIsNone(repository.active_model())
        self.assertEqual(repository.models["ml-candidate-v1"].status, "CANDIDATE")
        self.assertEqual(repository.audits[-1].action, "TRAINING_CANDIDATE_REGISTERED")

        approval = service.request_model_activation(
            "ml-candidate-v1",
            "Promote candidate after offline validation",
            {"ticket": "ML-77"},
            "user:maker",
        )
        activated = service.approve_model_activation(
            UUID(str(approval["id"])),
            "Approved after validation",
            {"checkerTicket": "ML-78"},
            "user:checker",
        )

        self.assertEqual(activated["status"], "ACTIVE")
        self.assertEqual(repository.audits[-1].action, "TRAINING_ACTIVATED")
        training_run = repository.training_run(training_run_id)
        self.assertIsNotNone(training_run)
        self.assertEqual(cast(TrainingRunRecord, training_run).status, "ACTIVE")

    def test_model_activation_request_rejects_duplicate_pending_request(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(
            repository,
            min_activation_event_count=2,
            min_activation_principal_count=1,
            auto_activate_trained_models=False,
        )
        service.train_related_courses(
            uuid4(),
            "ml-candidate-duplicate-v1",
            1,
            10,
            [
                TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
            ],
            "service:analytics",
        )
        first = service.request_model_activation(
            "ml-candidate-duplicate-v1",
            "Promote candidate after offline validation",
            {"ticket": "ML-97"},
            "user:maker",
        )

        with self.assertRaisesRegex(Exception, "activation request is already pending"):
            service.request_model_activation(
                "ml-candidate-duplicate-v1",
                "Create a duplicated activation request",
                {"ticket": "ML-98"},
                "user:other-maker",
            )

        self.assertEqual(first["status"], "PENDING")
        pending = service.list_model_activation_approvals("PENDING", 10)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], first["id"])

    def test_candidate_activation_rejection_closes_candidate_and_training_run(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(
            repository,
            min_activation_event_count=2,
            min_activation_principal_count=1,
            auto_activate_trained_models=False,
        )
        training_run_id = uuid4()
        service.train_related_courses(
            training_run_id,
            "ml-candidate-rejected-v1",
            1,
            10,
            [
                TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
            ],
            "service:analytics",
        )
        approval = service.request_model_activation(
            "ml-candidate-rejected-v1",
            "Promote candidate after offline validation",
            {"ticket": "ML-87"},
            "user:maker",
        )

        rejected = service.reject_model_activation(
            UUID(str(approval["id"])),
            "Offline validation did not meet expected lift",
            {"checkerTicket": "ML-88"},
            "user:checker",
        )

        self.assertEqual(rejected["status"], "REJECTED")
        self.assertEqual(repository.models["ml-candidate-rejected-v1"].status, "REJECTED")
        training_run = repository.training_run(training_run_id)
        self.assertIsNotNone(training_run)
        self.assertEqual(cast(TrainingRunRecord, training_run).status, "ACTIVATION_REJECTED")
        self.assertEqual(cast(TrainingRunRecord, training_run).error_class, "ACTIVATION_REJECTED")
        self.assertEqual(repository.audits[-1].action, "MODEL_ACTIVATION_REJECTED")
        with self.assertRaisesRegex(Exception, "model version was rejected"):
            service.request_model_activation(
                "ml-candidate-rejected-v1",
                "Try rejected candidate again",
                None,
                "user:maker",
            )

    def test_model_reactivation_requires_checker_and_writes_audit(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(
            repository,
            min_activation_event_count=2,
            min_activation_principal_count=1,
        )
        interactions = [
            TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
            TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
        ]
        service.train_related_courses(uuid4(), "ml-v1", 1, 10, interactions, "service:analytics")
        service.train_related_courses(uuid4(), "ml-v2", 1, 10, interactions, "service:analytics")

        with self.assertRaisesRegex(Exception, "Direct model reactivation is disabled"):
            service.reactivate_model_version(
                "ml-v1",
                "Rollback after degraded CTR",
                {"incidentId": "INC-42"},
                "user:admin",
            )

        approval = service.request_model_activation(
            "ml-v1",
            "Rollback after degraded CTR",
            {"incidentId": "INC-42"},
            "user:admin",
        )
        with self.assertRaisesRegex(Exception, "maker cannot approve"):
            service.approve_model_activation(
                UUID(str(approval["id"])),
                "Approval by same actor should fail",
                None,
                "user:admin",
            )
        response = service.approve_model_activation(
            UUID(str(approval["id"])),
            "Approved after support validation",
            {"checkerTicket": "OPS-42"},
            "user:reviewer",
        )

        self.assertEqual(response["modelVersion"], "ml-v1")
        self.assertEqual(response["status"], "ACTIVE")
        self.assertEqual(repository.models["ml-v2"].status, "SUPERSEDED")
        audits = service.list_model_ops_audit(10)
        self.assertEqual(audits[0]["action"], "MODEL_REACTIVATED")
        self.assertEqual(audits[0]["modelVersion"], "ml-v1")
        self.assertEqual(audits[0]["previousActiveModelVersion"], "ml-v2")
        evidence = cast(dict[str, object], audits[0]["evidence"])
        self.assertEqual(evidence["approvalId"], approval["id"])
        self.assertEqual(evidence["requestedBy"], "user:admin")
        self.assertEqual(repository.approvals[UUID(str(approval["id"]))].status, "EXECUTED")

    def test_model_activation_audit_evidence_remains_parseable_above_two_kb(self) -> None:
        approval_id = uuid4()
        request_evidence = json.dumps(
            {
                "changeTicket": "ML-900",
                "operatorNote": "x" * 900,
                "validationSummary": "candidate passed offline validation",
            },
            sort_keys=True,
        )
        review_evidence = json.dumps(
            {
                "checkerTicket": "ML-901",
                "reviewNote": "y" * 900,
                "decision": "approved",
            },
            sort_keys=True,
        )

        evidence_json = model_activation_approval_evidence(
            approval_id,
            "user:maker",
            "Checker approved after reviewing offline lift and rollback plan " + ("z" * 400),
            request_evidence,
            review_evidence,
        )
        parsed = json.loads(evidence_json)

        self.assertGreater(len(evidence_json), 2000)
        self.assertEqual(parsed["approvalId"], str(approval_id))
        self.assertEqual(parsed["requestEvidence"]["changeTicket"], "ML-900")
        self.assertEqual(parsed["reviewEvidence"]["checkerTicket"], "ML-901")

    def test_ops_lists_training_runs_and_model_versions(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(
            repository,
            min_activation_event_count=2,
            min_activation_principal_count=1,
        )
        service.train_related_courses(
            uuid4(),
            "ml-list-v1",
            1,
            10,
            [
                TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
            ],
            "service:analytics",
        )

        runs = service.list_training_runs("active", 10)
        models = service.list_model_versions("active", 10)

        self.assertEqual(runs[0]["status"], "ACTIVE")
        self.assertEqual(models[0]["modelVersion"], "ml-list-v1")

    def test_ops_status_filters_reject_unknown_values(self) -> None:
        service = RecommendationMlService(InMemoryRecommendationRepository())

        with self.assertRaisesRegex(RecommendationBadRequestError, "Unsupported training run"):
            service.list_training_runs("activ", 10)
        with self.assertRaisesRegex(RecommendationBadRequestError, "Unsupported model version"):
            service.list_model_versions("activ", 10)
        with self.assertRaisesRegex(
            RecommendationBadRequestError,
            "Unsupported model activation approval",
        ):
            service.list_model_activation_approvals("pendng", 10)

    def test_cancel_queued_training_run_writes_audit(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(repository)
        training_run_id = uuid4()
        service.enqueue_related_courses(
            training_run_id,
            "ml-cancel-v1",
            1,
            10,
            [
                TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
            ],
            "service:analytics",
        )

        response = service.cancel_training_run(
            training_run_id,
            "Operator cancelled duplicated batch",
            {"ticket": "OPS-7"},
            "user:admin",
        )

        self.assertEqual(response["status"], "CANCELLED")
        audits = service.list_training_ops_audit(10)
        self.assertEqual(audits[0]["action"], "TRAINING_CANCELLED")
        self.assertEqual(audits[0]["previousStatus"], "QUEUED")
        self.assertEqual(cast(dict[str, object], audits[0]["evidence"])["ticket"], "OPS-7")

    def test_requeue_cancelled_training_run_writes_audit_and_worker_processes_it(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(
            repository,
            min_activation_event_count=2,
            min_activation_principal_count=1,
        )
        training_run_id = uuid4()
        service.enqueue_related_courses(
            training_run_id,
            "ml-requeue-v1",
            1,
            10,
            [
                TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
            ],
            "service:analytics",
        )
        service.cancel_training_run(
            training_run_id,
            "Operator cancelled duplicated batch",
            None,
            "user:admin",
        )

        requeued = service.requeue_training_run(
            training_run_id,
            "Retry after support review",
            {"ticket": "OPS-8"},
            "user:admin",
        )
        processed = service.process_next_training_job("worker-1")

        self.assertEqual(requeued["status"], "QUEUED")
        self.assertIsNotNone(processed)
        self.assertEqual(cast(dict[str, object], processed)["status"], "ACTIVE")
        audits = service.list_training_ops_audit(10)
        self.assertEqual(audits[0]["action"], "TRAINING_REQUEUED")
        self.assertEqual(audits[0]["previousStatus"], "CANCELLED")

    def test_ops_audit_evidence_rejects_sensitive_fields_before_writing_audit(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(repository)
        training_run_id = uuid4()
        service.enqueue_related_courses(
            training_run_id,
            "ml-sensitive-evidence-v1",
            1,
            10,
            [
                TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
            ],
            "service:analytics",
        )

        with self.assertRaisesRegex(RecommendationBadRequestError, "sensitive field"):
            service.cancel_training_run(
                training_run_id,
                "Operator cancels duplicated training batch",
                {"accessToken": "Bearer should-never-be-audited"},
                "user:admin",
            )

        self.assertEqual(repository.runs[training_run_id].status, "QUEUED")
        self.assertEqual(repository.training_audits, [])

    def test_ops_audit_evidence_rejects_oversized_payload_without_truncation(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(repository)
        training_run_id = uuid4()
        service.enqueue_related_courses(
            training_run_id,
            "ml-oversized-evidence-v1",
            1,
            10,
            [
                TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
                TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
            ],
            "service:analytics",
        )

        with self.assertRaisesRegex(RecommendationBadRequestError, "exceeds 2000"):
            service.cancel_training_run(
                training_run_id,
                "Operator cancels duplicated training batch",
                {
                    "operatorNote1": "x" * 800,
                    "operatorNote2": "x" * 800,
                    "operatorNote3": "x" * 800,
                },
                "user:admin",
            )

        self.assertEqual(repository.runs[training_run_id].status, "QUEUED")
        self.assertEqual(repository.training_audits, [])

    def test_scrubs_expired_training_payloads_without_deleting_run_metadata(self) -> None:
        repository = InMemoryRecommendationRepository()
        service = RecommendationMlService(repository, training_payload_retention_days=7)
        observed_at = datetime(2026, 6, 15, tzinfo=UTC)
        old_run_id = uuid4()
        recent_run_id = uuid4()
        queued_run_id = uuid4()
        interactions = [
            TrainingInteraction("learner-1", COURSE_A, "ENROLLMENT"),
            TrainingInteraction("learner-1", COURSE_B, "ENROLLMENT"),
        ]
        for run_id, version in (
            (old_run_id, "ml-old-payload-v1"),
            (recent_run_id, "ml-recent-payload-v1"),
            (queued_run_id, "ml-queued-payload-v1"),
        ):
            service.enqueue_related_courses(
                run_id,
                version,
                1,
                10,
                interactions,
                "service:analytics",
            )
        repository.finish_training_run(
            old_run_id,
            "FAILED",
            None,
            2,
            1,
            2,
            0,
            0.0,
            "TEST_FAILURE",
            "old payload",
            observed_at - timedelta(days=10),
        )
        repository.finish_training_run(
            recent_run_id,
            "FAILED",
            None,
            2,
            1,
            2,
            0,
            0.0,
            "TEST_FAILURE",
            "recent payload",
            observed_at - timedelta(days=2),
        )

        scrubbed = service.scrub_expired_training_payloads(observed_at)

        self.assertEqual(scrubbed, 1)
        self.assertNotIn(old_run_id, repository.payloads)
        self.assertIn(recent_run_id, repository.payloads)
        self.assertIn(queued_run_id, repository.payloads)
        self.assertEqual(repository.runs[old_run_id].status, "FAILED")
        self.assertIsNotNone(repository.runs[old_run_id].request_hash)


class InMemoryRecommendationRepository:
    def __init__(self) -> None:
        self.runs: dict[UUID, TrainingRunRecord] = {}
        self.models: dict[str, ModelVersionRecord] = {}
        self.scores: dict[str, list[ScoredRecommendation]] = {}
        self.audits: list[ModelOpsAuditRecord] = []
        self.approvals: dict[UUID, ModelActivationApprovalRecord] = {}
        self.training_audits: list[TrainingOpsAuditRecord] = []
        self.payloads: dict[UUID, str] = {}
        self.attempts: dict[UUID, int] = {}
        self.locked_at: dict[UUID, datetime] = {}
        self.available_at: dict[UUID, datetime] = {}
        self.recovered_jobs = 0

    def training_run(self, run_id: UUID) -> TrainingRunRecord | None:
        return self.runs.get(run_id)

    def model_version(self, model_version: str) -> ModelVersionRecord | None:
        return self.models.get(model_version)

    def active_model(self) -> ModelVersionRecord | None:
        return next((model for model in self.models.values() if model.status == "ACTIVE"), None)

    def list_training_runs(self, status: str | None, limit: int) -> list[TrainingRunRecord]:
        runs = list(self.runs.values())
        if status is not None:
            runs = [run for run in runs if run.status == status]
        return sorted(runs, key=lambda run: run.started_at, reverse=True)[:limit]

    def list_model_versions(self, status: str | None, limit: int) -> list[ModelVersionRecord]:
        models = list(self.models.values())
        if status is not None:
            models = [model for model in models if model.status == status]
        sorted_models = sorted(
            models,
            key=lambda model: model.activated_at or model.trained_at,
            reverse=True,
        )
        return sorted_models[:limit]

    def list_model_ops_audit(self, limit: int) -> list[ModelOpsAuditRecord]:
        return sorted(self.audits, key=lambda row: row.created_at, reverse=True)[:limit]

    def model_activation_approval(
        self,
        approval_id: UUID,
    ) -> ModelActivationApprovalRecord | None:
        return self.approvals.get(approval_id)

    def list_model_activation_approvals(
        self,
        status: str | None,
        limit: int,
    ) -> list[ModelActivationApprovalRecord]:
        approvals = list(self.approvals.values())
        if status is not None:
            approvals = [approval for approval in approvals if approval.status == status]
        return sorted(approvals, key=lambda row: row.created_at, reverse=True)[:limit]

    def pending_model_activation_approval(
        self,
        model_version: str,
    ) -> ModelActivationApprovalRecord | None:
        pending = [
            approval
            for approval in self.approvals.values()
            if approval.model_version == model_version and approval.status == "PENDING"
        ]
        if not pending:
            return None
        return sorted(pending, key=lambda row: row.created_at, reverse=True)[0]

    def list_training_ops_audit(self, limit: int) -> list[TrainingOpsAuditRecord]:
        return sorted(self.training_audits, key=lambda row: row.created_at, reverse=True)[:limit]

    def scores_for_model(self, model_version: str) -> list[ScoredRecommendation]:
        return self.scores.get(model_version, [])

    def scores_for_course(
        self,
        model_version: str,
        course_id: UUID,
        limit: int,
    ) -> list[ScoredRecommendation]:
        return [
            score
            for score in self.scores.get(model_version, [])
            if score.course_id == course_id
        ][:limit]

    def create_training_run(
        self,
        run_id: UUID,
        requested_model_version: str | None,
        algorithm: str,
        request_hash: str,
        min_support: int,
        max_related_per_course: int,
        requested_by: str,
        started_at: datetime,
    ) -> None:
        self.runs[run_id] = TrainingRunRecord(
            run_id,
            requested_model_version,
            None,
            algorithm,
            "STARTED",
            request_hash,
            0,
            0,
            0,
            0,
            0.0,
            min_support,
            max_related_per_course,
            None,
            None,
            requested_by,
            started_at,
            None,
        )

    def enqueue_training_run(
        self,
        run_id: UUID,
        requested_model_version: str | None,
        algorithm: str,
        request_hash: str,
        min_support: int,
        max_related_per_course: int,
        requested_by: str,
        payload_json: str,
        queued_at: datetime,
    ) -> TrainingRunRecord:
        run = TrainingRunRecord(
            run_id,
            requested_model_version,
            None,
            algorithm,
            "QUEUED",
            request_hash,
            0,
            0,
            0,
            0,
            0.0,
            min_support,
            max_related_per_course,
            None,
            None,
            requested_by,
            queued_at,
            None,
        )
        self.runs[run_id] = run
        self.payloads[run_id] = payload_json
        self.attempts[run_id] = 0
        self.available_at[run_id] = queued_at
        return run

    def claim_next_training_job(
        self,
        worker_id: str,
        claimed_at: datetime,
    ) -> TrainingJobRecord | None:
        del worker_id
        queued = next(
            (
                run
                for run in self.runs.values()
                if run.status == "QUEUED"
                and self.available_at.get(run.id, claimed_at) <= claimed_at
            ),
            None,
        )
        if queued is None:
            return None
        self.attempts[queued.id] = self.attempts.get(queued.id, 0) + 1
        self.locked_at[queued.id] = claimed_at
        running = TrainingRunRecord(
            queued.id,
            queued.requested_model_version,
            queued.activated_model_version,
            queued.algorithm,
            "RUNNING",
            queued.request_hash,
            queued.event_count,
            queued.principal_count,
            queued.course_count,
            queued.pair_count,
            queued.quality_score,
            queued.min_support,
            queued.max_related_per_course,
            queued.error_class,
            queued.error_message,
            queued.requested_by,
            queued.started_at,
            queued.finished_at,
        )
        self.runs[queued.id] = running
        return TrainingJobRecord(running, self.payloads[queued.id])

    def recover_stale_training_jobs(
        self,
        stale_before: datetime,
        recovered_at: datetime,
        max_attempts: int,
        requeue_delay_seconds: int,
    ) -> int:
        recovered = 0
        for run in list(self.runs.values()):
            if run.status != "RUNNING":
                continue
            locked_at = self.locked_at.get(run.id)
            if locked_at is None or locked_at >= stale_before:
                continue
            recovered += 1
            if self.attempts.get(run.id, 0) >= max_attempts:
                self.runs[run.id] = self._copy_run(
                    run,
                    status="FAILED",
                    error_class="WORKER_LEASE_EXPIRED",
                    error_message="Worker lease expired after max attempts",
                    finished_at=recovered_at,
                )
            else:
                self.runs[run.id] = self._copy_run(
                    run,
                    status="QUEUED",
                    error_class="WORKER_LEASE_EXPIRED",
                    error_message="Worker lease expired; job was requeued",
                )
                self.available_at[run.id] = recovered_at + timedelta(seconds=requeue_delay_seconds)
            self.locked_at.pop(run.id, None)
        self.recovered_jobs += recovered
        return recovered

    def scrub_training_payloads(
        self,
        completed_before: datetime,
        statuses: tuple[str, ...],
    ) -> int:
        scrubbed = 0
        eligible_statuses = set(statuses)
        for run_id, run in list(self.runs.items()):
            if (
                run_id in self.payloads
                and run.status in eligible_statuses
                and run.finished_at is not None
                and run.finished_at < completed_before
            ):
                self.payloads.pop(run_id, None)
                scrubbed += 1
        return scrubbed

    def finish_training_run(
        self,
        run_id: UUID,
        status: str,
        activated_model_version: str | None,
        event_count: int,
        principal_count: int,
        course_count: int,
        pair_count: int,
        quality_score: float,
        error_class: str | None,
        error_message: str | None,
        finished_at: datetime,
    ) -> TrainingRunRecord:
        existing = self.runs[run_id]
        if existing.status == "CANCELLED":
            return existing
        run = TrainingRunRecord(
            run_id,
            existing.requested_model_version,
            activated_model_version,
            existing.algorithm,
            status,
            existing.request_hash,
            event_count,
            principal_count,
            course_count,
            pair_count,
            quality_score,
            existing.min_support,
            existing.max_related_per_course,
            error_class,
            error_message,
            existing.requested_by,
            existing.started_at,
            finished_at,
        )
        self.runs[run_id] = run
        self.locked_at.pop(run_id, None)
        return run

    def activate_model(
        self,
        run_id: UUID,
        model_version: str,
        algorithm: str,
        event_count: int,
        principal_count: int,
        course_count: int,
        pair_count: int,
        quality_score: float,
        params_json: str,
        training_hash: str,
        created_by: str,
        trained_at: datetime,
        scores: list[ScoredRecommendation],
    ) -> bool:
        if self.runs[run_id].status == "CANCELLED":
            return False
        previous_active = self.active_model()
        for version, model in list(self.models.items()):
            if model.status == "ACTIVE":
                self.models[version] = ModelVersionRecord(
                    model.model_version,
                    model.algorithm,
                    "SUPERSEDED",
                    model.event_count,
                    model.principal_count,
                    model.course_count,
                    model.pair_count,
                    model.quality_score,
                    model.trained_at,
                    model.activated_at,
                )
        self.models[model_version] = ModelVersionRecord(
            model_version,
            algorithm,
            "ACTIVE",
            event_count,
            principal_count,
            course_count,
            pair_count,
            quality_score,
            trained_at,
            trained_at,
        )
        self.scores[model_version] = scores
        self.audits.append(
            ModelOpsAuditRecord(
                uuid4(),
                "TRAINING_ACTIVATED",
                model_version,
                previous_active.model_version if previous_active else None,
                created_by,
                "Training run activated automatically after quality gates",
                '{"trainingRunId":"' + str(run_id) + '","trainingHash":"' + training_hash + '"}',
                trained_at,
            )
        )
        return True

    def register_candidate_model(
        self,
        run_id: UUID,
        model_version: str,
        algorithm: str,
        event_count: int,
        principal_count: int,
        course_count: int,
        pair_count: int,
        quality_score: float,
        params_json: str,
        training_hash: str,
        created_by: str,
        trained_at: datetime,
        scores: list[ScoredRecommendation],
    ) -> bool:
        del params_json
        if self.runs[run_id].status == "CANCELLED":
            return False
        previous_active = self.active_model()
        self.models[model_version] = ModelVersionRecord(
            model_version,
            algorithm,
            "CANDIDATE",
            event_count,
            principal_count,
            course_count,
            pair_count,
            quality_score,
            trained_at,
            None,
        )
        self.scores[model_version] = scores
        self.audits.append(
            ModelOpsAuditRecord(
                uuid4(),
                "TRAINING_CANDIDATE_REGISTERED",
                model_version,
                previous_active.model_version if previous_active else None,
                created_by,
                "Training run registered a candidate model for approval",
                '{"trainingRunId":"' + str(run_id) + '","trainingHash":"' + training_hash + '"}',
                trained_at,
            )
        )
        return True

    def reactivate_model_version(
        self,
        model_version: str,
        actor_id: str,
        reason: str,
        evidence_json: str | None,
        activated_at: datetime,
    ) -> ModelVersionRecord | None:
        target = self.models.get(model_version)
        if target is None:
            return None
        previous_active = self.active_model()
        for version, model in list(self.models.items()):
            status = "ACTIVE" if version == model_version else "SUPERSEDED"
            activated = activated_at if version == model_version else model.activated_at
            self.models[version] = ModelVersionRecord(
                model.model_version,
                model.algorithm,
                status,
                model.event_count,
                model.principal_count,
                model.course_count,
                model.pair_count,
                model.quality_score,
                model.trained_at,
                activated,
            )
        self.audits.append(
            ModelOpsAuditRecord(
                uuid4(),
                "MODEL_REACTIVATED",
                model_version,
                previous_active.model_version if previous_active else None,
                actor_id,
                reason,
                evidence_json,
                activated_at,
            )
        )
        return self.models[model_version]

    def create_model_activation_approval(
        self,
        approval_id: UUID,
        model_version: str,
        requested_by: str,
        request_reason: str,
        request_evidence_json: str | None,
        created_at: datetime,
    ) -> ModelActivationApprovalRecord | None:
        if model_version not in self.models:
            return None
        if self.pending_model_activation_approval(model_version) is not None:
            raise PendingModelActivationApprovalError
        approval = ModelActivationApprovalRecord(
            approval_id,
            model_version,
            "PENDING",
            requested_by,
            request_reason,
            request_evidence_json,
            None,
            None,
            None,
            None,
            created_at,
            None,
            None,
        )
        self.approvals[approval_id] = approval
        return approval

    def approve_model_activation_approval(
        self,
        approval_id: UUID,
        reviewer_id: str,
        review_reason: str,
        review_evidence_json: str | None,
        reviewed_at: datetime,
    ) -> ModelVersionRecord | None:
        approval = self.approvals.get(approval_id)
        if (
            approval is None
            or approval.status != "PENDING"
            or approval.requested_by == reviewer_id
        ):
            return None
        previous_active = self.active_model()
        target = self.models.get(approval.model_version)
        if target is None or target.status not in {"CANDIDATE", "SUPERSEDED"}:
            return None
        for version, model in list(self.models.items()):
            activated: datetime | None
            if version == approval.model_version:
                status = "ACTIVE"
                activated = reviewed_at
            elif model.status == "ACTIVE":
                status = "SUPERSEDED"
                activated = model.activated_at
            else:
                status = model.status
                activated = model.activated_at
            self.models[version] = ModelVersionRecord(
                model.model_version,
                model.algorithm,
                status,
                model.event_count,
                model.principal_count,
                model.course_count,
                model.pair_count,
                model.quality_score,
                model.trained_at,
                activated,
            )
        for run_id, run in list(self.runs.items()):
            if (
                run.activated_model_version == approval.model_version
                and run.status == "PENDING_ACTIVATION"
                and target.status == "CANDIDATE"
            ):
                self.runs[run_id] = self._copy_run(
                    run,
                    status="ACTIVE",
                    error_class=None,
                    error_message=None,
                    finished_at=run.finished_at or reviewed_at,
                )
        self.approvals[approval_id] = ModelActivationApprovalRecord(
            approval.id,
            approval.model_version,
            "EXECUTED",
            approval.requested_by,
            approval.request_reason,
            approval.request_evidence_json,
            reviewer_id,
            review_reason,
            review_evidence_json,
            previous_active.model_version if previous_active else None,
            approval.created_at,
            reviewed_at,
            reviewed_at,
        )
        self.audits.append(
            ModelOpsAuditRecord(
                uuid4(),
                "TRAINING_ACTIVATED"
                if target.status == "CANDIDATE"
                else "MODEL_REACTIVATED",
                approval.model_version,
                previous_active.model_version if previous_active else None,
                reviewer_id,
                approval.request_reason,
                (
                    '{"approvalId":"'
                    + str(approval_id)
                    + '","requestedBy":"'
                    + approval.requested_by
                    + '"}'
                ),
                reviewed_at,
            )
        )
        return self.models[approval.model_version]

    def reject_model_activation_approval(
        self,
        approval_id: UUID,
        reviewer_id: str,
        review_reason: str,
        review_evidence_json: str | None,
        reviewed_at: datetime,
    ) -> ModelActivationApprovalRecord | None:
        approval = self.approvals.get(approval_id)
        if (
            approval is None
            or approval.status != "PENDING"
            or approval.requested_by == reviewer_id
        ):
            return None
        previous_active = self.active_model()
        target = self.models.get(approval.model_version)
        if target is None:
            return None
        if target.status == "CANDIDATE":
            self.models[approval.model_version] = ModelVersionRecord(
                target.model_version,
                target.algorithm,
                "REJECTED",
                target.event_count,
                target.principal_count,
                target.course_count,
                target.pair_count,
                target.quality_score,
                target.trained_at,
                target.activated_at,
            )
            for run_id, run in list(self.runs.items()):
                if (
                    run.activated_model_version == approval.model_version
                    and run.status == "PENDING_ACTIVATION"
                ):
                    self.runs[run_id] = self._copy_run(
                        run,
                        status="ACTIVATION_REJECTED",
                        error_class="ACTIVATION_REJECTED",
                        error_message=review_reason,
                        finished_at=reviewed_at,
                    )
        rejected = ModelActivationApprovalRecord(
            approval.id,
            approval.model_version,
            "REJECTED",
            approval.requested_by,
            approval.request_reason,
            approval.request_evidence_json,
            reviewer_id,
            review_reason,
            review_evidence_json,
            previous_active.model_version if previous_active else None,
            approval.created_at,
            reviewed_at,
            None,
        )
        self.approvals[approval_id] = rejected
        self.audits.append(
            ModelOpsAuditRecord(
                uuid4(),
                "MODEL_ACTIVATION_REJECTED",
                approval.model_version,
                previous_active.model_version if previous_active else None,
                reviewer_id,
                review_reason,
                (
                    '{"approvalId":"'
                    + str(approval_id)
                    + '","requestedBy":"'
                    + approval.requested_by
                    + '"}'
                ),
                reviewed_at,
            )
        )
        return rejected

    def cancel_training_run(
        self,
        run_id: UUID,
        actor_id: str,
        reason: str,
        evidence_json: str | None,
        cancelled_at: datetime,
    ) -> TrainingRunRecord | None:
        existing = self.runs.get(run_id)
        if existing is None or existing.status not in {"QUEUED", "RUNNING", "STARTED"}:
            return None
        cancelled = self._copy_run(
            existing,
            status="CANCELLED",
            error_class="CANCELLED_BY_OPERATOR",
            error_message=reason,
            finished_at=cancelled_at,
        )
        self.runs[run_id] = cancelled
        self.locked_at.pop(run_id, None)
        self.training_audits.append(
            TrainingOpsAuditRecord(
                uuid4(),
                "TRAINING_CANCELLED",
                run_id,
                existing.status,
                "CANCELLED",
                actor_id,
                reason,
                evidence_json,
                cancelled_at,
            )
        )
        return cancelled

    def requeue_training_run(
        self,
        run_id: UUID,
        actor_id: str,
        reason: str,
        evidence_json: str | None,
        requeued_at: datetime,
    ) -> TrainingRunRecord | None:
        existing = self.runs.get(run_id)
        if (
            existing is None
            or existing.status not in {"FAILED", "CANCELLED"}
            or existing.activated_model_version is not None
            or run_id not in self.payloads
        ):
            return None
        requeued = self._copy_run(
            existing,
            status="QUEUED",
            error_class=None,
            error_message=None,
            finished_at=None,
        )
        self.runs[run_id] = requeued
        self.available_at[run_id] = requeued_at
        self.training_audits.append(
            TrainingOpsAuditRecord(
                uuid4(),
                "TRAINING_REQUEUED",
                run_id,
                existing.status,
                "QUEUED",
                actor_id,
                reason,
                evidence_json,
                requeued_at,
            )
        )
        return requeued

    def _copy_run(
        self,
        run: TrainingRunRecord,
        status: str,
        error_class: str | None,
        error_message: str | None,
        finished_at: datetime | None = None,
    ) -> TrainingRunRecord:
        return TrainingRunRecord(
            run.id,
            run.requested_model_version,
            run.activated_model_version,
            run.algorithm,
            status,
            run.request_hash,
            run.event_count,
            run.principal_count,
            run.course_count,
            run.pair_count,
            run.quality_score,
            run.min_support,
            run.max_related_per_course,
            error_class,
            error_message,
            run.requested_by,
            run.started_at,
            finished_at,
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config

from courseflow_ml.core.config import Settings
from courseflow_ml.domain.recommendation import TrainingInteraction
from courseflow_ml.repositories.postgres_recommendation_repository import (
    PostgresRecommendationRepository,
)
from courseflow_ml.services.recommendation_service import (
    RecommendationConflictError,
    RecommendationMlService,
)

EXPECTED_REVISION = "007_model_activation_governance"
INTEGRATION_DB_URL_ENV = "RECOMMENDATION_ML_INTEGRATION_DB_URL"
LOCAL_INTERNAL_JWT_SECRET = "courseflow-local-internal-jwt-secret-change-me-32"


@unittest.skipUnless(
    os.getenv(INTEGRATION_DB_URL_ENV),
    f"set {INTEGRATION_DB_URL_ENV} to run Postgres integration tests",
)
class PostgresRecommendationRepositoryIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        integration_db_url = os.environ[INTEGRATION_DB_URL_ENV]
        os.environ["RECOMMENDATION_ML_DB_URL"] = integration_db_url
        os.environ.setdefault("COURSEFLOW_INTERNAL_JWT_SECRET", LOCAL_INTERNAL_JWT_SECRET)
        command.upgrade(Config("alembic.ini"), "head")

        settings = Settings()
        self.repository = PostgresRecommendationRepository(settings.database_url)
        self.service = RecommendationMlService(
            self.repository,
            min_activation_event_count=2,
            min_activation_principal_count=1,
            min_activation_course_count=2,
            min_activation_pair_count=1,
            min_activation_quality_score=0.0,
        )
        self.governed_service = RecommendationMlService(
            self.repository,
            min_activation_event_count=2,
            min_activation_principal_count=1,
            min_activation_course_count=2,
            min_activation_pair_count=1,
            min_activation_quality_score=0.0,
            auto_activate_trained_models=False,
        )

    def test_migrations_repository_training_ops_and_metrics_on_postgres(self) -> None:
        self.assertEqual(self.repository.current_migration_version(), EXPECTED_REVISION)

        active_run_id = uuid4()
        model_version = f"it-ml-{active_run_id.hex[:16]}"
        queued = self.service.enqueue_related_courses(
            active_run_id,
            model_version,
            1,
            10,
            integration_interactions(),
            "service:analytics",
        )
        self.assertEqual(queued["status"], "QUEUED")

        processed = self.service.process_next_training_job("integration-worker")
        self.assertIsNotNone(processed)
        if processed is None:
            raise AssertionError("worker did not process the queued job")
        self.assertEqual(processed["status"], "ACTIVE")
        self.assertEqual(processed["modelVersion"], model_version)
        active_model = self.repository.active_model()
        self.assertIsNotNone(active_model)
        if active_model is None:
            raise AssertionError("Postgres repository did not return the active model")
        self.assertEqual(active_model.model_version, model_version)

        newer_run_id = uuid4()
        newer_model_version = f"it-ml-{newer_run_id.hex[:16]}"
        self.service.enqueue_related_courses(
            newer_run_id,
            newer_model_version,
            1,
            10,
            integration_interactions(),
            "service:analytics",
        )
        newer_processed = self.service.process_next_training_job("integration-worker")
        self.assertIsNotNone(newer_processed)
        newer_active_model = self.repository.active_model()
        self.assertIsNotNone(newer_active_model)
        if newer_active_model is None:
            raise AssertionError("Postgres repository did not return the newer active model")
        self.assertEqual(newer_active_model.model_version, newer_model_version)

        with self.assertRaisesRegex(
            RecommendationConflictError,
            "Direct model reactivation is disabled",
        ):
            self.service.reactivate_model_version(
                model_version,
                "Direct activation should stay disabled on Postgres",
                {"testCase": "postgres-integration"},
                "user:integration-admin",
            )

        approval = self.service.request_model_activation(
            model_version,
            "Rollback after integration validation",
            {"testCase": "postgres-integration"},
            "user:integration-maker",
        )
        with self.assertRaises(RecommendationConflictError):
            self.service.approve_model_activation(
                UUID(str(approval["id"])),
                "Same maker cannot approve rollback",
                None,
                "user:integration-maker",
            )
        approved = self.service.approve_model_activation(
            UUID(str(approval["id"])),
            "Checker approved integration rollback",
            {"checker": "integration"},
            "user:integration-checker",
        )
        self.assertEqual(approved["modelVersion"], model_version)
        restored_active_model = self.repository.active_model()
        self.assertIsNotNone(restored_active_model)
        if restored_active_model is None:
            raise AssertionError("Postgres repository did not return the restored active model")
        self.assertEqual(restored_active_model.model_version, model_version)

        executed_approvals = self.service.list_model_activation_approvals("EXECUTED", 20)
        executed = next(
            row for row in executed_approvals if row["id"] == str(approval["id"])
        )
        self.assertEqual(executed["status"], "EXECUTED")
        self.assertEqual(executed["requestedBy"], "user:integration-maker")
        self.assertEqual(executed["reviewedBy"], "user:integration-checker")
        self.assertEqual(executed["previousActiveModelVersion"], newer_model_version)
        self.assertEqual(executed["reviewEvidence"], {"checker": "integration"})

        model_audits = self.service.list_model_ops_audit(20)
        model_reactivation_audit = next(
            row
            for row in model_audits
            if row["action"] == "MODEL_REACTIVATED"
            and row["modelVersion"] == model_version
            and row["actorId"] == "user:integration-checker"
        )
        self.assertEqual(
            model_reactivation_audit["previousActiveModelVersion"],
            newer_model_version,
        )
        model_reactivation_evidence = cast(
            dict[str, object],
            model_reactivation_audit["evidence"],
        )
        self.assertEqual(
            model_reactivation_evidence["approvalId"],
            str(approval["id"]),
        )

        reject_approval = self.service.request_model_activation(
            newer_model_version,
            "Reject newer model after rollback validation",
            {"testCase": "postgres-integration-reject"},
            "user:integration-maker",
        )
        rejected = self.service.reject_model_activation(
            UUID(str(reject_approval["id"])),
            "Checker rejected rollback reversal",
            {"checker": "integration-reject"},
            "user:integration-checker",
        )
        self.assertEqual(rejected["status"], "REJECTED")
        rejected_approvals = self.service.list_model_activation_approvals("REJECTED", 20)
        rejected_row = next(
            row for row in rejected_approvals if row["id"] == str(reject_approval["id"])
        )
        self.assertEqual(rejected_row["reviewedBy"], "user:integration-checker")
        self.assertEqual(
            rejected_row["reviewEvidence"],
            {"checker": "integration-reject"},
        )

        cancelled_run_id = uuid4()
        self.service.enqueue_related_courses(
            cancelled_run_id,
            f"it-cancel-{cancelled_run_id.hex[:16]}",
            1,
            10,
            integration_interactions(),
            "service:analytics",
        )
        cancelled = self.service.cancel_training_run(
            cancelled_run_id,
            "Integration test cancellation audit",
            {"testCase": "postgres-integration"},
            "user:integration-admin",
        )
        self.assertEqual(cancelled["status"], "CANCELLED")

        audits = self.service.list_training_ops_audit(10)
        self.assertEqual(audits[0]["action"], "TRAINING_CANCELLED")
        self.assertEqual(audits[0]["trainingRunId"], str(cancelled_run_id))
        self.assertEqual(audits[0]["previousStatus"], "QUEUED")

        observed_at = datetime.now(UTC)
        metrics = self.repository.operational_metrics(
            observed_at,
            observed_at - timedelta(seconds=1800),
            observed_at - timedelta(days=7),
            EXPECTED_REVISION,
        )
        self.assertTrue(metrics.migration_ready)
        self.assertTrue(metrics.active_model_present)
        self.assertGreaterEqual(metrics.training_runs_by_status.get("ACTIVE", 0), 1)
        self.assertGreaterEqual(metrics.training_runs_by_status.get("CANCELLED", 0), 1)

    def test_candidate_activation_governance_on_postgres(self) -> None:
        self.assertEqual(self.repository.current_migration_version(), EXPECTED_REVISION)

        baseline_run_id = uuid4()
        baseline_model_version = f"it-active-{baseline_run_id.hex[:16]}"
        self.service.enqueue_related_courses(
            baseline_run_id,
            baseline_model_version,
            1,
            10,
            integration_interactions(),
            "service:analytics",
        )
        baseline_processed = self.service.process_next_training_job("integration-worker")
        self.assertIsNotNone(baseline_processed)
        if baseline_processed is None:
            raise AssertionError("worker did not process the baseline active job")
        self.assertEqual(baseline_processed["status"], "ACTIVE")
        baseline_active_model = self.repository.active_model()
        self.assertIsNotNone(baseline_active_model)
        if baseline_active_model is None:
            raise AssertionError("Postgres repository did not return the baseline active model")
        self.assertEqual(baseline_active_model.model_version, baseline_model_version)

        candidate_run_id = uuid4()
        candidate_model_version = f"it-candidate-{candidate_run_id.hex[:16]}"
        self.governed_service.enqueue_related_courses(
            candidate_run_id,
            candidate_model_version,
            1,
            10,
            integration_interactions(),
            "service:analytics",
        )
        candidate_processed = self.governed_service.process_next_training_job(
            "integration-worker"
        )
        self.assertIsNotNone(candidate_processed)
        if candidate_processed is None:
            raise AssertionError("worker did not process the governed candidate job")
        self.assertEqual(candidate_processed["status"], "PENDING_ACTIVATION")
        self.assertEqual(candidate_processed["modelVersion"], candidate_model_version)
        active_after_candidate = self.repository.active_model()
        self.assertIsNotNone(active_after_candidate)
        if active_after_candidate is None:
            raise AssertionError("Postgres repository did not retain the active model")
        self.assertEqual(active_after_candidate.model_version, baseline_model_version)

        candidate_run = self.governed_service.training_run(candidate_run_id)
        self.assertEqual(candidate_run["status"], "PENDING_ACTIVATION")
        pending_training_runs = self.governed_service.list_training_runs(
            "PENDING_ACTIVATION",
            20,
        )
        self.assertTrue(
            any(row["trainingRunId"] == str(candidate_run_id) for row in pending_training_runs)
        )
        candidate_versions = self.governed_service.list_model_versions("CANDIDATE", 20)
        self.assertTrue(
            any(row["modelVersion"] == candidate_model_version for row in candidate_versions)
        )

        approval = self.governed_service.request_model_activation(
            candidate_model_version,
            "Promote governed candidate after Postgres integration validation",
            {"testCase": "candidate-governance"},
            "user:integration-maker",
        )
        observed_at = datetime.now(UTC)
        metrics_with_pending = self.repository.operational_metrics(
            observed_at,
            observed_at - timedelta(seconds=1800),
            observed_at - timedelta(days=7),
            EXPECTED_REVISION,
        )
        self.assertGreaterEqual(metrics_with_pending.pending_activation_approvals, 1)
        self.assertGreaterEqual(
            metrics_with_pending.oldest_pending_activation_approval_age_seconds,
            0.0,
        )

        with self.assertRaises(RecommendationConflictError):
            self.governed_service.approve_model_activation(
                UUID(str(approval["id"])),
                "Same maker cannot approve candidate",
                None,
                "user:integration-maker",
            )
        approved = self.governed_service.approve_model_activation(
            UUID(str(approval["id"])),
            "Checker approved governed candidate",
            {"checker": "integration"},
            "user:integration-checker",
        )
        self.assertEqual(approved["modelVersion"], candidate_model_version)
        self.assertEqual(approved["status"], "ACTIVE")
        active_model = self.repository.active_model()
        self.assertIsNotNone(active_model)
        if active_model is None:
            raise AssertionError("Postgres repository did not return the candidate active model")
        self.assertEqual(active_model.model_version, candidate_model_version)
        self.assertEqual(self.governed_service.training_run(candidate_run_id)["status"], "ACTIVE")

        executed_approvals = self.governed_service.list_model_activation_approvals(
            "EXECUTED",
            20,
        )
        executed = next(row for row in executed_approvals if row["id"] == str(approval["id"]))
        self.assertEqual(executed["previousActiveModelVersion"], baseline_model_version)
        self.assertEqual(executed["reviewedBy"], "user:integration-checker")

        model_audits = self.governed_service.list_model_ops_audit(40)
        self.assertTrue(
            any(
                row["action"] == "TRAINING_CANDIDATE_REGISTERED"
                and row["modelVersion"] == candidate_model_version
                for row in model_audits
            )
        )
        self.assertTrue(
            any(
                row["action"] == "TRAINING_ACTIVATED"
                and row["modelVersion"] == candidate_model_version
                and row["previousActiveModelVersion"] == baseline_model_version
                for row in model_audits
            )
        )

    def test_candidate_rejection_governance_on_postgres(self) -> None:
        self.assertEqual(self.repository.current_migration_version(), EXPECTED_REVISION)

        baseline_run_id = uuid4()
        baseline_model_version = f"it-reject-active-{baseline_run_id.hex[:12]}"
        self.service.enqueue_related_courses(
            baseline_run_id,
            baseline_model_version,
            1,
            10,
            integration_interactions(),
            "service:analytics",
        )
        baseline_processed = self.service.process_next_training_job("integration-worker")
        self.assertIsNotNone(baseline_processed)
        if baseline_processed is None:
            raise AssertionError("worker did not process the rejection baseline job")
        self.assertEqual(baseline_processed["status"], "ACTIVE")

        candidate_run_id = uuid4()
        candidate_model_version = f"it-reject-candidate-{candidate_run_id.hex[:12]}"
        self.governed_service.enqueue_related_courses(
            candidate_run_id,
            candidate_model_version,
            1,
            10,
            integration_interactions(),
            "service:analytics",
        )
        candidate_processed = self.governed_service.process_next_training_job(
            "integration-worker"
        )
        self.assertIsNotNone(candidate_processed)
        if candidate_processed is None:
            raise AssertionError("worker did not process the rejected candidate job")
        self.assertEqual(candidate_processed["status"], "PENDING_ACTIVATION")

        approval = self.governed_service.request_model_activation(
            candidate_model_version,
            "Reject governed candidate after Postgres integration validation",
            {"testCase": "candidate-rejection-governance"},
            "user:integration-maker",
        )
        with self.assertRaises(RecommendationConflictError):
            self.governed_service.reject_model_activation(
                UUID(str(approval["id"])),
                "Same maker cannot reject candidate",
                None,
                "user:integration-maker",
            )
        rejected = self.governed_service.reject_model_activation(
            UUID(str(approval["id"])),
            "Checker rejected governed candidate",
            {"checker": "integration"},
            "user:integration-checker",
        )
        self.assertEqual(rejected["status"], "REJECTED")
        active_model = self.repository.active_model()
        self.assertIsNotNone(active_model)
        if active_model is None:
            raise AssertionError("Postgres repository did not retain the baseline active model")
        self.assertEqual(active_model.model_version, baseline_model_version)

        rejected_model = self.repository.model_version(candidate_model_version)
        self.assertIsNotNone(rejected_model)
        if rejected_model is None:
            raise AssertionError("Postgres repository did not return the rejected model")
        self.assertEqual(rejected_model.status, "REJECTED")
        rejected_run = self.governed_service.training_run(candidate_run_id)
        self.assertEqual(rejected_run["status"], "ACTIVATION_REJECTED")

        rejected_approvals = self.governed_service.list_model_activation_approvals(
            "REJECTED",
            20,
        )
        rejected_row = next(row for row in rejected_approvals if row["id"] == str(approval["id"]))
        self.assertEqual(rejected_row["previousActiveModelVersion"], baseline_model_version)
        self.assertEqual(rejected_row["reviewedBy"], "user:integration-checker")

        model_audits = self.governed_service.list_model_ops_audit(40)
        self.assertTrue(
            any(
                row["action"] == "MODEL_ACTIVATION_REJECTED"
                and row["modelVersion"] == candidate_model_version
                and row["previousActiveModelVersion"] == baseline_model_version
                for row in model_audits
            )
        )


def integration_interactions() -> list[TrainingInteraction]:
    course_a = uuid4()
    course_b = uuid4()
    return [
        TrainingInteraction("learner-it-1", course_a, "ENROLLMENT"),
        TrainingInteraction("learner-it-1", course_b, "ENROLLMENT"),
    ]


if __name__ == "__main__":
    unittest.main()

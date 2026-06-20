from __future__ import annotations

import importlib
import os
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import Mock, patch
from uuid import UUID

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient

from courseflow_ml.core.config import Settings
from courseflow_ml.domain.recommendation import (
    ModelVersionRecord,
    RecommendationOperationalMetrics,
)
from courseflow_ml.services.recommendation_service import RecommendationBadRequestError

LOCAL_INTERNAL_JWT_SECRET = "courseflow-local-internal-jwt-secret-change-me-32"
os.environ.setdefault("COURSEFLOW_INTERNAL_JWT_SECRET", LOCAL_INTERNAL_JWT_SECRET)


class RecommendationMlAppSurfaceTest(unittest.TestCase):
    def test_openapi_and_docs_are_disabled_by_default(self) -> None:
        client = TestClient(create_app(settings_without_env()))

        self.assertEqual(client.get("/health").status_code, 200)
        self.assertEqual(client.get("/internal/recommendation-ml/docs").status_code, 404)
        self.assertEqual(client.get("/internal/recommendation-ml/openapi.json").status_code, 404)
        self.assertEqual(client.get("/redoc").status_code, 404)

    def test_openapi_and_docs_can_be_enabled_explicitly(self) -> None:
        client = TestClient(
            create_app(settings_without_env(recommendation_ml_docs_enabled=True))
        )

        self.assertEqual(client.get("/internal/recommendation-ml/openapi.json").status_code, 200)
        self.assertEqual(client.get("/internal/recommendation-ml/docs").status_code, 200)
        self.assertEqual(client.get("/redoc").status_code, 404)

    def test_readiness_returns_503_when_active_model_is_required_and_missing(self) -> None:
        client = TestClient(
            create_app(settings_without_env(recommendation_ml_require_active_model_ready=True))
        )

        with patched_repository(FakeRepository(active_model=None)):
            response = client.get("/actuator/health")

        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body["status"], "DOWN")
        self.assertEqual(body["components"]["activeModel"]["status"], "DOWN")

    def test_readiness_returns_200_when_required_active_model_exists(self) -> None:
        client = TestClient(
            create_app(
                settings_without_env(
                    recommendation_ml_require_active_model_ready=True,
                    recommendation_ml_auto_activate_trained_models=False,
                )
            )
        )

        with patched_repository(FakeRepository(active_model=model_record())):
            response = client.get("/actuator/health")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "UP")
        self.assertEqual(body["components"]["activeModel"]["status"], "UP")

    def test_http_metrics_use_route_templates_and_hide_unmatched_paths(self) -> None:
        client = TestClient(create_app(settings_without_env()))

        client.get("/health")
        client.get("/missing/30000000-0000-0000-0000-000000000001")
        with patched_repository(FakeReadinessAndTelemetryRepository(active_model=None)):
            response = client.get("/actuator/prometheus")

        body = response.text
        self.assertIn(
            'courseflow_recommendation_ml_http_requests_total{method="GET",'
            'route="/health",status_class="2xx"}',
            body,
        )
        self.assertIn(
            'courseflow_recommendation_ml_http_requests_total{method="GET",'
            'route="__unmatched__",status_class="4xx"}',
            body,
        )
        self.assertNotIn("/missing/30000000-0000-0000-0000-000000000001", body)

    def test_internal_auth_rejection_metric_records_invalid_jwt_reason(self) -> None:
        client = TestClient(create_app(settings_without_env()))

        response = client.get(
            "/internal/recommendation-ml/models",
            headers={"Authorization": "Bearer invalid.internal.jwt"},
        )
        with patched_repository(FakeReadinessAndTelemetryRepository(active_model=None)):
            metrics = client.get("/actuator/prometheus")

        self.assertEqual(response.status_code, 403)
        self.assertIn(
            'courseflow_recommendation_ml_internal_auth_rejections_total'
            '{reason="invalid_jwt"}',
            metrics.text,
        )

    def test_ops_routes_require_ops_scope_not_train_scope(self) -> None:
        app = create_app(settings_without_env())
        with overridden_service(app, FakeRecommendationService()):
            client = TestClient(app)

            train_response = client.get(
                "/internal/recommendation-ml/models",
                headers=auth_headers(
                    service_token("service:analytics", "internal:recommendation-ml:train")
                ),
            )
            ops_response = client.get(
                "/internal/recommendation-ml/models",
                headers=auth_headers(
                    service_token("service:ops-smoke", "internal:recommendation-ml:ops")
                ),
            )

        self.assertEqual(train_response.status_code, 403)
        self.assertEqual(ops_response.status_code, 200)
        self.assertEqual(ops_response.json()[0]["modelVersion"], "ml-v1")

    def test_ops_status_filter_validation_errors_return_400(self) -> None:
        for path, method_name in (
            ("/internal/recommendation-ml/training-runs?status=activ", "list_training_runs"),
            ("/internal/recommendation-ml/models?status=activ", "list_model_versions"),
            (
                "/internal/recommendation-ml/models/activation-requests?status=pendng",
                "list_model_activation_approvals",
            ),
        ):
            with self.subTest(path=path):
                app = create_app(settings_without_env())
                service = Mock()
                getattr(service, method_name).side_effect = RecommendationBadRequestError(
                    "Unsupported status filter"
                )
                with overridden_service(app, service):
                    client = TestClient(app)
                    response = client.get(
                        path,
                        headers=auth_headers(
                            service_token("service:ops-smoke", "internal:recommendation-ml:ops")
                        ),
                    )

                self.assertEqual(response.status_code, 400)
                self.assertIn("Unsupported status filter", response.json()["detail"])

    def test_internal_routes_reject_wildcard_service_scope(self) -> None:
        app = create_app(settings_without_env())
        with overridden_service(app, FakeRecommendationService()):
            client = TestClient(app)
            response = client.get(
                "/internal/recommendation-ml/models",
                headers=auth_headers(service_token("service:overbroad-client", "*")),
            )

        self.assertEqual(response.status_code, 403)

    def test_internal_scope_boundaries_are_least_privilege(self) -> None:
        app = create_app(settings_without_env())
        training_run_id = UUID("40000000-0000-0000-0000-000000000099")
        with overridden_service(app, FakeRecommendationService()):
            client = TestClient(app)

            infer_on_ops = client.get(
                "/internal/recommendation-ml/models",
                headers=auth_headers(
                    service_token("service:learner-api", "internal:recommendation-ml:infer")
                ),
            )
            train_on_infer = client.get(
                "/internal/recommendation-ml/models/active",
                headers=auth_headers(
                    service_token("service:analytics", "internal:recommendation-ml:train")
                ),
            )
            ops_on_infer = client.get(
                "/internal/recommendation-ml/models/active",
                headers=auth_headers(
                    service_token("service:ops-smoke", "internal:recommendation-ml:ops")
                ),
            )
            ops_on_training_status = client.get(
                f"/internal/recommendation-ml/training-runs/{training_run_id}",
                headers=auth_headers(
                    service_token("service:ops-smoke", "internal:recommendation-ml:ops")
                ),
            )
            infer_on_training_status = client.get(
                f"/internal/recommendation-ml/training-runs/{training_run_id}",
                headers=auth_headers(
                    service_token("service:learner-api", "internal:recommendation-ml:infer")
                ),
            )

        self.assertEqual(infer_on_ops.status_code, 403)
        self.assertEqual(train_on_infer.status_code, 403)
        self.assertEqual(ops_on_infer.status_code, 403)
        self.assertEqual(ops_on_training_status.status_code, 403)
        self.assertEqual(infer_on_training_status.status_code, 403)

    def test_train_scope_can_still_read_specific_training_run_status(self) -> None:
        app = create_app(settings_without_env())
        training_run_id = UUID("40000000-0000-0000-0000-000000000001")
        with overridden_service(app, FakeRecommendationService()):
            client = TestClient(app)
            response = client.get(
                f"/internal/recommendation-ml/training-runs/{training_run_id}",
                headers=auth_headers(
                    service_token("service:analytics", "internal:recommendation-ml:train")
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["trainingRunId"], str(training_run_id))

    def test_infer_scope_can_read_active_model_training_run_id(self) -> None:
        app = create_app(settings_without_env())
        with overridden_service(app, FakeRecommendationService()):
            client = TestClient(app)
            response = client.get(
                "/internal/recommendation-ml/models/active",
                headers=auth_headers(
                    service_token("service:analytics", "internal:recommendation-ml:infer")
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["trainingRunId"],
            "40000000-0000-0000-0000-000000000001",
        )

    def test_related_courses_validation_error_returns_400(self) -> None:
        app = create_app(settings_without_env())
        service = Mock()
        service.related_courses.side_effect = RecommendationBadRequestError(
            "modelVersion may only contain safe registry characters"
        )
        with overridden_service(app, service):
            client = TestClient(app)
            response = client.get(
                "/internal/recommendation-ml/courses/"
                "30000000-0000-0000-0000-000000000001/related"
                "?modelVersion=bad%20version",
                headers=auth_headers(
                    service_token("service:analytics", "internal:recommendation-ml:infer")
                ),
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("modelVersion may only", response.json()["detail"])

    def test_sync_training_endpoint_can_be_disabled_for_production(self) -> None:
        routes_module = importlib.import_module("courseflow_ml.api.recommendation_routes")
        app = create_app(settings_without_env())
        service = Mock()
        with (
            overridden_service(app, service),
            patch.object(
                routes_module,
                "get_settings",
                return_value=settings_without_env(
                    recommendation_ml_sync_training_enabled=False
                ),
            ),
        ):
            client = TestClient(app)
            response = client.post(
                "/internal/recommendation-ml/related-courses:train",
                headers=auth_headers(
                    service_token("service:analytics", "internal:recommendation-ml:train")
                ),
                json={
                    "trainingRunId": "40000000-0000-0000-0000-000000000002",
                    "requestedModelVersion": "sync-disabled-test",
                    "minSupport": 1,
                    "maxRelatedPerCourse": 4,
                    "interactions": [],
                },
            )

        self.assertEqual(response.status_code, 403)
        service.train_related_courses.assert_not_called()


class RecommendationMlWorkerCliTest(unittest.TestCase):
    def test_worker_uses_configured_activation_governance(self) -> None:
        cli_module = cast(Any, importlib.import_module("courseflow_ml.training.cli"))
        settings = settings_without_env(
            recommendation_ml_auto_activate_trained_models=False,
            recommendation_ml_db_url="postgresql://recommendation-db/recommendation_ml",
        )
        service = Mock()
        service.process_next_training_job.return_value = None
        service.scrub_expired_training_payloads.return_value = 0

        with (
            patch.object(cli_module, "get_settings", return_value=settings),
            patch.object(cli_module, "PostgresRecommendationRepository") as repository_class,
            patch.object(
                cli_module,
                "RecommendationMlService",
                return_value=service,
            ) as service_class,
        ):
            exit_code = cast(
                int,
                cli_module.run_worker("worker-1", once=True, idle_sleep_seconds=0.25),
            )

        self.assertEqual(exit_code, 0)
        repository_class.assert_called_once_with(settings.database_url)
        service_class.assert_called_once()
        self.assertIs(
            service_class.call_args.kwargs["auto_activate_trained_models"],
            False,
        )
        self.assertEqual(
            service_class.call_args.kwargs["training_payload_retention_days"],
            settings.recommendation_ml_training_payload_retention_days,
        )
        service.scrub_expired_training_payloads.assert_called_once()


def create_app(settings: Settings) -> FastAPI:
    main_module = importlib.import_module("courseflow_ml.main")
    factory = cast(Any, main_module).create_app
    return cast(FastAPI, factory(settings))


@contextmanager
def overridden_service(app: FastAPI, service: object) -> Iterator[None]:
    routes_module = importlib.import_module("courseflow_ml.api.recommendation_routes")
    dependency = cast(Any, routes_module).get_recommendation_service
    app.dependency_overrides[dependency] = lambda: service
    try:
        yield
    finally:
        app.dependency_overrides.pop(dependency, None)


@contextmanager
def patched_repository(repository: object) -> Iterator[None]:
    routes_module = importlib.import_module("courseflow_ml.api.recommendation_routes")
    main_module = importlib.import_module("courseflow_ml.main")
    original_routes_getter = cast(Any, routes_module).get_recommendation_repository
    original_main_getter = cast(Any, main_module).get_recommendation_repository
    cast(Any, routes_module).get_recommendation_repository = lambda: repository
    cast(Any, main_module).get_recommendation_repository = lambda: repository
    try:
        yield
    finally:
        cast(Any, routes_module).get_recommendation_repository = original_routes_getter
        cast(Any, main_module).get_recommendation_repository = original_main_getter


class FakeRepository:
    def __init__(self, active_model: ModelVersionRecord | None) -> None:
        self._active_model = active_model

    def database_ping(self) -> None:
        return None

    def current_migration_version(self) -> str:
        return "007_model_activation_governance"

    def active_model(self) -> ModelVersionRecord | None:
        return self._active_model


class FakeReadinessAndTelemetryRepository(FakeRepository):
    def operational_metrics(
        self,
        observed_at: datetime,
        stale_running_before: datetime,
        active_model_stale_before: datetime,
        expected_migration_revision: str,
    ) -> RecommendationOperationalMetrics:
        del observed_at, stale_running_before, active_model_stale_before
        if expected_migration_revision != "007_model_activation_governance":
            raise AssertionError("unexpected migration revision")
        return RecommendationOperationalMetrics(
            training_runs_by_status={},
            stale_running_training_runs=0,
            oldest_queued_age_seconds=0.0,
            oldest_running_age_seconds=0.0,
            pending_activation_approvals=0,
            oldest_pending_activation_approval_age_seconds=0.0,
            active_model_present=self.active_model() is not None,
            active_model_age_seconds=None,
            active_model_stale=False,
            migration_ready=True,
        )


class FakeRecommendationService:
    def list_model_versions(self, status: str | None, limit: int) -> list[dict[str, object]]:
        del status, limit
        return [model_dict()]

    def active_model(self) -> ModelVersionRecord:
        return model_record()

    def training_run(self, training_run_id: UUID) -> dict[str, object]:
        return {
            "trainingRunId": str(training_run_id),
            "modelVersion": "ml-v1",
            "status": "ACTIVE",
            "algorithm": "IMPLICIT_ITEM_CF_V1",
            "eventCount": 10,
            "principalCount": 3,
            "courseCount": 2,
            "pairCount": 2,
            "qualityScore": 0.8,
            "generatedAt": "2026-01-01T00:00:00Z",
            "message": None,
            "recommendations": [],
        }


def model_record() -> ModelVersionRecord:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return ModelVersionRecord(
        model_version="ml-v1",
        algorithm="IMPLICIT_ITEM_CF_V1",
        status="ACTIVE",
        event_count=10,
        principal_count=3,
        course_count=2,
        pair_count=2,
        quality_score=0.8,
        trained_at=now,
        activated_at=now,
        training_run_id=UUID("40000000-0000-0000-0000-000000000001"),
    )


def model_dict() -> dict[str, object]:
    return {
        "trainingRunId": "40000000-0000-0000-0000-000000000001",
        "modelVersion": "ml-v1",
        "algorithm": "IMPLICIT_ITEM_CF_V1",
        "status": "ACTIVE",
        "eventCount": 10,
        "principalCount": 3,
        "courseCount": 2,
        "pairCount": 2,
        "qualityScore": 0.8,
        "trainedAt": "2026-01-01T00:00:00Z",
        "activatedAt": "2026-01-01T00:00:00Z",
    }


def service_token(subject: str, scope: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": "courseflow-token-converter",
            "aud": "courseflow-services",
            "sub": subject,
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "token_use": "internal",
            "actor_type": "service",
            "scope": scope,
        },
        LOCAL_INTERNAL_JWT_SECRET,
        algorithm="HS256",
    )


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def settings_without_env(**overrides: object) -> Settings:
    factory = cast(Any, Settings)
    return cast(
        Settings,
        factory(
            _env_file=None,
            courseflow_internal_jwt_secret=LOCAL_INTERNAL_JWT_SECRET,
            **overrides,
        ),
    )


if __name__ == "__main__":
    unittest.main()

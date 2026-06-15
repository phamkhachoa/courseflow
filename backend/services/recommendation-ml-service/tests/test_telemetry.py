from __future__ import annotations

import unittest
from datetime import datetime

from courseflow_ml.core.telemetry import (
    prometheus_response,
    record_http_request,
    record_internal_auth_rejection,
)
from courseflow_ml.domain.recommendation import RecommendationOperationalMetrics


class PrometheusTelemetryTest(unittest.TestCase):
    def test_prometheus_response_refreshes_operational_gauges(self) -> None:
        response = prometheus_response(
            FakeTelemetryRepository(
                RecommendationOperationalMetrics(
                    training_runs_by_status={
                        "QUEUED": 3,
                        "RUNNING": 2,
                        "QUALITY_GATE_FAILED": 1,
                    },
                    stale_running_training_runs=1,
                    oldest_queued_age_seconds=900.0,
                    oldest_running_age_seconds=1900.0,
                    pending_activation_approvals=2,
                    oldest_pending_activation_approval_age_seconds=7200.0,
                    active_model_present=True,
                    active_model_age_seconds=86400.0,
                    active_model_stale=False,
                    migration_ready=True,
                )
            ),
            "007_model_activation_governance",
            1800,
            604800,
        )

        body = bytes(response.body).decode("utf-8")
        self.assertIn(
            'courseflow_recommendation_ml_training_runs_by_status{status="queued"} 3.0',
            body,
        )
        self.assertIn(
            'courseflow_recommendation_ml_training_runs_by_status{status="running"} 2.0',
            body,
        )
        self.assertIn(
            'courseflow_recommendation_ml_training_runs_by_status'
            '{status="quality_gate_failed"} 1.0',
            body,
        )
        self.assertIn("courseflow_recommendation_ml_training_stale_running_runs 1.0", body)
        self.assertIn(
            "courseflow_recommendation_ml_training_oldest_queued_age_seconds 900.0",
            body,
        )
        self.assertIn(
            "courseflow_recommendation_ml_pending_activation_approvals 2.0",
            body,
        )
        self.assertIn(
            "courseflow_recommendation_ml_oldest_pending_activation_approval_age_seconds 7200.0",
            body,
        )
        self.assertIn("courseflow_recommendation_ml_active_model_present 1.0", body)
        self.assertIn("courseflow_recommendation_ml_active_model_stale 0.0", body)
        self.assertIn("courseflow_recommendation_ml_migration_ready 1.0", body)

    def test_prometheus_response_records_refresh_error_without_failing_scrape(self) -> None:
        response = prometheus_response(
            FailingTelemetryRepository(),
            "007_model_activation_governance",
            1800,
            604800,
        )

        body = bytes(response.body).decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'courseflow_recommendation_ml_metrics_refresh_total{result="error"}',
            body,
        )

    def test_http_request_metrics_use_bounded_labels(self) -> None:
        record_http_request(
            "get",
            "/internal/recommendation-ml/courses/{course_id}/related",
            503,
            0.25,
        )

        body = bytes(prometheus_response().body).decode("utf-8")

        self.assertIn(
            'courseflow_recommendation_ml_http_requests_total{method="GET",'
            'route="/internal/recommendation-ml/courses/{course_id}/related",'
            'status_class="5xx"}',
            body,
        )

    def test_internal_auth_rejection_metric_uses_bounded_reason_label(self) -> None:
        record_internal_auth_rejection("Invalid JWT!")

        body = bytes(prometheus_response().body).decode("utf-8")

        self.assertIn(
            'courseflow_recommendation_ml_internal_auth_rejections_total'
            '{reason="invalid_jwt"}',
            body,
        )
        self.assertIn(
            'courseflow_recommendation_ml_http_request_duration_seconds_bucket'
            '{le="0.5",method="GET",'
            'route="/internal/recommendation-ml/courses/{course_id}/related",'
            'status_class="5xx"}',
            body,
        )


class FakeTelemetryRepository:
    def __init__(self, metrics: RecommendationOperationalMetrics) -> None:
        self.metrics = metrics

    def operational_metrics(
        self,
        observed_at: datetime,
        stale_running_before: datetime,
        active_model_stale_before: datetime,
        expected_migration_revision: str,
    ) -> RecommendationOperationalMetrics:
        del observed_at, stale_running_before, active_model_stale_before
        self.assert_expected_revision(expected_migration_revision)
        return self.metrics

    def assert_expected_revision(self, expected_migration_revision: str) -> None:
        if expected_migration_revision != "007_model_activation_governance":
            raise AssertionError("unexpected migration revision")


class FailingTelemetryRepository:
    def operational_metrics(
        self,
        observed_at: datetime,
        stale_running_before: datetime,
        active_model_stale_before: datetime,
        expected_migration_revision: str,
    ) -> RecommendationOperationalMetrics:
        del (
            observed_at,
            stale_running_before,
            active_model_stale_before,
            expected_migration_revision,
        )
        raise RuntimeError("db unavailable")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response

from courseflow_ml.domain.recommendation import RecommendationOperationalMetrics

TRAINING_STATUSES = (
    "QUEUED",
    "RUNNING",
    "STARTED",
    "ACTIVE",
    "PENDING_ACTIVATION",
    "ACTIVATION_REJECTED",
    "INSUFFICIENT_DATA",
    "QUALITY_GATE_FAILED",
    "FAILED",
    "CANCELLED",
)


class TelemetryRepository(Protocol):
    def operational_metrics(
        self,
        observed_at: datetime,
        stale_running_before: datetime,
        active_model_stale_before: datetime,
        expected_migration_revision: str,
    ) -> RecommendationOperationalMetrics:
        ...


training_runs_total: Any = Counter(
    "courseflow_recommendation_ml_training_runs_total",
    "Recommendation ML training runs by terminal status.",
    ["status"],
)
training_runs_by_status: Any = Gauge(
    "courseflow_recommendation_ml_training_runs_by_status",
    "Current Recommendation ML training runs by status.",
    ["status"],
)
training_stale_running_runs: Any = Gauge(
    "courseflow_recommendation_ml_training_stale_running_runs",
    "Current Recommendation ML RUNNING training jobs with expired worker leases.",
)
training_oldest_queued_age_seconds: Any = Gauge(
    "courseflow_recommendation_ml_training_oldest_queued_age_seconds",
    "Age in seconds of the oldest queued Recommendation ML training job.",
)
training_oldest_running_age_seconds: Any = Gauge(
    "courseflow_recommendation_ml_training_oldest_running_age_seconds",
    "Age in seconds of the oldest running Recommendation ML training job.",
)
pending_activation_approvals: Any = Gauge(
    "courseflow_recommendation_ml_pending_activation_approvals",
    "Current pending Recommendation ML model activation approvals.",
)
oldest_pending_activation_approval_age_seconds: Any = Gauge(
    "courseflow_recommendation_ml_oldest_pending_activation_approval_age_seconds",
    "Age in seconds of the oldest pending Recommendation ML model activation approval.",
)
active_model_present: Any = Gauge(
    "courseflow_recommendation_ml_active_model_present",
    "Whether a Recommendation ML active model exists.",
)
active_model_age_seconds: Any = Gauge(
    "courseflow_recommendation_ml_active_model_age_seconds",
    "Age in seconds of the active Recommendation ML model.",
)
active_model_stale: Any = Gauge(
    "courseflow_recommendation_ml_active_model_stale",
    "Whether the active Recommendation ML model is older than the configured stale threshold.",
)
migration_ready: Any = Gauge(
    "courseflow_recommendation_ml_migration_ready",
    "Whether the Recommendation ML database migration revision matches "
    "the expected service revision.",
)
metrics_refresh_total: Any = Counter(
    "courseflow_recommendation_ml_metrics_refresh_total",
    "Recommendation ML operational metrics refresh attempts.",
    ["result"],
)
internal_auth_rejections_total: Any = Counter(
    "courseflow_recommendation_ml_internal_auth_rejections_total",
    "Recommendation ML internal authentication and authorization rejections by bounded reason.",
    ["reason"],
)
http_requests_total: Any = Counter(
    "courseflow_recommendation_ml_http_requests_total",
    "Recommendation ML HTTP requests by bounded route template and status class.",
    ["method", "route", "status_class"],
)
http_request_duration_seconds: Any = Histogram(
    "courseflow_recommendation_ml_http_request_duration_seconds",
    "Recommendation ML HTTP request duration in seconds by bounded route template "
    "and status class.",
    ["method", "route", "status_class"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


def record_training_run(status: str) -> None:
    training_runs_total.labels(status=status.lower()).inc()


def record_internal_auth_rejection(reason: str) -> None:
    internal_auth_rejections_total.labels(reason=normalize_rejection_reason(reason)).inc()


def normalize_rejection_reason(reason: str) -> str:
    normalized = "".join(
        char if char.isalnum() or char == "_" else "_"
        for char in reason.strip().lower()
    )
    normalized = "_".join(part for part in normalized.split("_") if part)
    return normalized[:80] or "unknown"


def record_http_request(
    method: str,
    route: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    labels = {
        "method": method.upper(),
        "route": normalize_route_template(route),
        "status_class": status_class(status_code),
    }
    http_requests_total.labels(**labels).inc()
    http_request_duration_seconds.labels(**labels).observe(max(0.0, duration_seconds))


def route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str) and path.startswith("/"):
        return path
    return "__unmatched__"


def normalize_route_template(route: str) -> str:
    if not route or not route.startswith("/"):
        return "__unmatched__"
    if len(route) > 160:
        return route[:160]
    return route


def status_class(status_code: int) -> str:
    if status_code < 100 or status_code > 599:
        return "unknown"
    return f"{status_code // 100}xx"


def refresh_operational_metrics(
    repository: TelemetryRepository,
    expected_migration_revision: str,
    training_job_lease_seconds: int,
    active_model_stale_after_seconds: int,
) -> None:
    observed_at = datetime.now(UTC)
    stale_running_before = observed_at - timedelta(
        seconds=max(60, training_job_lease_seconds)
    )
    active_model_stale_before = observed_at - timedelta(
        seconds=max(3600, active_model_stale_after_seconds)
    )
    try:
        metrics = repository.operational_metrics(
            observed_at,
            stale_running_before,
            active_model_stale_before,
            expected_migration_revision,
        )
        for status in TRAINING_STATUSES:
            training_runs_by_status.labels(status=status.lower()).set(
                metrics.training_runs_by_status.get(status, 0)
            )
        training_stale_running_runs.set(metrics.stale_running_training_runs)
        training_oldest_queued_age_seconds.set(metrics.oldest_queued_age_seconds)
        training_oldest_running_age_seconds.set(metrics.oldest_running_age_seconds)
        pending_activation_approvals.set(metrics.pending_activation_approvals)
        oldest_pending_activation_approval_age_seconds.set(
            metrics.oldest_pending_activation_approval_age_seconds
        )
        active_model_present.set(1 if metrics.active_model_present else 0)
        active_model_age_seconds.set(metrics.active_model_age_seconds or 0)
        active_model_stale.set(1 if metrics.active_model_stale else 0)
        migration_ready.set(1 if metrics.migration_ready else 0)
        metrics_refresh_total.labels(result="success").inc()
    except Exception:
        metrics_refresh_total.labels(result="error").inc()


def prometheus_response(
    repository: TelemetryRepository | None = None,
    expected_migration_revision: str = "",
    training_job_lease_seconds: int = 1800,
    active_model_stale_after_seconds: int = 604800,
) -> Response:
    if repository is not None and expected_migration_revision:
        refresh_operational_metrics(
            repository,
            expected_migration_revision,
            training_job_lease_seconds,
            active_model_stale_after_seconds,
        )
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

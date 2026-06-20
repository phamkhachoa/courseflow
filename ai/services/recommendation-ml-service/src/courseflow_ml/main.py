from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import perf_counter

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response

from courseflow_ml import __version__
from courseflow_ml.api.recommendation_routes import (
    get_recommendation_repository,
)
from courseflow_ml.api.recommendation_routes import (
    router as recommendation_router,
)
from courseflow_ml.core.config import Settings, get_settings
from courseflow_ml.core.health import readiness_report
from courseflow_ml.core.telemetry import prometheus_response, record_http_request, route_template

settings = get_settings()


def create_app(app_settings: Settings | None = None) -> FastAPI:
    active_settings = app_settings or settings
    docs_url = (
        "/internal/recommendation-ml/docs"
        if active_settings.recommendation_ml_docs_enabled
        else None
    )
    openapi_url = (
        "/internal/recommendation-ml/openapi.json"
        if active_settings.recommendation_ml_docs_enabled
        else None
    )

    app = FastAPI(
        title="CourseFlow Recommendation ML Service",
        version=__version__,
        docs_url=docs_url,
        openapi_url=openapi_url,
        redoc_url=None,
    )
    app.include_router(recommendation_router)

    @app.middleware("http")
    async def record_request_metrics(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started_at = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            record_http_request(
                request.method,
                route_template(request),
                status_code,
                perf_counter() - started_at,
            )

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "UP", "service": active_settings.service_name}

    @app.get("/actuator/health", include_in_schema=False)
    def actuator_health() -> Response:
        report = readiness_report(
            get_recommendation_repository(),
            active_settings.recommendation_ml_expected_migration_revision,
            active_settings.recommendation_ml_require_active_model_ready,
            active_settings.recommendation_ml_auto_activate_trained_models,
        )
        status_code = 200 if report.status == "UP" else 503
        return JSONResponse(report.to_dict(), status_code=status_code)

    @app.get("/actuator/prometheus", include_in_schema=False)
    def actuator_prometheus() -> Response:
        return prometheus_response(
            get_recommendation_repository(),
            active_settings.recommendation_ml_expected_migration_revision,
            active_settings.recommendation_ml_training_job_lease_seconds,
            active_settings.recommendation_ml_active_model_stale_after_seconds,
        )

    return app


app = create_app()

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from courseflow_ml.domain.recommendation import ModelVersionRecord


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    status: str
    details: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {"status": self.status, **self.details}


@dataclass(frozen=True, slots=True)
class HealthReport:
    status: str
    components: dict[str, ComponentHealth]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "components": {
                name: component.to_dict()
                for name, component in self.components.items()
            },
        }


class HealthRepository(Protocol):
    def database_ping(self) -> None:
        ...

    def current_migration_version(self) -> str | None:
        ...

    def active_model(self) -> ModelVersionRecord | None:
        ...


def readiness_report(
    repository: HealthRepository,
    expected_migration_revision: str,
    require_active_model: bool = False,
    auto_activate_trained_models: bool = True,
) -> HealthReport:
    components: dict[str, ComponentHealth] = {}
    status = "UP"

    try:
        repository.database_ping()
        components["database"] = ComponentHealth("UP", {})
    except Exception as exc:
        components["database"] = ComponentHealth(
            "DOWN",
            {"errorClass": exc.__class__.__name__, "message": str(exc)[:200]},
        )
        return HealthReport("DOWN", components)

    try:
        current_revision = repository.current_migration_version()
        if current_revision == expected_migration_revision:
            components["migration"] = ComponentHealth(
                "UP",
                {
                    "currentRevision": current_revision,
                    "expectedRevision": expected_migration_revision,
                },
            )
        else:
            components["migration"] = ComponentHealth(
                "DOWN",
                {
                    "currentRevision": current_revision,
                    "expectedRevision": expected_migration_revision,
                },
            )
            status = "DOWN"
    except Exception as exc:
        components["migration"] = ComponentHealth(
            "DOWN",
            {
                "expectedRevision": expected_migration_revision,
                "errorClass": exc.__class__.__name__,
                "message": str(exc)[:200],
            },
        )
        status = "DOWN"

    auto_activation_status = "DEGRADED" if auto_activate_trained_models else "UP"
    if require_active_model and auto_activate_trained_models:
        auto_activation_status = "DOWN"
        status = "DOWN"
    components["activationGovernance"] = ComponentHealth(
        auto_activation_status,
        {
            "autoActivateTrainedModels": auto_activate_trained_models,
            "requiresApprovalForTrainedModels": not auto_activate_trained_models,
            "required": require_active_model,
        },
    )

    try:
        active_model = repository.active_model()
        if active_model is None:
            components["activeModel"] = ComponentHealth(
                "DOWN" if require_active_model else "DEGRADED",
                {
                    "message": "No active recommendation ML model is available",
                    "required": require_active_model,
                },
            )
            if require_active_model:
                status = "DOWN"
        else:
            components["activeModel"] = ComponentHealth(
                "UP",
                {
                    "modelVersion": active_model.model_version,
                    "algorithm": active_model.algorithm,
                    "qualityScore": active_model.quality_score,
                    "activatedAt": (
                        active_model.activated_at.isoformat()
                        if active_model.activated_at is not None
                        else None
                    ),
                },
            )
    except Exception as exc:
        components["activeModel"] = ComponentHealth(
            "DOWN",
            {"errorClass": exc.__class__.__name__, "message": str(exc)[:200]},
        )
        status = "DOWN"

    return HealthReport(status, components)

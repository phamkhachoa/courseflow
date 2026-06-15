from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import cast

from courseflow_ml.core.health import readiness_report
from courseflow_ml.domain.recommendation import ModelVersionRecord

EXPECTED_REVISION = "007_model_activation_governance"


class ReadinessReportTest(unittest.TestCase):
    def test_reports_up_when_database_migration_and_model_are_available(self) -> None:
        report = readiness_report(
            FakeHealthRepository(
                migration_version=EXPECTED_REVISION,
                active_model=model_record(),
            ),
            EXPECTED_REVISION,
        )

        body = report.to_dict()
        self.assertEqual(body["status"], "UP")
        components = health_components(body)
        self.assertEqual(components["database"]["status"], "UP")
        self.assertEqual(components["migration"]["status"], "UP")
        self.assertEqual(components["activeModel"]["status"], "UP")
        self.assertEqual(components["activationGovernance"]["status"], "DEGRADED")
        self.assertEqual(
            components["activationGovernance"]["autoActivateTrainedModels"],
            True,
        )

    def test_reports_activation_governance_up_when_auto_activation_is_disabled(self) -> None:
        report = readiness_report(
            FakeHealthRepository(
                migration_version=EXPECTED_REVISION,
                active_model=model_record(),
            ),
            EXPECTED_REVISION,
            require_active_model=True,
            auto_activate_trained_models=False,
        )

        body = report.to_dict()
        self.assertEqual(body["status"], "UP")
        components = health_components(body)
        self.assertEqual(components["activationGovernance"]["status"], "UP")
        self.assertEqual(
            components["activationGovernance"]["requiresApprovalForTrainedModels"],
            True,
        )

    def test_reports_down_when_production_like_readiness_allows_auto_activation(self) -> None:
        report = readiness_report(
            FakeHealthRepository(
                migration_version=EXPECTED_REVISION,
                active_model=model_record(),
            ),
            EXPECTED_REVISION,
            require_active_model=True,
            auto_activate_trained_models=True,
        )

        body = report.to_dict()
        self.assertEqual(body["status"], "DOWN")
        components = health_components(body)
        self.assertEqual(components["activationGovernance"]["status"], "DOWN")

    def test_reports_down_when_database_is_unavailable(self) -> None:
        report = readiness_report(
            FakeHealthRepository(database_error=RuntimeError("db unavailable")),
            EXPECTED_REVISION,
        )

        body = report.to_dict()
        self.assertEqual(body["status"], "DOWN")
        components = health_components(body)
        self.assertEqual(components["database"]["status"], "DOWN")

    def test_reports_down_when_migration_is_not_at_expected_revision(self) -> None:
        report = readiness_report(
            FakeHealthRepository(migration_version="old", active_model=model_record()),
            EXPECTED_REVISION,
        )

        body = report.to_dict()
        self.assertEqual(body["status"], "DOWN")
        components = health_components(body)
        self.assertEqual(components["migration"]["status"], "DOWN")

    def test_missing_active_model_is_degraded_not_down(self) -> None:
        report = readiness_report(
            FakeHealthRepository(migration_version=EXPECTED_REVISION, active_model=None),
            EXPECTED_REVISION,
        )

        body = report.to_dict()
        self.assertEqual(body["status"], "UP")
        components = health_components(body)
        self.assertEqual(components["activeModel"]["status"], "DEGRADED")
        self.assertEqual(components["activeModel"]["required"], False)

    def test_missing_active_model_is_down_when_required(self) -> None:
        report = readiness_report(
            FakeHealthRepository(migration_version=EXPECTED_REVISION, active_model=None),
            EXPECTED_REVISION,
            require_active_model=True,
        )

        body = report.to_dict()
        self.assertEqual(body["status"], "DOWN")
        components = health_components(body)
        self.assertEqual(components["activeModel"]["status"], "DOWN")
        self.assertEqual(components["activeModel"]["required"], True)


class FakeHealthRepository:
    def __init__(
        self,
        migration_version: str | None = EXPECTED_REVISION,
        active_model: ModelVersionRecord | None = None,
        database_error: Exception | None = None,
    ) -> None:
        self.migration_version = migration_version
        self.model = active_model
        self.database_error = database_error

    def database_ping(self) -> None:
        if self.database_error is not None:
            raise self.database_error

    def current_migration_version(self) -> str | None:
        return self.migration_version

    def active_model(self) -> ModelVersionRecord | None:
        return self.model


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
    )


def health_components(body: dict[str, object]) -> dict[str, dict[str, object]]:
    components = body["components"]
    if not isinstance(components, dict):
        raise AssertionError("components must be a dict")
    return cast(dict[str, dict[str, object]], components)


if __name__ == "__main__":
    unittest.main()

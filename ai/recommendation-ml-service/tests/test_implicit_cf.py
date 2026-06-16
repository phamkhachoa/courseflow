from __future__ import annotations

import unittest
from uuid import UUID

from courseflow_ml.domain.recommendation import TrainingInteraction
from courseflow_ml.training.implicit_cf import ImplicitCfConfig, ImplicitItemCfTrainer

COURSE_A = UUID("30000000-0000-0000-0000-000000000001")
COURSE_B = UUID("30000000-0000-0000-0000-000000000002")
COURSE_C = UUID("30000000-0000-0000-0000-000000000003")


class ImplicitItemCfTrainerTest(unittest.TestCase):
    def test_trains_related_courses_from_co_enrollment(self) -> None:
        result = ImplicitItemCfTrainer(
            ImplicitCfConfig(min_support=1, max_related_per_course=3)
        ).train(
            [
                enrolled("learner-1", COURSE_A),
                enrolled("learner-1", COURSE_B),
                enrolled("learner-2", COURSE_A),
                enrolled("learner-2", COURSE_B),
                enrolled("learner-3", COURSE_A),
                enrolled("learner-3", COURSE_C),
            ]
        )

        self.assertGreater(result.quality_score, 0)
        self.assertEqual(result.event_count, 6)
        row = next(
            item
            for item in result.recommendations
            if item.course_id == COURSE_A and item.related_course_id == COURSE_B
        )
        self.assertEqual(row.rank, 1)
        self.assertGreater(row.score, 0)
        self.assertTrue(row.reason_code.startswith("ML_"))

    def test_returns_no_pairs_when_overlap_is_missing(self) -> None:
        result = ImplicitItemCfTrainer().train(
            [
                enrolled("learner-1", COURSE_A),
                enrolled("learner-2", COURSE_B),
            ]
        )

        self.assertEqual(result.pair_count, 0)
        self.assertEqual(result.recommendations, [])

    def test_respects_max_related_per_course(self) -> None:
        result = ImplicitItemCfTrainer(
            ImplicitCfConfig(min_support=1, max_related_per_course=1)
        ).train(
            [
                enrolled("learner-1", COURSE_A),
                enrolled("learner-1", COURSE_B),
                enrolled("learner-1", COURSE_C),
            ]
        )

        per_course = [row for row in result.recommendations if row.course_id == COURSE_A]
        self.assertEqual(len(per_course), 1)


def enrolled(principal_id: str, course_id: UUID) -> TrainingInteraction:
    return TrainingInteraction(
        principal_id=principal_id,
        course_id=course_id,
        event_type="ENROLLMENT",
    )


if __name__ == "__main__":
    unittest.main()

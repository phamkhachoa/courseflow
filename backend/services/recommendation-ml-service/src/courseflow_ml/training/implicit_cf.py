from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from courseflow_ml.domain.recommendation import (
    ScoredRecommendation,
    TrainingInteraction,
    TrainingResult,
)

ALGORITHM = "IMPLICIT_ITEM_CF_V1"


@dataclass(frozen=True, slots=True)
class ImplicitCfConfig:
    min_support: int = 1
    max_related_per_course: int = 24
    max_weight_per_course: float = 50.0


class ImplicitItemCfTrainer:
    """Item-item collaborative filtering from implicit learner-course interactions."""

    def __init__(self, config: ImplicitCfConfig | None = None) -> None:
        self.config = config or ImplicitCfConfig()

    def train(self, interactions: list[TrainingInteraction]) -> TrainingResult:
        normalized = [row for row in (normalize_interaction(row) for row in interactions) if row]
        principal_vectors: dict[str, dict[UUID, float]] = defaultdict(dict)
        for principal_id, course_id, weight in normalized:
            current = principal_vectors[principal_id].get(course_id, 0.0)
            principal_vectors[principal_id][course_id] = min(
                current + weight,
                self.config.max_weight_per_course,
            )

        norms: dict[UUID, float] = defaultdict(float)
        pairs: dict[UUID, dict[UUID, PairAccumulator]] = defaultdict(
            lambda: defaultdict(PairAccumulator)
        )
        courses: set[UUID] = set()
        for vector in principal_vectors.values():
            entries = sorted(
                (course_id, weight)
                for course_id, weight in vector.items()
                if weight > 0
            )
            for course_id, weight in entries:
                courses.add(course_id)
                norms[course_id] += weight * weight
            for left_course, left_weight in entries:
                for right_course, right_weight in entries:
                    if left_course == right_course:
                        continue
                    pairs[left_course][right_course].add(left_weight * right_weight)

        raw_scores: list[ScoredPair] = []
        quality_total = 0.0
        for course_id, related in pairs.items():
            for related_course_id, accumulator in related.items():
                if accumulator.support_count < self.config.min_support:
                    continue
                denominator = math.sqrt(norms[course_id]) * math.sqrt(norms[related_course_id])
                if denominator <= 0:
                    continue
                similarity = clamp(accumulator.dot_product / denominator)
                confidence = math.log1p(accumulator.support_count) / math.log1p(
                    max(2, len(principal_vectors))
                )
                score = clamp((similarity * 0.75) + (confidence * 0.25))
                quality_total += score
                raw_scores.append(
                    ScoredPair(
                        course_id=course_id,
                        related_course_id=related_course_id,
                        score=score,
                        similarity=similarity,
                        support_count=accumulator.support_count,
                        reason_code=(
                            "ML_CO_ENROLLMENT"
                            if accumulator.support_count >= 3
                            else "ML_SIMILAR_LEARNER"
                        ),
                    )
                )

        by_course: dict[UUID, list[ScoredPair]] = defaultdict(list)
        for scored_pair in raw_scores:
            by_course[scored_pair.course_id].append(scored_pair)

        recommendations: list[ScoredRecommendation] = []
        for course_scores in by_course.values():
            course_scores.sort(
                key=lambda row: (
                    -row.score,
                    -row.support_count,
                    str(row.related_course_id),
                )
            )
            top_scores = course_scores[: self.config.max_related_per_course]
            for index, row in enumerate(top_scores, start=1):
                recommendations.append(
                    ScoredRecommendation(
                        course_id=row.course_id,
                        related_course_id=row.related_course_id,
                        rank=index,
                        score=round(row.score, 6),
                        similarity=round(row.similarity, 6),
                        support_count=row.support_count,
                        reason_code=row.reason_code,
                    )
                )

        recommendations.sort(key=lambda row: (str(row.course_id), row.rank))
        quality_score = quality_total / len(raw_scores) if raw_scores else 0.0
        return TrainingResult(
            recommendations=recommendations,
            event_count=len(normalized),
            principal_count=len(principal_vectors),
            course_count=len(courses),
            pair_count=len(recommendations),
            quality_score=round(quality_score, 6),
        )


def normalize_interaction(row: TrainingInteraction) -> tuple[str, UUID, float] | None:
    principal_id = row.principal_id.strip() if row.principal_id else ""
    event_type = row.event_type.strip().upper().replace("-", "_") if row.event_type else ""
    if not principal_id or row.course_id is None or not event_type:
        return None
    weight = row.weight if row.weight is not None else default_event_weight(event_type)
    if not math.isfinite(weight) or weight <= 0:
        return None
    if weight > 50:
        raise ValueError("Training event weight must be between 0 and 50")
    return principal_id, row.course_id, weight


def default_event_weight(event_type: str) -> float:
    match event_type:
        case "ENROLLMENT":
            return 6.0
        case "CLICK":
            return 2.0
        case "IMPRESSION":
            return 0.2
        case _:
            raise ValueError(f"Unsupported recommendation ML event type: {event_type}")


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


@dataclass(slots=True)
class PairAccumulator:
    dot_product: float = 0.0
    support_count: int = 0

    def add(self, dot_product: float) -> None:
        self.dot_product += dot_product
        self.support_count += 1


@dataclass(frozen=True, slots=True)
class ScoredPair:
    course_id: UUID
    related_course_id: UUID
    score: float
    similarity: float
    support_count: int
    reason_code: str

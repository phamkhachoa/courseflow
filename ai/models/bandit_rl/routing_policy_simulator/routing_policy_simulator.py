from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MODEL_ID = "operations-routing-policy-simulator-v1"
HIGH_PRIORITY = frozenset({"p0", "p1", "urgent", "high"})


@dataclass(frozen=True, slots=True)
class WorkItemContext:
    work_item_id: str
    work_type: str
    priority: str
    required_skill_ids: tuple[str, ...]
    expected_effort_minutes: int
    customer_segment: str = "standard"

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> WorkItemContext:
        required_skill_ids = row.get("required_skill_ids", [])
        if not isinstance(required_skill_ids, list):
            raise ValueError("required_skill_ids must be a list")
        return cls(
            work_item_id=str(row.get("work_item_id", "")).strip(),
            work_type=str(row.get("work_type", "")).strip(),
            priority=str(row.get("priority", "")).strip().lower() or "p2",
            required_skill_ids=tuple(str(skill).strip() for skill in required_skill_ids),
            expected_effort_minutes=int(row.get("expected_effort_minutes", 30)),
            customer_segment=str(row.get("customer_segment", "standard")).strip(),
        )


@dataclass(frozen=True, slots=True)
class QueueState:
    queue_id: str
    available_agent_count: int
    backlog_count: int
    average_handle_time_minutes: int
    skill_ids: tuple[str, ...]
    max_concurrency: int

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> QueueState:
        skill_ids = row.get("skill_ids", [])
        if not isinstance(skill_ids, list):
            raise ValueError("skill_ids must be a list")
        return cls(
            queue_id=str(row.get("queue_id", "")).strip(),
            available_agent_count=int(row.get("available_agent_count", 0)),
            backlog_count=int(row.get("backlog_count", 0)),
            average_handle_time_minutes=int(row.get("average_handle_time_minutes", 30)),
            skill_ids=tuple(str(skill).strip() for skill in skill_ids),
            max_concurrency=int(row.get("max_concurrency", 1)),
        )


@dataclass(frozen=True, slots=True)
class RoutingPolicyInput:
    tenant_id: str
    policy_id: str
    safe_exploration_budget: float
    work_item: WorkItemContext
    queues: tuple[QueueState, ...]
    baseline_queue_id: str = ""

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> RoutingPolicyInput:
        queues = row.get("queues")
        if not isinstance(queues, list):
            raise ValueError("queues must be a list")
        return cls(
            tenant_id=str(row.get("tenant_id", "")).strip(),
            policy_id=str(row.get("policy_id", "")).strip() or MODEL_ID,
            safe_exploration_budget=float(row.get("safe_exploration_budget", 0.0)),
            work_item=WorkItemContext.from_dict(require_mapping(row, "work_item")),
            queues=tuple(QueueState.from_dict(queue) for queue in queues),
            baseline_queue_id=str(row.get("baseline_queue_id", "")).strip(),
        )


@dataclass(frozen=True, slots=True)
class RoutingPolicyDecision:
    model_id: str
    assigned_queue_id: str
    policy_score: float
    expected_sla_success: float
    baseline_queue_id: str
    baseline_score_delta: float
    exploration_budget_used: float
    constraint_violations: tuple[str, ...]
    reason_codes: tuple[str, ...]
    requires_human_review: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "assigned_queue_id": self.assigned_queue_id,
            "baseline_queue_id": self.baseline_queue_id,
            "baseline_score_delta": self.baseline_score_delta,
            "constraint_violations": list(self.constraint_violations),
            "expected_sla_success": self.expected_sla_success,
            "exploration_budget_used": self.exploration_budget_used,
            "model_id": self.model_id,
            "policy_score": self.policy_score,
            "reason_codes": list(self.reason_codes),
            "requires_human_review": self.requires_human_review,
        }


@dataclass(frozen=True, slots=True)
class QueueScore:
    queue: QueueState
    score: float
    expected_sla_success: float
    constraint_violations: tuple[str, ...]
    reason_codes: tuple[str, ...]


class RoutingPolicySimulator:
    def recommend(
        self,
        payload: RoutingPolicyInput | dict[str, Any],
    ) -> RoutingPolicyDecision:
        request = (
            payload
            if isinstance(payload, RoutingPolicyInput)
            else RoutingPolicyInput.from_dict(payload)
        )
        validate_request(request)
        scores = sorted(
            (score_queue(request.work_item, queue) for queue in request.queues),
            key=lambda scored: (scored.score, -scored.queue.backlog_count, scored.queue.queue_id),
            reverse=True,
        )
        selected = scores[0]
        baseline_score = find_baseline_score(scores, request.baseline_queue_id)
        exploration_budget_used = derive_exploration_budget(request, scores)
        reason_codes = set(selected.reason_codes)
        if exploration_budget_used > 0:
            reason_codes.add("SAFE_EXPLORATION_AVAILABLE")
        elif request.work_item.priority in HIGH_PRIORITY:
            reason_codes.add("NO_EXPLORATION_FOR_HIGH_PRIORITY")
        if selected.constraint_violations:
            reason_codes.add("HUMAN_REVIEW_REQUIRED")

        return RoutingPolicyDecision(
            model_id=MODEL_ID,
            assigned_queue_id=selected.queue.queue_id,
            policy_score=round(selected.score, 6),
            expected_sla_success=round(selected.expected_sla_success, 6),
            baseline_queue_id=request.baseline_queue_id,
            baseline_score_delta=round(selected.score - baseline_score, 6),
            exploration_budget_used=round(exploration_budget_used, 6),
            constraint_violations=selected.constraint_violations,
            reason_codes=tuple(sorted(reason_codes)),
            requires_human_review=bool(selected.constraint_violations),
        )


def validate_request(request: RoutingPolicyInput) -> None:
    if not request.tenant_id.startswith("tenant-"):
        raise ValueError("tenant_id must be a bounded tenant identifier")
    if not request.policy_id:
        raise ValueError("policy_id is required")
    if request.safe_exploration_budget < 0 or request.safe_exploration_budget > 0.2:
        raise ValueError("safe_exploration_budget must be between 0 and 0.2")
    if not request.work_item.work_item_id:
        raise ValueError("work_item_id is required")
    if not request.work_item.required_skill_ids:
        raise ValueError("required_skill_ids are required")
    if request.work_item.expected_effort_minutes <= 0:
        raise ValueError("expected_effort_minutes must be positive")
    if not request.queues:
        raise ValueError("queues are required")
    for queue in request.queues:
        if not queue.queue_id:
            raise ValueError("queue_id is required")
        if queue.available_agent_count < 0 or queue.backlog_count < 0:
            raise ValueError("queue capacity fields must be non-negative")
        if queue.max_concurrency <= 0 or queue.average_handle_time_minutes <= 0:
            raise ValueError("queue timing fields must be positive")


def score_queue(work_item: WorkItemContext, queue: QueueState) -> QueueScore:
    required = set(work_item.required_skill_ids)
    skills = set(queue.skill_ids)
    matched_skill_count = len(required & skills)
    skill_match = matched_skill_count / len(required)
    capacity_score = min(1.0, queue.available_agent_count / max(1, queue.max_concurrency))
    backlog_capacity = max(1, queue.available_agent_count * queue.max_concurrency)
    backlog_score = max(0.0, 1.0 - min(1.0, queue.backlog_count / (backlog_capacity + 4)))
    effort_fit = max(
        0.0,
        1.0
        - min(
            1.0,
            abs(queue.average_handle_time_minutes - work_item.expected_effort_minutes)
            / max(work_item.expected_effort_minutes, queue.average_handle_time_minutes),
        ),
    )
    priority_boost = 0.04 if work_item.priority in HIGH_PRIORITY else 0.0
    raw_score = (
        0.44 * skill_match
        + 0.24 * capacity_score
        + 0.2 * backlog_score
        + 0.08 * effort_fit
        + priority_boost
    )

    violations: list[str] = []
    reasons: set[str] = set()
    if skill_match >= 1.0:
        reasons.add("SKILL_MATCH")
    else:
        violations.append("MISSING_REQUIRED_SKILL")
        reasons.add("PARTIAL_SKILL_MATCH")
        raw_score -= 0.25
    if queue.available_agent_count > 0:
        reasons.add("CAPACITY_AVAILABLE")
    else:
        violations.append("NO_AVAILABLE_AGENT")
        raw_score -= 0.25
    if backlog_score >= 0.65:
        reasons.add("BACKLOG_HEALTHY")
    if effort_fit >= 0.75:
        reasons.add("EFFORT_FIT")

    score = max(0.0, min(0.99, raw_score))
    expected_sla_success = max(0.05, min(0.98, 0.2 + score * 0.78))
    return QueueScore(
        queue=queue,
        score=score,
        expected_sla_success=expected_sla_success,
        constraint_violations=tuple(violations),
        reason_codes=tuple(sorted(reasons)),
    )


def find_baseline_score(scores: list[QueueScore], baseline_queue_id: str) -> float:
    if not baseline_queue_id:
        return 0.0
    for score in scores:
        if score.queue.queue_id == baseline_queue_id:
            return score.score
    return 0.0


def derive_exploration_budget(
    request: RoutingPolicyInput,
    scores: list[QueueScore],
) -> float:
    if request.work_item.priority in HIGH_PRIORITY or len(scores) < 2:
        return 0.0
    top, second = scores[0], scores[1]
    if top.constraint_violations or second.constraint_violations:
        return 0.0
    score_gap = top.score - second.score
    if score_gap <= 0.08 and request.safe_exploration_budget >= 0.05:
        return 0.05
    return 0.0


def require_mapping(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return value

package edu.courseflow.events.quiz;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.math.BigDecimal;
import java.time.Instant;

public record QuizAttemptGradedEvent(
        String eventId,
        String attemptId,
        String quizId,
        String courseId,
        String studentId,
        BigDecimal score,
        BigDecimal maxScore,
        Instant gradedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "quiz.attempt.graded";
    }

    @Override
    public String aggregateId() {
        return attemptId;
    }

    @Override
    public String aggregateType() {
        return "quiz-attempt";
    }

    @Override
    public Instant occurredAt() {
        return gradedAt;
    }
}

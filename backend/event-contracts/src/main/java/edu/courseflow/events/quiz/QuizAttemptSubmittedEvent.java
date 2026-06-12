package edu.courseflow.events.quiz;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.time.Instant;

public record QuizAttemptSubmittedEvent(
        String eventId,
        String attemptId,
        String quizId,
        String courseId,
        String studentId,
        Instant submittedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "quiz.attempt.submitted";
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
        return submittedAt;
    }
}

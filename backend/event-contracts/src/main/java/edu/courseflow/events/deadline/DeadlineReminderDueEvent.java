package edu.courseflow.events.deadline;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.time.Instant;

public record DeadlineReminderDueEvent(
        String eventId,
        String reminderId,
        String assignmentId,
        String courseId,
        String studentId,
        Instant dueAt,
        Instant reminderAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "deadline.reminder.due";
    }

    @Override
    public String aggregateId() {
        return reminderId;
    }

    @Override
    public String aggregateType() {
        return "deadline-reminder";
    }

    @Override
    public Instant occurredAt() {
        return reminderAt;
    }
}

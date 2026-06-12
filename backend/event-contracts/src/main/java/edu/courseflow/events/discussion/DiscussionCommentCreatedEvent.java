package edu.courseflow.events.discussion;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.time.Instant;

public record DiscussionCommentCreatedEvent(
        String eventId,
        String commentId,
        String threadId,
        String courseId,
        String authorId,
        Instant createdAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "discussion.comment.created";
    }

    @Override
    public String aggregateId() {
        return commentId;
    }

    @Override
    public String aggregateType() {
        return "discussion-comment";
    }

    @Override
    public Instant occurredAt() {
        return createdAt;
    }
}

package edu.courseflow.discussion.dto;

import jakarta.validation.constraints.NotBlank;
import java.time.Instant;
import java.util.List;

public final class DiscussionDtos {

    private DiscussionDtos() {
    }

    public record DiscussionThreadDto(
            String id,
            String courseId,
            String assignmentId,
            String authorId,
            String title,
            String status,
            Instant createdAt,
            List<DiscussionCommentDto> comments
    ) {
    }

    public record DiscussionCommentDto(
            String id,
            String threadId,
            String authorId,
            String body,
            boolean accepted,
            Instant createdAt
    ) {
    }

    public record CreateThreadRequestDto(
            @NotBlank String courseId,
            String assignmentId,
            String authorId,
            @NotBlank String title
    ) {
    }

    public record CreateCommentRequestDto(
            String authorId,
            @NotBlank String body
    ) {
    }
}

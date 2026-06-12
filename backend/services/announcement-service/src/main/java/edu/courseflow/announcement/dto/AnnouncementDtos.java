package edu.courseflow.announcement.dto;

import jakarta.validation.constraints.NotBlank;
import java.time.Instant;

public final class AnnouncementDtos {

    private AnnouncementDtos() {
    }

    public record AnnouncementDto(
            String id,
            String courseId,
            String authorId,
            String title,
            String body,
            String audience,
            String status,
            Instant publishAt,
            Instant publishedAt
    ) {
    }

    public record CreateAnnouncementRequestDto(
            @NotBlank String courseId,
            String authorId,
            @NotBlank String title,
            @NotBlank String body,
            @NotBlank String audience,
            Instant publishAt
    ) {
    }
}

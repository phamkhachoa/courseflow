package edu.courseflow.course.dto;

import jakarta.validation.constraints.NotBlank;
import java.time.Instant;

public record RecordItemCompletionRequestDto(
        @NotBlank String studentId,
        String sourceType,
        String sourceId,
        Instant completedAt
) {
}

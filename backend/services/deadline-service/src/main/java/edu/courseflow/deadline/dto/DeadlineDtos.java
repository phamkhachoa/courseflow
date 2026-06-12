package edu.courseflow.deadline.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import java.time.Instant;

public final class DeadlineDtos {

    private DeadlineDtos() {
    }

    public record ReminderPolicyDto(
            String id,
            String courseId,
            String name,
            int offsetMinutes,
            String channel,
            boolean enabled
    ) {
    }

    public record ReminderRunDto(
            String id,
            String assignmentId,
            String studentId,
            String reminderPolicyId,
            Instant reminderAt,
            String status
    ) {
    }

    public record CreateReminderPolicyRequestDto(
            @NotBlank String courseId,
            @NotBlank String name,
            @NotNull @Positive Integer offsetMinutes,
            @NotBlank String channel
    ) {
    }

    public record ScheduleReminderRequestDto(
            @NotBlank String assignmentId,
            @NotBlank String studentId,
            @NotBlank String reminderPolicyId,
            @NotNull Instant reminderAt
    ) {
    }
}

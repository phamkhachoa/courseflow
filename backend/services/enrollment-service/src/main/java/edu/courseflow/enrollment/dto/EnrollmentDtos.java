package edu.courseflow.enrollment.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.time.Instant;
import java.util.List;

public final class EnrollmentDtos {

    private EnrollmentDtos() {
    }

    public record EnrollmentDto(
            String id,
            String studentId,
            String courseId,
            String sectionId,
            String status,
            Instant enrolledAt,
            Instant droppedAt,
            Instant completedAt,
            String dropReason
    ) {
    }

    public record WaitlistEntryDto(
            String id,
            String studentId,
            String courseId,
            int position,
            String status,
            Instant createdAt
    ) {
    }

    /**
     * {@code studentId} is optional and only honored for INSTRUCTOR/ADMIN callers enrolling someone
     * else. A STUDENT caller always enrolls themselves; the field is taken from the gateway identity.
     */
    public record EnrollRequestDto(
            String studentId,
            @NotBlank String courseId
    ) {
    }

    /**
     * {@code studentId} is optional and only honored for INSTRUCTOR/ADMIN callers acting on someone
     * else. A STUDENT caller always acts on themselves.
     */
    public record WaitlistRequestDto(
            String studentId,
            @NotBlank String courseId
    ) {
    }

    /** The actor is taken from the gateway identity, never from the body. */
    public record ChangeStatusRequestDto(
            @NotBlank String newStatus,
            String reason
    ) {
    }

    public record SetCapacityRequestDto(
            Integer capacity
    ) {
    }

    public record BatchEnrollRequestDto(
            @NotNull @NotEmpty List<@Valid SingleEnrollDto> entries
    ) {
        public record SingleEnrollDto(
                @NotBlank String studentId,
                @NotBlank String courseId,
                String sectionId
        ) {
        }
    }

    public record BatchEnrollResultDto(
            int enrolled,
            int skipped,
            List<String> errors
    ) {
    }

    public record EnrollmentStatsDto(
            String courseId,
            int totalActive,
            int totalDropped,
            int totalCompleted,
            int waitlistCount
    ) {
    }

    public record CourseAccessDto(
            String courseId,
            String studentId,
            boolean enrolled,
            String status
    ) {
    }

    public record AuditLogEntryDto(
            String id,
            String enrollmentId,
            String actorId,
            String action,
            String oldStatus,
            String newStatus,
            String reason,
            Instant createdAt
    ) {
    }
}

package edu.courseflow.livesession.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.Instant;

public final class LiveSessionDtos {

    private LiveSessionDtos() {
    }

    public record LiveSessionDto(
            String id,
            String courseId,
            String title,
            String description,
            String hostId,
            String provider,
            String providerMeetingId,
            Instant scheduledStart,
            Instant scheduledEnd,
            Instant actualStart,
            Instant actualEnd,
            Integer capacity,
            String status,
            String recordingStorageKey
    ) {
    }

    public record RegistrationDto(
            String id,
            String sessionId,
            String userId,
            Instant registeredAt,
            boolean attended
    ) {
    }

    public record JoinInfoDto(
            String sessionId,
            String userId,
            String joinUrl,
            String status
    ) {
    }

    // ---- requests ----

    public record CreateLiveSessionRequestDto(
            @NotBlank String courseId,
            @NotBlank String title,
            String description,
            String hostId,
            String provider,
            @NotNull Instant scheduledStart,
            Instant scheduledEnd,
            Integer capacity
    ) {
    }

    public record RegisterRequestDto(
            String userId
    ) {
    }

    public record EndSessionRequestDto(
            String recordingStorageKey
    ) {
    }
}

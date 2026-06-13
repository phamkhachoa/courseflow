package edu.courseflow.notification.dto;

import jakarta.validation.constraints.NotBlank;
import java.time.Instant;

public final class NotificationDtos {

    private NotificationDtos() {
    }

    public record NotificationDto(
            String id,
            String userId,
            String notificationType,
            String title,
            String body,
            Instant readAt,
            String deliveryStatus,
            Instant deliveredAt,
            String deliveryError,
            Instant createdAt
    ) {
    }

    public record NotificationPreferenceDto(
            String id,
            String userId,
            String channel,
            boolean enabled
    ) {
    }

    public record CreateNotificationRequestDto(
            @NotBlank String userId,
            @NotBlank String notificationType,
            @NotBlank String title,
            @NotBlank String body
    ) {
    }

    public record UpsertPreferenceRequestDto(
            String userId,
            @NotBlank String channel,
            boolean enabled
    ) {
    }
}

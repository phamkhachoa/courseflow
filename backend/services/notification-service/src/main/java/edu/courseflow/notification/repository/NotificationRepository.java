package edu.courseflow.notification.repository;

import edu.courseflow.notification.dto.NotificationDtos.NotificationDto;
import edu.courseflow.notification.dto.NotificationDtos.NotificationPreferenceDto;
import edu.courseflow.notification.dto.NotificationDtos.UpsertPreferenceRequestDto;
import edu.courseflow.notification.mapper.NotificationMapper;
import edu.courseflow.notification.model.Notification;
import edu.courseflow.notification.model.NotificationPreference;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class NotificationRepository {

    private final NotificationJpaRepository notifications;
    private final NotificationPreferenceJpaRepository preferences;
    private final NotificationMapper mapper;

    public NotificationRepository(NotificationJpaRepository notifications,
            NotificationPreferenceJpaRepository preferences,
            NotificationMapper mapper) {
        this.notifications = notifications;
        this.preferences = preferences;
        this.mapper = mapper;
    }

    public List<NotificationDto> listForUser(String userId, boolean unreadOnly) {
        List<Notification> rows = unreadOnly
                ? notifications.findByUserIdAndReadAtIsNullOrderByCreatedAtDesc(userId)
                : notifications.findByUserIdOrderByCreatedAtDesc(userId);
        return rows.stream().map(mapper::toDto).toList();
    }

    public Optional<NotificationDto> find(UUID notificationId) {
        return notifications.findById(notificationId).map(mapper::toDto);
    }

    /**
     * Insert one notification row and return it as a DTO. Shared by the REST create path and the
     * event fan-out so both produce an identical row shape (and a DTO the push channel can emit).
     */
    public NotificationDto insert(String userId, String notificationType, String title, String body) {
        return toDto(insertEntity(userId, notificationType, title, body));
    }

    public Notification insertEntity(String userId, String notificationType, String title, String body) {
        return notifications.save(new Notification(userId, notificationType, title, body));
    }

    public Notification saveEntity(Notification notification) {
        return notifications.save(notification);
    }

    public List<Notification> lockFailedForRetry(int maxAttempts, int limit) {
        return notifications.lockFailedForRetry(maxAttempts, limit);
    }

    public NotificationDto toDto(Notification notification) {
        return mapper.toDto(notification);
    }

    /**
     * Whether a user wants to receive notifications on the given channel. Preferences are opt-out:
     * a row with {@code enabled = FALSE} suppresses the channel; the absence of a row means the user
     * has never customised it and the default (enabled) applies.
     */
    public boolean channelEnabled(String userId, String channel) {
        return preferences.findByUserIdAndChannel(userId, channel)
                .map(NotificationPreference::isEnabled)
                .orElse(Boolean.TRUE);
    }

    public void markRead(UUID notificationId) {
        notifications.findById(notificationId).ifPresent(notification -> {
            notification.markRead();
            notifications.save(notification);
        });
    }

    public List<NotificationPreferenceDto> preferences(String userId) {
        return preferences.findByUserIdOrderByChannelAsc(userId).stream().map(mapper::toDto).toList();
    }

    public NotificationPreferenceDto upsertPreference(UpsertPreferenceRequestDto request) {
        NotificationPreference preference = preferences.findByUserIdAndChannel(request.userId(), request.channel())
                .orElseGet(() -> new NotificationPreference(request.userId(), request.channel(), request.enabled()));
        preference.setEnabled(request.enabled());
        return mapper.toDto(preferences.save(preference));
    }
}

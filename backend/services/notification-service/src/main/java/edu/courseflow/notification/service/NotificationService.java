package edu.courseflow.notification.service;

import edu.courseflow.notification.dto.NotificationDtos.CreateNotificationRequestDto;
import edu.courseflow.notification.dto.NotificationDtos.NotificationDto;
import edu.courseflow.notification.dto.NotificationDtos.NotificationPreferenceDto;
import edu.courseflow.notification.dto.NotificationDtos.UpsertPreferenceRequestDto;
import edu.courseflow.notification.repository.NotificationRepository;
import edu.courseflow.notification.web.ForbiddenException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class NotificationService {

    private final NotificationRepository notifications;

    public NotificationService(NotificationRepository notifications) {
        this.notifications = notifications;
    }

    public List<NotificationDto> listForUser(String userId, boolean unreadOnly) {
        return notifications.listForUser(userId, unreadOnly);
    }

    @Transactional
    public NotificationDto create(CreateNotificationRequestDto request) {
        return notifications.create(request);
    }

    @Transactional
    public void markRead(UUID notificationId, String userId) {
        NotificationDto notification = notifications.find(notificationId)
                .orElseThrow(() -> new NotFoundException("Notification not found: " + notificationId));
        if (!notification.userId().equals(userId)) {
            throw new ForbiddenException("FORBIDDEN_NOT_OWNER");
        }
        notifications.markRead(notificationId);
    }

    public List<NotificationPreferenceDto> preferences(String userId) {
        return notifications.preferences(userId);
    }

    @Transactional
    public NotificationPreferenceDto upsertPreference(UpsertPreferenceRequestDto request) {
        return notifications.upsertPreference(request);
    }
}

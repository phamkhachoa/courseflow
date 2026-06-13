package edu.courseflow.notification.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.notification.dto.NotificationDtos.CreateNotificationRequestDto;
import edu.courseflow.notification.dto.NotificationDtos.NotificationDto;
import edu.courseflow.notification.dto.NotificationDtos.NotificationPreferenceDto;
import edu.courseflow.notification.dto.NotificationDtos.UpsertPreferenceRequestDto;
import edu.courseflow.notification.service.NotificationService;
import edu.courseflow.notification.web.Authz;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class NotificationController {

    private final NotificationService notifications;

    public NotificationController(NotificationService notifications) {
        this.notifications = notifications;
    }

    @GetMapping("/internal/notifications")
    public List<NotificationDto> list(@RequestParam String userId,
                                      @RequestParam(defaultValue = "false") boolean unreadOnly,
                                      CurrentUser user) {
        Authz.requireSelfOrAdmin(user, userId);
        return notifications.listForUser(userId, unreadOnly);
    }

    @PostMapping("/internal/notifications")
    public NotificationDto create(@Valid @RequestBody CreateNotificationRequestDto request, CurrentUser user) {
        Authz.requireStaff(user);
        return notifications.create(request);
    }

    @PostMapping("/internal/notifications/{notificationId}/read")
    public ResponseEntity<Void> markRead(@PathVariable UUID notificationId, CurrentUser user) {
        notifications.markRead(notificationId, Authz.callerId(user));
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/internal/notifications/preferences")
    public List<NotificationPreferenceDto> preferences(@RequestParam String userId, CurrentUser user) {
        Authz.requireSelfOrAdmin(user, userId);
        return notifications.preferences(userId);
    }

    @PostMapping("/internal/notifications/preferences")
    public NotificationPreferenceDto upsertPreference(@Valid @RequestBody UpsertPreferenceRequestDto request,
                                                     CurrentUser user) {
        String targetUserId = Authz.isAdmin(user) && request.userId() != null && !request.userId().isBlank()
                ? request.userId()
                : Authz.callerId(user);
        Authz.requireSelfOrAdmin(user, targetUserId);
        UpsertPreferenceRequestDto trusted = new UpsertPreferenceRequestDto(
                targetUserId,
                request.channel(),
                request.enabled());
        return notifications.upsertPreference(trusted);
    }
}

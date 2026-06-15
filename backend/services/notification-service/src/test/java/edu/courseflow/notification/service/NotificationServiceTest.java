package edu.courseflow.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.notification.dto.NotificationDtos.CreateNotificationRequestDto;
import edu.courseflow.notification.dto.NotificationDtos.NotificationDto;
import edu.courseflow.notification.model.Notification;
import edu.courseflow.notification.repository.NotificationRepository;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class NotificationServiceTest {

    @Mock
    private NotificationRepository notifications;
    @Mock
    private NotificationDeliveryDispatcher dispatcher;

    @Test
    void createPersistsAndDispatchesDelivery() {
        NotificationService service = new NotificationService(notifications, dispatcher);
        Notification notification = new Notification("4", "SYSTEM", "Welcome", "Hello");
        NotificationDto dto = new NotificationDto(
                notification.getId().toString(),
                "4",
                "SYSTEM",
                "Welcome",
                "Hello",
                null,
                "DELIVERED",
                Instant.parse("2026-06-15T00:00:00Z"),
                null,
                Instant.parse("2026-06-15T00:00:00Z"));
        when(notifications.insertEntity("4", "SYSTEM", "Welcome", "Hello")).thenReturn(notification);
        when(dispatcher.dispatch(notification)).thenReturn(dto);

        NotificationDto response = service.create(new CreateNotificationRequestDto(
                "4",
                "SYSTEM",
                "Welcome",
                "Hello"));

        assertThat(response).isSameAs(dto);
        verify(dispatcher).dispatch(notification);
    }
}

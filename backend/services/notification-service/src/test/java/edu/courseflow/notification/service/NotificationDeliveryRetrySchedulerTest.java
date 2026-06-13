package edu.courseflow.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.notification.model.Notification;
import edu.courseflow.notification.repository.NotificationRepository;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class NotificationDeliveryRetrySchedulerTest {

    @Mock
    private NotificationRepository notifications;

    private NotificationDeliveryService delivery;
    private NotificationDeliveryRetryScheduler scheduler;

    @BeforeEach
    void setUp() {
        delivery = new NotificationDeliveryService(ignored -> {
        });
        scheduler = new NotificationDeliveryRetryScheduler(notifications, delivery, 5, 10);
    }

    @Test
    void retryFailedDeliveriesRedeliversAndPersistsRows() {
        Notification notification = new Notification("4", "ANNOUNCEMENT", "Welcome", "Body");
        notification.markDeliveryFailed("temporary outage");
        when(notifications.lockFailedForRetry(5, 10)).thenReturn(List.of(notification));

        scheduler.retryFailedDeliveries();

        assertThat(notification.getDeliveryStatus()).isEqualTo("DELIVERED");
        assertThat(notification.getDeliveryAttempts()).isEqualTo(1);
        verify(notifications).saveEntity(notification);
    }
}

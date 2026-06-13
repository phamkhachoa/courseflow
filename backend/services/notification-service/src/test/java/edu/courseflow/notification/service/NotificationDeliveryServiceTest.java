package edu.courseflow.notification.service;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.notification.model.Notification;
import org.junit.jupiter.api.Test;

class NotificationDeliveryServiceTest {

    @Test
    void marksDeliveredWhenProviderSucceeds() {
        Notification notification = new Notification("4", "ANNOUNCEMENT", "Welcome", "Body");
        NotificationDeliveryService service = new NotificationDeliveryService(ignored -> {
        });

        service.deliver(notification);

        assertThat(notification.getDeliveryStatus()).isEqualTo("DELIVERED");
        assertThat(notification.getDeliveredAt()).isNotNull();
        assertThat(notification.getDeliveryError()).isNull();
        assertThat(notification.getDeliveryAttempts()).isEqualTo(1);
        assertThat(notification.getLastDeliveryAttemptAt()).isNotNull();
    }

    @Test
    void marksFailedWhenProviderThrows() {
        Notification notification = new Notification("4", "ANNOUNCEMENT", "Welcome", "Body");
        NotificationDeliveryService service = new NotificationDeliveryService(ignored -> {
            throw new RuntimeException("provider unavailable");
        });

        service.deliver(notification);

        assertThat(notification.getDeliveryStatus()).isEqualTo("FAILED");
        assertThat(notification.getDeliveredAt()).isNull();
        assertThat(notification.getDeliveryError()).isEqualTo("provider unavailable");
        assertThat(notification.getDeliveryAttempts()).isEqualTo(1);
        assertThat(notification.getLastDeliveryAttemptAt()).isNotNull();
    }
}

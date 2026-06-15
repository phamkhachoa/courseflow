package edu.courseflow.notification.service;

import edu.courseflow.notification.model.Notification;
import org.springframework.stereotype.Service;

@Service
public class NotificationDeliveryService {

    private final NotificationDeliveryPort deliveryPort;

    public NotificationDeliveryService(NotificationDeliveryPort deliveryPort) {
        this.deliveryPort = deliveryPort;
    }

    public void deliver(Notification notification) {
        if (!"DISPATCHING".equals(notification.getDeliveryStatus())) {
            notification.markDeliveryInProgress();
        }
        try {
            deliveryPort.deliver(notification);
            notification.markDelivered();
        } catch (RuntimeException ex) {
            notification.markDeliveryFailed(ex.getMessage());
        }
    }
}

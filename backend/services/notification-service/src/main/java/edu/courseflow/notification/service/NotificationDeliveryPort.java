package edu.courseflow.notification.service;

import edu.courseflow.notification.model.Notification;

public interface NotificationDeliveryPort {

    void deliver(Notification notification);
}

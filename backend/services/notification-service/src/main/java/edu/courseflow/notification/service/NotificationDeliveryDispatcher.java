package edu.courseflow.notification.service;

import edu.courseflow.notification.dto.NotificationDtos.NotificationDto;
import edu.courseflow.notification.model.Notification;
import edu.courseflow.notification.push.NotificationStreamRegistry;
import edu.courseflow.notification.repository.NotificationRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Service
public class NotificationDeliveryDispatcher {

    private static final Logger log = LoggerFactory.getLogger(NotificationDeliveryDispatcher.class);

    private final NotificationRepository notifications;
    private final NotificationDeliveryService delivery;
    private final NotificationStreamRegistry streams;

    public NotificationDeliveryDispatcher(
            NotificationRepository notifications,
            NotificationDeliveryService delivery,
            NotificationStreamRegistry streams) {
        this.notifications = notifications;
        this.delivery = delivery;
        this.streams = streams;
    }

    public NotificationDto dispatch(Notification notification) {
        if (!TransactionSynchronizationManager.isSynchronizationActive()) {
            return dispatchNow(notification);
        }

        if ("FAILED".equals(notification.getDeliveryStatus())) {
            notification.markDeliveryInProgress();
        }
        NotificationDto pending = notifications.toDto(notification);
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                try {
                    dispatchNow(notification);
                } catch (RuntimeException ex) {
                    log.warn("notification delivery dispatch failed after commit for {}", notification.getId(), ex);
                }
            }
        });
        return pending;
    }

    public NotificationDto dispatchNow(Notification notification) {
        delivery.deliver(notification);
        Notification saved = notifications.saveEntity(notification);
        NotificationDto delivered = notifications.toDto(saved);
        streams.push(notification.getUserId(), delivered);
        return delivered;
    }
}

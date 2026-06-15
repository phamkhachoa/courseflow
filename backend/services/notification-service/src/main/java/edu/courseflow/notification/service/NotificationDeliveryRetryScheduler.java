package edu.courseflow.notification.service;

import edu.courseflow.notification.model.Notification;
import edu.courseflow.notification.repository.NotificationRepository;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(prefix = "courseflow.notification.delivery.retry", name = "enabled",
        havingValue = "true", matchIfMissing = true)
public class NotificationDeliveryRetryScheduler {

    private static final Logger log = LoggerFactory.getLogger(NotificationDeliveryRetryScheduler.class);

    private final NotificationRepository notifications;
    private final NotificationDeliveryDispatcher dispatcher;
    private final int maxAttempts;
    private final int batchSize;

    public NotificationDeliveryRetryScheduler(
            NotificationRepository notifications,
            NotificationDeliveryDispatcher dispatcher,
            @Value("${courseflow.notification.delivery.retry.max-attempts:5}") int maxAttempts,
            @Value("${courseflow.notification.delivery.retry.batch-size:100}") int batchSize) {
        this.notifications = notifications;
        this.dispatcher = dispatcher;
        this.maxAttempts = Math.max(1, maxAttempts);
        this.batchSize = Math.max(1, batchSize);
    }

    @Scheduled(fixedDelayString = "${courseflow.notification.delivery.retry.interval-ms:60000}")
    @Transactional
    public void retryFailedDeliveries() {
        List<Notification> failed = notifications.lockFailedForRetry(maxAttempts, batchSize);
        for (Notification notification : failed) {
            dispatcher.dispatch(notification);
        }
        if (!failed.isEmpty()) {
            log.info("notification delivery retry scheduled {} failed notification(s)", failed.size());
        }
    }
}

package edu.courseflow.notification.service;

import edu.courseflow.notification.model.Notification;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/**
 * Local/dev delivery adapter. Production can replace this bean with an email/push provider without
 * changing notification creation or event fan-out code.
 */
@Component
@ConditionalOnProperty(prefix = "courseflow.notification.delivery", name = "mode", havingValue = "log",
        matchIfMissing = true)
public class LoggingNotificationDeliveryPort implements NotificationDeliveryPort {

    private static final Logger log = LoggerFactory.getLogger(LoggingNotificationDeliveryPort.class);

    @Override
    public void deliver(Notification notification) {
        log.info("notification delivery log-mode user={} type={} title={}",
                notification.getUserId(), notification.getNotificationType(), notification.getTitle());
    }
}

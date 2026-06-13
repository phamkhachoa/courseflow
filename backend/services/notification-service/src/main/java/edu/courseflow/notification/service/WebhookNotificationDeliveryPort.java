package edu.courseflow.notification.service;

import edu.courseflow.notification.model.Notification;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
@ConditionalOnProperty(prefix = "courseflow.notification.delivery", name = "mode", havingValue = "webhook")
public class WebhookNotificationDeliveryPort implements NotificationDeliveryPort {

    private final RestClient client;

    public WebhookNotificationDeliveryPort(
            @Value("${courseflow.notification.delivery.webhook-url:}") String webhookUrl) {
        if (webhookUrl == null || webhookUrl.isBlank()) {
            throw new IllegalStateException(
                    "courseflow.notification.delivery.webhook-url is required when delivery mode is webhook");
        }
        this.client = RestClient.builder().baseUrl(webhookUrl).build();
    }

    @Override
    public void deliver(Notification notification) {
        client.post()
                .contentType(MediaType.APPLICATION_JSON)
                .body(NotificationDeliveryPayload.from(notification))
                .retrieve()
                .toBodilessEntity();
    }

    public record NotificationDeliveryPayload(
            UUID id,
            String userId,
            String notificationType,
            String title,
            String body) {

        static NotificationDeliveryPayload from(Notification notification) {
            return new NotificationDeliveryPayload(
                    notification.getId(),
                    notification.getUserId(),
                    notification.getNotificationType(),
                    notification.getTitle(),
                    notification.getBody());
        }
    }
}

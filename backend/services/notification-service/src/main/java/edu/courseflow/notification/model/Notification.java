package edu.courseflow.notification.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "notifications")
public class Notification {

    @Id
    private UUID id;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(name = "notification_type", nullable = false, length = 80)
    private String notificationType;

    @Column(nullable = false)
    private String title;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String body;

    @Column(name = "read_at")
    private Instant readAt;

    @Column(name = "delivery_status", nullable = false, length = 40)
    private String deliveryStatus = "PENDING";

    @Column(name = "delivered_at")
    private Instant deliveredAt;

    @Column(name = "delivery_error")
    private String deliveryError;

    @Column(name = "delivery_attempts", nullable = false)
    private int deliveryAttempts = 0;

    @Column(name = "last_delivery_attempt_at")
    private Instant lastDeliveryAttemptAt;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected Notification() {
    }

    public Notification(String userId, String notificationType, String title, String body) {
        this.id = UUID.randomUUID();
        this.userId = userId;
        this.notificationType = notificationType;
        this.title = title;
        this.body = body;
    }

    public UUID getId() { return id; }
    public String getUserId() { return userId; }
    public String getNotificationType() { return notificationType; }
    public String getTitle() { return title; }
    public String getBody() { return body; }
    public Instant getReadAt() { return readAt; }
    public String getDeliveryStatus() { return deliveryStatus; }
    public Instant getDeliveredAt() { return deliveredAt; }
    public String getDeliveryError() { return deliveryError; }
    public int getDeliveryAttempts() { return deliveryAttempts; }
    public Instant getLastDeliveryAttemptAt() { return lastDeliveryAttemptAt; }
    public Instant getCreatedAt() { return createdAt; }

    public void markRead() {
        this.readAt = Instant.now();
    }

    public void markDeliveryAttempt() {
        this.deliveryAttempts += 1;
        this.lastDeliveryAttemptAt = Instant.now();
    }

    public void markDeliveryInProgress() {
        markDeliveryAttempt();
        this.deliveryStatus = "DISPATCHING";
        this.deliveryError = null;
    }

    public void markDelivered() {
        this.deliveryStatus = "DELIVERED";
        this.deliveredAt = Instant.now();
        this.deliveryError = null;
    }

    public void markDeliveryFailed(String error) {
        this.deliveryStatus = "FAILED";
        this.deliveryError = error == null ? null : error.substring(0, Math.min(error.length(), 255));
    }
}

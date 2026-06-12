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
    public Instant getCreatedAt() { return createdAt; }

    public void markRead() {
        this.readAt = Instant.now();
    }
}

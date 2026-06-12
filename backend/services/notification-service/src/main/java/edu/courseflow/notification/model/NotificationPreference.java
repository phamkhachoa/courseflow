package edu.courseflow.notification.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;

@Entity
@Table(name = "notification_preferences")
public class NotificationPreference {

    @Id
    private UUID id;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(nullable = false, length = 40)
    private String channel;

    @Column(nullable = false)
    private boolean enabled = true;

    protected NotificationPreference() {
    }

    public NotificationPreference(String userId, String channel, boolean enabled) {
        this.id = UUID.randomUUID();
        this.userId = userId;
        this.channel = channel;
        this.enabled = enabled;
    }

    public UUID getId() { return id; }
    public String getUserId() { return userId; }
    public String getChannel() { return channel; }
    public boolean isEnabled() { return enabled; }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }
}

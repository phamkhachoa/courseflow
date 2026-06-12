package edu.courseflow.livesession.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "live_session_registrations")
public class LiveSessionRegistration {

    @Id
    private UUID id;

    @Column(name = "session_id", nullable = false)
    private UUID sessionId;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(name = "registered_at", nullable = false)
    private Instant registeredAt = Instant.now();

    @Column(nullable = false)
    private boolean attended;

    @Column(name = "joined_at")
    private Instant joinedAt;

    @Version
    @Column(nullable = false)
    private long version;

    protected LiveSessionRegistration() {
    }

    public LiveSessionRegistration(UUID sessionId, String userId) {
        this.id = UUID.randomUUID();
        this.sessionId = sessionId;
        this.userId = userId;
    }

    public UUID getId() { return id; }
    public UUID getSessionId() { return sessionId; }
    public String getUserId() { return userId; }
    public Instant getRegisteredAt() { return registeredAt; }
    public boolean isAttended() { return attended; }

    public void markAttended() {
        this.attended = true;
        if (this.joinedAt == null) {
            this.joinedAt = Instant.now();
        }
    }
}

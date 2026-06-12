package edu.courseflow.enrollment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "enrollment_audit_log")
public class EnrollmentAuditLog {

    @Id
    private UUID id;

    @Column(name = "enrollment_id", nullable = false)
    private UUID enrollmentId;

    @Column(name = "actor_id", nullable = false, length = 64)
    private String actorId;

    @Column(nullable = false, length = 60)
    private String action;

    @Column(name = "old_status", length = 40)
    private String oldStatus;

    @Column(name = "new_status", length = 40)
    private String newStatus;

    @Column(columnDefinition = "TEXT")
    private String reason;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected EnrollmentAuditLog() {
    }

    public EnrollmentAuditLog(UUID enrollmentId, String actorId, String action,
            String oldStatus, String newStatus, String reason) {
        this.id = UUID.randomUUID();
        this.enrollmentId = enrollmentId;
        this.actorId = actorId;
        this.action = action;
        this.oldStatus = oldStatus;
        this.newStatus = newStatus;
        this.reason = reason;
        this.createdAt = Instant.now();
    }

    public UUID getId() {
        return id;
    }

    public UUID getEnrollmentId() {
        return enrollmentId;
    }

    public String getActorId() {
        return actorId;
    }

    public String getAction() {
        return action;
    }

    public String getOldStatus() {
        return oldStatus;
    }

    public String getNewStatus() {
        return newStatus;
    }

    public String getReason() {
        return reason;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}

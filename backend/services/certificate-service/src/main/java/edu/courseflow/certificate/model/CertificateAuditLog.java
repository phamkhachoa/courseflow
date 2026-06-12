package edu.courseflow.certificate.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "certificate_audit_logs")
public class CertificateAuditLog {

    @Id
    private UUID id;

    @Column(name = "certificate_id", nullable = false)
    private UUID certificateId;

    @Column(nullable = false, length = 60)
    private String action;

    @Column(name = "actor_id", nullable = false, length = 64)
    private String actorId;

    @Column(columnDefinition = "TEXT")
    private String reason;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected CertificateAuditLog() {
    }

    public CertificateAuditLog(UUID certificateId, String action, String actorId, String reason) {
        this.id = UUID.randomUUID();
        this.certificateId = certificateId;
        this.action = action;
        this.actorId = actorId;
        this.reason = reason;
    }
}

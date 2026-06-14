package edu.courseflow.promotion.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "incentive_restore_drills")
public class IncentiveRestoreDrill {

    public static final String STATUS_PASSED = "PASSED";
    public static final String STATUS_FAILED = "FAILED";
    public static final String PROMOTION_DATABASE = "cf_promotion";

    @Id
    private UUID id;

    @Column(name = "restore_drill_ref", nullable = false, length = 160)
    private String restoreDrillRef;

    @Column(name = "database_name", nullable = false, length = 120)
    private String databaseName;

    @Column(name = "backup_path", nullable = false, length = 500)
    private String backupPath;

    @Column(name = "artifact_hash", nullable = false, length = 128)
    private String artifactHash;

    @Column(nullable = false, length = 40)
    private String status;

    @Column(name = "checked_at", nullable = false)
    private Instant checkedAt;

    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    @Column(name = "created_by", nullable = false, length = 160)
    private String createdBy;

    @Column(columnDefinition = "TEXT")
    private String note;

    @Column(name = "correlation_id", nullable = false, length = 160)
    private String correlationId;

    @Column(name = "source_client_id", length = 160)
    private String sourceClientId;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected IncentiveRestoreDrill() {
    }

    public IncentiveRestoreDrill(String restoreDrillRef,
                                 String databaseName,
                                 String backupPath,
                                 String artifactHash,
                                 String status,
                                 Instant checkedAt,
                                 Instant expiresAt,
                                 String createdBy,
                                 String note,
                                 String correlationId,
                                 String sourceClientId) {
        this.id = UUID.randomUUID();
        this.restoreDrillRef = restoreDrillRef;
        this.databaseName = databaseName;
        this.backupPath = backupPath;
        this.artifactHash = artifactHash;
        this.status = status;
        this.checkedAt = checkedAt;
        this.expiresAt = expiresAt;
        this.createdBy = createdBy;
        this.note = note;
        this.correlationId = correlationId;
        this.sourceClientId = sourceClientId;
    }

    public boolean validForPromotionExecution(Instant now) {
        return STATUS_PASSED.equals(status)
                && PROMOTION_DATABASE.equals(databaseName)
                && checkedAt != null
                && !checkedAt.isAfter(now)
                && expiresAt != null
                && expiresAt.isAfter(now);
    }

    public UUID getId() { return id; }
    public String getRestoreDrillRef() { return restoreDrillRef; }
    public String getDatabaseName() { return databaseName; }
    public String getBackupPath() { return backupPath; }
    public String getArtifactHash() { return artifactHash; }
    public String getStatus() { return status; }
    public Instant getCheckedAt() { return checkedAt; }
    public Instant getExpiresAt() { return expiresAt; }
    public String getCreatedBy() { return createdBy; }
    public String getNote() { return note; }
    public String getCorrelationId() { return correlationId; }
    public String getSourceClientId() { return sourceClientId; }
    public Instant getCreatedAt() { return createdAt; }
}

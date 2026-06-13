package edu.courseflow.assignment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "attachment_upload_grants")
public class AttachmentUploadGrant {

    @Id
    private UUID id;

    @Column(name = "assignment_id", nullable = false)
    private UUID assignmentId;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "storage_key", nullable = false, unique = true, length = 512)
    private String storageKey;

    @Column(name = "file_name", nullable = false)
    private String fileName;

    @Column(name = "content_type", length = 120)
    private String contentType;

    @Column(name = "size_bytes")
    private Long sizeBytes;

    @Column(name = "issued_at", nullable = false)
    private Instant issuedAt = Instant.now();

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Column(name = "consumed_at")
    private Instant consumedAt;

    @Column(name = "submission_id")
    private UUID submissionId;

    protected AttachmentUploadGrant() {
    }

    public AttachmentUploadGrant(UUID assignmentId, String studentId, String storageKey,
            String fileName, String contentType, Long sizeBytes, Instant expiresAt) {
        this.id = UUID.randomUUID();
        this.assignmentId = assignmentId;
        this.studentId = studentId;
        this.storageKey = storageKey;
        this.fileName = fileName;
        this.contentType = contentType;
        this.sizeBytes = sizeBytes;
        this.expiresAt = expiresAt;
        this.issuedAt = Instant.now();
    }

    public UUID getId() { return id; }
    public UUID getAssignmentId() { return assignmentId; }
    public String getStudentId() { return studentId; }
    public String getStorageKey() { return storageKey; }
    public String getFileName() { return fileName; }
    public String getContentType() { return contentType; }
    public Long getSizeBytes() { return sizeBytes; }
    public Instant getExpiresAt() { return expiresAt; }
    public Instant getConsumedAt() { return consumedAt; }

    public boolean isConsumed() {
        return consumedAt != null;
    }

    public void consume(UUID submissionId, Instant consumedAt) {
        this.submissionId = submissionId;
        this.consumedAt = consumedAt == null ? Instant.now() : consumedAt;
    }
}

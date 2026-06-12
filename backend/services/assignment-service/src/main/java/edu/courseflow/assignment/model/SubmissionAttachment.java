package edu.courseflow.assignment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "submission_attachments")
public class SubmissionAttachment {

    @Id
    private UUID id;

    @Column(name = "submission_id", nullable = false)
    private UUID submissionId;

    @Column(name = "media_asset_id", length = 64)
    private String mediaAssetId;

    @Column(name = "file_name", nullable = false)
    private String fileName;

    @Column(name = "storage_key", nullable = false, length = 512)
    private String storageKey;

    @Column(name = "content_type", length = 120)
    private String contentType;

    @Column(name = "size_bytes")
    private Long sizeBytes;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected SubmissionAttachment() {
    }

    public SubmissionAttachment(UUID submissionId, String mediaAssetId, String fileName,
            String storageKey, String contentType, Long sizeBytes) {
        this.id = UUID.randomUUID();
        this.submissionId = submissionId;
        this.mediaAssetId = mediaAssetId;
        this.fileName = fileName;
        this.storageKey = storageKey;
        this.contentType = contentType;
        this.sizeBytes = sizeBytes;
        this.createdAt = Instant.now();
    }

    public UUID getId() { return id; }
    public String getMediaAssetId() { return mediaAssetId; }
    public String getFileName() { return fileName; }
    public String getStorageKey() { return storageKey; }
    public String getContentType() { return contentType; }
    public Long getSizeBytes() { return sizeBytes; }
    public Instant getCreatedAt() { return createdAt; }
}

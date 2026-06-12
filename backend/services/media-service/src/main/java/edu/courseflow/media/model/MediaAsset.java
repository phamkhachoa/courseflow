package edu.courseflow.media.model;

import edu.courseflow.media.dto.MediaDtos.RegisterMediaAssetRequestDto;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "media_assets")
public class MediaAsset {

    @Id
    private UUID id;

    @Column(name = "owner_id", nullable = false, length = 64)
    private String ownerId;

    @Column(name = "file_name", nullable = false)
    private String fileName;

    @Column(name = "content_type", nullable = false, length = 120)
    private String contentType;

    @Column(name = "storage_key", nullable = false, length = 512)
    private String storageKey;

    @Column(name = "size_bytes", nullable = false)
    private long sizeBytes;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected MediaAsset() {
    }

    public MediaAsset(RegisterMediaAssetRequestDto request) {
        this(request.ownerId(), request.fileName(), request.contentType(), request.storageKey(), request.sizeBytes());
    }

    public MediaAsset(String ownerId, String fileName, String contentType, String storageKey, long sizeBytes) {
        this.id = UUID.randomUUID();
        this.ownerId = ownerId;
        this.fileName = fileName;
        this.contentType = contentType;
        this.storageKey = storageKey;
        this.sizeBytes = sizeBytes;
    }

    public UUID getId() { return id; }
    public String getOwnerId() { return ownerId; }
    public String getFileName() { return fileName; }
    public String getContentType() { return contentType; }
    public String getStorageKey() { return storageKey; }
    public long getSizeBytes() { return sizeBytes; }
    public Instant getCreatedAt() { return createdAt; }
}

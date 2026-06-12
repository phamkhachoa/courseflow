package edu.courseflow.media.model;

import edu.courseflow.media.dto.VideoDtos.RegisterVideoRequestDto;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "video_assets")
public class VideoAsset {

    @Id
    private UUID id;

    @Column(name = "media_asset_id")
    private UUID mediaAssetId;

    @Column(name = "course_id")
    private UUID courseId;

    @Column(nullable = false)
    private String title;

    @Column(name = "source_storage_key", nullable = false, length = 512)
    private String sourceStorageKey;

    @Column(name = "duration_seconds")
    private Integer durationSeconds;

    @Column(nullable = false, length = 40)
    private String status = "UPLOADED";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected VideoAsset() {
    }

    public VideoAsset(RegisterVideoRequestDto request) {
        this.id = UUID.randomUUID();
        this.mediaAssetId = request.mediaAssetId() == null ? null : UUID.fromString(request.mediaAssetId());
        this.courseId = request.courseId() == null ? null : UUID.fromString(request.courseId());
        this.title = request.title();
        this.sourceStorageKey = request.sourceStorageKey();
        this.durationSeconds = request.durationSeconds();
    }

    public UUID getId() { return id; }
    public UUID getMediaAssetId() { return mediaAssetId; }
    public UUID getCourseId() { return courseId; }
    public String getTitle() { return title; }
    public String getSourceStorageKey() { return sourceStorageKey; }
    public Integer getDurationSeconds() { return durationSeconds; }
    public String getStatus() { return status; }
    public Instant getCreatedAt() { return createdAt; }

    public void updateStatus(String status) {
        this.status = status;
        this.updatedAt = Instant.now();
    }
}

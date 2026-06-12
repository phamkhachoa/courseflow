package edu.courseflow.media.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "transcode_jobs")
public class TranscodeJob {

    @Id
    private UUID id;

    @Column(name = "video_id", nullable = false)
    private UUID videoId;

    @Column(nullable = false, length = 40)
    private String status = "QUEUED";

    @Column(name = "requested_by", nullable = false, length = 64)
    private String requestedBy;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "completed_at")
    private Instant completedAt;

    protected TranscodeJob() {
    }

    public TranscodeJob(UUID videoId, String requestedBy) {
        this.id = UUID.randomUUID();
        this.videoId = videoId;
        this.requestedBy = requestedBy;
    }

    public UUID getId() { return id; }
}

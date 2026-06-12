package edu.courseflow.media.model;

import edu.courseflow.media.dto.VideoDtos.UpdateProgressRequestDto;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "video_progress")
public class VideoProgress {

    @Id
    private UUID id;

    @Column(name = "video_id", nullable = false)
    private UUID videoId;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(name = "position_seconds", nullable = false)
    private int positionSeconds;

    @Column(name = "duration_seconds")
    private Integer durationSeconds;

    @Column(name = "playback_rate", nullable = false)
    private BigDecimal playbackRate = BigDecimal.ONE;

    @Column(nullable = false)
    private boolean completed;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected VideoProgress() {
    }

    public VideoProgress(UUID videoId, UpdateProgressRequestDto request) {
        this.id = UUID.randomUUID();
        this.videoId = videoId;
        this.userId = request.userId();
        updateFrom(request);
    }

    public UUID getVideoId() { return videoId; }
    public String getUserId() { return userId; }
    public int getPositionSeconds() { return positionSeconds; }
    public Integer getDurationSeconds() { return durationSeconds; }
    public BigDecimal getPlaybackRate() { return playbackRate; }
    public boolean isCompleted() { return completed; }
    public Instant getUpdatedAt() { return updatedAt; }

    public void updateFrom(UpdateProgressRequestDto request) {
        this.positionSeconds = request.positionSeconds();
        if (request.durationSeconds() != null) {
            this.durationSeconds = request.durationSeconds();
        }
        this.playbackRate = BigDecimal.valueOf(request.playbackRate() == null ? 1.0 : request.playbackRate());
        this.completed = request.completed() != null && request.completed();
        this.updatedAt = Instant.now();
    }
}

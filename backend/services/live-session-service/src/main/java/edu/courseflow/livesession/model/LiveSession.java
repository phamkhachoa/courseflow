package edu.courseflow.livesession.model;

import edu.courseflow.livesession.dto.LiveSessionDtos.CreateLiveSessionRequestDto;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "live_sessions")
public class LiveSession {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(nullable = false)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "host_id", nullable = false, length = 64)
    private String hostId;

    @Column(nullable = false, length = 40)
    private String provider = "internal";

    @Column(name = "provider_meeting_id")
    private String providerMeetingId;

    @Column(name = "scheduled_start", nullable = false)
    private Instant scheduledStart;

    @Column(name = "scheduled_end")
    private Instant scheduledEnd;

    @Column(name = "actual_start")
    private Instant actualStart;

    @Column(name = "actual_end")
    private Instant actualEnd;

    private Integer capacity;

    @Column(nullable = false, length = 40)
    private String status = "SCHEDULED";

    @Column(name = "recording_storage_key", length = 512)
    private String recordingStorageKey;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    @Column(nullable = false)
    private long version;

    protected LiveSession() {
    }

    public LiveSession(CreateLiveSessionRequestDto request) {
        this.id = UUID.randomUUID();
        this.courseId = UUID.fromString(request.courseId());
        this.title = request.title();
        this.description = request.description();
        this.hostId = request.hostId();
        this.provider = request.provider() == null ? "internal" : request.provider();
        this.scheduledStart = request.scheduledStart();
        this.scheduledEnd = request.scheduledEnd();
        this.capacity = request.capacity();
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public String getTitle() { return title; }
    public String getDescription() { return description; }
    public String getHostId() { return hostId; }
    public String getProvider() { return provider; }
    public String getProviderMeetingId() { return providerMeetingId; }
    public Instant getScheduledStart() { return scheduledStart; }
    public Instant getScheduledEnd() { return scheduledEnd; }
    public Instant getActualStart() { return actualStart; }
    public Instant getActualEnd() { return actualEnd; }
    public Integer getCapacity() { return capacity; }
    public String getStatus() { return status; }
    public String getRecordingStorageKey() { return recordingStorageKey; }

    public void updateStatus(String status, boolean setStart, boolean setEnd, String recordingKey) {
        this.status = status;
        if (setStart) {
            this.actualStart = Instant.now();
        }
        if (setEnd) {
            this.actualEnd = Instant.now();
        }
        if (recordingKey != null) {
            this.recordingStorageKey = recordingKey;
        }
        this.updatedAt = Instant.now();
    }
}

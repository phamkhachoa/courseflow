package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "recommendation_tracking_events")
public class RecommendationTrackingEvent {

    public static final String TYPE_IMPRESSION = "IMPRESSION";
    public static final String TYPE_CLICK = "CLICK";
    public static final String TYPE_ENROLLMENT = "ENROLLMENT";

    @Id
    @Column(name = "event_id")
    private UUID eventId;

    @Column(name = "event_type", nullable = false, length = 60)
    private String eventType;

    @Column(nullable = false, length = 60)
    private String source;

    @Column(name = "course_id")
    private UUID courseId;

    @Column(name = "related_course_id")
    private UUID relatedCourseId;

    @Column(name = "student_id", length = 64)
    private String studentId;

    @Column(name = "session_id", length = 120)
    private String sessionId;

    @Column(nullable = false, length = 60)
    private String placement = ManualRelatedCourse.DEFAULT_PLACEMENT;

    @Column(name = "reason_code", length = 80)
    private String reasonCode;

    @Column(name = "recommendation_source", length = 60)
    private String recommendationSource;

    @Column(name = "model_version", length = 80)
    private String modelVersion;

    @Column(name = "attribution_id", length = 120)
    private String attributionId;

    @Column(name = "occurred_at", nullable = false)
    private Instant occurredAt;

    @Column(name = "metadata_json")
    private String metadataJson;

    @Column(name = "request_hash", nullable = false, length = 96)
    private String requestHash;

    @Column(name = "actor_id", length = 120)
    private String actorId;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected RecommendationTrackingEvent() {
    }

    public RecommendationTrackingEvent(UUID eventId,
                                       String eventType,
                                       String source,
                                       UUID courseId,
                                       UUID relatedCourseId,
                                       String studentId,
                                       String sessionId,
                                       String placement,
                                       String reasonCode,
                                       String recommendationSource,
                                       String modelVersion,
                                       String attributionId,
                                       Instant occurredAt,
                                       String metadataJson,
                                       String requestHash,
                                       String actorId) {
        this.eventId = eventId;
        this.eventType = eventType;
        this.source = source;
        this.courseId = courseId;
        this.relatedCourseId = relatedCourseId;
        this.studentId = studentId;
        this.sessionId = sessionId;
        this.placement = placement;
        this.reasonCode = reasonCode;
        this.recommendationSource = recommendationSource;
        this.modelVersion = modelVersion;
        this.attributionId = attributionId;
        this.occurredAt = occurredAt;
        this.metadataJson = metadataJson;
        this.requestHash = requestHash;
        this.actorId = actorId;
    }

    public RecommendationTrackingEvent(UUID eventId,
                                       String eventType,
                                       String source,
                                       UUID courseId,
                                       UUID relatedCourseId,
                                       String studentId,
                                       String sessionId,
                                       String placement,
                                       String reasonCode,
                                       String recommendationSource,
                                       String modelVersion,
                                       Instant occurredAt,
                                       String metadataJson,
                                       String requestHash,
                                       String actorId) {
        this(
                eventId,
                eventType,
                source,
                courseId,
                relatedCourseId,
                studentId,
                sessionId,
                placement,
                reasonCode,
                recommendationSource,
                modelVersion,
                null,
                occurredAt,
                metadataJson,
                requestHash,
                actorId);
    }

    public UUID getEventId() { return eventId; }
    public String getEventType() { return eventType; }
    public String getSource() { return source; }
    public UUID getCourseId() { return courseId; }
    public UUID getRelatedCourseId() { return relatedCourseId; }
    public String getStudentId() { return studentId; }
    public String getSessionId() { return sessionId; }
    public String getAttributionId() { return attributionId; }
    public String getRequestHash() { return requestHash; }
    public Instant getOccurredAt() { return occurredAt; }
}

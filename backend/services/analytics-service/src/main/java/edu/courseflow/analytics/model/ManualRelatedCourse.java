package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "manual_related_courses")
public class ManualRelatedCourse {

    public static final String STATUS_ACTIVE = "ACTIVE";
    public static final String STATUS_ARCHIVED = "ARCHIVED";
    public static final String DEFAULT_PLACEMENT = "COURSE_DETAIL";

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "related_course_id", nullable = false)
    private UUID relatedCourseId;

    @Column(nullable = false, length = 60)
    private String placement = DEFAULT_PLACEMENT;

    @Column(nullable = false)
    private int position;

    @Column(nullable = false)
    private BigDecimal weight = BigDecimal.ONE;

    @Column(length = 160)
    private String reason;

    @Column(nullable = false, length = 30)
    private String status = STATUS_ACTIVE;

    @Column(name = "effective_from")
    private Instant effectiveFrom;

    @Column(name = "effective_to")
    private Instant effectiveTo;

    @Column(name = "created_by", length = 120)
    private String createdBy;

    @Column(name = "updated_by", length = 120)
    private String updatedBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    @Column(nullable = false)
    private long version;

    protected ManualRelatedCourse() {
    }

    public ManualRelatedCourse(UUID courseId, UUID relatedCourseId, String actorId) {
        this.id = UUID.randomUUID();
        this.courseId = courseId;
        this.relatedCourseId = relatedCourseId;
        this.createdBy = actorId;
        this.updatedBy = actorId;
    }

    public ManualRelatedCourse(UUID id, UUID courseId, UUID relatedCourseId, String placement, String actorId) {
        this.id = id;
        this.courseId = courseId;
        this.relatedCourseId = relatedCourseId;
        this.placement = placement == null || placement.isBlank() ? DEFAULT_PLACEMENT : placement;
        this.createdBy = actorId;
        this.updatedBy = actorId;
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public UUID getRelatedCourseId() { return relatedCourseId; }
    public String getPlacement() { return placement; }
    public int getPosition() { return position; }
    public BigDecimal getWeight() { return weight; }
    public String getReason() { return reason; }
    public String getStatus() { return status; }
    public Instant getEffectiveFrom() { return effectiveFrom; }
    public Instant getEffectiveTo() { return effectiveTo; }
    public String getCreatedBy() { return createdBy; }
    public String getUpdatedBy() { return updatedBy; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    public boolean isActive(Instant now) {
        return STATUS_ACTIVE.equals(status)
                && (effectiveFrom == null || !effectiveFrom.isAfter(now))
                && (effectiveTo == null || effectiveTo.isAfter(now));
    }

    public boolean isEffectiveAt(Instant now) {
        return isActive(now);
    }

    public void update(int position,
                       BigDecimal weight,
                       String reason,
                       Instant effectiveFrom,
                       Instant effectiveTo,
                       String actorId) {
        update(weight, reason, position, null, effectiveFrom, effectiveTo, actorId);
    }

    public void update(BigDecimal weight,
                       String reason,
                       Integer position,
                       String status,
                       Instant effectiveFrom,
                       Instant effectiveTo,
                       String actorId) {
        if (weight != null) {
            this.weight = weight;
        }
        this.reason = reason;
        if (position != null) {
            this.position = position;
        }
        if (status != null) {
            this.status = status;
        }
        this.effectiveFrom = effectiveFrom;
        this.effectiveTo = effectiveTo;
        this.updatedBy = actorId;
        this.updatedAt = Instant.now();
    }

    public void setPosition(int position, String actorId) {
        this.position = position;
        this.updatedBy = actorId;
        this.updatedAt = Instant.now();
    }

    public void archive(String actorId) {
        this.status = STATUS_ARCHIVED;
        this.updatedBy = actorId;
        this.updatedAt = Instant.now();
    }
}

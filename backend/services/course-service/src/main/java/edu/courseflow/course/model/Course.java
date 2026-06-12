package edu.courseflow.course.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "courses")
public class Course {

    @Id
    private UUID id;

    @Column(nullable = false, unique = true, length = 64)
    private String code;

    @Column(nullable = false)
    private String title;

    @Column(nullable = false, unique = true)
    private String slug;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String summary;

    @Column(name = "department_id", nullable = false)
    private UUID departmentId;

    @Column(name = "owner_id", nullable = false, length = 64)
    private String ownerId;

    @Column(nullable = false, length = 40)
    private String level;

    @Column(nullable = false, length = 40)
    private String status = "DRAFT";

    @Column(name = "current_version_no", nullable = false)
    private int currentVersionNo = 1;

    @Column(name = "review_state", nullable = false, length = 40)
    private String reviewState = "DRAFT";

    @Column(name = "last_authored_by", length = 64)
    private String lastAuthoredBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected Course() {
    }

    public Course(UUID id, String code, String title, String slug, String summary,
            UUID departmentId, String ownerId, String level) {
        this.id = id;
        this.code = code;
        this.title = title;
        this.slug = slug;
        this.summary = summary;
        this.departmentId = departmentId;
        this.ownerId = ownerId;
        this.level = level;
        this.status = "DRAFT";
        this.reviewState = "DRAFT";
        this.lastAuthoredBy = ownerId;
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    public UUID getId() {
        return id;
    }

    public String getCode() {
        return code;
    }

    public String getTitle() {
        return title;
    }

    public String getSlug() {
        return slug;
    }

    public String getSummary() {
        return summary;
    }

    public UUID getDepartmentId() {
        return departmentId;
    }

    public String getOwnerId() {
        return ownerId;
    }

    public String getLevel() {
        return level;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
        touch();
    }

    public int getCurrentVersionNo() {
        return currentVersionNo;
    }

    public void setCurrentVersionNo(int currentVersionNo) {
        this.currentVersionNo = currentVersionNo;
        touch();
    }

    public String getReviewState() {
        return reviewState;
    }

    public void setReviewState(String reviewState) {
        this.reviewState = reviewState;
        touch();
    }

    public String getLastAuthoredBy() {
        return lastAuthoredBy;
    }

    public void setLastAuthoredBy(String lastAuthoredBy) {
        this.lastAuthoredBy = lastAuthoredBy;
        touch();
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void touch() {
        this.updatedAt = Instant.now();
    }
}

package edu.courseflow.course.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "course_versions")
public class CourseVersion {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "version_no", nullable = false)
    private int versionNo;

    @Column(nullable = false, length = 40)
    private String state = "DRAFT";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private String snapshot;

    @Column(name = "created_by", nullable = false, length = 64)
    private String createdBy;

    @Column(columnDefinition = "TEXT")
    private String note;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "published_at")
    private Instant publishedAt;

    @Version
    @Column(nullable = false)
    private long version;

    protected CourseVersion() {
    }

    public CourseVersion(UUID id, UUID courseId, int versionNo, String state, String createdBy, String note) {
        this.id = id;
        this.courseId = courseId;
        this.versionNo = versionNo;
        this.state = state;
        this.createdBy = createdBy;
        this.note = note;
        this.createdAt = Instant.now();
    }

    public UUID getId() {
        return id;
    }

    public UUID getCourseId() {
        return courseId;
    }

    public int getVersionNo() {
        return versionNo;
    }

    public String getState() {
        return state;
    }

    public void setState(String state) {
        this.state = state;
    }

    public void publish(String snapshot, Instant publishedAt) {
        this.state = "PUBLISHED";
        this.snapshot = snapshot;
        this.publishedAt = publishedAt;
    }

    public String getSnapshot() {
        return snapshot;
    }

    public String getCreatedBy() {
        return createdBy;
    }

    public String getNote() {
        return note;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getPublishedAt() {
        return publishedAt;
    }
}

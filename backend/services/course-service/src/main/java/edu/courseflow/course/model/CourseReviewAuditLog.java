package edu.courseflow.course.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "course_review_audit_log")
public class CourseReviewAuditLog {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "version_no", nullable = false)
    private int versionNo;

    @Column(name = "actor_id", nullable = false, length = 64)
    private String actorId;

    @Column(name = "actor_role", length = 120)
    private String actorRole;

    @Column(nullable = false, length = 60)
    private String action;

    @Column(name = "from_state", length = 40)
    private String fromState;

    @Column(name = "to_state", length = 40)
    private String toState;

    @Column(columnDefinition = "TEXT")
    private String note;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb", nullable = false)
    private List<String> checklist = List.of();

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected CourseReviewAuditLog() {
    }

    public CourseReviewAuditLog(UUID id, UUID courseId, int versionNo, String actorId, String actorRole,
            String action, String fromState, String toState, String note, List<String> checklist) {
        this.id = id;
        this.courseId = courseId;
        this.versionNo = versionNo;
        this.actorId = actorId;
        this.actorRole = actorRole;
        this.action = action;
        this.fromState = fromState;
        this.toState = toState;
        this.note = note;
        this.checklist = checklist == null ? List.of() : List.copyOf(checklist);
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

    public String getActorId() {
        return actorId;
    }

    public String getActorRole() {
        return actorRole;
    }

    public String getAction() {
        return action;
    }

    public String getFromState() {
        return fromState;
    }

    public String getToState() {
        return toState;
    }

    public String getNote() {
        return note;
    }

    public List<String> getChecklist() {
        return checklist == null ? List.of() : checklist;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}

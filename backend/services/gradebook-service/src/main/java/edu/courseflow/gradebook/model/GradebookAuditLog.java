package edu.courseflow.gradebook.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "gradebook_audit_logs")
public class GradebookAuditLog {

    @Id
    private UUID id;

    @Column(nullable = false, length = 80)
    private String action;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "student_id", length = 64)
    private String studentId;

    @Column(name = "grade_item_id")
    private UUID gradeItemId;

    @Column(name = "grade_entry_id")
    private UUID gradeEntryId;

    @Column(name = "final_grade_id")
    private UUID finalGradeId;

    @Column(name = "actor_id", nullable = false, length = 64)
    private String actorId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "reason_codes", nullable = false, columnDefinition = "jsonb")
    private String reasonCodes;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false, columnDefinition = "jsonb")
    private String payload;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected GradebookAuditLog() {
    }

    public GradebookAuditLog(
            String action,
            UUID courseId,
            String studentId,
            UUID gradeItemId,
            UUID gradeEntryId,
            UUID finalGradeId,
            String actorId,
            String reasonCodes,
            String payload) {
        this.id = UUID.randomUUID();
        this.action = action;
        this.courseId = courseId;
        this.studentId = studentId;
        this.gradeItemId = gradeItemId;
        this.gradeEntryId = gradeEntryId;
        this.finalGradeId = finalGradeId;
        this.actorId = actorId == null || actorId.isBlank() ? "system" : actorId.trim();
        this.reasonCodes = reasonCodes == null || reasonCodes.isBlank() ? "[]" : reasonCodes;
        this.payload = payload == null || payload.isBlank() ? "{}" : payload;
    }

    public UUID getId() { return id; }
    public String getAction() { return action; }
    public UUID getCourseId() { return courseId; }
    public String getStudentId() { return studentId; }
    public UUID getGradeItemId() { return gradeItemId; }
    public UUID getGradeEntryId() { return gradeEntryId; }
    public UUID getFinalGradeId() { return finalGradeId; }
    public String getActorId() { return actorId; }
    public String getReasonCodes() { return reasonCodes; }
    public String getPayload() { return payload; }
    public Instant getCreatedAt() { return createdAt; }
}

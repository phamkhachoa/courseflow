package edu.courseflow.enrollment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "enrollment_remediation_cases")
public class EnrollmentRemediationCase {

    @Id
    private UUID id;

    @Column(name = "case_type", nullable = false, length = 60)
    private String caseType;

    @Column(nullable = false, length = 40)
    private String status;

    @Column(nullable = false, length = 20)
    private String severity;

    @Column(name = "enrollment_id")
    private UUID enrollmentId;

    @Column(name = "checkout_attempt_id")
    private UUID checkoutAttemptId;

    @Column(name = "promotion_application_id")
    private UUID promotionApplicationId;

    @Column(name = "order_id")
    private UUID orderId;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "assignee_id", nullable = false, length = 80)
    private String assigneeId;

    @Column(columnDefinition = "TEXT")
    private String note;

    @Column(name = "reason_code", nullable = false, length = 120)
    private String reasonCode;

    @Column(name = "sla_due_at", nullable = false)
    private Instant slaDueAt;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Column(name = "closed_at")
    private Instant closedAt;

    @Version
    private long version;

    protected EnrollmentRemediationCase() {
    }

    public EnrollmentRemediationCase(
            String caseType,
            String severity,
            UUID enrollmentId,
            UUID checkoutAttemptId,
            UUID promotionApplicationId,
            UUID orderId,
            String studentId,
            UUID courseId,
            String assigneeId,
            String note,
            String reasonCode,
            Instant slaDueAt) {
        this.id = UUID.randomUUID();
        this.caseType = caseType;
        this.status = "OPEN";
        this.severity = severity;
        this.enrollmentId = enrollmentId;
        this.checkoutAttemptId = checkoutAttemptId;
        this.promotionApplicationId = promotionApplicationId;
        this.orderId = orderId;
        this.studentId = studentId;
        this.courseId = courseId;
        this.assigneeId = assigneeId;
        this.note = note;
        this.reasonCode = reasonCode;
        this.slaDueAt = slaDueAt;
    }

    public void assign(String assigneeId, String note) {
        this.assigneeId = assigneeId;
        if ("OPEN".equals(this.status)) {
            this.status = "IN_PROGRESS";
        }
        if (note != null && !note.isBlank()) {
            this.note = note.trim();
        }
        touch();
    }

    public void updateNote(String note) {
        if (note != null && !note.isBlank()) {
            this.note = note.trim();
            touch();
        }
    }

    public void resolve(String note) {
        this.status = "RESOLVED";
        if (note != null && !note.isBlank()) {
            this.note = note.trim();
        }
        this.closedAt = Instant.now();
        touch();
    }

    public void reopen(String note) {
        this.status = "OPEN";
        if (note != null && !note.isBlank()) {
            this.note = note.trim();
        }
        this.closedAt = null;
        touch();
    }

    private void touch() {
        this.updatedAt = Instant.now();
    }

    public UUID getId() { return id; }
    public String getCaseType() { return caseType; }
    public String getStatus() { return status; }
    public String getSeverity() { return severity; }
    public UUID getEnrollmentId() { return enrollmentId; }
    public UUID getCheckoutAttemptId() { return checkoutAttemptId; }
    public UUID getPromotionApplicationId() { return promotionApplicationId; }
    public UUID getOrderId() { return orderId; }
    public String getStudentId() { return studentId; }
    public UUID getCourseId() { return courseId; }
    public String getAssigneeId() { return assigneeId; }
    public String getNote() { return note; }
    public String getReasonCode() { return reasonCode; }
    public Instant getSlaDueAt() { return slaDueAt; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public Instant getClosedAt() { return closedAt; }
}

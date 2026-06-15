package edu.courseflow.enrollment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "enrollments")
public class Enrollment {

    @Id
    private UUID id;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "section_id")
    private UUID sectionId;

    @Column(nullable = false, length = 40)
    private String status = "ACTIVE";

    @Column(name = "enrolled_at", nullable = false)
    private Instant enrolledAt = Instant.now();

    @Column(name = "dropped_at")
    private Instant droppedAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    @Column(name = "drop_reason", columnDefinition = "TEXT")
    private String dropReason;

    @Column(name = "dropped_by", length = 64)
    private String droppedBy;

    @Version
    @Column(nullable = false)
    private long version;

    protected Enrollment() {
    }

    public Enrollment(UUID id, String studentId, UUID courseId, UUID sectionId) {
        this.id = id;
        this.studentId = studentId;
        this.courseId = courseId;
        this.sectionId = sectionId;
        this.status = "ACTIVE";
        this.enrolledAt = Instant.now();
    }

    public UUID getId() {
        return id;
    }

    public String getStudentId() {
        return studentId;
    }

    public UUID getCourseId() {
        return courseId;
    }

    public UUID getSectionId() {
        return sectionId;
    }

    public String getStatus() {
        return status;
    }

    public Instant getEnrolledAt() {
        return enrolledAt;
    }

    public Instant getDroppedAt() {
        return droppedAt;
    }

    public Instant getCompletedAt() {
        return completedAt;
    }

    public String getDropReason() {
        return dropReason;
    }

    public void activate() {
        this.status = "ACTIVE";
        this.enrolledAt = Instant.now();
        this.droppedAt = null;
        this.completedAt = null;
        this.dropReason = null;
        this.droppedBy = null;
    }

    public void pendingPayment() {
        this.status = "PENDING_PAYMENT";
        this.enrolledAt = Instant.now();
        this.droppedAt = null;
        this.completedAt = null;
        this.dropReason = null;
        this.droppedBy = null;
    }

    public void changeStatus(String actorId, String newStatus, String reason) {
        Instant now = Instant.now();
        this.status = newStatus;
        if ("DROPPED".equals(newStatus)) {
            this.droppedAt = now;
            this.dropReason = reason == null ? this.dropReason : reason;
            this.droppedBy = actorId;
        } else if ("COMPLETED".equals(newStatus)) {
            this.completedAt = now;
            this.dropReason = reason == null ? this.dropReason : reason;
        } else if ("ACTIVE".equals(newStatus)) {
            activate();
        } else if ("PENDING_PAYMENT".equals(newStatus)) {
            pendingPayment();
        }
    }
}

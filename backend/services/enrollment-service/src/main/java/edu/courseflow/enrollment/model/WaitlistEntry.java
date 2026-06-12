package edu.courseflow.enrollment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "waitlist_entries")
public class WaitlistEntry {

    @Id
    private UUID id;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(nullable = false)
    private int position;

    @Column(nullable = false, length = 40)
    private String status = "WAITING";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "promoted_at")
    private Instant promotedAt;

    @Version
    @Column(nullable = false)
    private long version;

    protected WaitlistEntry() {
    }

    public WaitlistEntry(UUID id, String studentId, UUID courseId, int position) {
        this.id = id;
        this.studentId = studentId;
        this.courseId = courseId;
        this.position = position;
        this.status = "WAITING";
        this.createdAt = Instant.now();
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

    public int getPosition() {
        return position;
    }

    public void setPosition(int position) {
        this.position = position;
    }

    public String getStatus() {
        return status;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void markWaiting() {
        this.status = "WAITING";
        this.promotedAt = null;
    }

    public void requeue(int position) {
        this.position = position;
        this.status = "WAITING";
        this.createdAt = Instant.now();
        this.promotedAt = null;
    }

    public void markPromoted() {
        this.status = "PROMOTED";
        this.promotedAt = Instant.now();
    }

    public void markSkipped() {
        this.status = "SKIPPED";
        this.promotedAt = Instant.now();
    }
}

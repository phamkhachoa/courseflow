package edu.courseflow.course.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "learner_module_progress")
public class LearnerModuleProgress {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "module_id", nullable = false)
    private UUID moduleId;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(nullable = false, length = 40)
    private String status = "NOT_STARTED";

    @Column(name = "completed_at")
    private Instant completedAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected LearnerModuleProgress() {
    }

    public LearnerModuleProgress(UUID id, UUID courseId, UUID moduleId, String studentId,
            String status, Instant completedAt) {
        this.id = id;
        this.courseId = courseId;
        this.moduleId = moduleId;
        this.studentId = studentId;
        this.status = status;
        this.completedAt = completedAt;
        this.updatedAt = completedAt == null ? Instant.now() : completedAt;
    }

    public UUID getId() {
        return id;
    }

    public UUID getCourseId() {
        return courseId;
    }

    public UUID getModuleId() {
        return moduleId;
    }

    public String getStudentId() {
        return studentId;
    }

    public String getStatus() {
        return status;
    }

    public Instant getCompletedAt() {
        return completedAt;
    }

    public void complete(Instant completedAt) {
        this.status = "COMPLETED";
        this.completedAt = completedAt;
        this.updatedAt = completedAt;
    }
}

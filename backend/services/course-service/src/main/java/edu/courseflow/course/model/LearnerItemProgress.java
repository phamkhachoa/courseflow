package edu.courseflow.course.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "learner_item_progress")
public class LearnerItemProgress {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "module_id", nullable = false)
    private UUID moduleId;

    @Column(name = "item_id", nullable = false)
    private UUID itemId;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(nullable = false, length = 40)
    private String status = "NOT_STARTED";

    @Column(name = "progress_type", nullable = false, length = 60)
    private String progressType = "MANUAL";

    @Column(name = "completed_at")
    private Instant completedAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected LearnerItemProgress() {
    }

    public LearnerItemProgress(UUID id, UUID courseId, UUID moduleId, UUID itemId, String studentId) {
        this.id = id;
        this.courseId = courseId;
        this.moduleId = moduleId;
        this.itemId = itemId;
        this.studentId = studentId;
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

    public UUID getItemId() {
        return itemId;
    }

    public String getStudentId() {
        return studentId;
    }

    public String getStatus() {
        return status;
    }

    public String getProgressType() {
        return progressType;
    }

    public Instant getCompletedAt() {
        return completedAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void complete(String progressType, Instant completedAt) {
        this.status = "COMPLETED";
        this.progressType = progressType == null || progressType.isBlank() ? "MANUAL" : progressType;
        this.completedAt = completedAt;
        this.updatedAt = completedAt;
    }
}

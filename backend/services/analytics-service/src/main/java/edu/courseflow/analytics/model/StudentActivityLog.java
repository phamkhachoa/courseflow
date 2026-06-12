package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "student_activity_log")
public class StudentActivityLog {

    @Id
    private UUID id;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "activity_type", nullable = false, length = 60)
    private String activityType;

    @Column(name = "duration_minutes", nullable = false)
    private int durationMinutes;

    @Column(name = "occurred_at", nullable = false)
    private Instant occurredAt = Instant.now();

    protected StudentActivityLog() {
    }

    public StudentActivityLog(String studentId, UUID courseId, String activityType, int durationMinutes) {
        this.id = UUID.randomUUID();
        this.studentId = studentId;
        this.courseId = courseId;
        this.activityType = activityType;
        this.durationMinutes = durationMinutes;
    }

    public String getActivityType() { return activityType; }
    public int getDurationMinutes() { return durationMinutes; }
    public Instant getOccurredAt() { return occurredAt; }
}

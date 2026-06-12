package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "student_time_spent")
public class StudentTimeSpent {

    @Id
    private UUID id;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "minutes_spent", nullable = false)
    private int minutesSpent;

    @Column(name = "last_activity_at")
    private Instant lastActivityAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected StudentTimeSpent() {
    }

    public StudentTimeSpent(String studentId, UUID courseId) {
        this.id = UUID.randomUUID();
        this.studentId = studentId;
        this.courseId = courseId;
    }

    public String getStudentId() { return studentId; }
    public UUID getCourseId() { return courseId; }
    public int getMinutesSpent() { return minutesSpent; }
    public Instant getLastActivityAt() { return lastActivityAt; }

    public void addMinutes(int minutes, Instant lastActivity) {
        this.minutesSpent += minutes;
        this.lastActivityAt = lastActivity;
        this.updatedAt = Instant.now();
    }
}

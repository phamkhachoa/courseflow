package edu.courseflow.gradebook.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "grading_schemes")
public class GradingScheme {
    @Id
    private UUID id;
    @Column(name = "course_id", nullable = false)
    private UUID courseId;
    @Column(nullable = false, length = 120)
    private String name;
    @Column(name = "is_default", nullable = false)
    private boolean defaultScheme;
    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected GradingScheme() {
    }

    public GradingScheme(UUID id, UUID courseId, String name, boolean defaultScheme) {
        this.id = id;
        this.courseId = courseId;
        this.name = name;
        this.defaultScheme = defaultScheme;
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public String getName() { return name; }
    public boolean isDefaultScheme() { return defaultScheme; }
    public void setDefaultScheme(boolean defaultScheme) { this.defaultScheme = defaultScheme; }
}

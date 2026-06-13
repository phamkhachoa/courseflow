package edu.courseflow.course.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "course_modules")
public class CourseModule {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(nullable = false)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(nullable = false)
    private int position;

    @Column(nullable = false, length = 40)
    private String status = "DRAFT";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Version
    @Column(nullable = false)
    private long version;

    protected CourseModule() {
    }

    public CourseModule(UUID id, UUID courseId, String title, String description, int position, String status) {
        this.id = id;
        this.courseId = courseId;
        this.title = title;
        this.description = description;
        this.position = position;
        this.status = status;
        this.createdAt = Instant.now();
    }

    public UUID getId() {
        return id;
    }

    public UUID getCourseId() {
        return courseId;
    }

    public String getTitle() {
        return title;
    }

    public String getDescription() {
        return description;
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

    public void setStatus(String status) {
        this.status = status;
    }

    public void restoreDraft(String title, String description, int position) {
        this.title = title;
        this.description = description;
        this.position = position;
        this.status = "DRAFT";
    }

    public void updateDraft(String title, String description) {
        this.title = title;
        this.description = description;
        this.status = "DRAFT";
    }

    public void archive(int position) {
        this.position = position;
        this.status = "ARCHIVED";
    }
}

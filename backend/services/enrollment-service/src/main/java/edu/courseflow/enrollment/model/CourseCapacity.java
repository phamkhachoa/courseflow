package edu.courseflow.enrollment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "course_capacity")
public class CourseCapacity {

    @Id
    @Column(name = "course_id")
    private UUID courseId;

    private Integer capacity;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    @Column(nullable = false)
    private long version;

    protected CourseCapacity() {
    }

    public CourseCapacity(UUID courseId, Integer capacity) {
        this.courseId = courseId;
        this.capacity = capacity;
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    public Integer getCapacity() {
        return capacity;
    }

    public void setCapacity(Integer capacity) {
        this.capacity = capacity;
        this.updatedAt = Instant.now();
    }
}

package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "related_courses")
public class RelatedCourse {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "related_course_id", nullable = false)
    private UUID relatedCourseId;

    @Column(nullable = false)
    private BigDecimal score = BigDecimal.ZERO;

    protected RelatedCourse() {
    }

    public UUID getCourseId() { return courseId; }
    public UUID getRelatedCourseId() { return relatedCourseId; }
    public BigDecimal getScore() { return score; }
}

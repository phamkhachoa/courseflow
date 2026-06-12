package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.IdClass;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "grade_distribution")
@IdClass(GradeDistributionId.class)
public class GradeDistribution {

    @Id
    @Column(name = "course_id")
    private UUID courseId;

    @Id
    @Column(name = "grade_band", length = 10)
    private String gradeBand;

    @Column(name = "student_count", nullable = false)
    private int studentCount;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected GradeDistribution() {
    }

    public GradeDistribution(UUID courseId, String gradeBand) {
        this.courseId = courseId;
        this.gradeBand = gradeBand;
    }

    public String getGradeBand() { return gradeBand; }
    public int getStudentCount() { return studentCount; }

    public void setStudentCount(int studentCount) {
        this.studentCount = studentCount;
        this.updatedAt = Instant.now();
    }
}

package edu.courseflow.gradebook.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "final_grades")
public class FinalGrade {
    @Id
    private UUID id;
    @Column(name = "course_id", nullable = false)
    private UUID courseId;
    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;
    @Column(name = "final_score", nullable = false)
    private BigDecimal finalScore;
    @Column(length = 5)
    private String letter;
    @Column(nullable = false)
    private boolean passed;
    @Column(nullable = false, length = 40)
    private String status = "FINALIZED";
    @Column(name = "finalized_by", nullable = false, length = 64)
    private String finalizedBy;
    @Column(name = "finalized_at", nullable = false)
    private Instant finalizedAt = Instant.now();
    @Version
    @Column(nullable = false)
    private long version;

    protected FinalGrade() {
    }

    public FinalGrade(UUID id, UUID courseId, String studentId) {
        this.id = id;
        this.courseId = courseId;
        this.studentId = studentId;
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public String getStudentId() { return studentId; }
    public BigDecimal getFinalScore() { return finalScore; }
    public String getLetter() { return letter; }
    public boolean isPassed() { return passed; }
    public String getStatus() { return status; }
    public String getFinalizedBy() { return finalizedBy; }
    public Instant getFinalizedAt() { return finalizedAt; }

    public void finalizeAs(BigDecimal finalScore, String letter, boolean passed, String finalizedBy) {
        this.finalScore = finalScore;
        this.letter = letter;
        this.passed = passed;
        this.status = "FINALIZED";
        this.finalizedBy = finalizedBy;
        this.finalizedAt = Instant.now();
    }
}

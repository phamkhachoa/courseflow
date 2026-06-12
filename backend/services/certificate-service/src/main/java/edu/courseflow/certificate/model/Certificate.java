package edu.courseflow.certificate.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "certificates")
public class Certificate {

    @Id
    private UUID id;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "final_grade", nullable = false)
    private BigDecimal finalGrade;

    @Column(name = "issued_at", nullable = false)
    private Instant issuedAt = Instant.now();

    @Column(name = "expires_at")
    private Instant expiresAt;

    @Column(nullable = false, length = 40)
    private String status = "ISSUED";

    @Version
    @Column(nullable = false)
    private long version;

    protected Certificate() {
    }

    public Certificate(UUID id, String studentId, UUID courseId, BigDecimal finalGrade) {
        this.id = id;
        this.studentId = studentId;
        this.courseId = courseId;
        this.finalGrade = finalGrade;
        this.status = "ISSUED";
        this.issuedAt = Instant.now();
    }

    public UUID getId() { return id; }
    public String getStudentId() { return studentId; }
    public UUID getCourseId() { return courseId; }
    public BigDecimal getFinalGrade() { return finalGrade; }
    public Instant getIssuedAt() { return issuedAt; }
    public String getStatus() { return status; }

    public void revoke() {
        this.status = "REVOKED";
    }
}

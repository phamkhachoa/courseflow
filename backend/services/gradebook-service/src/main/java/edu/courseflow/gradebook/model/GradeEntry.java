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
@Table(name = "grade_entries")
public class GradeEntry {
    @Id
    private UUID id;
    @Column(name = "grade_item_id", nullable = false)
    private UUID gradeItemId;
    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;
    @Column(name = "raw_score", nullable = false)
    private BigDecimal rawScore;
    @Column(name = "adjusted_score")
    private BigDecimal adjustedScore;
    @Column(nullable = false, length = 40)
    private String status = "PUBLISHED";
    @Column(name = "graded_at", nullable = false)
    private Instant gradedAt = Instant.now();
    @Column(name = "is_late", nullable = false)
    private boolean late;
    @Column(name = "minutes_late", nullable = false)
    private int minutesLate;
    @Column(name = "late_penalty_applied", nullable = false)
    private BigDecimal latePenaltyApplied = BigDecimal.ZERO;
    @Column(length = 5)
    private String letter;
    @Column(name = "source_event_id", length = 80)
    private String sourceEventId;
    @Column(name = "source_graded_at")
    private Instant sourceGradedAt;
    @Version
    @Column(nullable = false)
    private long version;

    protected GradeEntry() {
    }

    public GradeEntry(UUID id, UUID gradeItemId, String studentId) {
        this.id = id;
        this.gradeItemId = gradeItemId;
        this.studentId = studentId;
    }

    public UUID getId() { return id; }
    public UUID getGradeItemId() { return gradeItemId; }
    public String getStudentId() { return studentId; }
    public BigDecimal getRawScore() { return rawScore; }
    public BigDecimal getAdjustedScore() { return adjustedScore; }
    public String getStatus() { return status; }
    public Instant getGradedAt() { return gradedAt; }
    public boolean isLate() { return late; }
    public int getMinutesLate() { return minutesLate; }
    public BigDecimal getLatePenaltyApplied() { return latePenaltyApplied; }
    public Instant getSourceGradedAt() { return sourceGradedAt; }
    public String getSourceEventId() { return sourceEventId; }

    public void publish(BigDecimal rawScore, BigDecimal adjustedScore,
            boolean late, int minutesLate, BigDecimal latePenaltyApplied) {
        this.rawScore = rawScore;
        this.adjustedScore = adjustedScore;
        this.status = "PUBLISHED";
        this.gradedAt = Instant.now();
        this.late = late;
        this.minutesLate = minutesLate;
        this.latePenaltyApplied = latePenaltyApplied == null ? BigDecimal.ZERO : latePenaltyApplied;
    }

    public boolean publishFromSource(BigDecimal rawScore, BigDecimal adjustedScore,
            boolean late, int minutesLate, BigDecimal latePenaltyApplied,
            UUID eventId, Instant eventGradedAt) {
        Instant effectiveGradedAt = eventGradedAt == null ? Instant.now() : eventGradedAt;
        if (sourceGradedAt != null && effectiveGradedAt.isBefore(sourceGradedAt)) {
            return false;
        }
        publish(rawScore, adjustedScore, late, minutesLate, latePenaltyApplied);
        this.gradedAt = effectiveGradedAt;
        this.sourceGradedAt = effectiveGradedAt;
        this.sourceEventId = eventId == null ? null : eventId.toString();
        return true;
    }
}

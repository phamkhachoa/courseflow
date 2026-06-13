package edu.courseflow.gradebook.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "grade_overrides")
public class GradeOverride {

    @Id
    private UUID id;

    @Column(name = "grade_entry_id", nullable = false)
    private UUID gradeEntryId;

    @Column(name = "old_score", nullable = false)
    private BigDecimal oldScore;

    @Column(name = "new_score", nullable = false)
    private BigDecimal newScore;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String reason;

    @Column(name = "actor_id", nullable = false, length = 64)
    private String actorId;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected GradeOverride() {
    }

    public GradeOverride(UUID gradeEntryId, BigDecimal oldScore, BigDecimal newScore, String reason, String actorId) {
        this.id = UUID.randomUUID();
        this.gradeEntryId = gradeEntryId;
        this.oldScore = oldScore;
        this.newScore = newScore;
        this.reason = reason;
        this.actorId = actorId;
        this.createdAt = Instant.now();
    }

    public UUID getId() { return id; }
    public UUID getGradeEntryId() { return gradeEntryId; }
    public BigDecimal getOldScore() { return oldScore; }
    public BigDecimal getNewScore() { return newScore; }
    public String getReason() { return reason; }
    public String getActorId() { return actorId; }
    public Instant getCreatedAt() { return createdAt; }
}

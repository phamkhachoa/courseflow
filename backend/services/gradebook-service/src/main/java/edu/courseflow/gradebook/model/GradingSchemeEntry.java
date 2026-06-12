package edu.courseflow.gradebook.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "grading_scheme_entries")
public class GradingSchemeEntry {
    @Id
    private UUID id;
    @Column(name = "scheme_id", nullable = false)
    private UUID schemeId;
    @Column(nullable = false, length = 5)
    private String letter;
    @Column(name = "min_percent", nullable = false)
    private BigDecimal minPercent;
    @Column(name = "gpa_points")
    private BigDecimal gpaPoints;
    @Column(nullable = false)
    private int position;

    protected GradingSchemeEntry() {
    }

    public GradingSchemeEntry(UUID schemeId, String letter, BigDecimal minPercent, BigDecimal gpaPoints, int position) {
        this.id = UUID.randomUUID();
        this.schemeId = schemeId;
        this.letter = letter;
        this.minPercent = minPercent;
        this.gpaPoints = gpaPoints;
        this.position = position;
    }

    public UUID getId() { return id; }
    public String getLetter() { return letter; }
    public BigDecimal getMinPercent() { return minPercent; }
    public BigDecimal getGpaPoints() { return gpaPoints; }
}

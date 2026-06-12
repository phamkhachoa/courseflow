package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "org_dashboard_metrics")
public class OrgDashboardMetric {

    @Id
    @Column(name = "org_id", length = 64)
    private String orgId;

    @Column(name = "active_learners", nullable = false)
    private int activeLearners;

    @Column(name = "total_enrollments", nullable = false)
    private int totalEnrollments;

    @Column(name = "avg_completion_rate", nullable = false)
    private BigDecimal avgCompletionRate = BigDecimal.ZERO;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected OrgDashboardMetric() {
    }

    public String getOrgId() { return orgId; }
    public int getActiveLearners() { return activeLearners; }
    public int getTotalEnrollments() { return totalEnrollments; }
    public BigDecimal getAvgCompletionRate() { return avgCompletionRate; }
    public Instant getUpdatedAt() { return updatedAt; }
}

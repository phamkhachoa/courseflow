package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "marketing_funnel_metrics")
public class MarketingFunnelMetric {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false, length = 80)
    private String tenantId;

    @Column(name = "application_id", nullable = false, length = 80)
    private String applicationId;

    @Column(name = "campaign_code", length = 120)
    private String campaignCode;

    @Column(length = 120)
    private String source;

    @Column(nullable = false, length = 80)
    private String stage;

    @Column(name = "bucket_date", nullable = false)
    private LocalDate bucketDate;

    @Column(name = "event_count", nullable = false)
    private long eventCount;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected MarketingFunnelMetric() {
    }

    public MarketingFunnelMetric(String tenantId,
                                 String applicationId,
                                 String campaignCode,
                                 String source,
                                 String stage,
                                 LocalDate bucketDate,
                                 long eventCount) {
        this.id = UUID.randomUUID();
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.campaignCode = campaignCode;
        this.source = source;
        this.stage = stage;
        this.bucketDate = bucketDate;
        this.eventCount = eventCount;
    }

    public UUID getId() { return id; }
    public String getTenantId() { return tenantId; }
    public String getApplicationId() { return applicationId; }
    public String getCampaignCode() { return campaignCode; }
    public String getSource() { return source; }
    public String getStage() { return stage; }
    public LocalDate getBucketDate() { return bucketDate; }
    public long getEventCount() { return eventCount; }
    public Instant getUpdatedAt() { return updatedAt; }
}

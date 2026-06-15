package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "marketing_funnel_event_receipts")
public class MarketingFunnelEventReceipt {

    @Id
    private UUID id;

    @Column(name = "source_event_id", nullable = false)
    private UUID sourceEventId;

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

    @Column(name = "request_hash", nullable = false, length = 96)
    private String requestHash;

    @Column(name = "actor_id", length = 120)
    private String actorId;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected MarketingFunnelEventReceipt() {
    }

    public MarketingFunnelEventReceipt(UUID sourceEventId,
                                       String tenantId,
                                       String applicationId,
                                       String campaignCode,
                                       String source,
                                       String stage,
                                       LocalDate bucketDate,
                                       long eventCount,
                                       String requestHash,
                                       String actorId) {
        this.id = UUID.randomUUID();
        this.sourceEventId = sourceEventId;
        this.tenantId = tenantId;
        this.applicationId = applicationId;
        this.campaignCode = campaignCode;
        this.source = source;
        this.stage = stage;
        this.bucketDate = bucketDate;
        this.eventCount = eventCount;
        this.requestHash = requestHash;
        this.actorId = actorId;
    }

    public UUID getSourceEventId() { return sourceEventId; }
    public String getRequestHash() { return requestHash; }
}

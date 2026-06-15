package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.MarketingFunnelMetric;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface MarketingFunnelMetricRepository extends JpaRepository<MarketingFunnelMetric, UUID> {

    @Query("""
            select metric
            from MarketingFunnelMetric metric
            where metric.tenantId = :tenantId
              and metric.applicationId = :applicationId
              and (:campaignCode is null or metric.campaignCode = :campaignCode)
              and (:source is null or metric.source = :source)
              and (:fromDate is null or metric.bucketDate >= :fromDate)
              and (:toDate is null or metric.bucketDate <= :toDate)
            order by metric.bucketDate asc, metric.stage asc
            """)
    List<MarketingFunnelMetric> queryFunnel(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("campaignCode") String campaignCode,
            @Param("source") String source,
            @Param("fromDate") LocalDate fromDate,
            @Param("toDate") LocalDate toDate,
            Pageable pageable);

    @Query("""
            select metric
            from MarketingFunnelMetric metric
            where metric.tenantId = :tenantId
              and metric.applicationId = :applicationId
              and (:campaignCode is null or metric.campaignCode = :campaignCode)
              and (:source is null or metric.source = :source)
              and (:fromDate is null or metric.bucketDate >= :fromDate)
              and (:toDate is null or metric.bucketDate <= :toDate)
            order by metric.bucketDate asc, coalesce(metric.campaignCode, '') asc, coalesce(metric.source, '') asc,
                     metric.stage asc, metric.id asc
            """)
    List<MarketingFunnelMetric> exportFunnel(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("campaignCode") String campaignCode,
            @Param("source") String source,
            @Param("fromDate") LocalDate fromDate,
            @Param("toDate") LocalDate toDate,
            Pageable pageable);

    @Modifying
    @Query(value = """
            insert into marketing_funnel_metrics (
                id,
                tenant_id,
                application_id,
                campaign_code,
                source,
                stage,
                bucket_date,
                event_count,
                updated_at
            )
            values (
                :id,
                :tenantId,
                :applicationId,
                :campaignCode,
                :source,
                :stage,
                :bucketDate,
                :eventCount,
                now()
            )
            on conflict (
                tenant_id,
                application_id,
                COALESCE(campaign_code, ''),
                COALESCE(source, ''),
                stage,
                bucket_date
            )
            do update set
                event_count = marketing_funnel_metrics.event_count + excluded.event_count,
                updated_at = now()
            """, nativeQuery = true)
    int incrementMetric(
            @Param("id") UUID id,
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("campaignCode") String campaignCode,
            @Param("source") String source,
            @Param("stage") String stage,
            @Param("bucketDate") LocalDate bucketDate,
            @Param("eventCount") long eventCount);
}

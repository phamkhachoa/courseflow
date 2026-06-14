package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveCampaignVersion;
import jakarta.persistence.LockModeType;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface IncentiveCampaignVersionRepository extends JpaRepository<IncentiveCampaignVersion, UUID> {

    @Query("""
            select v from IncentiveCampaignVersion v
            where v.tenantId = :tenantId
              and v.applicationId = :applicationId
              and v.versionStatus = 'PUBLISHED'
              and v.activeSnapshot = true
              and (v.startsAt is null or v.startsAt <= :now)
              and (v.endsAt is null or v.endsAt >= :now)
            order by v.priority desc, v.createdAt asc
            """)
    List<IncentiveCampaignVersion> findActivePublished(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("now") Instant now);

    @Query("""
            select v from IncentiveCampaignVersion v
            where v.campaignId = :campaignId
            order by v.versionNumber desc
            """)
    List<IncentiveCampaignVersion> findByCampaignIdOrderByVersionNumberDesc(
            @Param("campaignId") UUID campaignId);

    Optional<IncentiveCampaignVersion> findByCampaignIdAndVersionNumber(UUID campaignId, int versionNumber);

    Optional<IncentiveCampaignVersion> findFirstByCampaignIdAndActiveSnapshotTrue(UUID campaignId);

    @Query("""
            select v from IncentiveCampaignVersion v
            where (:tenantId is null or v.tenantId = :tenantId)
              and (:applicationId is null or v.applicationId = :applicationId)
              and (:status is null or v.versionStatus = :status)
              and (:status is not null or v.versionStatus = 'SUBMITTED')
            order by v.submittedAt asc nulls last, v.createdAt asc
            """)
    List<IncentiveCampaignVersion> reviewQueue(
            @Param("tenantId") String tenantId,
            @Param("applicationId") String applicationId,
            @Param("status") String status,
            org.springframework.data.domain.Pageable pageable);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select v from IncentiveCampaignVersion v
            where v.campaignId = :campaignId and v.versionNumber = :versionNumber
            """)
    Optional<IncentiveCampaignVersion> lockByCampaignIdAndVersionNumber(
            @Param("campaignId") UUID campaignId,
            @Param("versionNumber") int versionNumber);

    @Modifying
    @Query("""
            update IncentiveCampaignVersion v
            set v.activeSnapshot = false,
                v.versionStatus = case when v.versionStatus = 'PUBLISHED' then 'SUPERSEDED' else v.versionStatus end
            where v.campaignId = :campaignId
              and v.activeSnapshot = true
            """)
    int deactivateActiveSnapshots(@Param("campaignId") UUID campaignId);

    @Modifying
    @Query("""
            update IncentiveCampaignVersion v
            set v.activeSnapshot = false
            where v.campaignId = :campaignId
              and v.activeSnapshot = true
            """)
    int deactivateActiveSnapshotOnly(@Param("campaignId") UUID campaignId);
}

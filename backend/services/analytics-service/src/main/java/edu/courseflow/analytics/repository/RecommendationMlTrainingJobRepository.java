package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.RecommendationMlTrainingJob;
import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface RecommendationMlTrainingJobRepository extends JpaRepository<RecommendationMlTrainingJob, UUID> {

    @Query("""
            select job.trainingRunId
            from RecommendationMlTrainingJob job
            where job.materializedAt is null
              and job.status in :statuses
              and (job.lastCheckedAt is null or job.lastCheckedAt <= :eligibleBefore)
            order by job.submittedAt asc
            """)
    List<UUID> findPendingTrainingRunIds(@Param("statuses") Collection<String> statuses,
                                         @Param("eligibleBefore") Instant eligibleBefore,
                                         Pageable pageable);

    @Query("""
            select job.trainingRunId
            from RecommendationMlTrainingJob job
            where job.materializedAt is null
              and job.status in :statuses
              and (
                  (
                      job.materializationLockedAt is null
                      and (job.lastCheckedAt is null or job.lastCheckedAt <= :eligibleBefore)
                  )
                  or job.materializationLockedAt <= :staleLockBefore
              )
            order by job.submittedAt asc
            """)
    List<UUID> findClaimableTrainingRunIds(@Param("statuses") Collection<String> statuses,
                                           @Param("eligibleBefore") Instant eligibleBefore,
                                           @Param("staleLockBefore") Instant staleLockBefore,
                                           Pageable pageable);

    @Modifying(clearAutomatically = true, flushAutomatically = true)
    @Query("""
            update RecommendationMlTrainingJob job
               set job.materializationLockedBy = :workerId,
                   job.materializationLockedAt = :lockedAt,
                   job.materializationAttemptCount = job.materializationAttemptCount + 1,
                   job.updatedAt = :lockedAt
             where job.trainingRunId = :trainingRunId
               and job.materializedAt is null
               and job.status in :statuses
               and (
                   (
                       job.materializationLockedAt is null
                       and (job.lastCheckedAt is null or job.lastCheckedAt <= :eligibleBefore)
                   )
                   or job.materializationLockedAt <= :staleLockBefore
               )
            """)
    int claimTrainingRunForMaterialization(@Param("trainingRunId") UUID trainingRunId,
                                           @Param("statuses") Collection<String> statuses,
                                           @Param("workerId") String workerId,
                                           @Param("lockedAt") Instant lockedAt,
                                           @Param("eligibleBefore") Instant eligibleBefore,
                                           @Param("staleLockBefore") Instant staleLockBefore);
}

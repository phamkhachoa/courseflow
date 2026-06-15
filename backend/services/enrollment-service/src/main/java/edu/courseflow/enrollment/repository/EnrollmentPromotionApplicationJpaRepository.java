package edu.courseflow.enrollment.repository;

import edu.courseflow.enrollment.model.EnrollmentPromotionApplication;
import jakarta.persistence.LockModeType;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface EnrollmentPromotionApplicationJpaRepository
        extends JpaRepository<EnrollmentPromotionApplication, UUID> {

    Optional<EnrollmentPromotionApplication> findByEnrollmentId(UUID enrollmentId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select a from EnrollmentPromotionApplication a
            where a.id = :id
            """)
    Optional<EnrollmentPromotionApplication> findByIdForUpdate(@Param("id") UUID id);

    @Query("""
            select a from EnrollmentPromotionApplication a
            where ((:status is null and a.status in ('COMMIT_FAILED', 'MANUAL_REVIEW', 'RESERVED'))
                   or (:status is not null and a.status = :status))
              and (:courseId is null or a.courseId = :courseId)
              and (:studentId is null or a.studentId = :studentId)
            order by a.updatedAt asc
            """)
    List<EnrollmentPromotionApplication> findOperationsQueue(
            @Param("status") String status,
            @Param("courseId") UUID courseId,
            @Param("studentId") String studentId,
            Pageable pageable);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select a from EnrollmentPromotionApplication a
            where a.status = :status and a.reservationId is not null
              and (a.nextRetryAt is null or a.nextRetryAt <= :now)
            order by case when a.nextRetryAt is null then 0 else 1 end, a.nextRetryAt asc, a.updatedAt asc
            """)
    List<EnrollmentPromotionApplication> lockRetryableByStatus(
            @Param("status") String status,
            @Param("now") Instant now,
            Pageable pageable);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select a from EnrollmentPromotionApplication a
            where a.status = 'RESERVED'
              and a.updatedAt <= :cutoff
            order by a.updatedAt asc
            """)
    List<EnrollmentPromotionApplication> lockReservedOlderThan(
            @Param("cutoff") Instant cutoff,
            Pageable pageable);
}

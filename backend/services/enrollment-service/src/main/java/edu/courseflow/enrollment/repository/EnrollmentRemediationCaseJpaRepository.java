package edu.courseflow.enrollment.repository;

import edu.courseflow.enrollment.model.EnrollmentRemediationCase;
import jakarta.persistence.LockModeType;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface EnrollmentRemediationCaseJpaRepository
        extends JpaRepository<EnrollmentRemediationCase, UUID> {

    Optional<EnrollmentRemediationCase> findFirstByPromotionApplicationIdAndStatusInOrderByCreatedAtDesc(
            UUID promotionApplicationId,
            Collection<String> statuses);

    Optional<EnrollmentRemediationCase> findFirstByOrderIdAndStatusInOrderByCreatedAtDesc(
            UUID orderId,
            Collection<String> statuses);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select c from EnrollmentRemediationCase c
            where c.id = :id
            """)
    Optional<EnrollmentRemediationCase> findByIdForUpdate(@Param("id") UUID id);

    @Query("""
            select c from EnrollmentRemediationCase c
            where ((:status is null and c.status in ('OPEN', 'IN_PROGRESS'))
                   or (:status is not null and c.status = :status))
              and (:courseId is null or c.courseId = :courseId)
              and (:enrollmentId is null or c.enrollmentId = :enrollmentId)
              and (:promotionApplicationId is null or c.promotionApplicationId = :promotionApplicationId)
              and (:orderId is null or c.orderId = :orderId)
              and (:studentId is null or c.studentId = :studentId)
              and (:couponId is null or exists (
                    select 1 from EnrollmentPromotionApplication p
                    where p.id = c.promotionApplicationId
                      and p.couponId = :couponId
                  ))
              and (:redemptionId is null or exists (
                    select 1 from EnrollmentPromotionApplication p
                    where p.id = c.promotionApplicationId
                      and p.redemptionId = :redemptionId
                  ))
              and (:correlationId is null or exists (
                    select 1 from EnrollmentRemediationCaseAction a
                    where a.caseId = c.id
                      and lower(coalesce(function('jsonb_extract_path_text', a.payloadJson, 'correlationId'), ''))
                          like concat('%', lower(:correlationId), '%')
                  ))
              and (:assigneeId is null or c.assigneeId = :assigneeId)
            order by c.slaDueAt asc, c.createdAt asc
            """)
    List<EnrollmentRemediationCase> findOperationsQueue(
            @Param("status") String status,
            @Param("courseId") UUID courseId,
            @Param("enrollmentId") UUID enrollmentId,
            @Param("promotionApplicationId") UUID promotionApplicationId,
            @Param("orderId") UUID orderId,
            @Param("studentId") String studentId,
            @Param("couponId") UUID couponId,
            @Param("redemptionId") UUID redemptionId,
            @Param("correlationId") String correlationId,
            @Param("assigneeId") String assigneeId,
            Pageable pageable);
}

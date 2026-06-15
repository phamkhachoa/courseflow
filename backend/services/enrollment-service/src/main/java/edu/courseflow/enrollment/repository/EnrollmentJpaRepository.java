package edu.courseflow.enrollment.repository;

import edu.courseflow.enrollment.model.Enrollment;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface EnrollmentJpaRepository extends JpaRepository<Enrollment, UUID> {

    List<Enrollment> findByCourseIdOrderByEnrolledAtDesc(UUID courseId);

    List<Enrollment> findByStudentIdOrderByEnrolledAtDesc(String studentId);

    List<Enrollment> findByCourseIdAndStudentIdOrderByEnrolledAtDesc(UUID courseId, String studentId);

    List<Enrollment> findByCourseIdAndStatusOrderByEnrolledAtDesc(UUID courseId, String status);

    List<Enrollment> findByCourseIdAndSectionIdAndStatusOrderByEnrolledAtDesc(
            UUID courseId, UUID sectionId, String status);

    Optional<Enrollment> findByStudentIdAndCourseId(String studentId, UUID courseId);

    Optional<Enrollment> findFirstByStudentIdAndCourseIdAndStatusIn(
            String studentId, UUID courseId, Collection<String> statuses);

    int countByCourseIdAndStatus(UUID courseId, String status);

    int countByCourseIdAndStatusIn(UUID courseId, Collection<String> statuses);

    int countByCourseId(UUID courseId);

    @Query("""
            select e.id as enrollmentId,
                   e.studentId as studentId,
                   e.courseId as courseId,
                   e.status as enrollmentStatus,
                   e.enrolledAt as enrolledAt,
                   e.droppedAt as droppedAt,
                   e.dropReason as dropReason,
                   o.id as orderId,
                   o.status as orderStatus,
                   o.amount as orderAmount,
                   o.currency as orderCurrency,
                   o.paidAt as paidAt,
                   o.createdAt as orderCreatedAt,
                   o.updatedAt as orderUpdatedAt,
                   p.id as promotionApplicationId,
                   p.status as promotionStatus,
                   p.reservationId as reservationId,
                   p.redemptionId as redemptionId,
                   p.retryCount as promotionRetryCount,
                   p.nextRetryAt as promotionNextRetryAt,
                   p.lastRetryError as promotionLastRetryError,
                   p.updatedAt as promotionUpdatedAt
            from Enrollment e
            left join EnrollmentOrder o on o.enrollmentId = e.id
            left join EnrollmentPromotionApplication p on p.enrollmentId = e.id
            where (:enrollmentId is null or e.id = :enrollmentId)
              and (:courseId is null or e.courseId = :courseId)
              and (:studentId is null or e.studentId = :studentId)
            order by e.enrolledAt desc
            """)
    List<EnrollmentBenefitReconciliationRow> benefitReconciliationRows(
            @Param("enrollmentId") UUID enrollmentId,
            @Param("courseId") UUID courseId,
            @Param("studentId") String studentId,
            Pageable pageable);

    interface EnrollmentBenefitReconciliationRow {
        UUID getEnrollmentId();
        String getStudentId();
        UUID getCourseId();
        String getEnrollmentStatus();
        Instant getEnrolledAt();
        Instant getDroppedAt();
        String getDropReason();
        UUID getOrderId();
        String getOrderStatus();
        BigDecimal getOrderAmount();
        String getOrderCurrency();
        Instant getPaidAt();
        Instant getOrderCreatedAt();
        Instant getOrderUpdatedAt();
        UUID getPromotionApplicationId();
        String getPromotionStatus();
        UUID getReservationId();
        UUID getRedemptionId();
        Integer getPromotionRetryCount();
        Instant getPromotionNextRetryAt();
        String getPromotionLastRetryError();
        Instant getPromotionUpdatedAt();
    }
}

package edu.courseflow.enrollment.repository;

import edu.courseflow.enrollment.model.EnrollmentOrder;
import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface EnrollmentOrderJpaRepository extends JpaRepository<EnrollmentOrder, UUID> {

    Optional<EnrollmentOrder> findByEnrollmentId(UUID enrollmentId);

    Optional<EnrollmentOrder> findByCheckoutAttemptId(UUID checkoutAttemptId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select o from EnrollmentOrder o
            where lower(o.paymentProvider) = lower(:paymentProvider)
              and o.paymentReference = :paymentReference
            order by o.createdAt asc
            """)
    List<EnrollmentOrder> findByPaymentReferenceForUpdate(
            @Param("paymentProvider") String paymentProvider,
            @Param("paymentReference") String paymentReference);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select o from EnrollmentOrder o
            where o.id = :id
            """)
    Optional<EnrollmentOrder> findByIdForUpdate(@Param("id") UUID id);
}

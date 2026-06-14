package edu.courseflow.enrollment.repository;

import edu.courseflow.enrollment.model.EnrollmentCheckoutAttempt;
import jakarta.persistence.LockModeType;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface EnrollmentCheckoutAttemptJpaRepository
        extends JpaRepository<EnrollmentCheckoutAttempt, UUID> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select a from EnrollmentCheckoutAttempt a where a.idempotencyKey = :idempotencyKey")
    Optional<EnrollmentCheckoutAttempt> lockByIdempotencyKey(@Param("idempotencyKey") String idempotencyKey);

    Optional<EnrollmentCheckoutAttempt> findByEnrollmentId(UUID enrollmentId);
}

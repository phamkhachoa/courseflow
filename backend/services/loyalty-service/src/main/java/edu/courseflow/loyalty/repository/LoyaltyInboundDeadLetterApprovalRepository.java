package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyInboundDeadLetterApproval;
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

public interface LoyaltyInboundDeadLetterApprovalRepository
        extends JpaRepository<LoyaltyInboundDeadLetterApproval, UUID> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select approval
            from LoyaltyInboundDeadLetterApproval approval
            where approval.id = :id
            """)
    Optional<LoyaltyInboundDeadLetterApproval> findByIdForUpdate(@Param("id") UUID id);

    @Query("""
            select approval
            from LoyaltyInboundDeadLetterApproval approval
            where approval.deadLetterId = :deadLetterId
              and (:status is null or approval.status = :status)
            order by approval.requestedAt desc, approval.id desc
            """)
    List<LoyaltyInboundDeadLetterApproval> search(
            @Param("deadLetterId") UUID deadLetterId,
            @Param("status") String status,
            Pageable pageable);

    Optional<LoyaltyInboundDeadLetterApproval>
    findFirstByDeadLetterIdAndActionAndRequestHashAndStatusInOrderByRequestedAtDesc(
            UUID deadLetterId,
            String action,
            String requestHash,
            Collection<String> statuses);
}

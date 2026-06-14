package edu.courseflow.loyalty.repository;

import edu.courseflow.loyalty.model.LoyaltyPointLot;
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

public interface LoyaltyPointLotRepository extends JpaRepository<LoyaltyPointLot, UUID> {

    Optional<LoyaltyPointLot> findBySourceEntryId(UUID sourceEntryId);

    List<LoyaltyPointLot> findByAccountIdOrderByExpiresAtAscOccurredAtAsc(UUID accountId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select lot from LoyaltyPointLot lot
            where lot.accountId = :accountId
            order by lot.occurredAt asc, lot.createdAt asc
            """)
    List<LoyaltyPointLot> findByAccountIdForUpdate(@Param("accountId") UUID accountId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select lot from LoyaltyPointLot lot
            where lot.accountId = :accountId
              and lot.remainingPoints > 0
            """)
    List<LoyaltyPointLot> remainingLotsForUpdate(@Param("accountId") UUID accountId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select lot from LoyaltyPointLot lot
            where lot.accountId = :accountId
              and lot.remainingPoints > 0
              and (lot.expiresAt is null or lot.expiresAt > :asOf)
            order by lot.expiresAt asc, lot.occurredAt asc, lot.createdAt asc
            """)
    List<LoyaltyPointLot> activeRemainingLotsForUpdate(
            @Param("accountId") UUID accountId,
            @Param("asOf") Instant asOf);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select lot from LoyaltyPointLot lot
            where lot.id in :ids
            """)
    List<LoyaltyPointLot> findByIdsForUpdate(@Param("ids") List<UUID> ids);

    @Query("""
            select coalesce(sum(lot.remainingPoints), 0) from LoyaltyPointLot lot
            where lot.accountId = :accountId
              and lot.remainingPoints > 0
              and (lot.expiresAt is null or lot.expiresAt > :asOf)
            """)
    long activeRemainingPoints(
            @Param("accountId") UUID accountId,
            @Param("asOf") Instant asOf);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
            select lot from LoyaltyPointLot lot
            where lot.programUuid = :programUuid
              and lot.remainingPoints > 0
              and lot.expiresAt is not null
              and lot.expiresAt <= :asOf
            order by lot.expiresAt asc, lot.occurredAt asc, lot.createdAt asc
            """)
    List<LoyaltyPointLot> expiryCandidatesForUpdate(
            @Param("programUuid") UUID programUuid,
            @Param("asOf") Instant asOf,
            Pageable pageable);

    @Query("""
            select lot from LoyaltyPointLot lot
            where lot.programUuid = :programUuid
              and lot.remainingPoints > 0
              and lot.expiresAt is not null
              and lot.expiresAt <= :asOf
            order by lot.expiresAt asc, lot.occurredAt asc, lot.createdAt asc
            """)
    List<LoyaltyPointLot> expiryCandidates(
            @Param("programUuid") UUID programUuid,
            @Param("asOf") Instant asOf,
            Pageable pageable);
}

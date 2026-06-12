package edu.courseflow.identity.repository;

import edu.courseflow.identity.model.RefreshToken;
import java.time.Instant;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface RefreshTokenRepository extends JpaRepository<RefreshToken, Long> {

    Optional<RefreshToken> findByTokenHash(String tokenHash);

    @Modifying
    @Query("""
            update RefreshToken t set t.revoked = true, t.revokedAt = :now, t.revokedReason = :reason
            where t.userId = :userId and t.revoked = false
            """)
    int revokeAllForUser(@Param("userId") Long userId,
            @Param("now") Instant now,
            @Param("reason") String reason);

    @Modifying
    @Query("delete from RefreshToken t where t.expiresAt < :cutoff")
    int deleteExpired(@Param("cutoff") Instant cutoff);
}

package edu.courseflow.identity.repository;

import edu.courseflow.identity.model.EmailVerificationToken;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface EmailVerificationTokenRepository extends JpaRepository<EmailVerificationToken, UUID> {

    Optional<EmailVerificationToken> findByTokenHash(String tokenHash);

    @Modifying
    @Query("""
            update EmailVerificationToken token
               set token.consumedAt = :consumedAt
             where token.userId = :userId
               and token.consumedAt is null
            """)
    int consumeOutstandingForUser(@Param("userId") Long userId, @Param("consumedAt") Instant consumedAt);
}

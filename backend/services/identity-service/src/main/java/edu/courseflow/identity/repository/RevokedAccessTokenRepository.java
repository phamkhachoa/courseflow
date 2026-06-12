package edu.courseflow.identity.repository;

import edu.courseflow.identity.model.RevokedAccessToken;
import java.time.Instant;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface RevokedAccessTokenRepository extends JpaRepository<RevokedAccessToken, String> {

    @Modifying
    @Query("delete from RevokedAccessToken t where t.expiresAt < :cutoff")
    int deleteExpired(@Param("cutoff") Instant cutoff);
}

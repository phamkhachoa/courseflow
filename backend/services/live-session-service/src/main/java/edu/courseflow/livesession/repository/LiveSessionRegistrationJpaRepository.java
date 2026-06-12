package edu.courseflow.livesession.repository;

import edu.courseflow.livesession.model.LiveSessionRegistration;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LiveSessionRegistrationJpaRepository extends JpaRepository<LiveSessionRegistration, UUID> {

    int countBySessionId(UUID sessionId);

    Optional<LiveSessionRegistration> findBySessionIdAndUserId(UUID sessionId, String userId);
}

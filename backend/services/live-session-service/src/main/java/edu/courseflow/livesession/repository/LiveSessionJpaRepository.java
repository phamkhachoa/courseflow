package edu.courseflow.livesession.repository;

import edu.courseflow.livesession.model.LiveSession;
import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface LiveSessionJpaRepository extends JpaRepository<LiveSession, UUID> {

    List<LiveSession> findAllByOrderByScheduledStartAsc();

    List<LiveSession> findByCourseIdOrderByScheduledStartAsc(UUID courseId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select s from LiveSession s where s.id = :sessionId")
    Optional<LiveSession> lockById(@Param("sessionId") UUID sessionId);
}

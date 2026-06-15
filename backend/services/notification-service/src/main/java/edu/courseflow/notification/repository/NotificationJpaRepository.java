package edu.courseflow.notification.repository;

import edu.courseflow.notification.model.Notification;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface NotificationJpaRepository extends JpaRepository<Notification, UUID> {

    List<Notification> findByUserIdOrderByCreatedAtDesc(String userId);

    List<Notification> findByUserIdAndReadAtIsNullOrderByCreatedAtDesc(String userId);

    @Query(value = """
            SELECT *
              FROM notifications
             WHERE (delivery_status = 'FAILED'
                OR (delivery_status = 'DISPATCHING'
                    AND (last_delivery_attempt_at IS NULL
                         OR last_delivery_attempt_at < CURRENT_TIMESTAMP - INTERVAL '5 minutes')))
               AND delivery_attempts < :maxAttempts
             ORDER BY created_at ASC
             LIMIT :limit
             FOR UPDATE SKIP LOCKED
            """, nativeQuery = true)
    List<Notification> lockFailedForRetry(@Param("maxAttempts") int maxAttempts, @Param("limit") int limit);
}

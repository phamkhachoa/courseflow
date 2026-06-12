package edu.courseflow.notification.repository;

import edu.courseflow.notification.model.NotificationPreference;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface NotificationPreferenceJpaRepository extends JpaRepository<NotificationPreference, UUID> {

    List<NotificationPreference> findByUserIdOrderByChannelAsc(String userId);

    Optional<NotificationPreference> findByUserIdAndChannel(String userId, String channel);
}

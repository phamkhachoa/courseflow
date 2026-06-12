package edu.courseflow.media.repository;

import edu.courseflow.media.model.VideoProgress;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface VideoProgressJpaRepository extends JpaRepository<VideoProgress, UUID> {

    Optional<VideoProgress> findByVideoIdAndUserId(UUID videoId, String userId);
}

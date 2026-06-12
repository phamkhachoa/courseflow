package edu.courseflow.media.repository;

import edu.courseflow.media.model.VideoRendition;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface VideoRenditionJpaRepository extends JpaRepository<VideoRendition, UUID> {

    List<VideoRendition> findByVideoIdOrderByBitrateKbpsAsc(UUID videoId);
}

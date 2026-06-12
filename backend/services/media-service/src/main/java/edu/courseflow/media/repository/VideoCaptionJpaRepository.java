package edu.courseflow.media.repository;

import edu.courseflow.media.model.VideoCaption;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface VideoCaptionJpaRepository extends JpaRepository<VideoCaption, UUID> {

    List<VideoCaption> findByVideoIdOrderByLanguageAsc(UUID videoId);
}

package edu.courseflow.media.repository;

import edu.courseflow.media.model.VideoAsset;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface VideoAssetJpaRepository extends JpaRepository<VideoAsset, UUID> {

    List<VideoAsset> findAllByOrderByCreatedAtDesc();

    List<VideoAsset> findByCourseIdOrderByCreatedAtDesc(UUID courseId);
}

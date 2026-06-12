package edu.courseflow.media.repository;

import edu.courseflow.media.model.MediaAsset;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MediaAssetJpaRepository extends JpaRepository<MediaAsset, UUID> {

    List<MediaAsset> findAllByOrderByCreatedAtDesc();

    List<MediaAsset> findByOwnerIdOrderByCreatedAtDesc(String ownerId);
}

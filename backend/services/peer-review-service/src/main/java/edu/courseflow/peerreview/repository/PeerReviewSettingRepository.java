package edu.courseflow.peerreview.repository;

import edu.courseflow.peerreview.model.PeerReviewSetting;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PeerReviewSettingRepository extends JpaRepository<PeerReviewSetting, UUID> {

    Optional<PeerReviewSetting> findByAssignmentId(UUID assignmentId);
}

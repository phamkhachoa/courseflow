package edu.courseflow.peerreview.repository;

import edu.courseflow.peerreview.model.PeerReviewResult;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PeerReviewResultRepository extends JpaRepository<PeerReviewResult, UUID> {

    Optional<PeerReviewResult> findBySubmissionId(UUID submissionId);
}

package edu.courseflow.peerreview.repository;

import edu.courseflow.peerreview.model.ReviewSubmission;
import java.util.Collection;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ReviewSubmissionRepository extends JpaRepository<ReviewSubmission, UUID> {

    boolean existsByReviewAssignmentId(UUID reviewAssignmentId);

    List<ReviewSubmission> findByReviewAssignmentIdIn(Collection<UUID> reviewAssignmentIds);
}

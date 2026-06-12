package edu.courseflow.peerreview.repository;

import edu.courseflow.peerreview.model.ReviewAssignment;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ReviewAssignmentRepository extends JpaRepository<ReviewAssignment, UUID> {

    Optional<ReviewAssignment> findFirstBySubmissionId(UUID submissionId);

    List<ReviewAssignment> findBySubmissionId(UUID submissionId);

    List<ReviewAssignment> findByReviewerIdOrderByAssignedAtDesc(String reviewerId);
}

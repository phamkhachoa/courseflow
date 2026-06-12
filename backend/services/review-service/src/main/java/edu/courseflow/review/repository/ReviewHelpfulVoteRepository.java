package edu.courseflow.review.repository;

import edu.courseflow.review.model.ReviewHelpfulVote;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ReviewHelpfulVoteRepository extends JpaRepository<ReviewHelpfulVote, UUID> {

    Optional<ReviewHelpfulVote> findByReviewIdAndUserId(UUID reviewId, String userId);
}

package edu.courseflow.discussion.repository;

import edu.courseflow.discussion.model.DiscussionComment;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DiscussionCommentJpaRepository extends JpaRepository<DiscussionComment, UUID> {

    List<DiscussionComment> findByThreadIdOrderByCreatedAtAsc(UUID threadId);
}

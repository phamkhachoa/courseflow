package edu.courseflow.assignment.repository;

import edu.courseflow.assignment.model.SubmissionAttachment;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SubmissionAttachmentJpaRepository extends JpaRepository<SubmissionAttachment, UUID> {

    List<SubmissionAttachment> findBySubmissionIdOrderByCreatedAtAscFileNameAsc(UUID submissionId);
}

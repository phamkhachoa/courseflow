package edu.courseflow.assignment.repository;

import edu.courseflow.assignment.model.AttachmentUploadGrant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AttachmentUploadGrantJpaRepository extends JpaRepository<AttachmentUploadGrant, UUID> {

    Optional<AttachmentUploadGrant> findByAssignmentIdAndStudentIdAndStorageKey(
            UUID assignmentId, String studentId, String storageKey);
}

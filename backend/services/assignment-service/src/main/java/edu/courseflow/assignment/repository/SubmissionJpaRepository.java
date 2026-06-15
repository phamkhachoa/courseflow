package edu.courseflow.assignment.repository;

import edu.courseflow.assignment.model.Submission;
import java.util.Collection;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface SubmissionJpaRepository extends JpaRepository<Submission, UUID> {

    List<Submission> findByAssignmentIdAndStudentIdOrderByAttemptNoAsc(UUID assignmentId, String studentId);

    List<Submission> findByAssignmentIdInAndStudentIdOrderBySubmittedAtDesc(Collection<UUID> assignmentIds,
            String studentId);

    List<Submission> findByAssignmentIdInOrderBySubmittedAtAsc(Collection<UUID> assignmentIds, Pageable pageable);

    List<Submission> findByAssignmentIdInAndStatusInOrderBySubmittedAtAsc(Collection<UUID> assignmentIds,
            Collection<String> statuses, Pageable pageable);

    @Query("""
            select coalesce(max(s.attemptNo), 0) + 1
            from Submission s
            where s.assignmentId = :assignmentId and s.studentId = :studentId
            """)
    int nextAttemptNo(@Param("assignmentId") UUID assignmentId, @Param("studentId") String studentId);
}

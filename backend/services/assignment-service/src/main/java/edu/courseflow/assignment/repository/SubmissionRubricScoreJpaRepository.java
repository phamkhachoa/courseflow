package edu.courseflow.assignment.repository;

import edu.courseflow.assignment.model.SubmissionRubricScore;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface SubmissionRubricScoreJpaRepository extends JpaRepository<SubmissionRubricScore, UUID> {

    @Modifying
    @Query("delete from SubmissionRubricScore s where s.submissionId = :submissionId")
    int deleteBySubmissionId(@Param("submissionId") UUID submissionId);
}

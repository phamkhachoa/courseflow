package edu.courseflow.enrollment.repository;

import edu.courseflow.enrollment.model.EnrollmentRemediationCaseAction;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface EnrollmentRemediationCaseActionJpaRepository
        extends JpaRepository<EnrollmentRemediationCaseAction, UUID> {

    List<EnrollmentRemediationCaseAction> findByCaseIdOrderByCreatedAtAsc(UUID caseId);
}

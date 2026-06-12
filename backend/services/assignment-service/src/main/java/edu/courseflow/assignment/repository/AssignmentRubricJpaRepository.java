package edu.courseflow.assignment.repository;

import edu.courseflow.assignment.model.AssignmentRubric;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AssignmentRubricJpaRepository extends JpaRepository<AssignmentRubric, UUID> {

    Optional<AssignmentRubric> findByAssignmentId(UUID assignmentId);
}

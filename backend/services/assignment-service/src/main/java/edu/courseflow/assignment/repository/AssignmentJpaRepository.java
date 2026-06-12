package edu.courseflow.assignment.repository;

import edu.courseflow.assignment.model.Assignment;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AssignmentJpaRepository extends JpaRepository<Assignment, UUID> {

    List<Assignment> findByCourseIdOrderByDueAtAscTitleAsc(UUID courseId);
}

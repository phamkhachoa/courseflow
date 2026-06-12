package edu.courseflow.assignment.repository;

import edu.courseflow.assignment.model.AssignmentRubricCriterion;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AssignmentRubricCriterionJpaRepository extends JpaRepository<AssignmentRubricCriterion, UUID> {

    List<AssignmentRubricCriterion> findByRubricIdOrderByPositionAsc(UUID rubricId);

    @Modifying
    @Query("delete from AssignmentRubricCriterion c where c.rubricId = :rubricId")
    int deleteByRubricId(@Param("rubricId") UUID rubricId);
}

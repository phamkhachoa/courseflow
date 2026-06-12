package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.GradeDistribution;
import edu.courseflow.analytics.model.GradeDistributionId;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GradeDistributionRepository extends JpaRepository<GradeDistribution, GradeDistributionId> {

    List<GradeDistribution> findByCourseIdOrderByGradeBandAsc(UUID courseId);
}

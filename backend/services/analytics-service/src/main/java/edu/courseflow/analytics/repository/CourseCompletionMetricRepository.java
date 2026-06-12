package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.CourseCompletionMetric;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CourseCompletionMetricRepository extends JpaRepository<CourseCompletionMetric, UUID> {
}

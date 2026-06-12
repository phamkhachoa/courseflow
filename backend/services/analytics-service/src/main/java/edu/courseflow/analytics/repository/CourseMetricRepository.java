package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.CourseMetric;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CourseMetricRepository extends JpaRepository<CourseMetric, UUID> {
}

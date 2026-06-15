package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.CourseCompletionMetric;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface CourseCompletionMetricRepository extends JpaRepository<CourseCompletionMetric, UUID> {

    @Query("""
            select metric
            from CourseCompletionMetric metric
            order by metric.updatedAt asc, metric.courseId asc
            """)
    List<CourseCompletionMetric> exportSnapshot(Pageable pageable);
}

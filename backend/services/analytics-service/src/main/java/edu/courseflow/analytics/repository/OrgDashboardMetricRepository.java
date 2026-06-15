package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.OrgDashboardMetric;
import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface OrgDashboardMetricRepository extends JpaRepository<OrgDashboardMetric, String> {

    @Query("""
            select metric
            from OrgDashboardMetric metric
            order by metric.updatedAt asc, metric.orgId asc
            """)
    List<OrgDashboardMetric> exportSnapshot(Pageable pageable);
}
